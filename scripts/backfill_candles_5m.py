#!/usr/bin/env python3
"""
backfill_candles_5m.py — Backfill candles_5m from candles_1m.

Aggregates 1m candles into 5m bars to extend candles_5m retention.
No API calls needed — uses local candles_1m data (957 days available).

Usage:
    python3 scripts/backfill_candles_5m.py [--days 30]
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CANDLES_DB


def backfill_candles_5m(days: int = 30):
    """Aggregate candles_1m into candles_5m for the specified number of days."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=30)
        cur = conn.cursor()
        
        # Calculate cutoff timestamp
        cutoff_ts = int(datetime.now().timestamp()) - (days * 24 * 3600)
        
        # Get distinct tokens from candles_1m
        cur.execute("""
            SELECT DISTINCT token FROM candles_1m 
            WHERE ts >= ? AND is_closed = 1
        """, (cutoff_ts,))
        tokens = [row[0] for row in cur.fetchall()]
        print(f"Backfilling {len(tokens)} tokens for {days} days...")
        
        total_inserted = 0
        for token in tokens:
            # Get 1m candles for this token
            cur.execute("""
                SELECT ts, open, high, low, close, volume
                FROM candles_1m
                WHERE token = ? AND ts >= ? AND is_closed = 1
                ORDER BY ts ASC
            """, (token, cutoff_ts))
            rows = cur.fetchall()
            
            if not rows:
                continue
            
            # Aggregate into 5m bars
            current_bucket = None
            bucket_data = None
            inserted = 0
            
            for ts, open_px, high, low, close_px, volume in rows:
                # 5-minute bucket: floor to 5-minute boundary
                bucket_ts = (ts // 300) * 300
                
                if current_bucket is None or bucket_ts != current_bucket:
                    # Flush previous bucket
                    if bucket_data is not None:
                        cur.execute("""
                            INSERT OR REPLACE INTO candles_5m 
                            (token, ts, open, high, low, close, volume, is_closed)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                        """, (token, current_bucket, bucket_data['open'], 
                              bucket_data['high'], bucket_data['low'],
                              bucket_data['close'], bucket_data['volume']))
                        inserted += 1
                    
                    # Start new bucket
                    current_bucket = bucket_ts
                    bucket_data = {
                        'open': open_px,
                        'high': high,
                        'low': low,
                        'close': close_px,
                        'volume': volume
                    }
                else:
                    # Update current bucket
                    bucket_data['high'] = max(bucket_data['high'], high)
                    bucket_data['low'] = min(bucket_data['low'], low)
                    bucket_data['close'] = close_px
                    bucket_data['volume'] += volume
            
            # Flush last bucket
            if bucket_data is not None:
                cur.execute("""
                    INSERT OR REPLACE INTO candles_5m 
                    (token, ts, open, high, low, close, volume, is_closed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (token, current_bucket, bucket_data['open'],
                      bucket_data['high'], bucket_data['low'],
                      bucket_data['close'], bucket_data['volume']))
                inserted += 1
            
            total_inserted += inserted
            if inserted > 0:
                print(f"  {token}: {inserted} 5m candles")
        
        conn.commit()
        print(f"\nBackfill complete: {total_inserted} 5m candles inserted")
        
        # Check final state
        cur.execute("SELECT MIN(ts), MAX(ts), COUNT(*) FROM candles_5m WHERE is_closed = 1")
        min_ts, max_ts, count = cur.fetchone()
        if min_ts and max_ts:
            min_dt = datetime.fromtimestamp(min_ts).strftime('%Y-%m-%d')
            max_dt = datetime.fromtimestamp(max_ts).strftime('%Y-%m-%d')
            print(f"candles_5m span: {min_dt} → {max_dt} ({count} rows)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Backfill candles_5m from candles_1m')
    parser.add_argument('--days', type=int, default=30, help='Days to backfill (default: 30)')
    args = parser.parse_args()
    
    backfill_candles_5m(args.days)
