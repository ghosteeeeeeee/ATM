#!/usr/bin/env python3
"""
FIL LONG: Step-wise and edge analysis
Find the optimal adaptive trail that captures the most profit
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
ts_start = int(datetime(2026, 9, 13, 14, 0, 0).timestamp())
ts_end = int(datetime(2026, 9, 13, 16, 35, 0).timestamp())
c.execute('SELECT timestamp, price FROM price_history WHERE token="FIL" AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp', (ts_start, ts_end))
rows = c.fetchall()
conn.close()

times = [r[0] for r in rows]
prices = [r[1] for r in rows]
ENTRY = prices[0]

def simulate_step_trail(prices, times, entry, steps):
    """steps: list of (profit_threshold_pct, trail_pct)"""
    running_max = entry
    trail_stop = 0
    current_trail_pct = steps[0][1]

    for i, p in enumerate(prices):
        if p > running_max:
            running_max = p
            profit_pct = (running_max / entry - 1) * 100
            for threshold, trail_pct in steps:
                if profit_pct >= threshold:
                    current_trail_pct = trail_pct
            trail_stop = running_max * (1 - current_trail_pct / 100)

        if i > 0 and p <= trail_stop and running_max > entry:
            exit_price = trail_stop
            pnl = (exit_price / entry - 1) * 100
            t = datetime.fromtimestamp(times[i]).strftime('%H:%M')
            return i, exit_price, pnl, False, t

    return len(prices)-1, prices[-1], (prices[-1]/entry-1)*100, True, None

def simulate_fixed_trail(prices, times, entry, trail_pct):
    """trail_pct in PERCENTAGE units, e.g. 2.52 means 2.52%"""
    running_max = entry
    trail_stop = 0
    for i, p in enumerate(prices):
        if p > running_max:
            running_max = p
            trail_stop = running_max * (1 - trail_pct / 100)
        if i > 0 and p <= trail_stop and running_max > entry:
            exit_price = trail_stop
            pnl = (exit_price / entry - 1) * 100
            t = datetime.fromtimestamp(times[i]).strftime('%H:%M')
            return i, exit_price, pnl, False, t
    return len(prices)-1, prices[-1], (prices[-1]/entry-1)*100, True, None

# ============================================================
# The key constraint: Dip 1 at 14:47 reaches -2.52% from $0.92084
# At that point, profit = (0.92084/0.8545 - 1) * 100 = 7.76%
# So the trail at that profit level MUST be > 2.52%
#
# Dip 2 at 15:33 reaches -2.10% from $0.94041
# At that point, profit = (0.94041/0.8545 - 1) * 100 = 10.05%
# So the trail at that profit level MUST be > 2.10%
#
# Dip 3 at 16:03 reaches -2.00% from $0.96265
# At that point, profit = (0.96265/0.8545 - 1) * 100 = 12.65%
# So the trail at that profit level MUST be > 2.00%
# ============================================================

print("=" * 80)
print("CONSTRAINT ANALYSIS: What trail width is needed at each profit level")
print("=" * 80)
print("""
  The move has THREE major dips that set the floor for each trail width:

  Dip 1: 14:35-14:57 (the big one)
    Peak reached: $0.92084 (profit +7.76%)
    Worst drawdown: -2.52% (to $0.89767)
    ➜ Trail must be >2.52% when profit is ~7.76%

  Dip 2: 15:27-15:42
    Peak reached: $0.94041 (profit +10.05%)
    Worst drawdown: -2.10% (to $0.92065)
    ➜ Trail must be >2.10% when profit is ~10.05%

  Dip 3: 15:50-16:12
    Peak reached: $0.96265 (profit +12.65%)
    Worst drawdown: -2.00% (to $0.94335)
    ➜ Trail must be >2.00% when profit is ~12.65%

  CRITICAL INSIGHT: The FIRST dip is the widest (-2.52%).
  This means any trail that starts tighter and widens later
  MUST already be at >2.52% by the time profit reaches 7.76%.
""")

print("=" * 80)
print("TESTING STEP-WISE STRATEGIES (widening as profit grows)")
print("=" * 80)
print(f"{'Strategy':>60} {'Exit':>6} {'PnL%':>8} {'Survived':>8}")
print("-" * 85)

# The constraint is clear: by 7.76% profit we need trail > 2.52%
# So we need wide trails from the start, or accept getting stopped

step_strategies = [
    # Must survive the -2.52% dip at 7.76% profit
    [(0, 2.6), (10, 2.2), (12, 1.8)],          # Wide from start, narrow at high profit
    [(0, 2.7), (10, 2.2), (12, 1.8)],
    [(0, 2.8), (10, 2.2), (12, 1.8)],
    [(0, 3.0), (10, 2.2), (12, 1.8)],
    [(0, 2.6), (10, 2.1), (12, 1.5)],
    [(0, 3.0), (8, 2.5), (10, 2.0), (12, 1.5)],
    [(0, 2.6), (5, 2.5), (8, 2.2), (10, 2.0), (12, 1.5)],
    [(0, 2.52), (10, 2.1), (12, 1.6)],           # Just enough for dip 1
    # Aggressive narrowing approach
    [(0, 3.0), (5, 2.8), (8, 2.5), (10, 2.2), (12, 1.8)],
    [(0, 3.5), (10, 2.5), (12, 2.0)],
    # Ultra-wide (guaranteed survival)
    [(0, 4.0), (10, 3.0)],
    [(0, 5.0)],
]

for steps in step_strategies:
    idx, ep, pnl, surv, et = simulate_step_trail(prices, times, ENTRY, steps)
    exit_str = et if et else "END"
    surv_str = "YES ✓" if surv else "NO ✗"
    desc = " → ".join([f"@{t}%→{tr}%" for t, tr in steps])
    print(f"  {desc:>58}  {exit_str:>6}  {pnl:>+7.2f}%  {surv_str:>8}")

print()
print("=" * 80)
print("TESTING ALL FIXED % TRAILS (finer granularity)")
print("=" * 80)
print(f"{'Trail%':>7} {'Exit':>6} {'PnL%':>8} {'Peak%':>8} {'Survived':>8}")
print("-" * 55)

for pct in [1.0, 1.5, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.51, 2.52, 2.53, 2.55, 2.6, 2.7, 2.8, 2.9, 3.0, 3.5, 4.0, 5.0]:
    idx, ep, pnl, surv, et = simulate_fixed_trail(prices, times, ENTRY, pct)
    exit_str = et if et else "END"
    # Calculate what the peak was at exit
    peak_at_exit = max(prices[:idx+1])
    pk_pct = (peak_at_exit / ENTRY - 1) * 100
    surv_str = "YES ✓" if surv else "NO ✗"
    marker = " ◄ MINIMUM" if abs(pct - 2.52) < 0.01 else ""
    print(f"  {pct:>6.2f}%  {exit_str:>6}  {pnl:>+7.2f}%  {pk_pct:>+7.2f}%  {surv_str:>8}{marker}")

print()

# ============================================================
# What if we allow a FIXED stop loss too?
# ============================================================
print("=" * 80)
print("TRAIL + INITIAL STOP COMBINATION")
print("=" * 80)

def simulate_trail_with_initial_stop(prices, times, entry, initial_stop_pct, trail_pct):
    """First activate trail only after price reaches trail level above entry"""
    running_max = entry
    trail_stop = entry * (1 - initial_stop_pct / 100)  # initial hard stop
    activated = False

    for i, p in enumerate(prices):
        if p > running_max:
            running_max = p
            # Activate trail only once price exceeds trail level above max of entry/peak
            if running_max > entry:
                new_trail = running_max * (1 - trail_pct / 100)
                if not activated:
                    if p >= entry * (1 + trail_pct / 100):
                        activated = True
                        trail_stop = new_trail
                else:
                    trail_stop = max(trail_stop, new_trail)

        # Check stop hit
        effective_stop = trail_stop if activated else entry * (1 - initial_stop_pct / 100)
        if i > 0 and p <= effective_stop:
            exit_price = effective_stop
            pnl = (exit_price / entry - 1) * 100
            t = datetime.fromtimestamp(times[i]).strftime('%H:%M')
            return i, exit_price, pnl, False, t, activated

    return len(prices)-1, prices[-1], (prices[-1]/entry-1)*100, True, None, activated

# What if we use a tight initial stop to protect entry, then switch to trail?
print(f"{'InitStop':>9} {'Trail%':>7} {'Exit':>6} {'PnL%':>8} {'Survived':>8}")
print("-" * 50)

for init_stop in [1.0, 1.5, 2.0, 3.0]:
    for trail in [2.52, 2.6, 2.7, 2.8, 3.0, 3.5]:
        idx, ep, pnl, surv, et, act = simulate_trail_with_initial_stop(prices, times, ENTRY, init_stop, trail)
        exit_str = et if et else "END"
        surv_str = "YES ✓" if surv else "NO ✗"
        print(f"  {init_stop:>7.1f}%  {trail:>6.2f}%  {exit_str:>6}  {pnl:>+7.2f}%  {surv_str:>8}")

print()

# ============================================================
# FINAL: What's the MAXIMUM profit if we don't trail at all?
# ============================================================
print("=" * 80)
print("BASELINE: No trailing stop")
print("=" * 80)
print(f"  Hold from ${ENTRY:.5f} to ${prices[-1]:.5f}")
print(f"  Final PnL: {(prices[-1]/ENTRY-1)*100:+.2f}%")
print(f"  Max unrealized PnL: {(max(prices)/ENTRY-1)*100:+.2f}%")
print(f"  Money left on table (peak to close): {(prices[-1]/max(prices)-1)*100:+.2f}%")
print()

# ============================================================
# PROFIT CAPTURE RATIO for each surviving method
# ============================================================
print("=" * 80)
print("PROFIT CAPTURE COMPARISON")
print("=" * 80)

max_pnl = (max(prices) / ENTRY - 1) * 100  # theoretical max
hold_pnl = (prices[-1] / ENTRY - 1) * 100   # buy-and-hold

print(f"  Theoretical max PnL: {max_pnl:+.2f}%")
print(f"  Buy-and-hold PnL:    {hold_pnl:+.2f}%")
print()

surviving_methods = []
for pct in [2.52, 2.6, 2.7, 2.8, 2.9, 3.0, 3.5, 4.0, 5.0]:
    idx, ep, pnl, surv, et = simulate_fixed_trail(prices, times, ENTRY, pct)
    if surv:
        capture = pnl / hold_pnl * 100 if hold_pnl > 0 else 0
        surviving_methods.append((pct, pnl, capture, et))

print(f"  {'Method':>35} {'PnL%':>8} {'vs Hold':>8} {'Capture%':>10}")
print("  " + "-" * 65)
print(f"  {'Buy & hold (no stop)':>35} {hold_pnl:>+7.2f}%  {'---':>7}  {'100.0%':>9}")
print(f"  {'Theoretical max (sell peak)':>35} {max_pnl:>+7.2f}%  {'---':>7}  {'N/A':>9}")

for pct, pnl, cap, et in surviving_methods:
    print(f"  {'Fixed trail ' + str(pct) + '%':>35} {pnl:>+7.2f}%  {(pnl-hold_pnl):>+7.2f}%  {cap:>9.1f}%")

# Step-wise survivors
for steps in step_strategies:
    idx, ep, pnl, surv, et = simulate_step_trail(prices, times, ENTRY, steps)
    if surv:
        cap = pnl / hold_pnl * 100 if hold_pnl > 0 else 0
        desc = " → ".join([f"{tr}%" for _, tr in steps])
        print(f"  {'Step: ' + desc:>35} {pnl:>+7.2f}%  {(pnl-hold_pnl):>+7.2f}%  {cap:>9.1f}%")

print()
print("=" * 80)
print("FINAL RECOMMENDATION")
print("=" * 80)
print("""
  ┌─────────────────────────────────────────────────────────────────────┐
  │  MINIMUM TRAIL TO SURVIVE ENTIRE MOVE: 2.52% (fixed)              │
  │  OR: 2.60x ATR(14) 1h = $0.0232                                    │
  │                                                                     │
  │  BUT THIS HAS ZERO MARGIN — any slippage or execution delay        │
  │  would get you stopped out.                                        │
  │                                                                     │
  │  RECOMMENDED: 3.0% fixed trail OR 3.0x ATR ($0.0267)              │
  │  This gives ~19% safety margin over the worst dip.                │
  │                                                                     │
  │  For active management: Step trail starting at 3.0%,              │
  │  narrowing to 2.0% once profit exceeds 10%.                        │
  │                                                                     │
  │  RISK: The 2.52% dip at 14:47 was a single candle event.          │
  │  With 1m data, a 3.0% trail means you ride out the noise.         │
  │  Without 1m data (e.g., 5m candles), you'd never see the          │
  │  intra-candle dip and might use a tighter trail.                   │
  └─────────────────────────────────────────────────────────────────────┘
""")
