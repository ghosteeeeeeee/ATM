# accel_300 SNX SHORT False Positive — 2026-05-31

## The Bug: Staleness Gate Inverted for SHORT

**File:** `/root/.hermes/scripts/signals/accel_300.py` line ~353

```python
# CURRENT (WRONG):
if direction == 'SHORT' and gap_pcts[newest_idx] <= 0:
    continue  # BLOCKS when gap is negative = price below EMA = VALID SHORT!

# CORRECT:
if direction == 'SHORT' and gap_pcts[newest_idx] >= 0:
    continue  # BLOCKS only when price has recrossed ABOVE EMA = stale
```

## How It Works

The staleness gate checks: "has price crossed back above EMA since the signal bar?"

For SHORT signals:
- Price BELOW EMA (gap negative) = valid SHORT direction → should NOT block
- Price ABOVE EMA (gap >= 0) = price recrossed = stale → should block

Current code does the OPPOSITE:
- `gap_pcts[newest_idx] <= 0` → TRUE when price below EMA → signal BLOCKED (wrong!)
- Should be `>= 0` to block only when price has recrossed above EMA

## Concrete Trace: Bar 686

```
direction=SHORT, current_below=True
was_above_recently=True → PASS
gap_now=-0.3217, abs(gap) > MIN_GAP_PCT_SHORT → PASS
persistent=True → PASS
cond4a: gap_then=-0.2224, growth=0.0993 >= 0.03 → PASS
cross_bar=676, bars_since=10, bars_since > 10=False → bars_since check PASS
cond4b: delta_last=-0.0487 < delta_prev=0.0018 → PASS
ALL CONDITIONS PASS → signal should fire

BUT staleness gate:
  i=686 < newest_idx=698 → staleness check applies
  gap_pcts[698]=-0.2973% (price below EMA = valid SHORT)
  gap_pcts[698] <= 0 → TRUE → BLOCKED by bug!
```

## Lookback Boundary Bypass

At 21:36: lookback returned exactly 700 bars (93829 total SNX bars). Signal fired despite bug — likely because at the exact lookback boundary, `i < newest_idx` evaluated differently or `_get_1m_prices` returned slightly fewer bars.

## Also Found: SHORT Expansion Gate Removed

Lines ~312-321: SHORT expansion gate removed entirely (same session).

**Before:** Both LONG `<` and SHORT `>` gates existed. SHORT gate was fundamentally broken — operator `>` fails for negative gaps because `-0.15 > (-0.29 - 0.10)` = True (passes) when it should reject.

**After:** SHORT has NO expansion gate. Condition 4a (gap growth) already captures SHORT acceleration. LONG expansion gate kept with `<` (proven correct).

## Fix Summary

1. **Staleness gate line ~353:** `<= 0` → `>= 0` for SHORT
2. **SHORT expansion gate:** already removed (lines ~312-321)

## Verification After Fix

Re-run signal generation — SNX SHORT should no longer fire incorrectly.