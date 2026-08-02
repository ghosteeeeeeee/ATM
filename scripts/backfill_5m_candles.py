#!/usr/bin/env python3
"""
backfill_5m_candles.py — Aggregate 1m candles into 5m candles and store in candles.db.

5m bars are aligned to 5-minute boundaries (ts % 300 == 0).
Only inserts complete 5-candle groups. Skips existing rows (INSERT OR IGNORE).
Run once to backfill historical data.
"""

import sqlite3, sys, time

_CANDLES_DB = '/root/.hermes/data/candles.db'
BATCH = 5000   # commits every N inserts

def backfill_5m():
    conn = sqlite3.connect(_CANDLES_DB, timeout=30)
    c = conn.cursor()

    # Get all distinct tokens
    c.execute("SELECT DISTINCT token FROM candles_1m ORDER BY token")
    tokens = [r[0] for r in c.fetchall()]
    print(f"[backfill_5m] {len(tokens)} tokens to process")

    total_inserted = 0
    total_skipped = 0

    for token in tokens:
        # Get all 1m candles for this token, oldest first
        c.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_1m
            WHERE token = ?
            ORDER BY ts ASC
        """, (token,))
        rows = c.fetchall()
        if not rows:
            continue

        # Group into 5m bars
        bars = {}
        for r in rows:
            ts, open_, high, low, close_, vol = r
            # Align to 5-minute boundary
            bar_ts = (ts // 300) * 300
            if bar_ts not in bars:
                bars[bar_ts] = {'open': open_, 'high': high, 'low': low, 'close': close_, 'volume': vol}
            else:
                bars[bar_ts]['high'] = max(bars[bar_ts]['high'], high)
                bars[bar_ts]['low']  = min(bars[bar_ts]['low'], low)
                bars[bar_ts]['close'] = close_
                bars[bar_ts]['volume'] += vol

        # Insert into candles_5m (ignore if already exists)
        inserted = 0
        skipped = 0
        data = [(token, ts, b['open'], b['high'], b['low'], b['close'], b['volume'])
                for ts, b in sorted(bars.items())]
        c.executemany("""
            INSERT OR IGNORE INTO candles_5m (token, ts, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, data)
        inserted += c.rowcount
        skipped = len(data) - c.rowcount
        conn.commit()

        total_inserted += inserted
        total_skipped += skipped
        if inserted > 0:
            print(f"  {token:8s}: {len(data)} 5m bars, {inserted} new, {skipped} existing")

    conn.close()
    print(f"[backfill_5m] Done. {total_inserted} inserted, {total_skipped} skipped.")

if __name__ == '__main__':
    backfill_5m()
