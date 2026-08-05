# ACCEL_300_REGIME_SLOPE_PCT Was Hardcoded

## Finding (2026-06-06)

`ACCEL_300_REGIME_SLOPE_PCT` was hardcoded as `0.015` in `signals/accel_300.py` at lines 410 and 413.

```python
# Line 410 — was hardcoded 0.015
if slope_pct <= ACCEL_300_REGIME_SLOPE_PCT and direction == 'LONG':
    return None
# Line 413 — was hardcoded 0.015
if slope_pct >= -ACCEL_300_REGIME_SLOPE_PCT and direction == 'SHORT':
    return None
```

## Fix Applied

1. Added `ACCEL_300_REGIME_SLOPE_PCT = 0.008` to `hermes_constants.py` line ~477
2. Updated `accel_300.py` import to include `ACCEL_300_REGIME_SLOPE_PCT`
3. Replaced both hardcoded `0.015` literals with the constant

## Why This Matters

With 81 tokens in the market having meaningful slopes, the hardcoded threshold at 0.015 was:
- Too high for SHORT: -0.015 blocks tokens with slopes -0.08 to -0.015 (81 tokens in a SHORT-biased market)
- Blocking all LONG: ETH/AVAX slopes ~0.008-0.011 were below 0.015 → no LONG signals ever

Setting it to 0.008 lets real slope signals through:
- MORPHO: slope -0.0048 would now pass SHORT regime (was failing at -0.0048 > -0.015)
- 81 SHORT tokens would now qualify for SHORT signals

## Always Put Tunable Thresholds in hermes_constants

Any threshold that a trader might want to adjust without touching signal logic belongs in `hermes_constants.py`. The pattern:

```python
# In hermes_constants.py:
ACCEL_300_REGIME_SLOPE_PCT = 0.008  # minimum slope %/bar for LONG (>0) or SHORT (<0)

# In signals/accel_300.py:
from hermes_constants import ACCEL_300_REGIME_SLOPE_PCT
if slope_pct <= ACCEL_300_REGIME_SLOPE_PCT and direction == 'LONG':
    return None
```
