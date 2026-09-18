#!/usr/bin/env python3
"""
Backtest: Coin Tracker Composite Score Signal Edge
===================================================
Tests whether trades with high composite scores from coin_tracker
have higher win rates than trades with low composite scores.

Also tests wyckoff_phase accumulation vs non-accumulation for LONG trades.
"""

import sys
import os
import json
import sqlite3
import psycopg2
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from paths import HERMES_DATA

CT_DB = os.path.join(HERMES_DATA, "coin_tracker.db")
OUTPUT = os.path.join(HERMES_DATA, "backtest_composite.json")

# PostgreSQL connection
PG_CONFIG = {
    "host": "/var/run/postgresql",
    "database": "brain",
    "user": "postgres",
}


def get_pg_trades():
    """Fetch all closed trades with open_time and PnL."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            id, 
            LOWER(token) as token, 
            direction, 
            open_time, 
            close_time, 
            pnl_pct, 
            signal,
            entry_price,
            exit_price,
            leverage
        FROM trades 
        WHERE status = 'closed' 
          AND pnl_pct IS NOT NULL 
          AND open_time IS NOT NULL
        ORDER BY open_time
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_coin_tables(ct_conn):
    """Get list of coin_ tables in coin_tracker.db."""
    cur = ct_conn.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE 'coin_%'
    """)
    tables = [r[0] for r in cur.fetchall()]
    cur.close()
    return tables


def get_closest_score(ct_conn, table_name, target_ts):
    """
    Get health_score (composite) and wyckoff_phase from coin table
    closest to target_ts (at or before).
    """
    cur = ct_conn.cursor()
    try:
        cur.execute(f"""
            SELECT ts, health_score, wyckoff_phase, trend_quality, 
                   setup_score, rsi_14, macd_hist, trend_direction
            FROM [{table_name}]
            WHERE ts <= ? AND health_score IS NOT NULL
            ORDER BY ts DESC
            LIMIT 1
        """, (target_ts,))
        row = cur.fetchone()
        return row
    except Exception as e:
        return None
    finally:
        cur.close()


def bucket_composite(score):
    """Bucket composite score into 25-point ranges."""
    if score is None:
        return "no_data"
    if score < 25:
        return "0-25"
    elif score < 50:
        return "25-50"
    elif score < 75:
        return "50-75"
    else:
        return "75-100"


def run_backtest():
    print("=" * 70)
    print("BACKTEST: Coin Tracker Composite Score Signal Edge")
    print("=" * 70)
    
    # 1. Load trades
    print("\n[1/4] Loading trades from PostgreSQL...")
    trades = get_pg_trades()
    print(f"  Total closed trades: {len(trades)}")
    
    # 2. Open coin_tracker.db
    print("\n[2/4] Opening coin_tracker.db...")
    ct_conn = sqlite3.connect(CT_DB)
    coin_tables = get_coin_tables(ct_conn)
    print(f"  Coin tables found: {len(coin_tables)}")
    
    # Build lookup: lowercase symbol -> table name
    symbol_to_table = {}
    for t in coin_tables:
        # coin_HYPE -> hype
        sym = t.replace("coin_", "").lower()
        symbol_to_table[sym] = t
    
    # 3. Match trades to composite scores
    print("\n[3/4] Matching trades to coin_tracker scores...")
    matched = []
    unmatched_tokens = set()
    no_data_tokens = set()
    
    for i, trade in enumerate(trades):
        trade_id, token, direction, open_time, close_time, pnl_pct, signal, entry_price, exit_price, leverage = trade
        
        # Convert open_time to Unix timestamp
        if open_time is None:
            continue
        open_ts = int(open_time.replace(tzinfo=timezone.utc).timestamp())
        
        # Find matching coin table
        table = symbol_to_table.get(token)
        if table is None:
            unmatched_tokens.add(token)
            continue
        
        # Get closest score at or before trade entry
        row = get_closest_score(ct_conn, table, open_ts)
        if row is None:
            no_data_tokens.add(token)
            continue
        
        ts, composite, wyckoff_phase, trend_quality, setup_score, rsi_14, macd_hist, trend_direction = row
        
        # Calculate staleness (how old was the data at entry)
        staleness_min = (open_ts - ts) / 60.0 if ts else None
        
        matched.append({
            'trade_id': trade_id,
            'token': token,
            'direction': direction,
            'open_time': open_time.isoformat() if open_time else None,
            'close_time': close_time.isoformat() if close_time else None,
            'pnl_pct': float(pnl_pct),
            'signal': signal,
            'entry_price': float(entry_price) if entry_price else None,
            'exit_price': float(exit_price) if exit_price else None,
            'leverage': leverage,
            'composite': composite,
            'composite_bucket': bucket_composite(composite),
            'wyckoff_phase': wyckoff_phase or 'none',
            'trend_quality': trend_quality,
            'setup_score': setup_score,
            'rsi_14': rsi_14,
            'macd_hist': macd_hist,
            'trend_direction': trend_direction,
            'staleness_min': staleness_min,
            'is_win': float(pnl_pct) > 0,
        })
        
        if (i + 1) % 500 == 0:
            print(f"  Processed {i+1}/{len(trades)} trades...")
    
    print(f"  Matched trades: {len(matched)}")
    print(f"  Unmatched tokens (no coin table): {len(unmatched_tokens)} → {sorted(unmatched_tokens)[:10]}...")
    print(f"  No score data: {len(no_data_tokens)} → {sorted(no_data_tokens)[:10]}...")
    
    # 4. Analysis
    print("\n[4/4] Analyzing results...")
    
    results = {
        'backtest_date': datetime.now(timezone.utc).isoformat(),
        'total_trades': len(trades),
        'matched_trades': len(matched),
        'unmatched_tokens': sorted(list(unmatched_tokens)),
        'no_data_tokens': sorted(list(no_data_tokens)),
    }
    
    # ── A: Win rate by composite bucket ──
    print("\n" + "─" * 70)
    print("A) WIN RATE BY COMPOSITE SCORE BUCKET")
    print("─" * 70)
    
    bucket_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0.0, 'count': 0})
    for t in matched:
        b = t['composite_bucket']
        bucket_stats[b]['count'] += 1
        bucket_stats[b]['total_pnl'] += t['pnl_pct']
        if t['is_win']:
            bucket_stats[b]['wins'] += 1
        else:
            bucket_stats[b]['losses'] += 1
    
    composite_results = {}
    print(f"{'Bucket':<12} {'Count':>6} {'Win%':>8} {'Avg PnL':>10} {'Total PnL':>12} {'Wins':>6} {'Losses':>6}")
    print("-" * 70)
    for bucket in ['0-25', '25-50', '50-75', '75-100', 'no_data']:
        s = bucket_stats.get(bucket)
        if s and s['count'] > 0:
            wr = s['wins'] / s['count'] * 100
            avg_pnl = s['total_pnl'] / s['count']
            print(f"{bucket:<12} {s['count']:>6} {wr:>7.1f}% {avg_pnl:>9.2f}% {s['total_pnl']:>11.2f}% {s['wins']:>6} {s['losses']:>6}")
            composite_results[bucket] = {
                'count': s['count'],
                'wins': s['wins'],
                'losses': s['losses'],
                'win_rate_pct': round(wr, 2),
                'avg_pnl_pct': round(avg_pnl, 4),
                'total_pnl_pct': round(s['total_pnl'], 2),
            }
        elif s:
            print(f"{bucket:<12} {0:>6} {'N/A':>8}")
    results['composite_bucket_analysis'] = composite_results
    
    # ── B: High vs Low composite (50 threshold) ──
    print("\n" + "─" * 70)
    print("B) HIGH (>=50) vs LOW (<50) COMPOSITE")
    print("─" * 70)
    
    high = [t for t in matched if t['composite'] is not None and t['composite'] >= 50]
    low = [t for t in matched if t['composite'] is not None and t['composite'] < 50]
    
    for label, group in [("HIGH (>=50)", high), ("LOW (<50)", low)]:
        if group:
            wins = sum(1 for t in group if t['is_win'])
            wr = wins / len(group) * 100
            avg_pnl = sum(t['pnl_pct'] for t in group) / len(group)
            total_pnl = sum(t['pnl_pct'] for t in group)
            print(f"  {label}: {len(group)} trades, Win%={wr:.1f}%, Avg PnL={avg_pnl:.2f}%, Total PnL={total_pnl:.1f}%")
    
    if high and low:
        high_wr = sum(1 for t in high if t['is_win']) / len(high) * 100
        low_wr = sum(1 for t in low if t['is_win']) / len(low) * 100
        edge = high_wr - low_wr
        print(f"\n  EDGE: High composite wins {edge:+.1f}% more than low composite")
        results['high_vs_low'] = {
            'high_count': len(high),
            'high_win_rate': round(high_wr, 2),
            'high_avg_pnl': round(sum(t['pnl_pct'] for t in high) / len(high), 4),
            'low_count': len(low),
            'low_win_rate': round(low_wr, 2),
            'low_avg_pnl': round(sum(t['pnl_pct'] for t in low) / len(low), 4),
            'edge_pct': round(edge, 2),
        }
    
    # ── C: Wyckoff Phase Analysis (LONG trades) ──
    print("\n" + "─" * 70)
    print("C) WYCKOFF PHASE: ACCUMULATION vs OTHER (LONG trades only)")
    print("─" * 70)
    
    long_trades = [t for t in matched if t['direction'] == 'LONG']
    print(f"  Total LONG trades matched: {len(long_trades)}")
    
    wyckoff_groups = defaultdict(list)
    for t in long_trades:
        wyckoff_groups[t['wyckoff_phase']].append(t)
    
    wyckoff_results = {}
    print(f"\n  {'Phase':<16} {'Count':>6} {'Win%':>8} {'Avg PnL':>10} {'Total PnL':>12}")
    print("  " + "-" * 55)
    for phase in sorted(wyckoff_groups.keys(), key=lambda x: len(wyckoff_groups[x]), reverse=True):
        group = wyckoff_groups[phase]
        wins = sum(1 for t in group if t['is_win'])
        wr = wins / len(group) * 100
        avg_pnl = sum(t['pnl_pct'] for t in group) / len(group)
        total_pnl = sum(t['pnl_pct'] for t in group)
        print(f"  {phase:<16} {len(group):>6} {wr:>7.1f}% {avg_pnl:>9.2f}% {total_pnl:>11.2f}%")
        wyckoff_results[phase] = {
            'count': len(group),
            'wins': wins,
            'losses': len(group) - wins,
            'win_rate_pct': round(wr, 2),
            'avg_pnl_pct': round(avg_pnl, 4),
            'total_pnl_pct': round(total_pnl, 2),
        }
    results['wyckoff_long_analysis'] = wyckoff_results
    
    # Direct comparison: accumulation vs non-accumulation
    accum = [t for t in long_trades if t['wyckoff_phase'] == 'accumulation']
    non_accum = [t for t in long_trades if t['wyckoff_phase'] != 'accumulation']
    if accum and non_accum:
        accum_wr = sum(1 for t in accum if t['is_win']) / len(accum) * 100
        non_accum_wr = sum(1 for t in non_accum if t['is_win']) / len(non_accum) * 100
        print(f"\n  ACCUMULATION: {len(accum)} trades, Win%={accum_wr:.1f}%, Avg PnL={sum(t['pnl_pct'] for t in accum)/len(accum):.2f}%")
        print(f"  NON-ACCUM:    {len(non_accum)} trades, Win%={non_accum_wr:.1f}%, Avg PnL={sum(t['pnl_pct'] for t in non_accum)/len(non_accum):.2f}%")
        print(f"  EDGE: Accumulation LONG wins {accum_wr - non_accum_wr:+.1f}% more")
        results['wyckoff_accum_vs_non'] = {
            'accum_count': len(accum),
            'accum_win_rate': round(accum_wr, 2),
            'accum_avg_pnl': round(sum(t['pnl_pct'] for t in accum) / len(accum), 4),
            'non_accum_count': len(non_accum),
            'non_accum_win_rate': round(non_accum_wr, 2),
            'non_accum_avg_pnl': round(sum(t['pnl_pct'] for t in non_accum) / len(non_accum), 4),
            'edge_pct': round(accum_wr - non_accum_wr, 2),
        }
    
    # ── D: Wyckoff Phase Analysis (SHORT trades) ──
    print("\n" + "─" * 70)
    print("D) WYCKOFF PHASE: ACCUMULATION vs OTHER (SHORT trades only)")
    print("─" * 70)
    
    short_trades = [t for t in matched if t['direction'] == 'SHORT']
    print(f"  Total SHORT trades matched: {len(short_trades)}")
    
    swyckoff_groups = defaultdict(list)
    for t in short_trades:
        swyckoff_groups[t['wyckoff_phase']].append(t)
    
    print(f"\n  {'Phase':<16} {'Count':>6} {'Win%':>8} {'Avg PnL':>10} {'Total PnL':>12}")
    print("  " + "-" * 55)
    for phase in sorted(swyckoff_groups.keys(), key=lambda x: len(swyckoff_groups[x]), reverse=True):
        group = swyckoff_groups[phase]
        wins = sum(1 for t in group if t['is_win'])
        wr = wins / len(group) * 100
        avg_pnl = sum(t['pnl_pct'] for t in group) / len(group)
        total_pnl = sum(t['pnl_pct'] for t in group)
        print(f"  {phase:<16} {len(group):>6} {wr:>7.1f}% {avg_pnl:>9.2f}% {total_pnl:>11.2f}%")
    
    # ── E: Trend Direction + Composite interaction ──
    print("\n" + "─" * 70)
    print("E) TREND DIRECTION × COMPOSITE")
    print("─" * 70)
    
    trend_composite = defaultdict(lambda: {'wins': 0, 'count': 0, 'pnl': 0.0})
    for t in matched:
        key = (t['direction'], t['trend_direction'] or 'none')
        trend_composite[key]['count'] += 1
        trend_composite[key]['pnl'] += t['pnl_pct']
        if t['is_win']:
            trend_composite[key]['wins'] += 1
    
    print(f"  {'Dir+Trend':<20} {'Count':>6} {'Win%':>8} {'Avg PnL':>10}")
    print("  " + "-" * 50)
    for (d, td), s in sorted(trend_composite.items(), key=lambda x: -x[1]['count']):
        if s['count'] >= 10:
            wr = s['wins'] / s['count'] * 100
            avg = s['pnl'] / s['count']
            print(f"  {d}_{td:<14} {s['count']:>6} {wr:>7.1f}% {avg:>9.2f}%")
    
    # ── F: Staleness analysis ──
    print("\n" + "─" * 70)
    print("F) DATA STALENESS (minutes between coin_tracker data and trade entry)")
    print("─" * 70)
    
    staleness_buckets = defaultdict(lambda: {'wins': 0, 'count': 0, 'pnl': 0.0})
    for t in matched:
        s = t['staleness_min']
        if s is None:
            b = 'no_data'
        elif s < 10:
            b = '<10min'
        elif s < 30:
            b = '10-30min'
        elif s < 60:
            b = '30-60min'
        elif s < 360:
            b = '1-6hr'
        else:
            b = '6hr+'
        staleness_buckets[b]['count'] += 1
        staleness_buckets[b]['pnl'] += t['pnl_pct']
        if t['is_win']:
            staleness_buckets[b]['wins'] += 1
    
    print(f"  {'Staleness':<14} {'Count':>6} {'Win%':>8} {'Avg PnL':>10}")
    print("  " + "-" * 42)
    for b in ['<10min', '10-30min', '30-60min', '1-6hr', '6hr+', 'no_data']:
        s = staleness_buckets.get(b)
        if s and s['count'] > 0:
            wr = s['wins'] / s['count'] * 100
            avg = s['pnl'] / s['count']
            print(f"  {b:<14} {s['count']:>6} {wr:>7.1f}% {avg:>9.2f}%")
    
    # ── G: Top signals by composite ──
    print("\n" + "─" * 70)
    print("G) WIN RATE BY SIGNAL TYPE (with composite >= 50)")
    print("─" * 70)
    
    signal_stats = defaultdict(lambda: {'wins': 0, 'count': 0, 'pnl': 0.0})
    for t in matched:
        if t['composite'] is not None and t['composite'] >= 50:
            sig = t['signal'] or 'unknown'
            signal_stats[sig]['count'] += 1
            signal_stats[sig]['pnl'] += t['pnl_pct']
            if t['is_win']:
                signal_stats[sig]['wins'] += 1
    
    print(f"  {'Signal':<30} {'Count':>6} {'Win%':>8} {'Avg PnL':>10}")
    print("  " + "-" * 58)
    for sig, s in sorted(signal_stats.items(), key=lambda x: -x[1]['count']):
        if s['count'] >= 5:
            wr = s['wins'] / s['count'] * 100
            avg = s['pnl'] / s['count']
            print(f"  {sig:<30} {s['count']:>6} {wr:>7.1f}% {avg:>9.2f}%")
    
    # ── Statistical Summary ──
    print("\n" + "=" * 70)
    print("STATISTICAL SUMMARY")
    print("=" * 70)
    
    # Chi-squared-like test for composite >= 50 vs < 50
    if high and low:
        # Build 2x2 table
        a = sum(1 for t in high if t['is_win'])     # high wins
        b = len(high) - a                            # high losses
        c = sum(1 for t in low if t['is_win'])       # low wins
        d = len(low) - c                             # low losses
        n = len(high) + len(low)
        
        # Fisher's exact / chi-squared
        expected = [
            (a+b)*(a+c)/n, (a+b)*(b+d)/n,
            (c+d)*(a+c)/n, (c+d)*(b+d)/n
        ]
        chi2 = sum((obs-exp)**2/exp for obs, exp in zip([a,b,c,d], expected) if exp > 0)
        
        print(f"\n  2×2 Contingency Table (composite >= 50 vs < 50):")
        print(f"                {'Win':>8} {'Loss':>8} {'Total':>8}")
        print(f"  Composite≥50  {a:>8} {b:>8} {len(high):>8}")
        print(f"  Composite<50  {c:>8} {d:>8} {len(low):>8}")
        print(f"  Chi² = {chi2:.2f}  (p < 0.05 requires > 3.84)")
        if chi2 > 3.84:
            print(f"  ✅ SIGNIFICANT at p < 0.05 level")
        else:
            print(f"  ❌ NOT significant at p < 0.05 level")
        
        results['chi_squared'] = {
            'chi2': round(chi2, 4),
            'significant_005': chi2 > 3.84,
            'table': {'high_win': a, 'high_loss': b, 'low_win': c, 'low_loss': d},
        }
    
    # Overall stats
    all_composites = [t['composite'] for t in matched if t['composite'] is not None]
    if all_composites:
        results['composite_stats'] = {
            'mean': round(sum(all_composites) / len(all_composites), 2),
            'median': round(sorted(all_composites)[len(all_composites)//2], 2),
            'min': round(min(all_composites), 2),
            'max': round(max(all_composites), 2),
            'std': round((sum((x - sum(all_composites)/len(all_composites))**2 for x in all_composites) / len(all_composites))**0.5, 2),
        }
        print(f"\n  Composite score distribution (n={len(all_composites)}):")
        print(f"    Mean: {results['composite_stats']['mean']}")
        print(f"    Median: {results['composite_stats']['median']}")
        print(f"    Std: {results['composite_stats']['std']}")
        print(f"    Range: [{results['composite_stats']['min']}, {results['composite_stats']['max']}]")
    
    # Save results
    with open(OUTPUT, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✅ Results saved to {OUTPUT}")
    
    ct_conn.close()
    return results


if __name__ == '__main__':
    run_backtest()
