# Hermes Pipeline Test Report - 2026-04-13

## Test Summary

Pipeline executed end-to-end with components: `signal_gen.py`, `decider-run.py`, and `run_pipeline.py`.

---

## DB State Changes

### signals_hermes_runtime.db

| Table | Before | After | Delta |
|-------|--------|-------|-------|
| signals | 6770 | 6770 | 0 |
| decisions | 0 | 1 | +1 |
| token_speeds | 0 | 0 | 0 |
| token_intel | 0 | 0 | 0 |
| cooldown_tracker | 0 | 0 | 0 |
| signal_outcomes | 7 | 7 | 0 |

### signals_hermes.db - regime_log

| Regime | Count |
|--------|-------|
| SHORT_BIAS | 106 |
| LONG_BIAS | 20 |
| NEUTRAL | 1 |

---

## Key Findings

### 1. signal_gen.py - PARTIAL SUCCESS
- Ran successfully without Python exceptions
- Generated regime: BEARISH (L:x1.0 S:x1.2), broad_z=+3.05 [BROAD UPTREND]
- 190 tokens processed
- 1 blocked signal (PYTH - blocked by broad market filter)
- 0 new signals emitted
- Warning: `table token_speeds has no column named wave_phase` (non-fatal)

### 2. decider-run.py - PARTIAL SUCCESS
- Executed and processed 10 trade executions (XRP, ETH, BCH, ASTER, ZK, PENDLE, ORDI, DYDX, FIL)
- All trades FAILED with: `brain.py trade: error: unrecognized arguments: ...`
- 0 decisions actually entered
- Root cause: `brain.py trade` command interface issue (not a Python exception)

### 3. run_pipeline.py - COMPLETED
- Pipeline orchestration completed without crashing
- Sequence: price_collector → signal_gen → ai_decider → decider-run → position_manager → hermes-trades-api
- ai_decider blocked by lock (another process running)
- decider-run failed (script path `/root/.hermes/scripts/decider-run.py` not found)

---

## Issues Identified

1. **decider-run.py path issue**: Uses wrong script path `/root/.hermes/scripts/decider-run.py` but actual file is at `/root/hermes-v3/hermes-export-v3/decider-run.py`

2. **brain.py trade interface broken**: All trade executions fail with "unrecognized arguments" - the brain.py CLI interface needs fixing

3. **token_speeds schema mismatch**: `wave_phase` column doesn't exist in token_speeds table

4. **Regime imbalance**: 84% SHORT_BIAS (106/127) vs 16% LONG_BIAS (20/127) - not balanced as expected

---

## Success Criteria Assessment

| Criteria | Status |
|----------|--------|
| No Python errors/exceptions | PARTIAL (speed tracker warning, but no crashes) |
| All 5 tracking tables increased | FAILED (only decisions went from 0→1) |
| Pipeline completes without crashing | PASS |
| Regime balanced LONG/SHORT/NEUTRAL | FAILED (84% SHORT_BIAS) |

---

## Recommendations

1. Fix `decider-run.py` script path in `run_pipeline.py`
2. Fix `brain.py trade` argument parsing
3. Add `wave_phase` column to `token_speeds` table or remove from SpeedTracker
4. Investigate regime detector for imbalanced SHORT_BIAS output
