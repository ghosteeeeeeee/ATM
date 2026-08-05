# accel-300 June 2027 Session — Chop Filter + Gap Expansion Debug

## 2026-06-07

### Problem
accel-300 firing 0 signals for FET, ZORA, and likely the full universe. Market looks trending.

### Root Causes Found (in priority order)

#### 1. Chop Filter Hardcoded Values (3 gates, ALL hardcoded in signal file)
The chop filter at lines 323-336 had THREE hardcoded values:
```python
cross_gap < 0.18   # gap at cross bar
abs(ema_angle) < 0.07  # 50-bar EMA angle
avg_gap_mag < 0.9  # avg gap magnitude
```
**Fix**: Moved to hermes_constants.py:
```
ACCEL_300_CHOP_CROSS_GAP_PCT = 0.18
ACCEL_300_CHOP_EMA_ANGLE_PCT = 0.07
ACCEL_300_CHOP_AVG_GAP_PCT  = 0.90
```
And wired into signals/accel_300.py import + chop filter condition.

#### 2. Gap Expansion (gap_exp) — Top Blocker for FET
FET cross_gap was ~0.47% above EMA. Price pulled back to 0.21-0.37%, failing:
```
gap_now < gap_at_cross + ACCEL_300_MIN_GAP_EXPANSION(0.05)
0.37 < 0.47 + 0.05 = 0.52  → FAIL
```
After pullback, gap_at_cross is anchored at the cross point. The signal requires price to be even FURTHER from EMA than at the cross — which means it only fires in strong parabolic extensions, NOT in clean trend starts.

#### 3. MIN_GAP_PCT_LONG = 0.15 — Too Tight for Mid-Cap Tokens
FET max gap: 0.06-0.14% (below 0.15% threshold)
ZORA max gap: 0.03-0.14% (below 0.15% threshold)
Even when trending, mid-caps with smaller absolute moves can't clear the gap threshold.

#### 4. ACCEL_300_REGIME_SLOPE_PCT = 0.003 — Still Too Tight
FET slope_pct = 0.00043%/bar — flat market regime filter blocks LONG.
Threshold 0.003 means the 20-bar price series must slope > 0.003%/bar. FET at 0.00043 fails.

### Diagnostic Trace Output (FET, 2026-06-07 ~22:27-01:31)
```
FET LONG:
  i=441 fail persistent: price=0.195840 <= ema=0.195862
  i=443 LONG fail gap check: gap_now=0.0919 < min_gap=0.1500
  i=445 LONG fail gap_growth: -0.2941 <= 0.0400  ← gap contracting
  i=447 LONG fail gap_exp: gap_now=0.3696 < gap_at_cross+exp=0.5212  ← pullback from cross
  i=448 LONG fail marg_accel: d_last=-0.0025 d_prev=0.1839  ← momentum fading
  i=485 LONG fail regime: slope_pct=0.000430 <= 0.003000

ZORA LONG:
  i=335 fail gap check: gap_now=0.0299 < min_gap=0.1500
  i=338 gap=0.1356 < 0.15 (close!)
```

### Proposed Constants to Get Firing
```
MIN_GAP_PCT_LONG              = 0.08  # was 0.15 — FET/ZORA max ~0.14%
ACCEL_300_MIN_GAP_EXPANSION   = 0.02  # was 0.05 — remove additional expansion beyond cross gap
ACCEL_300_REGIME_SLOPE_PCT    = 0.001 # was 0.003 — allow flatter trends
ACCEL_300_CHOP_CROSS_GAP_PCT = 0.10  # was 0.18 — loosen cross gap requirement
ACCEL_300_CHOP_EMA_ANGLE_PCT = 0.04  # was 0.07 — loosen EMA angle requirement
ACCEL_300_CHOP_AVG_GAP_PCT   = 0.50  # was 0.90 — loosen avg gap magnitude
```

### Debug Pattern
```python
# Full per-bar trace to find exact blocker per token
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from signals.accel_300 import _get_1m_prices, _ema_series, detect_accel_300
from hermes_constants import (MIN_GAP_PCT_LONG, MIN_GAP_PCT_SHORT,
    ACCEL_300_MIN_GAP_GROWTH, ACCEL_300_MIN_GAP_EXPANSION,
    ACCEL_300_PERSISTENCE_BARS, ACCEL_300_REGIME_SLOPE_PCT,
    ACCEL_300_STALE_BARS, ACCEL_300_LOOKBACK,
    ACCEL_300_CHOP_CROSS_GAP_PCT, ACCEL_300_CHOP_EMA_ANGLE_PCT,
    ACCEL_300_CHOP_AVG_GAP_PCT)

token = 'FET'
prices = _get_1m_prices(token, lookback=700)
result = detect_accel_300(token, prices)
print(f'Result: {result}')
```

### Key Lesson
The gap_expansion gate (`gap_now < gap_at_cross + ACCEL_300_MIN_GAP_EXPANSION`) only allows parabolic extensions — it blocks clean trend starts where price gaps above EMA, pulls back slightly, then continues higher. A 0.05% expansion requirement after already being 0.47% above EMA is nearly impossible to satisfy.
