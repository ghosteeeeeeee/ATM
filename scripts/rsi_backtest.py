#!/usr/bin/env python3
"""
RSI Signal Backtest — Compare signal quality with and without RSI components.

Uses PostgreSQL brain.trades as the source of truth.
Analyzes closed Hermes trades grouped by their signal field.

Key metrics:
- Win rate (WR): % of trades with pnl_pct > 0
- Avg PnL: mean pnl_pct across all trades in the group
- Total PnL: sum of all pnl_pct (proxy for $)
- expectancy: win_rate * avg_win - loss_rate * avg_loss
- Sharpe-like: expectancy / std_dev (if n >= 5)
"""

import psycopg2
import sys
from collections import defaultdict

BRAIN_DB = {'host': '/var/run/postgresql', 'database': 'brain', 'user': 'postgres'}

def get_trades():
    conn = psycopg2.connect(**BRAIN_DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT 
            token, direction, signal, pnl_pct, close_reason, leverage,
            entry_price, stop_loss, entry_timing
        FROM trades
        WHERE server = 'Hermes' AND status = 'closed'
          AND signal IS NOT NULL AND signal != ''
          AND pnl_pct IS NOT NULL
        ORDER BY entry_timing
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows

def classify_signal(sig):
    """Classify a signal string into categories."""
    if not sig:
        return 'unknown'
    sig = sig.lower()
    if 'rsi' in sig:
        return 'has_rsi'
    elif 'vel-hermes' in sig and 'pct-hermes' in sig and 'hzscore' in sig:
        return 'best_no_rsi'
    elif 'pct-hermes' in sig and 'hzscore' in sig:
        return 'pct_hzscore'
    elif 'vel-hermes' in sig and 'hzscore' in sig:
        return 'vel_hzscore'
    elif 'hzscore' in sig:
        return 'hzscore_only'
    elif 'pct-hermes' in sig:
        return 'pct_only'
    elif 'vel-hermes' in sig:
        return 'vel_only'
    elif 'conf-' in sig:
        return 'confluence'
    else:
        return 'other'

def analyze_group(trades, label):
    """Analyze a group of trades."""
    if not trades:
        return None
    # Convert Decimal to float
    trades = [(t[0], t[1], t[2], float(t[3]), t[4], t[5], t[6], t[7], t[8]) for t in trades]
    n = len(trades)
    wins = sum(1 for t in trades if t[3] > 0)
    losses = n - wins
    win_rate = wins / n * 100 if n > 0 else 0
    avg_pnl = sum(t[3] for t in trades) / n
    total_pnl = sum(t[3] for t in trades)
    
    wins_list = [t[3] for t in trades if t[3] > 0]
    losses_list = [t[3] for t in trades if t[3] <= 0]
    avg_win = sum(wins_list) / len(wins_list) if wins_list else 0
    avg_loss = sum(losses_list) / len(losses_list) if losses_list else 0
    
    # Expectancy
    loss_rate = 1 - win_rate/100
    expectancy = (win_rate/100 * avg_win) - (loss_rate * abs(avg_loss))
    
    # Std dev for Sharpe-like
    import statistics
    pnls = [t[3] for t in trades]
    std_dev = statistics.stdev(pnls) if n >= 2 else 0
    sharpe = (expectancy / std_dev) if std_dev > 0 else 0
    
    return {
        'label': label,
        'n': n,
        'wr': win_rate,
        'avg_pnl': avg_pnl,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy,
        'sharpe': sharpe,
        'wins': wins,
        'losses': losses,
    }

def print_result(r):
    if r is None:
        return
    print(f"  {r['label']:45} N={r['n']:4} WR={r['wr']:5.1f}%  "
          f"Avg={r['avg_pnl']:>8.3f}%  Total={r['total_pnl']:>9.3f}%  "
          f"Expect={r['expectancy']:>7.4f}  Sharpe={r['sharpe']:>6.2f}  "
          f"W={r['wins']:3} L={r['losses']:3}")

def main():
    trades = get_trades()
    print(f"Loaded {len(trades)} closed Hermes trades with signals\n")
    
    # Classify all trades
    by_sig = defaultdict(list)
    for t in trades:
        token, direction, signal, pnl_pct, close_reason, leverage, entry_price, stop_loss, entry_timing = t
        by_sig[signal].append(t)
    
    print("=" * 120)
    print("ALL SIGNALS (min 2 trades)")
    print("=" * 120)
    print(f"  {'Signal':45} {'N':>4} {'WR':>6} {'Avg':>9} {'Total':>10} {'Expect':>8} {'Sharpe':>7} {'W':>4} {'L':>4}")
    print("-" * 120)
    
    all_results = []
    for sig, sig_trades in sorted(by_sig.items(), key=lambda x: sum(t[3] for t in x[1]), reverse=True):
        if len(sig_trades) < 2:
            continue
        r = analyze_group(sig_trades, sig)
        if r:
            all_results.append(r)
            print_result(r)
    
    print()
    print("=" * 120)
    print("BY RSI STATUS")
    print("=" * 120)
    
    has_rsi = [t for t in trades if 'rsi' in (t[2] or '').lower()]
    no_rsi = [t for t in trades if 'rsi' not in (t[2] or '').lower()]
    
    rsi_result = analyze_group(has_rsi, 'HAS RSI (any rsi in signal)')
    no_rsi_result = analyze_group(no_rsi, 'NO RSI (signal has no rsi)')
    
    print(f"\n  {'Category':45} {'N':>4} {'WR':>6} {'Avg':>9} {'Total':>10} {'Expect':>8} {'Sharpe':>7}")
    print("-" * 90)
    print_result(rsi_result)
    print_result(no_rsi_result)
    
    print()
    print("=" * 120)
    print("BEST COMBO: hzscore,pct-hermes,vel-hermes (NO RSI) vs WITH RSI")
    print("=" * 120)
    
    # hzscore,pct-hermes,vel-hermes (no RSI)
    best_no_rsi = [t for t in trades if t[2] == 'hzscore,pct-hermes,vel-hermes']
    # hzscore,pct-hermes,rsi-hermes (with RSI)
    with_rsi = [t for t in trades if t[2] == 'hzscore,pct-hermes,rsi-hermes']
    
    r1 = analyze_group(best_no_rsi, 'hzscore,pct-hermes,vel-hermes (NO RSI)')
    r2 = analyze_group(with_rsi, 'hzscore,pct-hermes,rsi-hermes (WITH RSI)')
    
    print(f"\n  {'Signal':45} {'N':>4} {'WR':>6} {'Avg':>9} {'Total':>10} {'Expect':>8} {'Sharpe':>7}")
    print("-" * 90)
    print_result(r1)
    print_result(r2)
    
    print()
    print("=" * 120)
    print("ALL hzscore+pct COMBOS (with vs without vel and/or RSI)")
    print("=" * 120)
    
    combos = {
        'hzscore,pct-hermes (2-source)': lambda s: s in ('hzscore,pct-hermes',),
        'hzscore,pct-hermes,vel-hermes (3-source, no RSI)': lambda s: s == 'hzscore,pct-hermes,vel-hermes',
        'hzscore,pct-hermes,rsi-hermes (3-source, with RSI)': lambda s: s == 'hzscore,pct-hermes,rsi-hermes',
        'hzscore,pct-hermes,vel-hermes,rsi-hermes (4-source)': lambda s: s == 'hzscore,pct-hermes,vel-hermes,rsi-hermes',
    }
    
    for label, fn in combos.items():
        group = [t for t in trades if fn(t[2])]
        r = analyze_group(group, label)
        print_result(r)
    
    print()
    print("=" * 120)
    print("DIRECTION SPLIT: Which direction wins with RSI?")
    print("=" * 120)
    
    for direction in ['LONG', 'SHORT']:
        dir_trades = [t for t in trades if t[1] == direction]
        has_rsi_d = [t for t in dir_trades if 'rsi' in (t[2] or '').lower()]
        no_rsi_d = [t for t in dir_trades if 'rsi' not in (t[2] or '').lower()]
        
        rsi_r = analyze_group(has_rsi_d, f'{direction} + HAS RSI')
        no_rsi_r = analyze_group(no_rsi_d, f'{direction} + NO RSI')
        
        print(f"\n  {direction}:")
        print_result(rsi_r)
        print_result(no_rsi_r)
    
    print()
    print("=" * 120)
    print("CLOSE REASON BREAKDOWN FOR LOSING TRADES")
    print("=" * 120)
    
    losing = [t for t in trades if t[3] < 0]
    by_cr = defaultdict(list)
    for t in losing:
        by_cr[t[4]].append(t)
    
    for cr, cr_trades in sorted(by_cr.items(), key=lambda x: sum(t[3] for t in x[1])):
        n = len(cr_trades)
        total = sum(t[3] for t in cr_trades)
        avg = total / n
        has_rsi_n = sum(1 for t in cr_trades if 'rsi' in (t[2] or '').lower())
        print(f"  {cr:30} N={n:4}  Total={total:9.3f}%  Avg={avg:8.3f}%  HasRSI={has_rsi_n}/{n}")

if __name__ == '__main__':
    main()
