#!/usr/bin/env python3
"""
backfill_candles.py — One-shot backfill of historical 15m/1h/4h candles from price_history.

Run: python3 /root/.hermes/scripts/backfill_candles.py

This script is idempotent — re-running it produces the same result.
It only writes closed windows (is_closed=1) and leaves developing candles untouched.
Takes ~40 min to complete (sequential for all TFs). Run in background:
  nohup python3 /root/.hermes/scripts/backfill_candles.py &
"""
import sys, os, time, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
from paths import STATIC_DB, CANDLES_DB


def backfill_tf(ph_conn, candle_conn, tf_seconds: int, table: str, chunk_hours: int = 24):
    """
    Backfill all historical closed windows for one timeframe.

    Chunks the backfill into time ranges to avoid long write transactions.
    Each chunk commits independently so a crash only loses one chunk.

    Args:
        tf_seconds: window size in seconds
        table: candles table name
        chunk_hours: size of each backfill chunk in hours (default 24)
    """
    ph_cur = ph_conn.cursor()
    cc = candle_conn.cursor()

    # Get the oldest and newest price_history timestamps
    row = ph_cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM price_history").fetchone()
    if not row or not row[0]:
        print(f'  [{table}] No price_history data')
        return
    oldest_ts, newest_ts = row
    print(f'  [{table}] price_history spans {time.strftime("%Y-%m-%d %H:%M", time.localtime(oldest_ts))} '
          f'to {time.strftime("%Y-%m-%d %H:%M", time.localtime(newest_ts))}')

    # Get last already-computed window
    row = cc.execute(f"SELECT MAX(ts) FROM {table} WHERE is_closed=1").fetchone()
    last_computed = row[0] if row and row[0] else 0
    if last_computed:
        start_ts = last_computed + tf_seconds
        print(f'  [{table}] Already has data up to {time.strftime("%H:%M", time.localtime(last_computed))}, backfilling from there')
    else:
        # No data at all — start from oldest price_history, rounded up to first complete window
        start_ts = ((oldest_ts // tf_seconds) + 1) * tf_seconds
        print(f'  [{table}] No existing data, starting from {time.strftime("%H:%M", time.localtime(start_ts))}')

    end_ts = newest_ts - tf_seconds  # last closed window
    if start_ts >= end_ts:
        print(f'  [{table}] Nothing to backfill')
        return

    total_windows = (end_ts - start_ts) // tf_seconds + 1
    print(f'  [{table}] Backfilling {total_windows:,} windows in {chunk_hours}h chunks...')

    chunk_seconds = chunk_hours * 3600
    chunks_done = 0
    total_rows = 0
    t0 = time.time()

    while start_ts < end_ts:
        chunk_end = min(start_ts + chunk_seconds, end_ts) + tf_seconds

        rows = ph_cur.execute(f"""
            WITH windowed AS (
                SELECT
                    token,
                    ((timestamp / {tf_seconds}) * {tf_seconds}) AS window_ts,
                    price,
                    timestamp,
                    ROW_NUMBER() OVER (
                        PARTITION BY token, ((timestamp / {tf_seconds}) * {tf_seconds})
                        ORDER BY timestamp
                    ) AS rn,
                    COUNT(*) OVER (
                        PARTITION BY token, ((timestamp / {tf_seconds}) * {tf_seconds})
                    ) AS cnt
                FROM price_history
                WHERE timestamp >= {start_ts}
                  AND timestamp < {chunk_end}
            ),
            agg AS (
                SELECT
                    token, window_ts,
                    MIN(price) AS low,
                    MAX(price) AS high,
                    SUM(cnt) AS bar_count
                FROM windowed
                GROUP BY token, window_ts
            ),
            first_last AS (
                SELECT w.token, w.window_ts, w.price AS close_price
                FROM windowed w
                INNER JOIN (
                    SELECT token, window_ts, MAX(timestamp) AS max_ts
                    FROM windowed GROUP BY token, window_ts
                ) f ON w.token = f.token AND w.window_ts = f.window_ts AND w.timestamp = f.max_ts
            )
            SELECT
                a.token, a.window_ts,
                (SELECT price FROM windowed w2
                 WHERE w2.token=a.token AND w2.window_ts=a.window_ts AND w2.rn=1
                 LIMIT 1) AS open_price,
                a.high, a.low, f.close_price, a.bar_count
            FROM agg a
            JOIN first_last f USING (token, window_ts)
            WHERE a.bar_count >= 4
            ORDER BY a.token, a.window_ts
        """).fetchall()

        for (token, window_ts, open_px, high, low, close_px, bar_count) in rows:
            cc.execute(f"""
                INSERT OR IGNORE INTO {table}
                    (token, ts, open, high, low, close, volume, is_closed)
                VALUES (?, ?, ?, ?, ?, ?, 0, 1)
            """, (token, window_ts, open_px, high, low, close_px))

        cc.commit()
        total_rows += len(rows)
        chunks_done += 1
        elapsed = time.time() - t0

        # Progress report
        windows_done = (start_ts - (last_computed + tf_seconds if last_computed else start_ts)) // tf_seconds + chunks_done
        pct = min(100, windows_done / max(1, total_windows) * 100)
        rate = total_rows / elapsed if elapsed > 0 else 0
        eta = (total_windows - windows_done) / (windows_done / elapsed) if windows_done > 0 else 0

        print(f'  [{table}] chunk {chunks_done}: {len(rows):,} rows, '
              f'total={total_rows:,} ({pct:.0f}%) '
              f'[{time.strftime("%H:%M", time.localtime(start_ts))}–{time.strftime("%H:%M", time.localtime(chunk_end))}] '
              f'ETA={eta/60:.0f}m')

        start_ts = chunk_end

    print(f'  [{table}] Done: {total_rows:,} candles in {time.time()-t0:.0f}s')


def main():
    t0 = time.time()
    print(f'=== Backfill candles from price_history ===')
    print(f'Started: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    ph_conn = sqlite3.connect(STATIC_DB, timeout=60)
    ph_conn.execute("PRAGMA journal_mode=WAL")
    candle_conn = sqlite3.connect(CANDLES_DB, timeout=60)
    candle_conn.execute("PRAGMA journal_mode=WAL")

    try:
        backfill_tf(ph_conn, candle_conn, 900,  'candles_15m', chunk_hours=24)
        print()
        backfill_tf(ph_conn, candle_conn, 3600, 'candles_1h',  chunk_hours=48)
        print()
        backfill_tf(ph_conn, candle_conn, 14400,'candles_4h',  chunk_hours=96)
    finally:
        ph_conn.close()
        candle_conn.close()

    print()
    print(f'=== Complete in {(time.time()-t0)/60:.1f} minutes ===')


if __name__ == '__main__':
    main()
