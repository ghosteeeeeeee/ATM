# accel-300 Fix Session — 2026-06-07

## Problem
accel_300 signal firing 0 times for FET/ZORA despite trending market conditions.

## Root Causes Found (in order of discovery)

1. **MIN_GAP_PCT_LONG too high** — 0.15% but FET/ZORA max gaps ~0.14%. Changed to 0.08%.
2. **Condition 1 (was_below/above_recently) blocked sustained breakouts** — cross >35 bars ago never allowed through. Removed.
3. **max(310, ...) constraint swallowed real crosses** — was mathematically impossible to fire before EMA warmup at index 299. Removed.
4. **Marginal acceleration gate (cond 4b) blocked micro-pullbacks** — fighting against sustained trends. Removed.
5. **gap_growth blocking gate** — incompatible with sustained trends, moved to confidence scoring only.
6. **avg_gap_growth blocking gate** — same as above, removed as blocking, kept as confidence.
7. **regime_slope blocking** — original 0.015 threshold too strict for slow-moving trends. Reduced to 0.0001, used for confidence only.
8. **ACCEL_300_REGIME_SLOPE_PCT hardcoded at 0.015** — must be in hermes_constants.py. Added.
9. **Stale check bars_since_cross > 200** — incompatible with sustained trends. Removed.
10. **bars_since_cross > 3 gate in marginal acceleration** — same. Removed.
11. **Stale gate inequality `>= 0` vs `<= 0`** — equality allowed through. Fixed to `<= 0`.
12. **Gap decay check missing** — after removing gap_growth/marginal_accel, stale signals on fading trends needed a decay guard. Added 50% threshold.
13. **SHORT gap expansion gate missing** — asymmetry: LONG had the gate, SHORT did not. Added SHORT branch.
14. **Fallback cross_bar range stopped at PERIOD=300** — with 600-bar fetches, cross at index 378+ was missed. Extended to `range(i-1, -1, -1)`.
15. **None guard on stale gate entry missing** — whole stale gate section needed `and gap_pcts[i] is not None` to prevent TypeError on EMA warmup bars.

## Key Constants Changed (hermes_constants.py)

| Constant | Before | After |
|---|---|---|
| MIN_GAP_PCT_LONG | 0.15 | 0.08 |
| ACCEL_300_MIN_GAP_EXPANSION | 0.05 | 0.00 |
| ACCEL_300_MIN_GAP_GROWTH | 0.04 | 0.005 |
| ACCEL_300_REGIME_SLOPE_PCT | hardcoded 0.015 | 0.0001 |
| ACCEL_300_STALE_GAP_DECAY_THRESHOLD | hardcoded 0.50 | 0.50 (in constants) |

## Signals That Fire After Fix

```
FET: FIRE dir=LONG gap=1.1881% bars_since_cross=999
ZORA: FIRE dir=LONG gap=0.4248% bars_since_cross=999
```

bars_since_cross=999 means no cross in the 600-bar lookback window. This is correct behavior for sustained trends — the persistence check and gap decay check confirm trend quality independently.

## Subagent False Positives This Session

- **abs() unguarded at lines 374-377** — subagent misread scope, the `abs()` is inside the `if gap_pcts[newest_idx] is not None` block at line 361. Not a real bug.
- **SHORT `>` inequality inverted** — subagent sign-blind analysis. `>` with negative gap values is correct (tests "less negative = contracting toward EMA = block").