# accel-300 Cross-Back Validation Fix — 2026-06-08

## Root Cause: Condition 1 Removed

The bug that caused ME/TON SHORT signals to fire when price was ABOVE EMA300 traces back to `accel_300.py` lines ~203-208. The original cross confirmation check — which required price to have been on the *other* side of EMA within the last LOOKBACK bars — was deleted. The comment said "All other conditions are sufficient" but they are NOT.

**What the deleted check did**: Before firing a signal, verify the cross is STILL VALID (price is still on the correct side of EMA). Without it, the code finds an old cross within the lookback window and fires based on it, even if price has since reversed back through EMA.

## Two Fixes Applied

### Fix 1 — Cross-Back Validation (lines ~289-336)

After finding a valid `cross_bar` within the lookback window, scan from `cross_bar+1` through `i`. If price crosses BACK through EMA and stays there for 2+ consecutive bars, block the signal.

```python
# For SHORT: if price crossed back ABOVE EMA for 2+ bars, block
# For LONG: if price crossed back BELOW EMA for 2+ bars, block
cross_back_count = 0
for k in range(cross_bar + 1, i + 1):
    if direction == 'SHORT':
        if gap_pcts[k] >= 0:  # crossed back above EMA
            cross_back_count += 1
        else:
            cross_back_count = 0  # reset on brief crossing back
    # ...
    if cross_back_count >= 2:
        return None  # BLOCK: cross is stale
```

**Effect**: ME (cross at j=626, crossed back up at j=637) and TON (cross at j=548, price above EMA for 91 of last 100 bars) are now correctly blocked.

**Risk**: May be too aggressive for sustained trends where brief EMA breaches are normal. Currently set at 2-bar threshold.

### Fix 2 — Fallback Finds First Bar in Gap Sequence (lines ~281-285)

The fallback search (for when no cross_bar is found in lookback) was finding the **most recent** negative-gap bar instead of the **first** bar of the negative-gap sequence. This made `bars_since_cross=1` instead of the actual ~99 bars.

**Before**: Walk backward from `i-1`, stop at first gap with wrong sign → returns most recent bar of previous sequence  
**After**: Walk backward to find the first bar of the current gap sequence → returns actual cross point

```python
# For SHORT (gap_pcts < 0 means below EMA):
j = i - 1
while j >= max(0, i - ACCEL_300_LOOKBACK):
    if gap_pcts[j] >= 0:  # first bar ABOVE EMA (start of negative sequence)
        break
    j -= 1
cross_bar = j  # this is the first below-EMA bar = actual cross
```

**Effect on BTC**: bars_since_cross = 99 (was 1) → persistence check fails (99 > 4) → correctly blocked.

### Gap Expansion TypeError for Fallback Crosses

For fallback crosses (cross_is_fallback=True), `gap_at_cross = None`. The gap expansion check at lines ~399-400:
```python
if gap_now > gap_at_cross + ACCEL_300_MIN_GAP_EXPANSION:  # TypeError: float > None
```
raises `TypeError: '>=' not supported between instances of 'float' and 'NoneType'`. Fixed by skipping gap_expansion check for fallback crosses.

## Over-Filtering After Both Fixes

After applying Fix #1 + Fix #2 to the full universe (213 tokens): **0 signals**. Investigation showed:
- cond2_fail=776, cond3_fail=33, cross_back_fail=126, chop_fail=0, stale_fail=0

All tokens fail at Condition 2 (gap_pcts threshold) or cross_back validation. The cross_back check appears too aggressive for the current market — many tokens in sustained trends with brief cross-backs through EMA are being blocked.

**Key diagnostic**: T's observation "on the chart the price has still not fallen below the EMA300" for ME is exactly what cross_back check catches. But the 126 tokens being blocked by cross_back may represent tokens where brief EMA breaches are normal in an otherwise valid trend.

## EMA300 Calculation Verified Correct

Compared `_ema_series()` implementation against pandas `ewm(span=300)`. Zero difference across all bars for ME and TON. The EMA300 math is not the problem.

## Debug Pattern for accel-300

```python
# Manual trace for a token
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from signals.accel_300 import _get_1m_prices, detect_accel_300

token = 'ME'
prices = _get_1m_prices(token)
result = detect_accel_300(token, prices)
print(f'Result: {result}')

# If result is None, trace each condition manually:
# 1. Check gap_pcts around detection time
# 2. Check cross_bar position
# 3. Check cross_back count (bars 305-309 for ME)
# 4. Check chop filter (avg_gap_mag vs ACCEL_300_CHOP_AVG_GAP_PCT=0.90)
# 5. Check persistence (bars_since_cross vs ACCEL_300_PERSISTENCE_BARS=4)
```

## Key Constants for This Session

```python
ACCEL_300_PERSISTENCE_BARS   = 4
ACCEL_300_LOOKBACK           = 100   # effective (from constants, not hardcoded)
ACCEL_300_STALE_BARS         = 100   # from hermes_constants.py
ACCEL_300_MIN_GAP_EXPANSION   = 0.01
ACCEL_300_CHOP_CROSS_GAP_PCT  = 0.22
ACCEL_300_CHOP_ANGLE_PCT      = 0.07
ACCEL_300_CHOP_AVG_GAP_PCT    = 0.90  # from hermes_constants.py line 492
MIN_GAP_PCT_SHORT             = 0.15
MIN_GAP_PCT_LONG              = 0.20
```

## Outstanding Questions

1. **Gap expansion logic inverted for SHORT**: Comments say "gap must be expanding (more negative)" but condition `gap_now > gap_at_cross + ACCEL_300_MIN_GAP_EXPANSION` blocks when gap is becoming *less* negative (contracting). This may be correct (detecting momentum loss) but the comment is misleading.

2. **Cross_back 2-bar threshold may be too aggressive**: 126 tokens blocked by cross_back across 213 tokens. In sustained trends, brief EMA breaches are common. Need to determine if threshold should be raised to 3-4 bars or removed for fallback crosses.

3. **Universe scan 0 signals**: After fixes, system returns 0 signals from 213 tokens. T's market read says tokens like XLM, ONDO, AAVE are in real trends — the system should find them. Either cross_back is over-filtering or other conditions are too tight.