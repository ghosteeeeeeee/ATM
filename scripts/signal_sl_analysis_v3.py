#!/usr/bin/env python3
"""
Signal Analyst V3: Deep dive into trailing stops, close reasons, and signal quality.
"""
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2
from collections import defaultdict, Counter

conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()

# ─── PART 1: Close reason distribution ───
print("="*100)
print("PART 1: CLOSE REASON DISTRIBUTION (30d live trades)")
print("="*100)
cur.execute("""
    SELECT close_reason, COUNT(*), 
           ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl,
           SUM(pnl_usdt)::numeric as total_pnl_usdt
    FROM trades 
    WHERE paper = FALSE AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
    GROUP BY close_reason
    ORDER BY COUNT(*) DESC
""")
for row in cur.fetchall():
    print(f"  {str(row[0]):40s} Count: {row[1]:4d}  Avg PnL: {float(row[2]):+7.3f}%  Total PnL: {float(row[3]):+10.2f} USDT")

# ─── PART 2: SL-related close reasons detail ───
print("\n" + "="*100)
print("PART 2: SL-RELATED CLOSE REASONS BY SIGNAL")
print("="*100)
cur.execute("""
    SELECT signal, close_reason, COUNT(*), 
           ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl,
           ROUND(AVG(sl_distance)::numeric, 4) as avg_sl_dist
    FROM trades 
    WHERE paper = FALSE AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
      AND (close_reason ILIKE '%stop%' OR close_reason ILIKE '%sl%' OR close_reason ILIKE '%trailing%')
    GROUP BY signal, close_reason
    HAVING COUNT(*) >= 3
    ORDER BY COUNT(*) DESC
    LIMIT 40
""")
for row in cur.fetchall():
    print(f"  {str(row[0]):45s} | {str(row[1]):30s} | N={row[2]:3d} | AvgPnL={float(row[3]):+7.3f}% | AvgSLDist={float(row[4]) if row[4] else 'N/A'}")

# ─── PART 3: Trailing stop activation and effectiveness ───
print("\n" + "="*100)
print("PART 3: TRAILING STOP ACTIVATION & EFFECTIVENESS")
print("="*100)
cur.execute("""
    SELECT 
        CASE WHEN trailing_activated = TRUE THEN 'Activated' ELSE 'Not Activated' END as trailing_status,
        COUNT(*) as cnt,
        ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl,
        ROUND(AVG(highest_price - entry_price)::numeric, 6) as avg_upside,
        ROUND(AVG(pnl_usdt)::numeric, 2) as avg_pnl_usdt
    FROM trades 
    WHERE paper = FALSE AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
      AND direction = 'LONG'
    GROUP BY trailing_activated
""")
print("LONG trades:")
for row in cur.fetchall():
    print(f"  Trailing {row[0]}: {row[1]} trades, Avg PnL: {row[2]:+.3f}%, Avg Upside: {row[3]}, Avg USDT: {row[4]:+.2f}")

cur.execute("""
    SELECT 
        CASE WHEN trailing_activated = TRUE THEN 'Activated' ELSE 'Not Activated' END as trailing_status,
        COUNT(*) as cnt,
        ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl,
        ROUND(AVG(entry_price - lowest_price)::numeric, 6) as avg_downside,
        ROUND(AVG(pnl_usdt)::numeric, 2) as avg_pnl_usdt
    FROM trades 
    WHERE paper = FALSE AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
      AND direction = 'SHORT'
    GROUP BY trailing_activated
""")
print("SHORT trades:")
for row in cur.fetchall():
    print(f"  Trailing {row[0]}: {row[1]} trades, Avg PnL: {row[2]:+.3f}%, Avg Downside: {row[3]}, Avg USDT: {row[4]:+.2f}")

# ─── PART 4: MFE/MAE analysis by signal ───
print("\n" + "="*100)
print("PART 4: MFE/MAE ANALYSIS BY MAJOR SIGNAL")
print("="*100)
cur.execute("""
    SELECT 
        signal, COUNT(*) as cnt,
        ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl,
        ROUND(AVG(mfe_pct)::numeric, 3) as avg_mfe,
        ROUND(AVG(mae_pct)::numeric, 3) as avg_mae,
        ROUND(AVG(mfe_pct - ABS(pnl_pct))::numeric, 3) as mfe_left_on_table,
        ROUND(AVG(highest_price - entry_price)::numeric, 6)::float as avg_high_entry,
        ROUND(AVG(entry_price - lowest_price)::numeric, 6)::float as avg_entry_low
    FROM trades 
    WHERE paper = FALSE AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
      AND mfe_pct IS NOT NULL
    GROUP BY signal
    HAVING COUNT(*) >= 10
    ORDER BY COUNT(*) DESC
""")
print(f"{'Signal':45s} | {'N':>3s} | {'PnL':>7s} | {'MFE':>7s} | {'MAE':>7s} | {'MFE-Left':>8s} | {'H-E':>10s} | {'E-L':>10s}")
print("-"*120)
for row in cur.fetchall():
    print(f"  {str(row[0]):43s} | {row[1]:3d} | {float(row[2]):+7.3f}% | {float(row[3]):+7.3f}% | {float(row[4]):+7.3f}% | {float(row[5]):+8.3f}% | {float(row[6]):10.6f} | {float(row[7]):10.6f}")

# ─── PART 5: Breakeven activation effectiveness ───
print("\n" + "="*100)
print("PART 5: BREAKEVEN ACTIVATION EFFECTIVENESS")
print("="*100)
cur.execute("""
    SELECT 
        signal,
        CASE WHEN breakeven_activated = TRUE THEN 'BE Yes' ELSE 'BE No' END as breakeven,
        COUNT(*) as cnt,
        ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl,
        SUM(pnl_usdt)::numeric as total_pnl
    FROM trades 
    WHERE paper = FALSE AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
    GROUP BY signal, breakeven_activated
    HAVING COUNT(*) >= 5
    ORDER BY signal, breakeven_activated
""")
print(f"{'Signal':40s} | {'BE Status':8s} | {'N':>3s} | {'AvgPnL':>7s} | {'TotalPnL':>10s}")
print("-"*80)
for row in cur.fetchall():
    print(f"  {str(row[0]):40s} | {str(row[1]):8s} | {row[2]:3d} | {float(row[3]):+7.3f}% | {float(row[4]):+10.2f}")

# ─── PART 6: Signal-level SL simulation (0.75% vs current) ───
print("\n" + "="*100)
print("PART 6: SIGNAL-LEVEL 0.75% SL SIMULATION")
print("="*100)

cur.execute("""
    SELECT 
        signal, direction, pnl_pct, entry_price, lowest_price, highest_price, 
        stop_loss, close_reason
    FROM trades 
    WHERE paper = FALSE AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
      AND entry_price > 0 AND lowest_price IS NOT NULL
""")
all_trades = cur.fetchall()
cols = [d[0] for d in cur.description]

signal_sim = defaultdict(lambda: {'total': 0, 'better_075': 0, 'worse_075': 0, 'net_pnl_current': 0.0, 'net_pnl_new': 0.0})

for trade in all_trades:
    t = dict(zip(cols, trade))
    sig = t['signal']
    old_pnl = float(t['pnl_pct'] or 0)
    entry = float(t['entry_price'])
    lowest = float(t['lowest_price'])
    highest = float(t['highest_price'])
    direction = t['direction']
    
    signal_sim[sig]['total'] += 1
    signal_sim[sig]['net_pnl_current'] += old_pnl
    
    # Simulate 0.75% SL
    if direction == 'LONG':
        would_hit = lowest <= entry * (1 - 0.75 / 100)
    else:
        would_hit = lowest >= entry * (1 + 0.75 / 100)
    
    new_pnl = -0.75 if would_hit else old_pnl
    signal_sim[sig]['net_pnl_new'] += new_pnl
    
    if new_pnl > old_pnl + 0.001:
        signal_sim[sig]['better_075'] += 1
    elif new_pnl < old_pnl - 0.001:
        signal_sim[sig]['worse_075'] += 1

# Print sorted by improvement
print(f"{'Signal':45s} | {'N':>3s} | {'Old PnL':>8s} | {'New PnL':>8s} | {'Delta':>8s} | {'B':>3s} | {'W':>3s} | {'Net':>3s}")
print("-"*105)
ranked = sorted(signal_sim.items(), key=lambda x: x[1]['net_pnl_new'] - x[1]['net_pnl_current'], reverse=True)
for sig, data in ranked:
    if data['total'] >= 10:
        delta = data['net_pnl_new'] - data['net_pnl_current']
        net = data['better_075'] - data['worse_075']
        print(f"  {sig:43s} | {data['total']:3d} | {data['net_pnl_current']:+8.2f}% | {data['net_pnl_new']:+8.2f}% | {delta:+8.2f}% | {data['better_075']:3d} | {data['worse_075']:3d} | {net:+3d}")

# ─── PART 7: Direction-specific SL distance analysis ───
print("\n" + "="*100)
print("PART 7: SL DISTANCE ANALYSIS BY DIRECTION")
print("="*100)
cur.execute("""
    SELECT 
        direction,
        COUNT(*) as cnt,
        ROUND(AVG(sl_distance)::numeric, 4) as avg_sl_dist,
        ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl,
        ROUND(AVG(CASE WHEN close_reason ILIKE '%stop%' THEN ABS(sl_distance) ELSE NULL END)::numeric, 4) as avg_sl_when_stopped,
        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sl_distance)::numeric, 4) as p25_sl,
        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY sl_distance)::numeric, 4) as p50_sl,
        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sl_distance)::numeric, 4) as p75_sl
    FROM trades 
    WHERE paper = FALSE AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
      AND sl_distance IS NOT NULL
    GROUP BY direction
""")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} trades")
    print(f"    Avg SL Distance: {float(row[2]):.4f} ({float(row[2])*100:.2f}%)")
    print(f"    Avg PnL: {float(row[3]):+.3f}%")
    print(f"    Avg SL Distance When Stopped: {float(row[4]) if row[4] else 'N/A'}")
    print(f"    SL Distance Distribution: P25={float(row[5]):.4f}, P50={float(row[6]):.4f}, P75={float(row[7]):.4f}")

# ─── PART 8: Worst losers and their characteristics ───
print("\n" + "="*100)
print("PART 8: WORST LOSING SIGNALS (by total PnL)")
print("="*100)
cur.execute("""
    SELECT 
        signal, COUNT(*) as cnt,
        ROUND(SUM(pnl_pct)::numeric, 2) as total_pnl_pct,
        SUM(pnl_usdt)::numeric as total_pnl_usdt,
        ROUND(AVG(pnl_pct)::numeric, 3) as avg_pnl,
        ROUND(100.0 * SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1) as winrate
    FROM trades 
    WHERE paper = FALSE AND status = 'closed'
      AND close_time > NOW() - INTERVAL '30 days'
    GROUP BY signal
    HAVING COUNT(*) >= 5
    ORDER BY SUM(pnl_pct) ASC
    LIMIT 20
""")
for row in cur.fetchall():
    print(f"  {str(row[0]):40s} | N={row[1]:3d} | TotalPnL={float(row[2]):+8.2f}% | USDT={float(row[3]):+10.2f} | Avg={float(row[4]):+7.3f}% | WR={float(row[5]):5.1f}%")

cur.close()
conn.close()
