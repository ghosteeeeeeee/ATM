# Plan: Sub-10 Second Trades + Guardian False Closes

**Date**: 2026-07-20
**Status**: COMPLETE
**Commits**: `8101949`, `a69685a`, `6adf768`

---

## Problem 1: Sub-10 Second Trades Closed Instantly

### Symptom
23 trades under 3 seconds, 35 under 60 seconds. ALL sub-3s trades were SHORT, ALL closed with `atr_sl_hit`, ALL had tiny losses (0.03%-0.6%).

### Root Cause
Pipeline lock released immediately at `run_pipeline.py:176` via `os.close(lock_fd)`. This allows two `position_manager` runs to overlap:

1. **Run 1** (correct): `current_sl=0` → `is_initial_write=True` → `ref_price=entry_price` → SL computed correctly (e.g. ZEN SHORT SL=4.1428, above entry)
2. **Run 2** (overlap): `current_sl=4.1428 > 0` → `is_initial_write=False` → `ref_price=lowest_price` (HL fill) → SL re-anchored to `lowest_price × 1.005` → **SL below entry** → instant trigger

### Evidence
| Trade | Entry | SL (actual) | SL (correct) | Exit | Formula |
|-------|-------|-------------|--------------|------|---------|
| ZEN #12535 SHORT | 4.1222 | 4.1205 | 4.1428 | 4.1234 | `lowest_price(4.1) × 1.005` |
| AXS #12531 SHORT | 0.91455 | 0.9045 | 0.91912 | 0.91555 | `lowest_price(0.9) × 1.005` |
| SKY #12533 SHORT | 0.060111 | 0.060432 | 0.060472 | 0.060472 | `lowest_price(0.060072) × 1.006` |

### Fix (commit `8101949`)

**`tpsl_utils.py` — `compute_atr_sl_tp()`**:
- Added `trade_open_time: Optional[str] = None` parameter
- Added brand-new trade guard: if trade opened <120s ago, force `is_initial_write=True` (prevents wrong-anchor overwrite) AND `is_new_trade=True` (applies INIT floor, bypasses breakeven guard)

**`position_manager.py` — `_collect_atr_updates()`**:
- Passes `trade_open_time=pos.get('open_time')` to `compute_atr_sl_tp()`

### Verification
- Unit test: ZEN SHORT with recent open_time → SL=4.1428 (above entry) ✓
- Unit test: ZEN SHORT with old open_time → SL=4.1205 (normal trailing) ✓
- Unit test: No open_time → backward compatible ✓
- Subagent audit: PASS
- Existing test suite: 6 pre-existing failures (unrelated)

---

## Problem 2: AAVE False Guardian SL Close

### Symptom
AAVE #12538 LONG opened at $90.012, closed 56 seconds later by `guardian_sl` at $90.005 (-0.01%). SL in `trades` table was 89.472 (correct, 0.6% below entry). But guardian closed based on `tpsl_self_close.sl_price=97.99621` — stale value from April 28 when AAVE was ~$98.

### Root Cause
`_check_and_close_breached_trades()` in `hl-sync-guardian.py` ran the breach check BEFORE refreshing TP/SL:

1. Read `sl_price=97.99` from stale `tpsl_self_close` record (from April)
2. Breach check: `90.007 <= 97.99` → TRUE → false close
3. Refresh SL/TP (too late — position already closed)

### Fix (commit `a69685a`)

**`hl-sync-guardian.py` — `_check_and_close_breached_trades()`**:
- Moved TP/SL refresh (ATR computation + `_upsert_self_close`) BEFORE the breach check
- Breach check now uses local `fresh_sl`/`fresh_tp` variables computed from current price
- Deleted dead `self_close_records` code (commit `6adf768`)

### Verification
- Trace: fresh SL = `curr × (1 - 0.006)` ≈ 89.5, not 97.99 ✓
- Non-unprotectable coins unaffected (separate code path) ✓
- Subagent audit: PASS

---

## Files Changed

| File | Commit | Lines |
|------|--------|-------|
| `scripts/tpsl_utils.py` | `8101949` | +33, -6 |
| `scripts/position_manager.py` | `8101949` | +1 |
| `scripts/hl-sync-guardian.py` | `a69685a` + `6adf768` | +144, -102 |

## Related Constants (hermes_constants.py)

| Param | Value | Used by |
|-------|-------|---------|
| `ATR_SL_MIN_INIT` | 0.6% | New trade SL floor |
| `ATR_SL_MIN_ACCEL` | 0.5% | Established trade SL floor |
| `ATR_SL_MAX` | 0.8% | Absolute SL cap |
| `ATR_TP_MIN` | 1.0% | TP floor |
| `ATR_K_NORMAL_VOL` | 1.0 | Guardian SL k multiplier |

## Lessons Learned

1. **Pipeline lock must persist** — releasing it immediately causes overlapping runs. The `os.close(lock_fd)` at line 176 was added to prevent blocking but introduced this bug.
2. **DB reads before refresh are dangerous** — the guardian's breach check used stale DB values. Always compute fresh values first.
3. **Brand-new trades need protection** — the first 120s after entry are critical. SL should anchor to entry_price, not peak/low.
4. **Unprotectable coins accumulate stale state** — `tpsl_self_close` records persist across trade cycles. Must refresh on every guardian run.
