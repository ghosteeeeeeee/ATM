# VVV Trade Failure + Z-Score Divergence Fix (2026-05-18)

## What Happened

- **Trade:** VVV LONG, entry $14.136, SL hit $14.0365, -0.70%, 3x leverage
- **Opened:** 2026-05-18 03:12:07 UTC
- **Closed:** 03:15:06 UTC (atr_sl_hit)
- **Signal sources:** `zscore-pump+` (z=+1.483) + `rs-s213` (broken support with 213 touches)

## Root Cause

z-score (lookback=100) peaked at **+2.985** at bar ~91 (~03:02-03:05 UTC), then collapsed for
**50 consecutive bars** while price ranged near $14.05-$14.15 making marginal new highs.
`zscore-pump+` fired LONG at z=+1.483 — exactly when z was in freefall from extreme.

The system had no divergence detection: it saw z above threshold and triggered LONG,
with no awareness that z had been dramatically overextended and was now reversing.

## Fix: Z-Score Divergence Gate

### Constants (hermes_constants.py lines ~581-585)

```python
ZSCORE_PUMP_DIVERGENCE_ENABLED = True
ZSCORE_PUMP_DIVERGENCE_LOOKBACK = 20   # spot lookback for momentum check (independent of signal lookback=100)
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 2.5
ZSCORE_PUMP_DIVERGENCE_VEL_THD  = -0.3
ZSCORE_PUMP_DIVERGENCE_BARS     = 3
```

### Logic (signals/zscore_pump.py)

`_check_divergence(prices, lookback)`:
1. Compute rolling spot z-score using `ZSCORE_PUMP_DIVERGENCE_LOOKBACK=20` over full price window
2. Find peak z — if below EXTREME_Z (2.5), PASS (no extreme to diverge from)
3. Find LAST occurrence of peak (`max(idx for idx, z in enumerate(...) if z == peak_z)`)
4. If peak within last BARS (3) bars → PASS (still at peak, not diverging)
5. Count consecutive bars after peak with z-velocity < VEL_THD (-0.3); reset on any recovery bar
6. If ≥ BARS (3) consecutive neg-velocity bars → **REJECT** (negative divergence = trap)

### Integration (detect_zscore_pump line ~267)

```python
# Gate threshold uses spot_lookback (25 bars min), NOT lookback*2 (205 bars — dead code)
if ZSCORE_PUMP_DIVERGENCE_ENABLED and len(prices) >= ZSCORE_PUMP_DIVERGENCE_LOOKBACK + ZSCORE_PUMP_DIVERGENCE_BARS + 2:
    if _check_divergence(prices, lookback):
        return None  # REJECTED
```

## Bugs Caught by ai-engineer Audit (all fixed)

| Bug | Severity | Description |
|-----|----------|-------------|
| Gate threshold 205 bars > fetch 150 | CRITICAL | `lookback * 2 + BARS + 2` → dead code. Fixed to `spot_lookback + BARS + 2` |
| `peak_idx = list.index()` finds first not last | Logic | Fixed to `max(idx for idx, z in enumerate(recent_zs) if z == peak_z)` |
| Off-by-one: most recent bar never scored | Stale data | `range(spot_lookback, len(closes))` → `range(spot_lookback, len(closes) + 1)` |
| Tuner confidence overwritten by z-bonus | Minor | `confidence + conf_bonus` → `max(confidence, confidence + conf_bonus)` |

## Key Design Decisions

1. **Separate spot lookback (20) from signal lookback (100)** — the extreme spike in the 20-bar
   window collapses to +2.985 in the 100-bar window but is still above 2.5. A single lookback
   for both would need to be 20 (noisy) to catch the spike, or 100 (misses it). Separate
   lookbacks solve both requirements.

2. **Full window passed to `_check_divergence`, not sliced** — the peak was ~50 bars before
   signal time. A naive "last N bars" approach misses it. The function receives the full
   history and finds the peak anywhere in the window.

3. **Require 2x lookback bars for gate to activate** — ensures enough history exists to
   find and verify a real extreme, prevents false rejections on short-data tokens.

4. **VEL_THD reset on any recovery bar** — prevents slow bleeds from accumulating false
   positives. Only sustained consecutive decline triggers rejection.