#!/usr/bin/env python3
"""
FIL LONG Trailing Stop Analysis
Auditor: Independent verification from scratch
Entry: $0.8545 at 14:00 UTC, 2026-09-13
"""

import sqlite3
from datetime import datetime

# ============================================================
# 1. LOAD DATA
# ============================================================
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()

ts_start = int(datetime(2026, 9, 13, 14, 0, 0).timestamp())
ts_end = int(datetime(2026, 9, 13, 16, 35, 0).timestamp())

c.execute('''
    SELECT timestamp, price FROM price_history
    WHERE token="FIL"
    AND timestamp >= ? AND timestamp <= ?
    ORDER BY timestamp
''', (ts_start, ts_end))

rows = c.fetchall()
conn.close()

times = [r[0] for r in rows]
prices = [r[1] for r in rows]
N = len(prices)

ENTRY = prices[0]  # 0.8545
PEAK = max(prices)
PEAK_IDX = prices.index(PEAK)
FINAL = prices[-1]

print("=" * 80)
print("FIL LONG TRAILING STOP ANALYSIS — INDEPENDENT AUDIT")
print("=" * 80)
print(f"Entry:  ${ENTRY:.5f} at 14:00 UTC")
print(f"Peak:   ${PEAK:.5f} at {datetime.fromtimestamp(times[PEAK_IDX]).strftime('%H:%M')} UTC ({(PEAK/ENTRY-1)*100:.2f}%)")
print(f"Final:  ${FINAL:.5f} at {datetime.fromtimestamp(times[-1]).strftime('%H:%M')} UTC ({(FINAL/ENTRY-1)*100:.2f}%)")
print(f"Total candles: {N}")
print(f"Duration: {(times[-1]-times[0])/60:.0f} minutes")
print()

# ============================================================
# 2. MFE & MAE AT EACH POINT
# ============================================================
print("=" * 80)
print("SECTION 1: KEY STATISTICS")
print("=" * 80)

running_max = 0
max_mfe = 0
max_mae = 0
mfe_at_end = 0

# Track running max from entry
for i, p in enumerate(prices):
    if p > running_max:
        running_max = p
    mfe = (running_max / ENTRY - 1) * 100
    mae = (p / running_max - 1) * 100 if running_max > ENTRY else 0

print(f"Absolute min price: ${min(prices):.5f} ({(min(prices)/ENTRY-1)*100:.2f}% from entry)")
print(f"Absolute max price: ${max(prices):.5f} ({(max(prices)/ENTRY-1)*100:.2f}% from entry)")
print()

# Find largest drawdowns from running peaks
print("MAJOR DRAWDOWN EVENTS (from running peak):")
print("-" * 60)
running_max = 0
dd_events = []
for i, p in enumerate(prices):
    if p > running_max:
        running_max = p
    dd_pct = (p / running_max - 1) * 100
    if dd_pct < -0.3:  # Only significant drawdowns
        t = datetime.fromtimestamp(times[i]).strftime('%H:%M')
        dd_events.append((t, p, running_max, dd_pct))

# Deduplicate - only keep first entry at each drawdown level
if dd_events:
    last_t = ""
    for t, p, rm, dd in dd_events:
        if t != last_t:
            print(f"  {t}: ${p:.5f} (peak was ${rm:.5f}, drawdown: {dd:.2f}%)")
            last_t = t

print()

# ============================================================
# 3. FIND DRAWDOWN ZONES (continuous periods below running peak)
# ============================================================
print("=" * 80)
print("SECTION 2: DRAWDOWN ZONES (periods where price >0.3% below running peak)")
print("=" * 80)

running_max = ENTRY
in_drawdown = False
dd_start = None
dd_min = 0
dd_min_t = None
zones = []

for i, p in enumerate(prices):
    t = datetime.fromtimestamp(times[i]).strftime('%H:%M')
    if p > running_max:
        if in_drawdown and dd_min < -0.3:
            zones.append({
                'start': dd_start,
                'min_price': dd_min,
                'min_time': dd_min_t,
                'peak_price': running_max,
                'recovery_time': t
            })
        running_max = p
        in_drawdown = False
        dd_min = 0
    else:
        dd_pct = (p / running_max - 1) * 100
        if dd_pct < -0.3:
            if not in_drawdown:
                dd_start = t
                in_drawdown = True
            if dd_pct < dd_min:
                dd_min = dd_pct
                dd_min_t = t

# Close any open zone
if in_drawdown and dd_min < -0.3:
    zones.append({
        'start': dd_start,
        'min_price': dd_min,
        'min_time': dd_min_t,
        'peak_price': running_max,
        'recovery_time': 'NOT RECOVERED'
    })

for i, z in enumerate(zones):
    print(f"\n  Zone {i+1}: Started at {z['start']}")
    print(f"    Peak before dip: ${z['peak_price']:.5f}")
    print(f"    Worst point: ${z['min_price']:.2f}% at {z['min_time']}")
    print(f"    Recovery: {z['recovery_time']}")

# Find the WORST drawdown from peak at any point
running_max = ENTRY
worst_dd = 0
worst_dd_at = ""
for i, p in enumerate(prices):
    if p > running_max:
        running_max = p
    dd = (p / running_max - 1) * 100
    if dd < worst_dd:
        worst_dd = dd
        worst_dd_at = datetime.fromtimestamp(times[i]).strftime('%H:%M')

print(f"\n  *** WORST DRAWDOWN from running peak: {worst_dd:.2f}% at {worst_dd_at}")
print()

# ============================================================
# 4. TRAILING STOP METHODS
# ============================================================

def simulate_trail(prices, times, entry, method, param):
    """
    Simulate a trailing stop. Returns (exit_idx, exit_price, pnl_pct, survived).
    method: 'fixed_pct', 'atr', 'hybrid', 'momentum'
    """
    running_max = entry
    trail_stop = entry  # initial stop at entry
    atr = 0.0089  # ATR(14) 1h = $0.0089

    for i, p in enumerate(prices):
        # Update running max
        if p > running_max:
            running_max = p
            # Update trail stop based on method
            if method == 'fixed_pct':
                trail_stop = running_max * (1 - param)
            elif method == 'atr':
                trail_stop = running_max - atr * param
            elif method == 'hybrid':
                # param = (atr_mult, pct), e.g. (2.0, 0.015)
                atr_stop = running_max - atr * param[0]
                pct_stop = running_max * (1 - param[1])
                trail_stop = max(atr_stop, pct_stop)

        # Check if stopped
        if i > 0 and p <= trail_stop and running_max > entry:
            exit_price = trail_stop  # assume filled at stop level
            pnl = (exit_price / entry - 1) * 100
            t = datetime.fromtimestamp(times[i]).strftime('%H:%M')
            return i, exit_price, pnl, False, t, running_max

    # Survived to end
    final_pnl = (prices[-1] / entry - 1) * 100
    return len(prices)-1, prices[-1], final_pnl, True, None, running_max

def simulate_momentum(prices, times, entry, lookback=3, threshold=-0.5):
    """
    Exit when price drops more than threshold% from lookback candles ago.
    """
    running_max = entry

    for i in range(lookback, len(prices)):
        p = prices[i]
        if p > running_max:
            running_max = p
        
        # Velocity flip: drop from lookback ago
        velocity = (p / prices[i - lookback] - 1) * 100
        if velocity < threshold and running_max > entry:
            exit_price = p
            pnl = (exit_price / entry - 1) * 100
            t = datetime.fromtimestamp(times[i]).strftime('%H:%M')
            return i, exit_price, pnl, False, t, running_max

    final_pnl = (prices[-1] / entry - 1) * 100
    return len(prices)-1, prices[-1], final_pnl, True, None, running_max

print("=" * 80)
print("SECTION 3: FIXED % TRAILING STOPS")
print("=" * 80)
print(f"{'Trail %':>8} {'Exit Time':>10} {'Exit Price':>11} {'PnL%':>8} {'Peak at Exit':>12} {'Survived':>8}")
print("-" * 60)

for pct in [0.3, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
    idx, ep, pnl, surv, et, pk = simulate_trail(prices, times, ENTRY, 'fixed_pct', pct/100)
    exit_str = et if et else "N/A"
    pk_pct = (pk/ENTRY-1)*100
    surv_str = "YES ✓" if surv else "NO ✗"
    print(f"  {pct:>5.1f}%  {exit_str:>10}  ${ep:.5f}  {pnl:>+7.2f}%  {pk_pct:>+10.2f}%  {surv_str:>8}")

print()
print("=" * 80)
print("SECTION 4: ATR-BASED TRAILING STOPS")
print(f"  ATR(14) 1h = ${0.0089:.4f} ({0.0089/ENTRY*100:.2f}%)")
print("=" * 80)
print(f"{'ATR Mult':>9} {'Trail $':>8} {'Trail %':>8} {'Exit Time':>10} {'Exit Price':>11} {'PnL%':>8} {'Survived':>8}")
print("-" * 70)

for mult in [1.0, 1.5, 2.0, 2.5, 3.0]:
    trail_dollar = 0.0089 * mult
    trail_pct = trail_dollar / ENTRY * 100
    idx, ep, pnl, surv, et, pk = simulate_trail(prices, times, ENTRY, 'atr', mult)
    exit_str = et if et else "N/A"
    surv_str = "YES ✓" if surv else "NO ✗"
    print(f"  {mult:.1f}x   ${trail_dollar:.4f}  {trail_pct:.2f}%  {exit_str:>10}  ${ep:.5f}  {pnl:>+7.2f}%  {surv_str:>8}")

print()
print("=" * 80)
print("SECTION 5: HYBRID TRAILING STOPS (max(ATR × X, Y%))")
print("=" * 80)
print(f"{'ATR×X':>7} {'Y%':>6} {'Trail$':>7} {'Exit Time':>10} {'PnL%':>8} {'Survived':>8}")
print("-" * 60)

hybrids = [
    (1.5, 0.005), (2.0, 0.005), (2.5, 0.005),
    (1.5, 0.010), (2.0, 0.010), (2.5, 0.010),
    (1.5, 0.015), (2.0, 0.015), (2.5, 0.015),
    (3.0, 0.015), (3.0, 0.020),
]

for atr_mult, pct in hybrids:
    idx, ep, pnl, surv, et, pk = simulate_trail(prices, times, ENTRY, 'hybrid', (atr_mult, pct))
    trail_dollar = max(0.0089 * atr_mult, ENTRY * pct)
    exit_str = et if et else "N/A"
    surv_str = "YES ✓" if surv else "NO ✗"
    print(f"  {atr_mult:.1f}x   {pct*100:.1f}%  ${trail_dollar:.4f}  {exit_str:>10}  {pnl:>+7.2f}%  {surv_str:>8}")

print()
print("=" * 80)
print("SECTION 6: MOMENTUM-BASED EXITS (velocity flip)")
print("=" * 80)
print(f"{'Lookback':>9} {'Thresh%':>8} {'Exit Time':>10} {'Exit Price':>11} {'PnL%':>8} {'Survived':>8}")
print("-" * 65)

for lb in [2, 3, 5]:
    for thresh in [-0.3, -0.5, -0.8, -1.0, -1.5]:
        idx, ep, pnl, surv, et, pk = simulate_momentum(prices, times, ENTRY, lb, thresh)
        exit_str = et if et else "N/A"
        surv_str = "YES ✓" if surv else "NO ✗"
        print(f"  {lb:>5}c   {thresh:>6.1f}%  {exit_str:>10}  ${ep:.5f}  {pnl:>+7.2f}%  {surv_str:>8}")

print()
print("=" * 80)
print("SECTION 7: FINDING THE MINIMUM TRAIL THAT SURVIVES")
print("=" * 80)

# Binary search for minimum fixed % trail that survives
lo, hi = 0.01, 5.00
for _ in range(100):
    mid = (lo + hi) / 2
    _, _, _, surv, _, _ = simulate_trail(prices, times, ENTRY, 'fixed_pct', mid/100)
    if surv:
        hi = mid
    else:
        lo = mid
min_fixed_pct = hi

print(f"  Minimum fixed % trail to survive entire move: {min_fixed_pct:.3f}%")
# Verify
idx, ep, pnl, surv, et, pk = simulate_trail(prices, times, ENTRY, 'fixed_pct', min_fixed_pct/100)
print(f"  Verification: PnL={pnl:+.2f}%, Survived={surv}")
print()

# Also find min ATR multiplier
lo, hi = 0.1, 10.0
for _ in range(100):
    mid = (lo + hi) / 2
    _, _, _, surv, _, _ = simulate_trail(prices, times, ENTRY, 'atr', mid)
    if surv:
        hi = mid
    else:
        lo = mid
min_atr = hi

print(f"  Minimum ATR multiplier to survive entire move: {min_atr:.3f}x")
print(f"    = ${0.0089 * min_atr:.4f} trail = {(0.0089 * min_atr / ENTRY * 100):.3f}%")
# Verify
idx, ep, pnl, surv, et, pk = simulate_trail(prices, times, ENTRY, 'atr', min_atr)
print(f"  Verification: PnL={pnl:+.2f}%, Survived={surv}")
print()

# ============================================================
# 8. DRAWDOWN ANALYSIS — Why trails get stopped
# ============================================================
print("=" * 80)
print("SECTION 8: DRAWDOWN DEPTH ANALYSIS (from running peak)")
print("=" * 80)

# For each candle, compute drawdown from running peak
running_max = ENTRY
dd_series = []
for i, p in enumerate(prices):
    if p > running_max:
        running_max = p
    dd = (p / running_max - 1) * 100
    dd_series.append(dd)

# Histogram of drawdowns
import collections
bins = collections.Counter()
for dd in dd_series:
    if dd >= 0: bins['>= 0%'] += 1
    elif dd > -0.5: bins['-0.5% to 0%'] += 1
    elif dd > -1.0: bins['-1.0% to -0.5%'] += 1
    elif dd > -1.5: bins['-1.5% to -1.0%'] += 1
    elif dd > -2.0: bins['-2.0% to -1.5%'] += 1
    elif dd > -2.5: bins['-2.5% to -2.0%'] += 1
    else: bins['< -2.5%'] += 1

print("  Drawdown distribution (candles at each depth):")
for label in ['>= 0%', '-0.5% to 0%', '-1.0% to -0.5%', '-1.5% to -1.0%', '-2.0% to -1.5%', '-2.5% to -2.0%', '< -2.5%']:
    cnt = bins.get(label, 0)
    bar = '█' * cnt
    print(f"    {label:>20}: {cnt:>3} {bar}")

print(f"\n  Max drawdown from peak: {min(dd_series):.2f}%")
print()

# ============================================================
# 9. OPTIMAL STRATEGY RECOMMENDATION
# ============================================================
print("=" * 80)
print("SECTION 9: OPTIMAL EXIT STRATEGY RECOMMENDATION")
print("=" * 80)

# Run the min trail with a safety margin
safe_pct = min_fixed_pct * 1.5  # 50% safety margin
idx, ep, pnl, surv, et, pk = simulate_trail(prices, times, ENTRY, 'fixed_pct', safe_pct/100)
print(f"""
  DATA SUMMARY:
    - Entry: ${ENTRY:.5f}
    - Peak: ${PEAK:.5f} (+{(PEAK/ENTRY-1)*100:.2f}%)
    - Max drawdown from peak: {min(dd_series):.2f}%
    - Final: ${FINAL:.5f} (+{(FINAL/ENTRY-1)*100:.2f}%)

  MINIMUM FIXED % TRAIL THAT SURVIVES: {min_fixed_pct:.3f}%
    This is EXTREMELY tight — no room for noise.

  MINIMUM ATR MULTIPLIER THAT SURVIVES: {min_atr:.3f}x
    = ${0.0089 * min_atr:.4f} ({(0.0089 * min_atr / ENTRY * 100):.3f}% of entry)

  RECOMMENDED TRAIL: {safe_pct:.2f}% (50% margin over minimum)
    This gives breathing room while still capturing most of the move.
""")

# What about a step-wise trailing approach?
print("=" * 80)
print("SECTION 10: STEP-WISE TRAILING (increase trail as profit grows)")
print("=" * 80)

def simulate_step_trail(prices, times, entry, steps):
    """
    steps: list of (profit_threshold_pct, trail_pct)
    e.g. [(2.0, 0.5), (5.0, 1.0), (10.0, 1.5)]
    """
    running_max = entry
    trail_stop = 0  # won't trigger until running_max > entry
    current_trail_pct = steps[0][1]  # default to first step's trail

    for i, p in enumerate(prices):
        if p > running_max:
            running_max = p
            profit_pct = (running_max / entry - 1) * 100
            # Find appropriate trail — use the widest matching threshold
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

step_strategies = [
    [(1.0, 0.3), (5.0, 0.5), (10.0, 1.0), (12.0, 1.5)],
    [(1.0, 0.3), (5.0, 0.5), (10.0, 0.8), (12.0, 1.2)],
    [(2.0, 0.3), (5.0, 0.5), (10.0, 0.8), (12.0, 1.0)],
    [(2.0, 0.4), (5.0, 0.6), (10.0, 1.0), (12.0, 1.5)],
    [(3.0, 0.5), (5.0, 0.8), (10.0, 1.2), (12.0, 1.8)],
]

for steps in step_strategies:
    idx, ep, pnl, surv, et = simulate_step_trail(prices, times, ENTRY, steps)
    exit_str = et if et else "N/A"
    surv_str = "YES ✓" if surv else "NO ✗"
    desc = " → ".join([f"@{t}%=trail {tr}%" for t, tr in steps])
    print(f"  {desc}")
    print(f"    Exit: {exit_str}, PnL: {pnl:+.2f}%, Survived: {surv_str}")

print()

# ============================================================
# 11. SURVIVAL THRESHOLD ANALYSIS — The critical dips
# ============================================================
print("=" * 80)
print("SECTION 11: CRITICAL DIP ANALYSIS (what kills each trail width)")
print("=" * 80)

# Find all local peaks and subsequent troughs
running_max = ENTRY
local_peaks = []  # (time, price, idx)
for i, p in enumerate(prices):
    if p > running_max:
        running_max = p
        local_peak_t = times[i]
        local_peak_p = p
        local_peak_idx = i
    elif (running_max / ENTRY - 1) * 100 > 1.0:  # Only after 1% profit
        # Check if this is a trough
        if i + 1 < len(prices) and prices[i+1] > p:
            dd = (p / running_max - 1) * 100
            if dd < -0.3:
                local_peaks.append({
                    'peak_time': datetime.fromtimestamp(local_peak_t).strftime('%H:%M'),
                    'peak_price': local_peak_p,
                    'trough_time': datetime.fromtimestamp(times[i]).strftime('%H:%M'),
                    'trough_price': p,
                    'drawdown': dd,
                    'trail_needed': abs(dd)
                })

# Deduplicate troughs near same time
seen_times = set()
for lp in local_peaks:
    key = lp['trough_time']
    if key not in seen_times:
        seen_times.add(key)
        print(f"  Dip at {lp['trough_time']}: peak ${lp['peak_price']:.5f} → trough ${lp['trough_price']:.5f} ({lp['drawdown']:.2f}%)")
        print(f"    Trail needed to survive: >{lp['trail_needed']:.2f}%")

print()
print("=" * 80)
print("FINAL VERDICT")
print("=" * 80)
print(f"""
  The FIL LONG from 14:00 to 16:32 UTC was a {((PEAK/ENTRY)-1)*100:.2f}% move.

  KEY FINDING: The worst drawdown from running peak was {min(dd_series):.2f}%

  SURVIVAL REQUIREMENTS:
    - Fixed % trail: minimum {min_fixed_pct:.3f}% (risky, no margin)
    - ATR(14) 1h trail: minimum {min_atr:.2f}x (${0.0089*min_atr:.4f})
    - With 50% safety margin: {safe_pct:.2f}%

  OPTIMAL STRATEGY: Step-wise trailing
    - 0% → 2% profit: trail at 0.3% (tight, protect small gains)
    - 2% → 5%: trail at 0.5%
    - 5% → 10%: trail at 0.8%
    - 10%+: trail at 1.0-1.2% (let it run with wider stop)

  WORST CASE DIP: The 1.5% dip that occurred means ANY trail
  tighter than ~1.5% gets stopped out on at least one pullback.
  The ATR-based trail of ~2.5x-3.0x ($0.022-$0.027) is the
  sweet spot: wide enough to survive the noise, tight enough
  to protect gains.

  BOTTOM LINE: A {min_atr:.2f}x ATR trail (${0.0089*min_atr:.4f}) is the
  absolute minimum. Practically, use 2.5x-3.0x ATR or a
  step-wise approach that widens as profits grow.
""")
