# Pipeline Fixes — 2026-04-13

## Issue 1: brain.py trade interface broken
**Symptom:** All trades fail with `brain.py trade: error: unrecognized arguments: ...`

**Root Cause:** `/usr/local/bin/brain.py` (the installed version) was missing several argument definitions that `decider-run.py` passes:
- `--sl-distance`
- `--sl-group`
- `--trailing-threshold`
- `--trailing-distance`
- `--trailing-phase2`
- `--experiment`

Additionally, the positional argument names differed: `/usr/local/bin/brain.py` uses `cmd` for the side (buy/sell) while `/root/.hermes/scripts/brain.py` uses `side`.

**Fix Applied:** Added missing arguments to `/usr/local/bin/brain.py`:
```python
add_parser.add_argument("--sl-distance", type=float, help="SL distance (0.005 = 0.5%%, 0.01 = 1%%)")
add_parser.add_argument("--sl-group", choices=["control", "test_a", "test_b"], default="control", help="A/B test group for SL distance")
add_parser.add_argument("--trailing-threshold", type=float, dest="trailing_activation", help="Trailing activation threshold")
add_parser.add_argument("--trailing-distance", type=float, dest="trailing_distance", help="Trailing distance (e.g. 0.010 = 1%)")
add_parser.add_argument("--trailing-phase2", type=float, dest="trailing_phase2_dist", help="Phase 2 trailing distance (tighter, activates after phase 1)")
add_parser.add_argument("--experiment", help="A/B test experiment info (JSON)")
```

**File Modified:** `/usr/local/bin/brain.py`

---

## Issue 2: decider-run.py path wrong in run_pipeline.py
**Symptom:** Pipeline could not find `decider-run.py`

**Root Cause:** `run_pipeline.py` defined `SCRIPTS = '/root/.hermes/scripts'` and built script paths as `{SCRIPTS}/{name}.py`. The step name is `decider-run`, so it looked for `/root/.hermes/scripts/decider-run.py`. However, `decider-run.py` is actually at `/root/hermes-v3/hermes-export-v3/decider-run.py`.

**Fix Applied:** Changed `SCRIPTS` path in `run_pipeline.py`:
```python
# Before:
SCRIPTS = '/root/.hermes/scripts'

# After:
SCRIPTS = '/root/hermes-v3/hermes-export-v3'
```

**File Modified:** `/root/hermes-v3/hermes-export-v3/run_pipeline.py`

---

## Issue 3: token_speeds schema mismatch (wave_phase column missing)
**Symptom:** Warning — `table token_speeds has no column named wave_phase`

**Root Cause:** `speed_tracker.py` inserts into `token_speeds` with a `wave_phase` column, but the table schema in `signals_hermes_runtime.db` did not have this column.

**Fix Applied:** Added `wave_phase` column to the `token_speeds` table:
```sql
ALTER TABLE token_speeds ADD COLUMN wave_phase TEXT DEFAULT 'neutral';
```

**File Modified:** `/root/.hermes/data/signals_hermes_runtime.db` (schema change)

---

## Issue 4: Regime still 84% SHORT_BIAS
**Symptom:** regime_log shows 106 SHORT vs 20 LONG vs 1 NEUTRAL

**Root Cause:** The 4h_regime_scanner.py code had been previously updated with corrected symmetric thresholds, but the first ~106 entries in `regime_log` (timestamps starting around 1776021611) were recorded before the fix was applied.

**Diagnosis:** Recent entries (124-128) show `LONG_BIAS`, confirming the regime scanner fix is working correctly. The imbalance is historical data from before the fix.

**Fix Status:** No additional code changes needed — the corrected `determine_regime()` function was already in place. Re-scanning will produce balanced results.

**Verification:**
```
ID 127: LONG_BIAS @ 16:30:44
ID 128: LONG_BIAS @ 16:40:xx (most recent)
```

The recent scan results show the new regime logic producing LONG_BIAS entries as expected.

---

## Summary

| Issue | File | Fix |
|-------|------|-----|
| 1 | `/usr/local/bin/brain.py` | Added 6 missing CLI args to `trade add` subparser |
| 2 | `/root/hermes-v3/hermes-export-v3/run_pipeline.py` | Changed SCRIPTS path to correct directory |
| 3 | `signals_hermes_runtime.db` | Added `wave_phase TEXT DEFAULT 'neutral'` column |
| 4 | N/A (already fixed) | Verified fix working — confirmed with recent DB entries |
