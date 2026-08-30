#!/usr/bin/env python3
"""
Signal Analyst V2: Evaluate impact of tightening SL/TP/trailing parameters.
Groups signals by primary type for cleaner analysis.
"""
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

# Connect to brain DB
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()

# Get last 30 days of closed live trades
cur.execute("""
    SELECT 
        signal, direction, pnl_pct, pnl_usdt, close_reason, 
        stop_loss, entry_price, highest_price, lowest_price,
        close_time, token, open_time, sl_distance,
        trailing_activated, trailing_distance, breakeven_activated,
        mfe_pct, mae_pct
    FROM trades 
    WHERE paper = FALSE 
      AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
    ORDER BY close_time DESC
""")
trades = cur.fetchall()
columns = [desc[0] for desc in cur.description]
print(f"Total closed live trades (30d): {len(trades)}")

# Group trades by signal
signal_trades = defaultdict(list)
for trade in trades:
    t = dict(zip(columns, trade))
    signal_trades[t['signal']].append(t)

print(f"Unique signals: {len(signal_trades)}")

# Analyze each signal
results = {}
for signal, trades_list in signal_trades.items():
    # Basic stats
    pnls = [float(t['pnl_pct'] or 0) for t in trades_list]
    winrate = sum(1 for p in pnls if p > 0) / len(pnls) * 100
    avg_pnl = sum(pnls) / len(pnls)
    total_pnl = sum(pnls)
    
    # SL analysis
    sl_hits = 0
    sl_hit_pnls = []
    for t in trades_list:
        close_reason = str(t['close_reason']).lower() if t['close_reason'] else ''
        if 'stop' in close_reason or 'sl' in close_reason or 'stop_loss' in close_reason:
            sl_hits += 1
            sl_hit_pnls.append(float(t['pnl_pct'] or 0))
    
    sl_rate = sl_hits / len(trades_list) * 100
    avg_sl_pnl = sum(sl_hit_pnls) / len(sl_hit_pnls) if sl_hit_pnls else 0
    
    # MFE analysis
    mfe_pcts = [float(t['mfe_pct'] or 0) for t in trades_list if t['mfe_pct']]
    avg_mfe = sum(mfe_pcts) / len(mfe_pcts) if mfe_pcts else 0
    
    # Capture ratio (actual PnL / MFE)
    captures = []
    for t in trades_list:
        if t['mfe_pct'] and t['mfe_pct'] > 0:
            capture = float(t['pnl_pct'] or 0) / float(t['mfe_pct'])
            captures.append(capture)
    avg_capture = sum(captures) / len(captures) if captures else 0
    
    # Direction breakdown
    longs = [t for t in trades_list if t['direction'] == 'LONG']
    shorts = [t for t in trades_list if t['direction'] == 'SHORT']
    
    long_winrate = sum(1 for t in longs if float(t['pnl_pct'] or 0) > 0) / len(longs) * 100 if longs else 0
    short_winrate = sum(1 for t in shorts if float(t['pnl_pct'] or 0) > 0) / len(shorts) * 100 if shorts else 0
    
    # Simulation: tighter SL (1.0% and 0.75%)
    better_1, worse_1 = 0, 0
    better_075, worse_075 = 0, 0
    
    for t in trades_list:
        old_pnl = t['pnl_pct'] or 0
        entry = t['entry_price']
        lowest = t['lowest_price']
        direction = t['direction']
        
        if entry and lowest and entry > 0:
            entry_f = float(entry)
            lowest_f = float(lowest)
            # Simulate 1.0% SL
            if direction == 'LONG':
                would_hit_1 = lowest_f <= entry_f * (1 - 1.0 / 100)
                would_hit_075 = lowest_f <= entry_f * (1 - 0.75 / 100)
            else:
                would_hit_1 = lowest_f >= entry_f * (1 + 1.0 / 100)
                would_hit_075 = lowest_f >= entry_f * (1 + 0.75 / 100)
            
            new_pnl_1 = -1.0 if would_hit_1 else old_pnl
            new_pnl_075 = -0.75 if would_hit_075 else old_pnl
            
            if new_pnl_1 > old_pnl:
                better_1 += 1
            elif new_pnl_1 < old_pnl:
                worse_1 += 1
                
            if new_pnl_075 > old_pnl:
                better_075 += 1
            elif new_pnl_075 < old_pnl:
                worse_075 += 1
    
    results[signal] = {
        'count': len(trades_list),
        'winrate': winrate,
        'avg_pnl': avg_pnl,
        'total_pnl': total_pnl,
        'sl_rate': sl_rate,
        'sl_hits': sl_hits,
        'avg_sl_pnl': avg_sl_pnl,
        'avg_mfe': avg_mfe,
        'avg_capture': avg_capture,
        'long_count': len(longs),
        'short_count': len(shorts),
        'long_winrate': long_winrate,
        'short_winrate': short_winrate,
        'better_1': better_1,
        'worse_1': worse_1,
        'better_075': better_075,
        'worse_075': worse_075
    }

# Print detailed analysis for top signals
print("\n" + "="*100)
print("DETAILED ANALYSIS FOR TOP SIGNALS BY TRADE COUNT")
print("="*100)

top_signals = sorted(results.items(), key=lambda x: -x[1]['count'])[:20]
for signal, data in top_signals:
    print(f"\n{'─'*80}")
    print(f"SIGNAL: {signal}")
    print(f"Trades: {data['count']}, Winrate: {data['winrate']:.1f}%, Avg PnL: {data['avg_pnl']:.2f}%")
    print(f"Total PnL: {data['total_pnl']:.2f}%")
    print(f"SL Hit Rate: {data['sl_rate']:.1f}% ({data['sl_hits']}/{data['count']})")
    print(f"Avg PnL when SL hit: {data['avg_sl_pnl']:.2f}%")
    print(f"Avg MFE: {data['avg_mfe']:.2f}%, Capture Ratio: {data['avg_capture']:.2f}")
    print(f"LONG: {data['long_count']} trades ({data['long_winrate']:.1f}% WR)")
    print(f"SHORT: {data['short_count']} trades ({data['short_winrate']:.1f}% WR)")
    print(f"Tighter SL (1.0%): Better {data['better_1']}, Worse {data['worse_1']}")
    print(f"Tighter SL (0.75%): Better {data['better_075']}, Worse {data['worse_075']}")

# Summary rankings
print("\n" + "="*100)
print("SIGNAL RANKINGS")
print("="*100)

# 1. Most affected by tighter SL (highest SL hit rate)
print("\n1. MOST AFFECTED BY TIGHTER SL (Highest SL Hit Rate):")
sl_ranked = sorted(results.items(), key=lambda x: -x[1]['sl_rate'])
for i, (signal, data) in enumerate(sl_ranked[:15], 1):
    print(f"{i:2d}. {signal:40s} SL Rate: {data['sl_rate']:5.1f}% ({data['sl_hits']}/{data['count']})")

# 2. Most benefited by tighter trailing (low capture ratio with high MFE)
print("\n2. MOST BENEFITED BY TIGHTER TRAILING (Low Capture, High MFE):")
mfe_ranked = sorted(results.items(), key=lambda x: x[1]['avg_capture'] if x[1]['avg_capture'] > 0 else 99)
for i, (signal, data) in enumerate(mfe_ranked[:15], 1):
    if data['avg_capture'] > 0:
        print(f"{i:2d}. {signal:40s} Capture: {data['avg_capture']:.2f}, MFE: {data['avg_mfe']:.2f}%")

# 3. Would tighter SL hurt profitable signals?
print("\n3. PROFITABLE SIGNALS THAT TIGHTER SL WOULD HURT:")
hurt_profitable = []
for signal, data in results.items():
    if data['winrate'] > 55 and data['avg_pnl'] > 0 and data['worse_1'] > data['better_1']:
        hurt_profitable.append((signal, data))
hurt_profitable.sort(key=lambda x: -x[1]['worse_1'])
for i, (signal, data) in enumerate(hurt_profitable[:15], 1):
    print(f"{i:2d}. {signal:40s} WR: {data['winrate']:.1f}%, PnL: {data['avg_pnl']:.2f}%, Worse: {data['worse_1']}, Better: {data['better_1']}")

# 4. Direction impact
print("\n4. DIRECTION IMPACT (LONG vs SHORT):")
all_longs = sum(data['long_count'] for data in results.values())
all_shorts = sum(data['short_count'] for data in results.values())
print(f"Total LONG trades: {all_longs}")
print(f"Total SHORT trades: {all_shorts}")

# Calculate average SL rates by direction
long_sl_rates = []
short_sl_rates = []
for signal, data in results.items():
    if data['long_count'] > 5:
        long_sl_rates.append(data['long_winrate'])
    if data['short_count'] > 5:
        short_sl_rates.append(data['short_winrate'])

print(f"Avg LONG winrate: {sum(long_sl_rates)/len(long_sl_rates):.1f}% (n={len(long_sl_rates)})")
print(f"Avg SHORT winrate: {sum(short_sl_rates)/len(short_sl_rates):.1f}% (n={len(short_sl_rates)})")

# 5. Overall simulation impact
print("\n5. OVERALL SIMULATION IMPACT:")
total_better_1 = sum(data['better_1'] for data in results.values())
total_worse_1 = sum(data['worse_1'] for data in results.values())
total_better_075 = sum(data['better_075'] for data in results.values())
total_worse_075 = sum(data['worse_075'] for data in results.values())
print(f"With 1.0% SL: {total_better_1} better, {total_worse_1} worse, net: {total_better_1 - total_worse_1}")
print(f"With 0.75% SL: {total_better_075} better, {total_worse_075} worse, net: {total_better_075 - total_worse_075}")

# Close connection
cur.close()
conn.close()
