#!/usr/bin/env python3
"""
_aggregate_1m.py — Standalone 1m candle aggregator.

Reads from signals_hermes.db price_history (seconds-level ticks),
aggregates into candles_hermes.db candles_1m.

Self-healing: fills any missed closed windows, writes developing candle
for the open window when >= 1 bar is available.

Architecture: NO Binance API calls. Fully derived from local price_history.
Candles are always current because price_history is written every 1 minute
by hermes-price-collector.timer.

Timer: hermes-1m-candle.timer (every 1 min)
"""
import sys, os, time, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
from paths import STATIC_DB, CANDLES_DB

TF_SECONDS = 60
TABLE = 'candles_1m'
# price_history ticks are ~155s apart; 1 tick is sufficient for a valid 1m candle
MIN_BARS_FOR_CLOSED = 1
MIN_BARS_FOR_DEVELOPING = 1


def migrate_is_closed():
    """Add is_closed=1 to all existing candles_1m rows that lack the column."""
    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN is_closed INTEGER DEFAULT 1")
        conn.execute(f"UPDATE {TABLE} SET is_closed = 1 WHERE is_closed IS NULL")
        conn.commit()
        print(f"[migrate] Added is_closed=1 to {TABLE}")
    except Exception as e:
        if 'duplicate column' not in str(e).lower():
            print(f"[migrate] {TABLE}: {e}")
    conn.close()


def aggregate_1m():
    ph_conn = sqlite3.connect(STATIC_DB, timeout=30)
    ph_conn.execute("PRAGMA journal_mode=WAL")
    candle_conn = sqlite3.connect(CANDLES_DB, timeout=60)
    candle_conn.execute("PRAGMA journal_mode=WAL")
    candle_conn.execute("PRAGMA synchronous=NORMAL")

    tf = TF_SECONDS

    # Per-token last closed window (safe from developing candle corruption)
    candle_cur = candle_conn.cursor()
    candle_cur.execute(f"""
        SELECT token, MAX(ts) FROM {TABLE}
        WHERE is_closed = 1
        GROUP BY token
    """)
    last_computed = {r[0]: r[1] for r in candle_cur.fetchall()}

    candle_cur.execute(f"""
        SELECT token, MIN(ts) FROM {TABLE}
        WHERE is_closed = 0
        GROUP BY token
    """)
    first_dev = {r[0]: r[1] for r in candle_cur.fetchall()}

    last_closed_dict = {}
    for token in set(list(last_computed.keys()) + list(first_dev.keys())):
        dev_ts = first_dev.get(token)
        lc = last_computed.get(token, 0)
        if not lc:
            last_closed_dict[token] = 0
            continue
        if dev_ts is None:
            last_closed_dict[token] = lc
            continue
        t = dev_ts - tf
        while t > lc:
            t -= tf
        t += tf
        last_closed_dict[token] = t

    # Clock from price_history
    ph_cur = ph_conn.cursor()
    clock_row = ph_cur.execute("SELECT MAX(timestamp) FROM price_history").fetchone()
    if not clock_row or not clock_row[0]:
        print("[1m] No price_history data")
        ph_conn.close()
        candle_conn.close()
        return
    now = clock_row[0]
    current_window = (now // tf) * tf
    last_closed = current_window - tf

    filled = 0
    for token, token_last_closed in last_closed_dict.items():
        if token_last_closed is None or token_last_closed <= 0:
            continue
        if token_last_closed >= last_closed:
            continue

        ph_cur.execute(f"""
            WITH windowed AS (
                SELECT
                    ((timestamp / {tf}) * {tf}) AS window_ts,
                    MIN(timestamp) AS first_ts,
                    MAX(timestamp) AS last_ts,
                    MIN(price) AS low,
                    MAX(price) AS high,
                    COUNT(*) AS bar_count
                FROM price_history
                WHERE token = :token
                  AND timestamp > :token_last_closed
                  AND timestamp <= :last_closed
                GROUP BY window_ts
            )
            SELECT window_ts, first_ts, last_ts, low, high, bar_count
            FROM windowed
            WHERE bar_count >= {MIN_BARS_FOR_CLOSED}
            ORDER BY window_ts
        """, {'token': token, 'token_last_closed': token_last_closed, 'last_closed': last_closed})

        for (window_ts, first_ts, last_ts, low, high, bar_count) in ph_cur.fetchall():
            open_row = ph_cur.execute(
                "SELECT price FROM price_history WHERE token=? AND timestamp=? LIMIT 1",
                (token, first_ts)
            ).fetchone()
            close_row = ph_cur.execute(
                "SELECT price FROM price_history WHERE token=? AND timestamp=? LIMIT 1",
                (token, last_ts)
            ).fetchone()
            if open_row and close_row:
                candle_cur.execute(f"""
                    INSERT OR REPLACE INTO {TABLE}
                        (token, ts, open, high, low, close, volume, is_closed)
                    VALUES (?, ?, ?, ?, ?, ?, 0, 1)
                """, (token, window_ts, open_row[0], high, low, close_row[0]))
                filled += 1

    # Developing candle
    dev_rows = ph_cur.execute(f"""
        WITH windowed AS (
            SELECT
                token,
                ((timestamp / {tf}) * {tf}) AS window_ts,
                price, timestamp,
                ROW_NUMBER() OVER (
                    PARTITION BY token, ((timestamp / {tf}) * {tf})
                    ORDER BY timestamp
                ) AS rn,
                COUNT(*) OVER (
                    PARTITION BY token, ((timestamp / {tf}) * {tf})
                ) AS cnt
            FROM price_history
            WHERE ((timestamp / {tf}) * {tf}) = {current_window}
        ),
        agg AS (
            SELECT token,
                MIN(price) AS low,
                MAX(price) AS high,
                MAX(cnt) AS bar_count
            FROM windowed GROUP BY token
        ),
        first_last AS (
            SELECT w.token, w.price AS close_price
            FROM windowed w
            INNER JOIN (
                SELECT token, MAX(timestamp) AS max_ts
                FROM windowed GROUP BY token
            ) f ON w.token = f.token AND w.timestamp = f.max_ts
        )
        SELECT
            a.token,
            (SELECT price FROM windowed WHERE token=a.token AND window_ts={current_window} AND rn=1 LIMIT 1) AS open_price,
            a.high, a.low, f.close_price, a.bar_count
        FROM agg a
        JOIN first_last f ON a.token = f.token
        WHERE a.bar_count >= {MIN_BARS_FOR_DEVELOPING}
    """).fetchall()

    dev_written = 0
    for (token, open_px, high, low, close_px, bar_count) in dev_rows:
        exists = candle_cur.execute(
            f"SELECT is_closed FROM {TABLE} WHERE token=? AND ts=?",
            (token, current_window)
        ).fetchone()
        if exists and exists[0] == 1:
            continue
        candle_cur.execute(f"""
            INSERT OR REPLACE INTO {TABLE}
                (token, ts, open, high, low, close, volume, is_closed)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """, (token, current_window, open_px, high, low, close_px))
        dev_written += 1

    candle_conn.commit()
    ph_conn.close()
    candle_conn.close()

    last_dt = time.strftime('%H:%M:%S', time.localtime(last_closed)) if filled else 'N/A'
    print(f"[1m] filled={filled} closed windows, dev={dev_written} tokens, clock={time.strftime('%H:%M:%S', time.localtime(now))}, last_closed={last_closed} ({last_dt})")


if __name__ == '__main__':
    migrate_is_closed()
    aggregate_1m()
