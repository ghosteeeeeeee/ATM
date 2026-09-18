#!/usr/bin/env python3
"""
Backfill 1m candles for tokens traded before Aug 5, 2026.
Fetches from Binance and inserts into candles.db.

Usage:
    python3 scripts/analysis/backfill_1m_candles.py          # Dry run
    python3 scripts/analysis/backfill_1m_candles.py --fetch   # Actually fetch
"""

import sys, os, time, sqlite3, requests
from datetime import datetime, timezone

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)

from _secrets import BRAIN_DB_DICT

CANDLES_DB = '/root/.hermes/data/candles.db'
BINANCE_BASE = 'https://api.binance.com/api/v3'
REQUEST_DELAY = 0.06  # ~1000 req/min safe

# Import the symbol mapping from existing script
sys.path.insert(0, SCRIPTS_DIR)
from fetch_binance_candles import get_binance_symbol, fetch_binance_klines, insert_candles


def get_tokens_needing_backfill():
    """Get tokens traded before Aug 5 and their date ranges."""
    import psycopg2
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT token, 
               MIN(open_time) as first_trade,
               MAX(open_time) as last_trade,
               COUNT(*) as trades
        FROM trades 
        WHERE status = 'closed' 
          AND open_time < '2026-08-05'
          AND token IS NOT NULL
        GROUP BY token
        ORDER BY trades DESC
    """)
    
    tokens = cur.fetchall()
    cur.close()
    conn.close()
    return tokens


def get_existing_coverage(token):
    """Check what 1m candle data we already have for a token."""
    try:
        conn = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT MIN(ts), MAX(ts), COUNT(*) 
            FROM candles_1m WHERE token = ?
        """, (token.upper(),))
        row = cur.fetchone()
        conn.close()
        if row and row[2] > 0:
            return {
                'min_ts': row[0],
                'max_ts': row[1],
                'count': row[2],
                'min_date': datetime.fromtimestamp(row[0], tz=timezone.utc),
                'max_date': datetime.fromtimestamp(row[1], tz=timezone.utc),
            }
        return None
    except:
        return None


def fetch_token_candles(token, start_dt, end_dt, dry_run=True):
    """Fetch 1m candles for a token from Binance between two dates."""
    symbol = get_binance_symbol(token)
    if not symbol:
        return 0, f"Not on Binance"
    
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    MS_PER_CANDLE = 60_000
    
    if dry_run:
        return 0, f"Would fetch {symbol} from {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"
    
    total_inserted = 0
    current_ms = start_ms
    loops = 0
    
    while current_ms < end_ms:
        loops += 1
        if loops > 500:
            print(f"    Safety stop at 500 loops")
            break
        
        candles = fetch_binance_klines(
            symbol, interval='1m', limit=1000,
            start_time_ms=current_ms, end_time_ms=end_ms
        )
        
        if not candles:
            break
        
        n = insert_candles(token, candles, 'candles_1m')
        total_inserted += n
        
        last_ts_sec = int(candles[-1][0] // 1000)
        if len(candles) < 1000:
            break
        
        current_ms = int(candles[-1][0]) + MS_PER_CANDLE
        time.sleep(REQUEST_DELAY)
    
    return total_inserted, f"inserted {total_inserted} candles"


def main():
    dry_run = '--fetch' not in sys.argv
    
    print("="*70)
    print("1M CANDLE BACKFILL FOR LINREG MA180 ANALYSIS")
    print("="*70)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE FETCH'}")
    print()
    
    tokens = get_tokens_needing_backfill()
    print(f"Tokens traded before Aug 5: {len(tokens)}")
    
    # Check which tokens need backfill
    plan = []
    for token, first_trade, last_trade, trades in tokens:
        symbol = get_binance_symbol(token)
        if not symbol:
            plan.append((token, 'SKIP', 'Not on Binance', 0, trades, None, None))
            continue
        
        coverage = get_existing_coverage(token)
        
        # We need candles from (first_trade - 7 hours for MA180 lookback) to Aug 5
        # MA180 needs 180 minutes = 3 hours, plus buffer
        needed_start = first_trade.replace(tzinfo=timezone.utc) if first_trade.tzinfo is None else first_trade
        needed_start = needed_start - __import__('datetime').timedelta(hours=8)  # 8h buffer for MA180
        
        needed_end = datetime(2026, 8, 5, tzinfo=timezone.utc)
        
        if coverage:
            # Check if we already have data covering the needed range
            if coverage['min_date'] <= needed_start and coverage['max_date'] >= needed_end:
                plan.append((token, 'DONE', f"Already covered ({coverage['count']} candles)", 
                           coverage['count'], trades, None, None))
                continue
            
            # Calculate the gap
            if coverage['min_date'] > needed_start:
                # Need older data
                plan.append((token, 'BACKFILL', f"Need data before {coverage['min_date'].strftime('%Y-%m-%d')}",
                           coverage['count'], trades, needed_start, coverage['min_date']))
            else:
                plan.append((token, 'PARTIAL', f"Have {coverage['count']} candles but gap exists",
                           coverage['count'], trades, None, None))
        else:
            # No data at all
            plan.append((token, 'NEW', f"No candle data",
                       0, trades, needed_start, needed_end))
    
    # Print summary
    print(f"\n{'Token':<12} {'Status':<10} {'Detail':<45} {'Candles':>8} {'Trades':>7}")
    print("-"*90)
    
    fetch_count = 0
    for token, status, detail, candles, trades, start, end in plan:
        print(f"{token:<12} {status:<10} {detail:<45} {candles:>8} {trades:>7}")
        if status in ('BACKFILL', 'NEW'):
            fetch_count += 1
    
    print(f"\nTokens needing fetch: {fetch_count}")
    
    if dry_run:
        print("\nDRY RUN — run with --fetch to actually fetch data.")
        return
    
    # Actually fetch
    print("\nFetching data from Binance...")
    total_inserted = 0
    
    for token, status, detail, candles, trades, start, end in plan:
        if status not in ('BACKFILL', 'NEW'):
            continue
        
        if start is None:
            continue
        
        end_dt = end if end else datetime(2026, 8, 5, tzinfo=timezone.utc)
        
        print(f"\n{token}: fetching from {start.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}...")
        inserted, msg = fetch_token_candles(token, start, end_dt, dry_run=False)
        total_inserted += inserted
        print(f"  → {msg}")
    
    print(f"\n{'='*70}")
    print(f"Total new candles inserted: {total_inserted}")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
