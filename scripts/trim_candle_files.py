#!/usr/bin/env python3
"""
Trim candles.db tables to MAX_CANDLES rows per token per timeframe.
Keeps the most recent candles (highest ts) — discards oldest.

MTF-MACD MACD params: max slow=65, signal=28, need slow+sig=93 previous bars.
With 5-bar buffer: need 98 candles. MAX_CANDLES=500 for 4H gives 83 days coverage.
For 1H: slow(65)+sig(28)=93 prev bars, need 98 total. MAX_CANDLES=1500 = 62 days.
For 15m: 500 candles = 5.2 days, enough for z-score percentile computation.
For 1m: 1500 candles = 1 day, enough for short-term fallbacks.

Run via: python3 trim_candle_files.py [--dry-run]
"""
import sqlite3, sys, os, argparse

CANDLES_DB = '/root/.hermes/data/candles.db'

# Per-timeframe trim limits (keep N most recent candles per token):
# MTF-MACD 4H: 500 candles = 83 days — enough for 90d backtest (540 4H bars needed)
# MTF-MACD 1H: 1500 candles = 62 days
# z-score 15m: 1000 candles = 10.4 days
# fallback 1m: 1500 candles = 1 day
MAX_CANDLES = {
    '1m':  1500,
    '15m': 1000,
    '1h':  1500,
    '4h':  500,
}
FALLBACK_MAX = 500

def get_tf_tables():
    """Return {interval: table_name} for all candle tables in candles.db."""
    return {
        '1m':  'candles_1m',
        '15m': 'candles_15m',
        '1h':  'candles_1h',
        '4h':  'candles_4h',
    }

def trim_table(conn, table, max_allowed, dry_run=False):
    """Trim a single table: keep max_allowed newest rows per token."""
    c = conn.cursor()

    # Get count per token
    c.execute(f"SELECT token, COUNT(*) FROM {table} GROUP BY token")
    rows = c.fetchall()
    if not rows:
        return 0

    total_saved = 0
    for token, count in rows:
        if count <= max_allowed:
            continue

        # Find the threshold ts: keep the newest max_allowed rows
        c.execute(f"""
            SELECT ts FROM {table}
            WHERE token=?
            ORDER BY ts DESC
            LIMIT 1 OFFSET {max_allowed}
        """, (token,))
        row = c.fetchone()
        if not row:
            continue
        threshold_ts = row[0]

        if dry_run:
            print(f"  [DRY]  {table}/{token}: {count} -> {max_allowed}")
        else:
            c.execute(f"""
                DELETE FROM {table}
                WHERE token=? AND ts < ?
            """, (token, threshold_ts))
            saved = count - max_allowed
            total_saved += saved
            if saved > 0:
                print(f"  [TRIM] {table}/{token}: {count} -> {max_allowed} (saved {saved})")

    return total_saved

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if not os.path.exists(CANDLES_DB):
        print(f'Candles DB not found: {CANDLES_DB}')
        return

    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")

    tables = get_tf_tables()

    print(f'Candle trimmer — MAX_CANDLES={MAX_CANDLES}')
    print(f'{"[DRY RUN] " if args.dry_run else ""}Trimming {CANDLES_DB}...\n')

    total_saved = 0
    for tf, table in tables.items():
        max_allowed = MAX_CANDLES.get(tf, FALLBACK_MAX)
        print(f'Trimming {table} (max {max_allowed} per token)...')
        saved = trim_table(conn, table, max_allowed, dry_run=args.dry_run)
        total_saved += saved

    conn.commit()
    conn.close()

    print(f'\nDone. Total rows saved: {total_saved}')

if __name__ == '__main__':
    main()
