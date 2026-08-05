# accel-300: SHORT Fires While Price Above EMA300

**Date:** 2026-06-08  
**Severity:** Critical — fundamentally broken signal direction  
**Status:** Root cause identified, fix not yet implemented  

## What Happened

Two SHORT signals fired on ME and TON while price was clearly in an uptrend above EMA300:
- ME SHORT: fired 13:35 UTC, entry 0.06172. TON SHORT: fired 13:36 UTC, entry 1.73905.
- Both trades lost money, closed by atr_sl_hit within 18 minutes.
- TON had been above EMA300 for 95 out of the last 100 bars at detection time.

## Root Cause: Condition 1 Was Removed

**File:** `/root/.hermes/scripts/signals/accel_300.py`, lines 203–208

The original accel_300 signal required:
> "Price was on the OTHER SIDE of EMA300 within the last LOOKBACK (100) bars"

This was the **cross confirmation** — ensuring price had genuinely crossed EMA300 and the cross was recent and valid.

This condition was **removed** with comment:
```
# ── Condition 1 REMOVED ─────────────────────────────────────────────────────
# Original: required price to have been BELOW EMA within last LOOKBACK bars.
# This blocked sustained breakouts where price crossed 276+ bars ago (FET/ZORA).
# All other conditions (persistence, growth, marginal accel, chop, regime)
# are sufficient to filter false breakouts.
```

## Why This Breaks Signal Direction

With Condition 1 gone, the signal logic only checks:
1. **Direction** = price vs EMA at current bar
2. **Gap check** = |gap| >= MIN_GAP_PCT (0.15%)
3. **Persistence** = price was on correct side for last 4 bars
4. **Cross bar** = was there a cross within 100 bars (NOT whether the cross has since reversed)

The problem: a cross can be found in the 100-bar lookback, but price can then **cross BACK** above EMA, and the signal still fires SHORT because the cross exists somewhere in the history.

### TON Example (i=639 detection)
- j=548 (91 bars ago): cross DOWN detected, gap=-0.08%
- j=633 (6 bars ago): cross UP — price back ABOVE EMA
- i=639 (detection): price BELOW EMA again, gap=-0.25%
- **Result**: SHORT fires, but price was above EMA 89 of last 91 bars

### ME Example (i=629 detection)
- Price above EMA for 100 consecutive bars (100% of last 100 bars)
- i=629: micro-slip below EMA for 4 bars (-0.17% gap)
- SHORT fires on the micro-slip
- Price immediately reverses back above EMA
- **Result**: Signal is inverted — should have been LONG

## Debugging Technique

When debugging accel_300 direction issues, the key verification:

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts/signals')
from accel_300 import _get_1m_prices, _ema_series, PERIOD

prices = _get_1m_prices('SYMBOL', lookback=700)
closes = [p['price'] for p in prices]
ema300 = _ema_series(closes, PERIOD)

# Count how many of the last 100 bars were above vs below EMA
above_count = sum(1 for j in range(max(0, i-100), i) if closes[j] > ema300[j])
below_count = 100 - above_count

# If above_count is high (e.g., 95+) but signal is SHORT, Condition 1 was violated
```

## EMA Calculation

**Verified correct** — `_ema_series()` in accel_300.py matches pandas `ewm(span=300, adjust=False)` exactly (max diff < 1e-10). The EMA is not the problem.

## The Fix (Not Yet Implemented)

1. **Restore cross-reversal check**: Before emitting a signal, verify price has not crossed BACK over EMA since the detected cross_bar. If cross_bar was found at j, but price crossed back above EMA between j and i, the signal must be blocked.

2. **Or: Require recent cross with no reversal**: Change cross_bar search to only accept crosses where price has NOT crossed back since. This is a harder fix since it requires modifying the cross detection loop.

3. **Minimum bar count on correct side**: Instead of requiring a specific cross, require price has been on the correct side of EMA for at least X of the last Y bars (e.g., 80 of last 100). This is simpler and more robust than cross detection.
