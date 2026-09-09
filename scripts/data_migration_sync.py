#!/usr/bin/env python3
"""
data_migration_sync.py — Full data sync for trades ↔ signals linkage

Fixes:
1. signal_created_at field in trades (never populated)
2. Signal naming convention (dashes vs underscores mismatch)
3. Pump-chain signal_type correction (source vs signal_type bug)

Run: python3 scripts/data_migration_sync.py [--dry-run] [--fix-signal-types] [--fix-created-at]
"""

import psycopg2
import sqlite3
import os
import sys
import json
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
BRAIN_DB = "host=/var/run/postgresql dbname=brain user=postgres password=***"
SIGNALS_DB = "/root/.hermes/data/signals_hermes_runtime.db"
DRY_RUN = '--dry-run' in sys.argv
FIX_SIGNAL_TYPES = '--fix-signal-types' in sys.argv
FIX_CREATED_AT = '--fix-created-at' in sys.argv

# ── Signal name normalization ─────────────────────────────────────────────────
# Maps trade signal names to signals.signal_type names
SIGNAL_NAME_MAP = {
    # pump-chain variants
    'pump-chain+': 'pump-chain',
    'pump-chain-': 'pump-chain',
    'pump_chain+': 'pump-chain',
    'pump_chain-': 'pump-chain',
    'pump_chain': 'pump-chain',
    
    # bb_bounce variants
    'bb-bounce-v2-long+': 'bb_bounce_v2_long',
    'bb-bounce-v2-long-': 'bb_bounce_v2_short',
    'bb_bounce_v2_long+': 'bb_bounce_v2_long',
    'bb_bounce_v2_long-': 'bb_bounce_v2_short',
    'bb-bounce-short+': 'bb_bounce_short',
    'bb-bounce-short-': 'bb_bounce_short',
    'bb_bounce_short+': 'bb_bounce_short',
    'bb_bounce+': 'bb_bounce',
    'bb-bounce-long+': 'bb_bounce_long',
    'bb-bounce-long-': 'bb_bounce_short',
    
    # accel-300 variants
    'accel-300+': 'accel_300',
    'accel-300-': 'accel_300',
    'accel-300-v2-long+': 'accel_300_v2_long',
    'accel-300-v2-long-': 'accel_300_v2_short',
    'accel-300-v2-short+': 'accel_300_v2_short',
    'accel-300-v2-short-': 'accel_300_v2_short',
    'accel-300-v2-long-5m+': 'accel_300_v2_long_5m',
    'accel-300-v3-long+': 'accel_300_v3_long',
    'accel-300-v3-short+': 'accel_300_v3_short',
    'accel-300-v3-short-': 'accel_300_v3_short',
    'inv-accel-300-v2+': 'inverse_accel_300_v2',
    'inv-accel-300-v2-': 'inverse_accel_300_v2',
    
    # tl_break variants
    'tl_break_long': 'tl_break',
    'tl_break_short': 'tl_break',
    'tl_break+': 'tl_break',
    'tl_break-': 'tl_break',
    
    # rs variants
    'rs-s': 'support_resistance',
    'rs-r': 'support_resistance',
    'rs+': 'support_resistance',
    'rs-': 'support_resistance',
    
    # other signals
    'coil-spring+': 'coiled_spring',
    'coil-spring-': 'coiled_spring',
    'coil_spring+': 'coiled_spring',
    'coil_spring-': 'coiled_spring',
    'open-skies+': 'open_skies',
    'open-skies-': 'open_skies',
    'open_skies+': 'open_skies',
    'open_skies-': 'open_skies',
    'mover+': 'mover',
    'mover-': 'mover',
    'ct-hot+': 'coin_tracker_hot',
    'ct-hot-': 'coin_tracker_hot',
    'ema300-dip': 'ema300_dip',
    'ema300-dip-long': 'ema300_dip_long',
    'ema300-dip-short': 'ema300_dip_short',
    'sma20-dip+': 'sma20_dip',
    'sma20-dip-': 'sma20_dip',
    'hl_copy_trader': 'hl_copy_trader',
    'r2-trend-long': 'r2_trend_long',
    'r2-trend-short': 'r2_trend_short',
    'hzscore+': 'hzscore',
    'hzscore-': 'hzscore',
    'hzscore': 'hzscore',
    'continuation+': 'continuation',
    'continuation-': 'continuation',
    'confluence+': 'signal_confluence',
    'confluence-': 'signal_confluence',
    'macd-div+': 'macd_divergence',
    'macd-div-': 'macd_divergence',
    'liq-hunt+': 'liquidation_hunt',
    'liq-hunt-': 'liquidation_hunt',
    'return-exhaustion-short+': 'return_exhaustion_short',
    'spike-exhaustion-short-': 'spike_exhaustion_short',
    'stop-hunt-reversal-long+': 'stop_hunt_reversal_long',
    'counter-flip+': 'counter_flip',
    'counter-flip-': 'counter_flip',
    'gap-300+': 'gap_300',
    'gap-300-': 'gap_300',
    'bb-squeeze+': 'bollinger_squeeze',
    'bb-squeeze-': 'bollinger_squeeze',
    'ma-cross+': 'ma_cross',
    'ma-cross-': 'ma_cross',
    'ma-cross-5m+': 'ma_cross_5m',
    'ma-cross-5m-': 'ma_cross_5m',
    'range-reversion-long+': 'range_reversion',
    'range-reversion-short-': 'range_reversion',
    'volume-breakout-long+': 'volume_breakout',
    'volume-breakout-short-': 'volume_breakout',
    'neutral-sniper-long+': 'neutral_sniper',
    'neutral-sniper-short-': 'neutral_sniper',
}


def normalize_signal_name(signal_name):
    """Normalize trade signal name to signals.signal_type format."""
    if not signal_name:
        return signal_name
    
    # Strip trailing digits (level numbers like rs-s386, rs-r1774)
    import re
    normalized = re.sub(r'\d+$', '', signal_name)
    
    # Check exact match first
    if normalized in SIGNAL_NAME_MAP:
        return SIGNAL_NAME_MAP[normalized]
    
    # Try without +/- suffix
    stripped = normalized.rstrip('+-')
    if stripped in SIGNAL_NAME_MAP:
        return SIGNAL_NAME_MAP[stripped]
    
    # Try with underscores instead of dashes
    underscored = normalized.replace('-', '_')
    if underscored in SIGNAL_NAME_MAP:
        return SIGNAL_NAME_MAP[underscored]
    
    # Return normalized version
    return underscored


def fix_signal_created_at(pg_conn, sl_conn):
    """Fix signal_created_at field in trades table by matching to signals."""
    print("\n=== FIX 1: signal_created_at ===")
    
    pg_cur = pg_conn.cursor()
    sl_cur = sl_conn.cursor()
    
    # Get trades without signal_created_at
    pg_cur.execute('''
        SELECT id, token, signal, direction, open_time
        FROM trades
        WHERE signal_created_at IS NULL
        AND open_time > '2026-09-01'
        ORDER BY open_time
    ''')
    trades = pg_cur.fetchall()
    
    print(f"Trades to fix: {len(trades)}")
    
    fixed = 0
    for trade_id, token, signal, direction, open_time in trades:
        trade_dt = open_time if isinstance(open_time, datetime) else datetime.strptime(str(open_time)[:19], '%Y-%m-%d %H:%M:%S')
        
        # Find matching signal in SQLite
        sl_cur.execute('''
            SELECT signal_type, source, created_at
            FROM signals
            WHERE token = ? AND direction = ?
            AND created_at IS NOT NULL
            AND created_at <= ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (token, direction, trade_dt.strftime('%Y-%m-%d %H:%M:%S')))
        
        row = sl_cur.fetchone()
        if row:
            sig_type, sig_source, sig_created = row
            if sig_created:
                if not DRY_RUN:
                    pg_cur.execute('''
                        UPDATE trades SET signal_created_at = %s
                        WHERE id = %s
                    ''', (sig_created, trade_id))
                fixed += 1
                if fixed <= 5:  # Show first 5
                    print(f"  Fixed {trade_id} {token}: signal_created_at = {sig_created}")
    
    if not DRY_RUN:
        pg_conn.commit()
    
    print(f"Fixed: {fixed}/{len(trades)}")
    pg_cur.close()
    sl_cur.close()


def fix_signal_types(pg_conn, sl_conn):
    """Fix signal_type in trades table by normalizing names."""
    print("\n=== FIX 2: Signal type normalization ===")
    
    pg_cur = pg_conn.cursor()
    
    # Get all trades with signal types
    pg_cur.execute('''
        SELECT id, token, signal, direction
        FROM trades
        WHERE signal IS NOT NULL AND signal != ''
        AND open_time > '2026-09-01'
    ''')
    trades = pg_cur.fetchall()
    
    print(f"Trades to normalize: {len(trades)}")
    
    fixed = 0
    for trade_id, token, signal, direction in trades:
        normalized = normalize_signal_name(signal)
        if normalized != signal:
            if not DRY_RUN:
                pg_cur.execute('''
                    UPDATE trades SET signal = %s
                    WHERE id = %s
                ''', (normalized, trade_id))
            fixed += 1
            if fixed <= 10:  # Show first 10
                print(f"  Fixed {trade_id} {token}: '{signal}' → '{normalized}'")
    
    if not DRY_RUN:
        pg_conn.commit()
    
    print(f"Fixed: {fixed}/{len(trades)}")
    pg_cur.close()


def verify_data_quality(pg_conn):
    """Verify data quality after fixes."""
    print("\n=== DATA QUALITY VERIFICATION ===")
    
    pg_cur = pg_conn.cursor()
    
    # Check signal_created_at population
    pg_cur.execute('''
        SELECT COUNT(*) FROM trades
        WHERE open_time > '2026-09-01'
    ''')
    total = pg_cur.fetchone()[0]
    
    pg_cur.execute('''
        SELECT COUNT(*) FROM trades
        WHERE open_time > '2026-09-01'
        AND signal_created_at IS NOT NULL
    ''')
    with_created_at = pg_cur.fetchone()[0]
    
    print(f"signal_created_at: {with_created_at}/{total} ({with_created_at/total*100:.1f}%)")
    
    # Check signal type distribution
    pg_cur.execute('''
        SELECT signal, COUNT(*) as cnt
        FROM trades
        WHERE open_time > '2026-09-01'
        AND signal IS NOT NULL AND signal != ''
        GROUP BY signal
        ORDER BY cnt DESC
        LIMIT 15
    ''')
    rows = pg_cur.fetchall()
    print(f"\nTop signal types:")
    for r in rows:
        print(f"  {r[0]:30s} {r[1]:5d}")
    
    pg_cur.close()


def main():
    print("=" * 60)
    print("DATA MIGRATION SYNC")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"Fix signal types: {FIX_SIGNAL_TYPES}")
    print(f"Fix created_at: {FIX_CREATED_AT}")
    
    # Connect to databases
    pg_conn = psycopg2.connect(BRAIN_DB)
    sl_conn = sqlite3.connect(f"file:{SIGNALS_DB}?mode=ro", uri=True, timeout=10)
    
    try:
        if FIX_SIGNAL_TYPES:
            fix_signal_types(pg_conn, sl_conn)
        
        if FIX_CREATED_AT:
            fix_signal_created_at(pg_conn, sl_conn)
        
        if not FIX_SIGNAL_TYPES and not FIX_CREATED_AT:
            print("\nNo fixes specified. Use --fix-signal-types and/or --fix-created-at")
        
        verify_data_quality(pg_conn)
        
    finally:
        pg_conn.close()
        sl_conn.close()
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == '__main__':
    main()
