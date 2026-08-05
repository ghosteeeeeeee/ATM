# accel-300 + RS Win Rate Fixes — 2026-06-05

## Problem Summary
96h analysis (562 trades): profit-monster=276 wins/100%, atr_sl_hit=269 trades/3%WR/-0.81%avg.
Root cause: signals fire in chop/ranging markets where EMA300 oscillates.

## Findings

### 1. rs.py price= bug — FIXED
Line 771 of signals/rs.py: `price=price` confirmed present. No action needed.

### 2. Regime Filter Broken
- `regime_5m.json`: 91/97 tokens = NEUTRAL, 6 = LONG_BIAS, 0 = SHORT_BIAS
- accel_300.py regime check (lines 407-410): only blocks when `slope < 0` for LONG or `slope > 0` for SHORT
- In NEUTRAL (flat) markets, slope ≈ 0 → filter NEVER fires → counter-regime signals not blocked
- `regime` column in trades table = NULL for all 562 recent trades — regime never recorded at trade time

### 3. accel-300 Chop Filter (lines 294-321 in accel_300.py)
Hardcoded values that are too lenient in chop:
```
cross_gap threshold: 0.15   (fires on shallow EMA crosses)
ema_angle threshold: 0.05  (almost flat EMA = no trend)
avg_gap_mag threshold: 0.80 (tiny oscillations around EMA)
```
All three must be true simultaneously to suppress — in chop, at least one is usually not extreme enough.

### 4. RS Fires Too Often
- RS_DECIDER_MIN_TOUCHES=200 (too high → almost nothing passes → but weak signals still get through via co-signals)
- RS_MIN_TOUCHES=3 (too low → structural levels with only 3 touches are noise)
- DECIDER_CONF_FLOOR=55 (weak signals above 55% conf get through)

## Constants Changes (hermes_constants.py)

| Param | Was | Now | Reason |
|---|---|---|---|
| MIN_GAP_PCT_LONG | 0.20 | 0.30 | Reject micro-pulses in chop |
| MIN_GAP_PCT_SHORT | 0.20 | 0.30 | Reject micro-pulses in chop |
| ACCEL_300_PERSISTENCE_BARS | 3 | 4 | Need 4 consecutive bars, not 3 |
| ACCEL_300_MIN_GAP_GROWTH | 0.03 | 0.05 | Tighter growth requirement |
| ACCEL_300_MIN_GAP_EXPANSION | 0.10 | 0.15 | Price must be farther from EMA at cross |
| RS_MIN_TOUCHES | 3 | 5 | Higher quality structural levels |
| RS_DECIDER_MIN_TOUCHES | 200 | 150 | Lower so something still passes |
| RS_DECIDER_CONF_FLOOR | 55 | 60 | Block weaker signals more aggressively |

## accel_300.py Code Changes (hardcoded, not in constants)

### Chop filter (lines ~312-321):
```python
# Hardcoded thresholds — tighten to suppress choppy signals
cross_gap threshold: 0.15 → 0.25
ema_angle threshold: 0.05 → 0.10
avg_gap_mag threshold: 0.80 → 1.2
```

### Regime filter (lines ~406-410):
```python
# Slope near 0 = NEUTRAL = chop → block both LONG and SHORT
# Was: only block when slope clearly negative for LONG or positive for SHORT
# Now: block when slope is slight (near 0) in either direction
if abs(slope) < 0.02 and direction == 'LONG':
    return None  # flat/slight-up slope: chop, suppress LONG
if abs(slope) < 0.02 and direction == 'SHORT':
    return None  # flat/slight-down slope: chop, suppress SHORT
if slope < -0.02 and direction == 'LONG':  # was < 0
    return None
if slope > 0.02 and direction == 'SHORT':  # was > 0
    return None
```

## What NOT to Do
- Do NOT add coins to ACCEL_300_TOKEN_ALLOWLIST (T explicitly rejected)
- Do NOT increase RS_DECIDER_MIN_TOUCHES above 200 (T wants RS MORE selective, not less)
- Do NOT add coins to LONG_BLACKLIST as a shortcut for bad LONG signals
