# CEO Decision: RSI Timeframe Mismatch Between Signals and Filters

**Date:** 2026-09-22
**Issue:** Timeframe mismatch between signal generators and execution filters causing bad entries
**Priority:** 🔴 CRITICAL — directly caused bad COMP SHORT entry
**Decision by:** CEO (Hermes Trading System)

---

## The Problem

Three independent RSI computation points in the pipeline can disagree on the same token:

| Component | Data Source | Timeframe | Example (COMP SHORT) |
|-----------|------------|-----------|---------------------|
| Signal generator (pullback_entry.py) | `candles_5m` | 5-minute | RSI = 13.04 (extreme oversold) |
| Execution filter (`_ctx_gate_get_rsi`) | `candles_1m` | 1-minute | RSI = 56.54 (neutral) |
| Entry feature recorder (`feature_recorder`) | `price_history` | 1-minute | RSI = 56.54 (neutral) |
| SIGNAL_FILTER (`decider_run.py:975`) | signal metadata `rsi_14` | varies | `None` (field mismatch — looks for `rsi_14`, signal stores `rsi`) |

**What happened:** COMP SHORT signal fired at RSI 13.04 (5m oversold). By execution time (6.16 min later), 1m RSI had recovered to 56.54. The execution filter saw neutral RSI and let it through. Trade entered at the wrong RSI level.

---

## Scope Audit: 42 Signal Files Analyzed

### Signals using `candles_5m` for RSI (HIGH RISK — mismatch with 1m execution filter):
1. `pullback_entry.py` — stores RSI ✅
2. `doji_top.py` — stores RSI ✅
3. `doji_bottom.py` — stores RSI ✅
4. `bb_bounce.py` — stores RSI ✅
5. `bb_bounce_long.py` — stores RSI ✅
6. `bb_bounce_short.py` — stores RSI ✅
7. `bb_bounce_v2_long.py` — stores RSI ✅
8. `bb_bounce_v2_short.py` — stores RSI ✅
9. `bb_bounce_v3_long.py` — stores RSI ✅
10. `trend_ignition.py` — stores RSI ✅
11. `oversold_bounce.py` — stores RSI ✅
12. `volume_breakout.py` — stores RSI ✅
13. `neutral_sniper.py` — stores RSI ✅
14. `range_reversion_long.py` — stores RSI ✅
15. `range_reversion_short.py` — stores RSI ✅
16. `range_reversion.py` — stores RSI ✅
17. `hh_hl.py` — stores RSI ✅
18. `coiled_spring.py` — NO RSI in metadata
19. `coiled_spring_trigger.py` — NO RSI in metadata
20. `macd_divergence.py` — NO RSI in metadata
21. `open_skies.py` — NO RSI in metadata

### Signals using `candles_1h` for RSI (EXTREME MISMATCH):
22. `wall_street_cycle.py` — stores RSI ✅
23. `continuation.py` — NO RSI in metadata

### Signals using `candles_1m` for RSI (ALIGNED with filter):
24. `btc_pump_rider.py` — NO RSI in metadata
25. `slow_grind_long.py` — stores RSI ✅
26. `slow_grind_short.py` — stores RSI ✅
27. `rr_structural_v2_long.py` — NO RSI in metadata
28. `rr_structural.py` — NO RSI in metadata
29. `r2_trend_v2_long.py` — NO RSI in metadata
30. `range_finder_short.py` — stores RSI ✅ (resamples 1m→5m)

### Signals using `price_history` (≈1m) for RSI (ALIGNED with filter):
31. `range_breakout.py` — stores RSI ✅
32. `range_finder.py` — stores RSI ✅
33. `ema300_dip_long.py` — stores RSI ✅
34. `ema300_dip_short.py` — stores RSI ✅
35. `ema20_50.py` — stores RSI ✅
36. `return_exhaustion.py` — stores RSI ✅
37. `return_exhaustion_short.py` — NO RSI in metadata
38. `accel_300_v3_long.py` — stores RSI ✅
39. `accel_300_v3_short.py` — stores RSI ✅
40. `r2_trend_long.py` — NO RSI in metadata
41. `r2_trend_short.py` — NO RSI in metadata
42. `pump_catcher.py` — stores RSI ✅

### Additional Bug Found: SIGNAL_FILTER RSI Check is a No-Op for Most Signals

`decider_run.py:975` checks `sig.get('rsi_14')` but signals store RSI as `'rsi'`, not `'rsi_14'`. The field name mismatch means the global SIGNAL_FILTER RSI check **never fires** for any signal that stores RSI under the `'rsi'` key. This is a silent bug that has been allowing overbought/oversold entries through.

---

## DECISION: Three-Part Fix

### Part 1: IMMEDIATE (Today) — Fix the Silent Bugs

**1a. Fix SIGNAL_FILTER field name mismatch**
- `decider_run.py:975`: Change `sig.get('rsi_14')` → `sig.get('rsi') or sig.get('rsi_14')`
- This immediately activates the global RSI filter that has been silently disabled

**1b. Add execution-time RSI re-validation for ALL signals that store RSI**
- For every signal that stores `'rsi'` in metadata, compare the stored detection-time RSI against the live 1m RSI at execution time
- If drift exceeds threshold (±15 points), reject the signal as stale
- This catches the COMP SHORT case directly

**1c. Add signal staleness limit**
- Maximum time between signal creation and trade execution: 5 minutes default
- Signals that rely on momentum (btc_pump_rider, accel_300): 2 minutes
- Signals that rely on structure (pullback_entry, bb_bounce): 5 minutes
- Store detection timestamp in signal metadata, check at execution

### Part 2: SHORT-TERM (This Week) — Standardize RSI Timeframe

**All signals that store RSI in metadata must compute it from `candles_1m` (or `price_history`).**

This is the root cause fix. The signal's RSI value must match what the execution filter will see.

For signals where5m/15m/1h RSI is semantically important for detection:
- Keep the higher-timeframe RSI for **detection logic** (trend checks, structure)
- Switch to 1m RSI for the **stored RSI value** that goes to metadata and filters
- The signal can still use 5m RSI internally for other decisions

**Signals to update (21 files using candles_5m/15m/1h for stored RSI):**
1. pullback_entry.py
2. doji_top.py
3. doji_bottom.py
4. bb_bounce.py, bb_bounce_long.py, bb_bounce_short.py
5. bb_bounce_v2_long.py, bb_bounce_v2_short.py, bb_bounce_v3_long.py
6. trend_ignition.py
7. oversold_bounce.py
8. volume_breakout.py
9. neutral_sniper.py
10. range_reversion_long.py, range_reversion_short.py, range_reversion.py
11. hh_hl.py
12. wall_street_cycle.py

### Part 3: MEDIUM-TERM (Next Sprint) — Architectural Fix

**Create a shared RSI utility that all signals import.**

```python
# scripts/signals/rsi_utils.py
def compute_rsi_1m(token, period=14):
    """Standard RSI from candles_1m — used for all signal metadata."""
    
def compute_rsi_from_closes(closes, period=14):
    """RSI from arbitrary closes — used for detection logic."""
```

- All signals import `compute_rsi_1m()` for their stored RSI value
- Internal detection logic can still use `compute_rsi_from_closes()` with whatever timeframe
- Eliminates duplicated RSI functions (currently 20+ copies)
- Single source of truth for RSI computation

---

## Execution Order

| Step | Action | Files | Risk |
|------|--------|-------|------|
| 1 | Fix SIGNAL_FILTER field name | `decider_run.py` | LOW — activates existing logic |
| 2 | Add drift detection | `decider_run.py` | LOW — new filter, doesn't change existing |
| 3 | Add staleness limit | `signal_compactor.py` | LOW — new filter |
| 4 | Create rsi_utils.py | new file | NONE |
| 5 | Migrate signals to 1m RSI | 21 signal files | MEDIUM — must test each |
| 6 | Add shared RSI import | all signal files | LOW — mechanical change |

---

## Expected Impact

- **Immediate:** SIGNAL_FILTER RSI check activates → blocks overbought/oversold entries (estimated 2-3 bad entries/week blocked)
- **Short-term:** Drift detection catches stale signals → prevents COMP SHORT-type entries
- **Medium-term:** Standardized RSI eliminates class of bugs entirely

---

## Risk Assessment

- **Doing nothing:** Continued bad entries from timeframe mismatches. Each bad entry costs $0.50-$2.00.
- **Part 1 only:** Fixes the immediate bugs, catches most cases. ~80% risk reduction.
- **Parts 1+2:** Eliminates the root cause. ~95% risk reduction.
- **Parts 1+2+3:** Full architectural fix + maintainability. ~100% for this class of bug.

**Recommendation: Parts 1+2 minimum. Part 3 when convenient.**
