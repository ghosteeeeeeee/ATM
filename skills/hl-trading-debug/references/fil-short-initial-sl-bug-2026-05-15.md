# FIL SHORT — Initial SL Set to Hardcoded Fallback (2026-05-14)

## Symptom

FIL SHORT trade #XXXX opened at entry = 1.05370000.
DB shows `stop_loss = 1.00700000` (4.43% ABOVE entry — price must RALLY 4.43% to hit SL).
Expected SL at 1% away: **1.04316300**.
Trade closed in 4 seconds via `atr_sl_hit` — price never went near the SL.

## Root Cause

`decider_run.py` lines 620-624 defers SL/TP to position_manager by passing `sl=0, tp=0` to brain.py:

```python
# A/B TEST DISABLED (2026-04-17) — ATR handles SL/TP via position_manager.
# position_manager._collect_atr_updates() sets dynamic ATR-based SL/TP within 1 min.
sl_pct_val = 0.0  # defer to ATR
tp_pct_val = 0.0  # defer to ATR
```

`brain.py` `add_trade()` stores whatever SL is passed to it — if `sl=0`, the DB column gets `0` (or a fallback).
`position_manager._collect_atr_updates()` runs in the same pipeline cycle (position_manager step, after decider_run),
but only updates trades where `current_sl <= 0`. If the initial SL was somehow set to a hardcoded value
other than 0, `_collect_atr_updates()` might not correct it.

**The SL value 1.00700000 looks like a static fallback** — round number, not ATR-scaled.
Possible sources:
1. `hl-sync-guardian.py` `_update_hl_positions_from_hl()` fallback at lines 1011-1020 (but would be 0.20% = 1.0558, not 1.007)
2. `get_trade_params()` in position_manager.py fallback (line 1983: `sl_pct_fallback = SL_PCT_FALLBACK = 0.015` = 1.5%, would give 1.0387)
3. A hardcoded test value somewhere in decider_run or brain.py

## Key Diagnostic

Check what `_collect_atr_updates()` does for a newly opened trade:
```python
# In position_manager.py _collect_atr_updates(), lines 1590-1591:
if not current_sl or float(current_sl) <= 0:
    sl_pct = min(sl_pct, ATR_SL_MAX_INIT)  # ATR_SL_MAX_INIT = 1.0%
```

This only triggers when `current_sl <= 0`. If the trade opens with `stop_loss = 1.00700000` (non-zero),
the condition `if not current_sl or float(current_sl) <= 0` is **False**, so the clamp is NOT applied.
The existing SL value stays as-is — no ATR correction happens.

## Two Bugs in One

**Bug A (decider_run/brain.py):** Initial SL written to DB is not ATR-based.
- If decider_run passes `sl=0` and brain.py stores `0` in the DB, `_collect_atr_updates()` should correct it
- But if brain.py has a fallback that writes a hardcoded value instead of 0, correction never triggers

**Bug B (position_manager):** `_collect_atr_updates()` only corrects when `current_sl <= 0`.
- If the initial SL was set to ANY positive value (even a wrong one), the correction is skipped.
- Should instead check: is the existing SL ATR-distance-appropriate for current price + ATR?

## FIL SL Math

- Entry: 1.0537
- Stored SL: 1.007 (4.43% above entry — WRONG direction for SHORT protection)
- Expected (1% away): 1.0432
- ATR at time: ~0.0040 (0.38% of price)
- With ATR_SL_MAX_INIT=1.0%, expected SL = 1.0537 × 0.99 = 1.0432

The SL=1.007 is NOT ATR-scaled. It's a fixed hardcoded value.

## Fix Needed

1. In `decider_run.py`, ensure initial SL is either:
   - Properly ATR-calculated at open time, OR
   - Explicitly set to 0 so position_manager always corrects it

2. In `position_manager._collect_atr_updates()`, change the correction trigger from:
   ```python
   if not current_sl or float(current_sl) <= 0:
   ```
   to also trigger when the existing SL is not ATR-consistent with the current price/ATR:
   ```python
   if not current_sl or float(current_sl) <= 0 or not _is_sl_atr_valid(current_sl, entry, current_price, atr):
   ```