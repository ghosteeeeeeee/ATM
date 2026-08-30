#!/usr/bin/env python3
"""
Signal Analyst: Evaluate impact of tightening SL/TP/trailing parameters.
Analyzes last 30 days of closed live trades.
"""
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict
import json

# Connect to brain DB
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()

# Get last 30 days of closed live trades
cur.execute("""
    SELECT 
        signal, direction, pnl_pct, pnl_usdt, close_reason, 
        stop_loss, entry_price, highest_price, lowest_price,
        close_time, token, open_time
    FROM trades 
    WHERE paper = FALSE 
      AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
    ORDER BY close_time DESC
""")
trades = cur.fetchall()
columns = [desc[0] for desc in cur.description]
print(f"Total closed live trades (30d): {len(trades)}")

# Group by signal
signal_trades = defaultdict(list)
for trade in trades:
    t = dict(zip(columns, trade))
    signal_trades[t['signal']].append(t)

print(f"\nUnique signals: {len(signal_trades)}")
for sig, trades_list in sorted(signal_trades.items(), key=lambda x: -len(x[1])):
    print(f"  {sig}: {len(trades_list)} trades")

# Analysis functions
def analyze_sl_hits(trades_list):
    """Analyze SL hit rate and drawdown."""
    sl_hits = 0
    sl_hit_pnls = []
    no_sl_pnls = []
    
    for t in trades_list:
        if t['stop_loss'] and t['entry_price']:
            sl_pct = abs((t['stop_loss'] - t['entry_price']) / t['entry_price']) * 100
        else:
            sl_pct = None
            
        # Check if stopped out (close_reason contains 'stop' or 'sl')
        is_sl = 'stop' in str(t['close_reason']).lower() or 'sl' in str(t['close_reason']).lower()
        
        if is_sl:
            sl_hits += 1
            sl_hit_pnls.append(t['pnl_pct'] or 0)
        else:
            no_sl_pnls.append(t['pnl_pct'] or 0)
    
    total = len(trades_list)
    sl_rate = sl_hits / total * 100 if total > 0 else 0
    avg_sl_pnl = sum(sl_hit_pnls) / len(sl_hit_pnls) if sl_hit_pnls else 0
    avg_no_sl_pnl = sum(no_sl_pnls) / len(no_sl_pnls) if no_sl_pnls else 0
    
    return {
        'total': total,
        'sl_hits': sl_hits,
        'sl_rate': sl_rate,
        'avg_sl_pnl': avg_sl_pnl,
        'avg_no_sl_pnl': avg_no_sl_pnl,
        'sl_pnls': sl_hit_pnls,
        'no_sl_pnls': no_sl_pnls
    }

def analyze_mfe(trades_list):
    """Analyze Maximum Favorable Excursion vs actual capture."""
    mfe_data = []
    for t in trades_list:
        entry = t['entry_price']
        highest = t['highest_price']
        pnl = t['pnl_pct'] or 0
        direction = t['direction']
        
        if entry and highest and entry > 0:
            if direction == 'LONG':
                mfe = ((highest - entry) / entry) * 100
            else:  # SHORT
                mfe = ((entry - highest) / entry) * 100
            
            capture_ratio = pnl / mfe if mfe > 0 else 0
            mfe_data.append({
                'mfe': mfe,
                'pnl': pnl,
                'capture': capture_ratio
            })
    
    if mfe_data:
        avg_mfe = sum(d['mfe'] for d in mfe_data) / len(mfe_data)
        avg_capture = sum(d['capture'] for d in mfe_data) / len(mfe_data)
        high_mfe_low_capture = sum(1 for d in mfe_data if d['mfe'] > 2.0 and d['capture'] < 0.3)
        return {
            'avg_mfe': avg_mfe,
            'avg_capture': avg_capture,
            'high_mfe_low_capture': high_mfe_low_capture,
            'total': len(mfe_data)
        }
    return {'avg_mfe': 0, 'avg_capture': 0, 'high_mfe_low_capture': 0, 'total': 0}

def simulate_sl_impact(trades_list, new_sl_pct):
    """Simulate impact of tighter SL."""
    better = 0
    worse = 0
    neutral = 0
    pnl_changes = []
    
    for t in trades_list:
        old_pnl = t['pnl_pct'] or 0
        entry = t['entry_price']
        lowest = t['lowest_price']
        direction = t['direction']
        
        if entry and lowest and entry > 0:
            # Calculate what would happen with tighter SL
            if direction == 'LONG':
                # For LONG, SL triggers if price drops below entry - SL%
                would_hit_sl = lowest <= entry * (1 - new_sl_pct / 100)
                if would_hit_sl:
                    new_pnl = -new_sl_pct  # Lost the SL amount
                else:
                    new_pnl = old_pnl  # Trade plays out as normal
            else:  # SHORT
                # For SHORT, SL triggers if price rises above entry + SL%
                would_hit_sl = lowest >= entry * (1 + new_sl_pct / 100)
                if would_hit_sl:
                    new_pnl = -new_sl_pct
                else:
                    new_pnl = old_pnl
            
            pnl_change = new_pnl - old_pnl
            pnl_changes.append(pnl_change)
            
            if pnl_change > 0.01:
                better += 1
            elif pnl_change < -0.01:
                worse += 1
            else:
                neutral += 1
    
    total = len(pnl_changes)
    avg_change = sum(pnl_changes) / total if total > 0 else 0
    
    return {
        'better': better,
        'worse': worse,
        'neutral': neutral,
        'avg_change': avg_change,
        'total': total
    }

def analyze_by_direction(trades_list):
    """Separate LONG vs SHORT analysis."""
    longs = [t for t in trades_list if t['direction'] == 'LONG']
    shorts = [t for t in trades_list if t['direction'] == 'SHORT']
    
    long_analysis = analyze_sl_hits(longs)
    short_analysis = analyze_sl_hits(shorts)
    
    long_mfe = analyze_mfe(longs)
    short_mfe = analyze_mfe(shorts)
    
    return {
        'long': {'count': len(longs), 'sl': long_analysis, 'mfe': long_mfe},
        'short': {'count': len(shorts), 'sl': short_analysis, 'mfe': short_mfe}
    }

# Run analyses
print("\n" + "="*80)
print("DETAILED SIGNAL ANALYSIS")
print("="*80)

results = {}
for signal, trades_list in signal_trades.items():
    print(f"\n{'='*60}")
    print(f"SIGNAL: {signal}")
    print(f"{'='*60}")
    
    # Basic stats
    pnls = [t['pnl_pct'] or 0 for t in trades_list]
    winrate = sum(1 for p in pnls if p > 0) / len(pnls) * 100
    avg_pnl = sum(pnls) / len(pnls)
    
    print(f"Trades: {len(trades_list)}, Winrate: {winrate:.1f}%, Avg PnL: {avg_pnl:.2f}%")
    
    # SL analysis
    sl_analysis = analyze_sl_hits(trades_list)
    print(f"\nSL Analysis:")
    print(f"  SL Hit Rate: {sl_analysis['sl_rate']:.1f}% ({sl_analysis['sl_hits']}/{sl_analysis['total']})")
    print(f"  Avg PnL when SL hit: {sl_analysis['avg_sl_pnl']:.2f}%")
    print(f"  Avg PnL when NOT SL hit: {sl_analysis['avg_no_sl_pnl']:.2f}%")
    
    # MFE analysis
    mfe_analysis = analyze_mfe(trades_list)
    print(f"\nMFE Analysis:")
    print(f"  Avg MFE: {mfe_analysis['avg_mfe']:.2f}%")
    print(f"  Avg Capture Ratio: {mfe_analysis['avg_capture']:.2f}")
    print(f"  High MFE (>2%) but Low Capture (<30%): {mfe_analysis['high_mfe_low_capture']}/{mfe_analysis['total']}")
    
    # Direction analysis
    dir_analysis = analyze_by_direction(trades_list)
    print(f"\nDirection Breakdown:")
    print(f"  LONG: {dir_analysis['long']['count']} trades, Winrate: {dir_analysis['long']['sl']['sl_rate']:.1f}% SL hit")
    print(f"  SHORT: {dir_analysis['short']['count']} trades, Winrate: {dir_analysis['short']['sl']['sl_rate']:.1f}% SL hit")
    
    # Simulate tighter SL (1.0% vs current ~1.5%)
    print(f"\nSimulation: Tighter SL (1.0% vs current):")
    sim_1 = simulate_sl_impact(trades_list, 1.0)
    print(f"  Better: {sim_1['better']}, Worse: {sim_1['worse']}, Neutral: {sim_1['neutral']}")
    print(f"  Avg PnL Change: {sim_1['avg_change']:.2f}%")
    
    # Simulate even tighter SL (0.75%)
    print(f"\nSimulation: Very Tight SL (0.75%):")
    sim_075 = simulate_sl_impact(trades_list, 0.75)
    print(f"  Better: {sim_075['better']}, Worse: {sim_075['worse']}, Neutral: {sim_075['neutral']}")
    print(f"  Avg PnL Change: {sim_075['avg_change']:.2f}%")
    
    # Store results
    results[signal] = {
        'count': len(trades_list),
        'winrate': winrate,
        'avg_pnl': avg_pnl,
        'sl_analysis': sl_analysis,
        'mfe_analysis': mfe_analysis,
        'direction_analysis': dir_analysis,
        'simulation_1': sim_1,
        'simulation_075': sim_075
    }

# Summary analysis
print("\n" + "="*80)
print("SUMMARY ANALYSIS")
print("="*80)

# Rank signals by SL hit rate (most affected by tighter SL)
print("\nSignals ranked by SL Hit Rate (most affected by tighter SL):")
sl_ranked = sorted(results.items(), key=lambda x: -x[1]['sl_analysis']['sl_rate'])
for i, (signal, data) in enumerate(sl_ranked[:10], 1):
    print(f"{i}. {signal}: {data['sl_analysis']['sl_rate']:.1f}% SL hit rate ({data['count']} trades)")

# Rank signals by MFE capture inefficiency (most benefited by tighter trailing)
print("\nSignals ranked by MFE Capture Inefficiency (most benefited by tighter trailing):")
mfe_ranked = sorted(results.items(), key=lambda x: x[1]['mfe_analysis']['avg_capture'])
for i, (signal, data) in enumerate(mfe_ranked[:10], 1):
    print(f"{i}. {signal}: Capture ratio {data['mfe_analysis']['avg_capture']:.2f} (MFE: {data['mfe_analysis']['avg_mfe']:.2f}%)")

# Rank signals by simulation improvement (tighter SL helps most)
print("\nSignals ranked by improvement with 1.0% SL:")
sim_ranked = sorted(results.items(), key=lambda x: -x[1]['simulation_1']['avg_change'])
for i, (signal, data) in enumerate(sim_ranked[:10], 1):
    print(f"{i}. {signal}: {data['simulation_1']['avg_change']:+.2f}% avg change")

# Overall impact assessment
print("\n" + "="*80)
print("OVERALL IMPACT ASSESSMENT")
print("="*80)

total_trades = sum(data['count'] for data in results.values())
total_sl_hits = sum(data['sl_analysis']['sl_hits'] for data in results.values())
avg_sl_rate = total_sl_hits / total_trades * 100 if total_trades > 0 else 0

# Overall simulation
total_better_1 = sum(data['simulation_1']['better'] for data in results.values())
total_worse_1 = sum(data['simulation_1']['worse'] for data in results.values())
total_neutral_1 = sum(data['simulation_1']['neutral'] for data in results.values())

total_better_075 = sum(data['simulation_075']['better'] for data in results.values())
total_worse_075 = sum(data['simulation_075']['worse'] for data in results.values())
total_neutral_075 = sum(data['simulation_075']['neutral'] for data in results.values())

print(f"Total Trades: {total_trades}")
print(f"Overall SL Hit Rate: {avg_sl_rate:.1f}%")
print(f"\nWith 1.0% SL: {total_better_1} better, {total_worse_1} worse, {total_neutral_1} neutral")
print(f"With 0.75% SL: {total_better_075} better, {total_worse_075} worse, {total_neutral_075} neutral")

# Direction-specific impact
print("\nDirection-Specific Impact:")
long_trades = sum(data['direction_analysis']['long']['count'] for data in results.values())
short_trades = sum(data['direction_analysis']['short']['count'] for data in results.values())
print(f"LONG trades: {long_trades}")
print(f"SHORT trades: {short_trades}")

# Close connection
cur.close()
conn.close()

print("\nAnalysis complete. Results saved to signal_sl_analysis_results.json")
