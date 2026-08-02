#!/usr/bin/env python3
"""
backfill_5m_from_ph.py — Aggregate fresh 1m price_history bars into 5m candles
for the gap period between last candles_5m bar and now.

Unlike backfill_5m_candles.py (which reads from stale candles_1m), this reads
from signals_hermes.db price_history which is continuously updated.

Run: python3 backfill_5m_from_ph.py [--token TOKEN]
"""
import sqlite3, sys, time, datetime, argparse

_CANDLES_DB = '/root/.hermes/data/candles.db'
_PRICES_DB  = '/root/.hermes/data/signals_hermes.db'
BATCH = 5000

def backfill_5m_from_ph(token=None):
    conn_c = sqlite3.connect(_CANDLES_DB, timeout=30)
    conn_p = sqlite3.connect(_PRICES_DB, timeout=30)
    c_c = conn_c.cursor()
    c_p = conn_p.cursor()

    try:
        c_p.execute("SELECT 1 FROM price_history LIMIT 1")
    except sqlite3.OperationalError:
        print("[backfill_5m_from_ph] price_history not found in signals_hermes.db")
        return

    if token:
        tokens = [token]
    else:
        c_c.execute("SELECT DISTINCT token FROM candles_5m ORDER BY token")
        tokens = [r[0] for r in c_c.fetchall()]

    total_inserted = 0
    now_ts = int(time.time())

    for tok in tokens:
        # Last 5m bar in candles_5m
        c_c.execute("SELECT MAX(ts) FROM candles_5m WHERE token=?", (tok,))
        r = c_c.fetchone()
        last_5m_ts = r[0] if r and r[0] else None

        # Get price_history from last_5m_ts to now (or from beginning if no 5m data)
        if last_5m_ts:
            query = """
                SELECT timestamp, price FROM price_history
                WHERE token=? AND timestamp > ?
                ORDER BY timestamp ASC
            """
            params = (tok, last_5m_ts)
        else:
            # No existing 5m data — get from beginning of price_history
            query = """
                SELECT timestamp, price FROM price_history
                WHERE token=?
                ORDER BY timestamp ASC
            """
            params = (tok,)

        c_p.execute(query, params)
        rows = c_p.fetchall()
        if not rows:
            continue

        # Group into 5m bars using price (not OHLCV — price_history only has price)
        bars = {}
        for ts, price in rows:
            bar_ts = (ts // 300) * 300
            if bar_ts not in bars:
                bars[bar_ts] = {'open': price, 'high': price, 'low': price, 'close': price}
            else:
                bars[bar_ts]['high'] = max(bars[bar_ts]['high'], price)
                bars[bar_ts]['low']  = min(bars[bar_ts]['low'], price)
                bars[bar_ts]['close'] = price

        if not bars:
            continue

        # Insert OR IGNORE into candles_5m
        data = [(tok, ts, b['open'], b['high'], b['low'], b['close'], 0.0)
                for ts, b in sorted(bars.items())]

        inserted = 0
        for i in range(0, len(data), BATCH):
            chunk = data[i:i+BATCH]
            c_c.executemany("""
                INSERT OR IGNORE INTO candles_5m (token, ts, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, chunk)
            inserted += c_c.rowcount
            conn_c.commit()

        if inserted > 0:
            mn = datetime.datetime.fromtimestamp(sorted(bars.keys())[0], tz=datetime.timezone.utc).strftime('%m-%d %H:%M')
            mx = datetime.datetime.fromtimestamp(sorted(bars.keys())[-1], tz=datetime.timezone.utc).strftime('%m-%d %H:%M')
            print(f"  {tok:8s}: {len(data)} 5m bars ({mn} -> {mx}), {inserted} new")

        total_inserted += inserted

    conn_c.close()
    conn_p.close()
    print(f"[backfill_5m_from_ph] Done. {total_inserted} bars inserted.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', default=None)
    args = parser.parse_args()
    backfill_5m_from_ph(args.token)
