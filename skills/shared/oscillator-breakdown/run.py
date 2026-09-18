#!/usr/bin/env python3
"""
oscillator_breakdown.py — Break down a signal's trades by BTC oscillator state.

Usage:
    python3 oscillator_breakdown.py [signal_name] [--direction LONG|SHORT] [--days 14]
    
Examples:
    python3 oscillator_breakdown.py pump-chain
    python3 oscillator_breakdown.py pullback-entry --direction SHORT
    python3 oscillator_breakdown.py mover --days 7
"""

import sys
import os
import sqlite3
import psycopg2
from datetime import datetime, timezone, timedelta

# Add scripts dir for imports
sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


def get_btc_state(ts, cconn):
    """Get BTC oscillator state at a given timestamp."""
    row = cconn.execute('''
        SELECT zscore_val, state_score, trend_quality, 
               linreg_direction, linreg_alignment,
               market_phase, velocity_val
        FROM continuum_states
        WHERE token = 'BTC'
        ORDER BY ABS(ts - ?) ASC
        LIMIT 1
    ''', (int(ts.timestamp()),)).fetchone()
    
    if not row:
        return None
    
    zscore, score, trend, linreg_dir, linreg_align, phase, vel = row
    
    # Classify linreg bias
    if linreg_dir and 'BULL' in str(linreg_dir).upper():
        linreg_bias = 'BULL'
    elif linreg_dir and 'BEAR' in str(linreg_dir).upper():
        linreg_bias = 'BEAR'
    else:
        linreg_bias = 'MIXED'
    
    # Classify score range
    if score is None:
        score_range = 'UNKNOWN'
    elif score < 20:
        score_range = '0-20'
    elif score < 40:
        score_range = '20-40'
    elif score < 60:
        score_range = '40-60'
    elif score < 80:
        score_range = '60-80'
    else:
        score_range = '80-100'
    
    return {
        'zscore': float(zscore) if zscore else 0,
        'score': float(score) if score else 0,
        'score_range': score_range,
        'trend': trend,
        'linreg_bias': linreg_bias,
        'phase': phase,
        'vel': float(vel) if vel else 0,
    }


def run_breakdown(signal_name, direction=None, days=14):
    """Run the oscillator breakdown for a signal."""
    # Connect to databases
    conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
    cur = conn.cursor()
    cconn = sqlite3.connect(CONTINUUM_DB, timeout=10)
    
    # Query trades
    query = '''
        SELECT token, signal, direction, volatility_regime,
               ROUND(pnl_usdt::numeric, 3) as pnl,
               ROUND(pnl_pct::numeric, 2) as pnl_pct,
               open_time
        FROM trades
        WHERE signal ILIKE %s
          AND status = 'closed'
          AND open_time >= NOW() - INTERVAL '%s days'
        ORDER BY open_time
    '''
    
    pattern = f'%{signal_name}%'
    cur.execute(query, (pattern, days))
    trades = cur.fetchall()
    
    if not trades:
        print(f"No trades found for '{signal_name}' in last {days} days")
        return
    
    # Match with BTC oscillator data
    all_data = []
    for t in trades:
        token, signal, direction_db, regime, pnl, pnl_pct, open_time = t
        btc = get_btc_state(open_time, cconn)
        if btc:
            all_data.append({
                'token': token, 'signal': signal, 'dir': direction_db,
                'pnl': float(pnl), 'pnl_pct': float(pnl_pct),
                **btc
            })
    
    conn.close()
    cconn.close()
    
    if not all_data:
        print(f"No BTC oscillator data matched for '{signal_name}'")
        return
    
    # Filter by direction if specified
    if direction:
        all_data = [d for d in all_data if d['dir'].upper() == direction.upper()]
    
    # Print results
    print(f"\n{'='*70}")
    print(f"  {signal_name.upper()} — BTC Oscillator Analysis")
    if direction:
        print(f"  Direction: {direction}")
    print(f"  Period: Last {days} days | Trades: {len(all_data)}")
    print(f"{'='*70}")
    
    # 1. BTC Score Ranges
    print(f"\n=== BTC Score Ranges ===")
    print(f"{'Score':10s} {'Trades':>6s} {'Wins':>5s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 45)
    
    ranges = [('0-20', 0, 20), ('20-40', 20, 40), ('40-60', 40, 60), 
              ('60-80', 60, 80), ('80-100', 80, 101)]
    
    for label, low, high in ranges:
        subset = [d for d in all_data if low <= d['score'] < high]
        if subset:
            wins = sum(1 for d in subset if d['pnl'] > 0)
            pnl = sum(d['pnl'] for d in subset)
            wr = wins / len(subset) * 100
            avg = pnl / len(subset)
            marker = '✅' if pnl > 0 else '❌'
            print(f"  {marker} {label:8s}  {len(subset):5d}  {wins:4d}  {wr:5.1f}%  ${pnl:>+7.2f}  ${avg:>+5.3f}")
    
    # 2. Linreg Bias
    print(f"\n=== Linreg Bias ===")
    print(f"{'Linreg':10s} {'Trades':>6s} {'Wins':>5s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 45)
    
    for bias in ['BULL', 'BEAR', 'MIXED']:
        subset = [d for d in all_data if d['linreg_bias'] == bias]
        if subset:
            wins = sum(1 for d in subset if d['pnl'] > 0)
            pnl = sum(d['pnl'] for d in subset)
            wr = wins / len(subset) * 100
            avg = pnl / len(subset)
            marker = '✅' if pnl > 0 else '❌'
            print(f"  {marker} {bias:8s}  {len(subset):5d}  {wins:4d}  {wr:5.1f}%  ${pnl:>+7.2f}  ${avg:>+5.3f}")
    
    # 3. BTC Trend
    print(f"\n=== BTC Trend ===")
    print(f"{'Trend':15s} {'Trades':>6s} {'Wins':>5s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 50)
    
    trends = ['STRONG_UP', 'UP', 'CALM', 'STRONG_DOWN', 'DOWN', 'RECOVERY', 'DECLINING']
    for trend in trends:
        subset = [d for d in all_data if d['trend'] == trend]
        if subset and len(subset) >= 3:
            wins = sum(1 for d in subset if d['pnl'] > 0)
            pnl = sum(d['pnl'] for d in subset)
            wr = wins / len(subset) * 100
            avg = pnl / len(subset)
            marker = '✅' if pnl > 0 else '❌'
            print(f"  {marker} {trend:13s}  {len(subset):5d}  {wins:4d}  {wr:5.1f}%  ${pnl:>+7.2f}  ${avg:>+5.3f}")
    
    # 4. Follow vs Fight
    print(f"\n=== Follow vs Fight ===")
    print(f"{'Setup':40s} {'Trades':>6s} {'Wins':>5s} {'WR':>6s} {'PnL':>8s}")
    print('-' * 70)
    
    configs = [
        ('LONG + BTC Score > 60 (follow)', lambda d: d['dir']=='LONG' and d['score']>60),
        ('LONG + BTC Score < 40 (fight)', lambda d: d['dir']=='LONG' and d['score']<40),
        ('SHORT + BTC Score < 40 (follow)', lambda d: d['dir']=='SHORT' and d['score']<40),
        ('SHORT + BTC Score > 80 (fight)', lambda d: d['dir']=='SHORT' and d['score']>80),
        ('LONG + Linreg BULL (follow)', lambda d: d['dir']=='LONG' and d['linreg_bias']=='BULL'),
        ('LONG + Linreg BEAR (fight)', lambda d: d['dir']=='LONG' and d['linreg_bias']=='BEAR'),
        ('SHORT + Linreg BEAR (follow)', lambda d: d['dir']=='SHORT' and d['linreg_bias']=='BEAR'),
        ('SHORT + Linreg BULL (fight)', lambda d: d['dir']=='SHORT' and d['linreg_bias']=='BULL'),
    ]
    
    for label, fn in configs:
        subset = [d for d in all_data if fn(d)]
        if subset and len(subset) >= 3:
            wins = sum(1 for d in subset if d['pnl'] > 0)
            pnl = sum(d['pnl'] for d in subset)
            wr = wins / len(subset) * 100
            marker = '✅' if pnl > 0 else '❌'
            print(f"  {marker} {label:38s}  {len(subset):5d}  {wins:4d}  {wr:5.1f}%  ${pnl:>+7.2f}")
    
    # Key Insight
    print(f"\n{'='*70}")
    best_score = max(ranges, key=lambda r: sum(d['pnl'] for d in all_data if r[1] <= d['score'] < r[2]))
    worst_score = min(ranges, key=lambda r: sum(d['pnl'] for d in all_data if r[1] <= d['score'] < r[2]))
    print(f"  Best BTC score range: {best_score[0]}")
    print(f"  Worst BTC score range: {worst_score[0]}")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 oscillator_breakdown.py [signal_name] [--direction LONG|SHORT] [--days 14]")
        sys.exit(1)
    
    signal_name = sys.argv[1]
    direction = None
    days = 14
    
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == '--direction' and i + 1 < len(sys.argv):
            direction = sys.argv[i + 1]
        elif arg == '--days' and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])
    
    run_breakdown(signal_name, direction, days)
