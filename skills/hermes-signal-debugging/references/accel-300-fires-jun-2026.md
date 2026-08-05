# accel-300 Fix Session — 2026-06-07

## Problem
accel_300 firing 0 times for FET/ZORA despite trending market conditions.

## Root Causes Found (in order of discovery)

1. **MIN_GAP_PCT_LONG too high** — 0.15% but FET/ZORA max gaps ~0.14%. Changed to 0.08%.
2. **Condition 1 (was_below/above_recently) blocked sustained breakouts** — cross >35 bars ago never allowed through. Removed.
3. **max(310, ...) constraint swallowed real crosses** — mathematically impossible before EMA warmup at index 299. Removed.
4. **Marginal acceleration gate (cond 4b) blocked micro-pullbacks** — fought against sustained trends. Removed.
5. **gap_growth blocking gate** — moved to confidence scoring only.
6. **avg_gap_growth blocking gate** — same, removed as blocking, kept as confidence.
7. **regime_slope blocking** — original 0.015 hardcoded threshold too strict. Reduced to 0.0001, used for confidence only.
8. **ACCEL_300_REGIME_SLOPE_PCT hardcoded at 0.015** — added to hermes_constants.py.
9. **Stale check bars_since_cross > 200** — removed.
10. **bars_since_cross > 3 gate in marginal acceleration** — removed.
11. **Stale gate inequality `>= 0` vs `<= 0`** — equality was allowed through. Fixed to `<= 0`.
12. **Gap decay check missing** — added 50% threshold: newest gap must be ≥ 50% of signal bar gap.
13. **SHORT gap expansion gate missing** — asymmetry: LONG had the gate, SHORT did not. Added SHORT branch.
14. **Fallback cross_bar range stopped at PERIOD=300** — extended to `range(i-1, -1, -1)`.
15. **None guard on stale gate entry missing** — added `and gap_pcts[i] is not None`.

## Key Constants Changed

| Constant | Before | After |
|---|---|---|
| MIN_GAP_PCT_LONG | 0.15 | 0.08 |
| ACCEL_300_MIN_GAP_EXPANSION | 0.05 | 0.00 |
| ACCEL_300_MIN_GAP_GROWTH | 0.04 | 0.005 |
| ACCEL_300_REGIME_SLOPE_PCT | hardcoded 0.015 | 0.0001 |
| ACCEL_300_STALE_GAP_DECAY_THRESHOLD | hardcoded 0.50 | in hermes_constants.py |

## Signals That Fire After Fix

```
FET: FIRE dir=LONG gap=1.1881% bars_since_cross=999
ZORA: FIRE dir=LONG gap=0.4248% bars_since_cross=999
```

bars_since_cross=999 = no cross in 600-bar lookback window. Correct for sustained trends — the persistence check and gap decay check confirm trend quality independently.

## Subagent False Positives This Session

- **abs() unguarded at lines 374-377** — subagent misread scope, `abs()` is inside `if gap_pcts[newest_idx] is not None:` block at line 361. Not a real bug.
- **SHORT `>` inequality inverted** — subagent sign-blind analysis. With negative SHORT gap values:
  - gap_now=-0.25 > -0.20 → False → pass ✓ (expanding, correct)
  - gap_now=-0.15 > -0.20 → True → block ✓ (contracting, correct)

## Key Lesson

The signal was fundamentally too strict for sustained trends. Removing marginal_accel, gap_growth, and regime_slope as blocking conditions — while keeping them as confidence modifiers — lets the signal fire on genuine sustained breakouts. The gap decay check (50% threshold) replaces all three as the staleness guard.