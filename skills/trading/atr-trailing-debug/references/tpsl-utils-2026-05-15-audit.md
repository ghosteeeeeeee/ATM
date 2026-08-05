# tpsl_utils.py Audit — 2026-05-15

## Files Audited
- `/root/.hermes/scripts/tpsl_utils.py` (522 lines, complete rewrite as sole ATR authority)
- `/root/.hermes/scripts/position_manager.py` — `_collect_atr_updates` (delegates to `compute_atr_sl_tp`)
- `/root/.hermes/scripts/decider_run.py` — HL TP/SL disabled confirmed (sl=0, tp=0)
- `/root/.hermes/scripts/hl-sync-guardian.py` — Step 10 ATR reconcile disabled (line 3933)
- `/root/.hermes/scripts/self_close_watcher.py` — uses `compute_atr_sl_price`/`compute_atr_tp_price`

## Architecture — VERIFIED CORRECT

| Component | Role | Status |
|-----------|------|--------|
| `hermes_constants.py` | Single source for all ATR values. `ATR_UPDATE_THRESHOLD=0.0015` added (line 269). | ✅ |
| `position_manager._collect_atr_updates()` | Orchestration + DB persist; delegates SL/TP math to `tpsl_utils.compute_atr_sl_tp()`. `ATR_UPDATE_THRESHOLD_PCT = ATR_UPDATE_THRESHOLD` (line 81). | ✅ |
| `tpsl_utils.compute_atr_sl_tp()` | Sole ATR SL/TP computation authority | ✅ |
| `tpsl_utils.compute_atr_sl_price()` | Standalone SL price for guardian/self_close_watcher | ✅ FIXED |
| `tpsl_utils.compute_atr_tp_price()` | Standalone TP price for guardian/self_close_watcher | ✅ |
| `decider_run.py` | Passes sl=0, tp=0 → HL; position_manager sets ATR levels | ✅ |
| `hl-sync-guardian.py` | Reads SL/TP from DB; orphan detection only; Step 10 ATR disabled | ✅ |
| `self_close_watcher.py` | Uses `compute_atr_sl_price`/`compute_atr_tp_price` from tpsl_utils | ✅ |

## BUG #1 — `compute_atr_sl_price` LONG anchor — FIXED ✅

**Location**: `tpsl_utils.py` lines 193-195 (before fix)

**Problem**: For LONG, the anchor was `entry_price`. If price has risen since entry, `entry_price < current_price` and the SL would be set below entry, not below current. A protective LONG SL should always be below the current price.

**Fix applied (2026-05-15)**: `compute_atr_sl_price` and `compute_atr_tp_price` now accept optional `highest_price`/`lowest_price` params:
```python
def compute_atr_sl_price(token, direction, entry_price, current_price,
                         highest_price=0.0, lowest_price=0.0) -> float:
    # ...
    if direction == 'LONG':
        anchor = highest_price if highest_price > 0 else current_price
        return round(anchor * (1 - eff), 8)
    else:
        anchor = lowest_price if lowest_price > 0 else current_price
        return round(anchor * (1 + eff), 8)
```
LONG uses `highest_price` (peak) as anchor if available, else `current_price`. SHORT uses `lowest_price` (nadir) if available, else `current_price`. Backward compatible — all existing 4-arg calls work without changes.

## BUG #2 — `ATR_UPDATE_THRESHOLD_PCT` hardcoded — FIXED ✅

**Location**: `position_manager.py` line 81 (before fix)
```python
ATR_UPDATE_THRESHOLD_PCT = 0.0015  # hardcoded
```

**Fix applied (2026-05-15)**:
1. `ATR_UPDATE_THRESHOLD = 0.0015` added to `hermes_constants.py` (line 269)
2. `position_manager.py` imports `ATR_UPDATE_THRESHOLD` from hermes_constants
3. `position_manager.py:81` now reads: `ATR_UPDATE_THRESHOLD_PCT = ATR_UPDATE_THRESHOLD`

**Note**: `ATR_UPDATE_THRESHOLD_PCT` name kept (vs renaming to `ATR_UPDATE_THRESHOLD`) to avoid rewriting all internal references in position_manager. The hermes_constants name is the authoritative one.

## NON-CRITICAL ISSUES

| Item | Location | Severity | Status |
|------|----------|----------|--------|
| `STOP_LOSS_DEFAULT` still in hermes_constants (line 280) | hermes_constants.py | Low — dead code | Pending T approval for removal |
| `_compute_dynamic_sl` / `_compute_dynamic_tp` still in position_manager.py | position_manager.py ~1397-1488 | Low — dead code | Pending T approval for deletion |
| `compute_atr_sl_price` doesn't import `ATR_TP_K_MULT` | tpsl_utils.py line 190 | Low — k computed via `_atr_tier`, TP uses k_tp inline | No action needed |

## VERIFIED CORRECT

- `compute_atr_sl_tp` SHORT formula: `new_sl = round(ref_price * (1 + eff_sl_pct), 8)` — anchor = `_peak_low` (profit) or `current_price` (new/underwater)
- `compute_atr_sl_tp` LONG formula: `new_sl = round(ref_price * (1 - eff_sl_pct), 8)` — anchor = `_peak_high` (profit) or `current_price` (new/underwater)
- Trailing SL gate: LONG `new_sl > current_sl` ✅, SHORT `new_sl < current_sl` ✅
- Trailing TP gate: LONG `tp_at_ref < current_tp` (block loosen) ✅, SHORT `tp_at_ref >= current_tp` (block loosen) ✅
- INIT→ACCEL migration: `_atr_computed_sl` saved before trailing gate ✅
- `compute_atr_sl_tp` INIT floor selection: `ATR_SL_MIN_INIT` for new trades, `ATR_SL_MIN_ACCEL` for established ✅
- `_collect_atr_updates` correctly calls `compute_atr_sl_tp()` with all args ✅
- `_collect_atr_updates` uses `_atr_computed_new_sl` for INIT→ACCEL migration write ✅
- k-tier multiplier (`_atr_tier`): 1.0 (<1% ATR), 0.75 (1-3%), 0.5 (>3%) — matches `position_manager._atr_multiplier` ✅
- Phase k multipliers from hermes_constants: `K_PHASE_ACCEL_*`, `K_PHASE_EXH_*`, `K_PHASE_EXT_*` ✅
- HL TP/SL disabled in decider_run (sl=0, tp=0 passed to HL) ✅
- Guardian Step 10 ATR reconcile explicitly disabled ✅
- `ATR_SL_MIN_INIT=0.005` and `ATR_SL_MAX_INIT=0.010` confirmed in hermes_constants ✅
- `ATR_TP_MIN_INIT` NOT in hermes_constants (same value as `ATR_TP_MIN=0.015`; user flagged for removal) — not used in new code ✅
- Syntax verified: `python3 -m py_compile tpsl_utils.py position_manager.py` → both OK ✅

## Audit Workflow

When auditing a code rewrite or refactor:
1. Read the entire new file (all lines — don't truncate mid-function)
2. Trace every code path for both LONG and SHORT directions
3. Check dict keys returned match what caller consumes (`needs_sl`, `needs_tp`, `new_sl`, `new_tp`, `_atr_computed_new_sl`, `is_init_to_accel_migration`)
4. Verify constant imports match what's actually used (no missing imports, no hardcoding)
5. Check backward compatibility — existing callers with 4 args must still work with new 6-arg signature
6. Verify all operators (+/-) are correct for each direction
7. Check the trailing gate logic (only tighten, never loosen) for both SL and TP
8. Run `python3 -m py_compile` on all modified files
9. Delegate to ai-engineer subagent for full audit when time permits (but verify independently too — subagent can timeout)