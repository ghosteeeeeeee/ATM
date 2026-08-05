# zscore_pump Migration — 2026-05-16

## Problem
`zscore_pump_hunter.py` was a standalone executor that opened positions directly via `mirror_open()`. Guardian had no awareness of these positions — when guardian synced, it saw "unknown position" and closed it immediately.

## Solution
Migrated to pipeline signal: `signals/zscore_pump.py`. Goes through `add_signal()` → `signals_hermes_runtime.db` → `signal_compactor` → hot-set → guardian. Guardian now has full awareness, no conflicts.

## Files Created/Modified

### New: `/root/.hermes/scripts/signals/zscore_pump.py`
- Uses `price_history` (signals_hermes.db) — NOT candles.db directly
- `scan_zscore_pump_signals(prices_dict) -> int` — main scanner
- `run(prices_dict=None)` — wrapper for signals_runner
- `detect_zscore_pump(token, prices, lookback, threshold)` — pure detection
- No own position tracking, no `mirror_open/mirror_close`
- Reads per-token tuned params from `zscore_momentum_tuner.db` when `signal_count >= 15`
- Constants: `ZSCORE_PUMP_LOOKBACK=24`, `ZSCORE_PUMP_THRESHOLD=2.0`, `ZSCORE_PUMP_COOLDOWN_BARS=10`

### Modified: `hermes_constants.py`
```
ZSCORE_PUMP_ENABLED        = True   # ← SET TO TRUE 2026-05-16
ZSCORE_PUMP_PLUS_ENABLED   = True   # LONG direction
ZSCORE_PUMP_MINUS_ENABLED  = True   # SHORT direction
ZSCORE_PUMP_LOOKBACK       = 24     # default lookback bars
ZSCORE_PUMP_THRESHOLD      = 2.0    # |z| must exceed this
ZSCORE_PUMP_COOLDOWN_BARS  = 10     # bars before re-fire
ZSCORE_PUMP_MIN_SIGNALS_FOR_TUNED = 15
PUMP_HUNTER_ENABLED        = False  # standalone executor disabled separately
```

### Modified: `signals/__init__.py`
- Import: `from signals.zscore_pump import scan_zscore_pump_signals as _zscore_pump_run`
- From hermes_constants: `ZSCORE_PUMP_ENABLED, ZSCORE_PUMP_PLUS_ENABLED, ZSCORE_PUMP_MINUS_ENABLED`
- Registry: `{'name': 'zscore_pump', 'enabled': ZSCORE_PUMP_ENABLED, 'run': _zscore_pump_run}`
- `name_to_module`: `'zscore_pump': 'zscore_pump'`

## Key pattern from this migration
A migrated signal does NOT call `mirror_open/mirror_close`. Guardian handles execution. The signal only writes to DB via `add_signal()`.

## Verification (dry run — 2026-05-16)
```
19 signals emitted: AAVE, BSV, COMP, DOT, ENS, ETHFI, FET, LINK, ME, NOT,
                    ONDO, PEOPLE, STRK (LONG), TAO, TRB, TURBO, UNI, XLM, ZK
```
All SHORT except STRK (LONG). Confidences range 80-95%. All dry-run (no trades).

## CRITICAL: Master Kill-Switch Was Blocking (Silent Fail)
The signal was fully wired (registered, name_to_module, imports all correct, no errors) but ZSCORE_PUMP_ENABLED=False was blocking it silently. This is the same silent-fail pattern as `accel_300` missing its `run()` function.

**Lesson:** Per-direction flags True is necessary but not sufficient — master kill-switch must also be True.