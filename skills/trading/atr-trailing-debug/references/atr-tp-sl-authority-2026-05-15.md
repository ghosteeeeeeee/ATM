# ATR TP/SL Authority Audit — 2026-05-15

## Authority Chain (VERIFIED 2026-05-15)

| Component | Role | Status |
|-----------|------|--------|
| `hermes_constants.py` | SINGLE source for all ATR TP/SL values | ✅ |
| `position_manager.py` | Sole ATR engine: `_collect_atr_updates()` → `_persist_atr_levels()` → `check_atr_tp_sl_hits()` | ✅ |
| `hl-sync-guardian.py` | Reads SL/TP from DB. Orphan detection only. Step 10 ATR reconcile explicitly disabled (line 3933). `_check_hard_stops()` reads DB values only. | ✅ |
| `decider_run.py` | Non-pump: `sl=0, tp=0` → brain.py → position_manager takes over within 1 min. Pump: uses `PUMP_SL_PCT/PUMP_TP_PCT` from signal_gen.py. | ✅ |
| `self_close_watcher.py` | UNPROTECTABLE coins only. `UNPROTECTABLE_COINS = frozenset()` (empty — no active unprotectable coins). | ✅ |
| HL TP/SL orders | **`ATR_HL_ORDERS_ENABLED = False`** — HL orders disabled, Hermes self-closes internally via `check_atr_tp_sl_hits()`. | ✅ |

## Authority Rules (Sole Source of Truth)

1. **position_manager is the SOLE authority for computing ATR SL/TP values.**
2. All other components READ from DB or DEFER to position_manager — they do NOT compute ATR independently.
3. Guardian orphan path (lines 1060-1061, 1085-1087) explicitly does NOT touch SL/TP.
4. `UNPROTECTABLE_COINS = frozenset()` — no separate self_close path needed; guardian handles orphan detection only.

## Issues Found (2026-05-15)

### Issue 1: PUMP_SL_PCT / PUMP_TP_PCT not in hermes_constants
- **Location:** `signal_gen.py:1221-1222`
- **Values:** `PUMP_SL_PCT = 0.015` (1.5%), `PUMP_TP_PCT = 0.025` (2.5%)
- **Problem:** These are different from `ATR_SL_MIN_INIT` (0.50%) / `ATR_SL_MAX_INIT` (1.0%). Pump mode uses fixed 1.5%/2.5% instead of ATR-based values. Not co-located with other ATR constants.
- **T's intent:** "these should follow the initial ATR values in hermes-constants" — pump mode should use `ATR_SL_MIN_INIT` / `ATR_TP_MIN` instead.

### Issue 2: position_manager.py had local overrides of hermes_constants values (FIXED 2026-05-15)
- **Before:** `position_manager.py:80-83` defined local `TP_PCT=0.08`, `SL_PCT=0.03`, `SL_PCT_MIN=0.01`
- **Problem:** These shadowed the hermes_constants values. `TP_PCT=0.08` was different from `TP_PCT_FALLBACK=0.08` (same value, different semantic purpose). `SL_PCT=0.03` was a hardcoded value not present in hermes_constants at all.
- **Fix applied (2026-05-15):** Removed local definitions, added `SL_PCT_MIN` to hermes_constants, imported via `from hermes_constants import ... SL_PCT_MIN`
- **Verification:**
  ```python
  from position_manager import SL_PCT_MIN, STOP_LOSS_DEFAULT
  from hermes_constants import SL_PCT_MIN as HC_MIN
  assert SL_PCT_MIN == HC_MIN  # ✅ passes
  ```

### Issue 3: Guardian orphan path hardcodes ATR values
- **Location:** `hl-sync-guardian.py:1012-1021`
- **Values:** `sl_pct = ATR_SL_MIN_ACCEL` (0.50%), `tp_pct = ATR_TP_MIN_ACCEL` (0.50%)
- **Problem:** These are used as temporary defaults before position_manager computes ATR levels. Hardcoded, not read from DB or hermes_constants.
- **Context:** These are ONLY used as temporary placeholders during orphan reconciliation — position_manager overwrites them within 1 min. Still should use hermes_constants for clarity.

## Fix Verification Commands

```python
# Verify position_manager imports from hermes_constants
cd /root/.hermes/scripts
python3 -c "from position_manager import SL_PCT_MIN, STOP_LOSS_DEFAULT; print(f'SL_PCT_MIN={SL_PCT_MIN} STOP_LOSS_DEFAULT={STOP_LOSS_DEFAULT}')"
# Expected: SL_PCT_MIN=0.01 STOP_LOSS_DEFAULT=0.015

# Verify no local TP_PCT/SL_PCT remain in position_manager
grep -n "^TP_PCT\|^SL_PCT" position_manager.py
# Expected: no output (all removed)

# Verify hermes_constants has SL_PCT_MIN
grep -n "SL_PCT_MIN" hermes_constants.py
# Expected: SL_PCT_MIN = 0.01    # 1% minimum SL for any trade (hard floor)

# Verify ATR_HL_ORDERS_ENABLED kill switch
grep -n "ATR_HL_ORDERS_ENABLED" position_manager.py
# Expected: ATR_HL_ORDERS_ENABLED = False (line 90)
```

## File Map

| File | ATR TP/SL Role |
|------|---------------|
| `hermes_constants.py` | All ATR values — ATR_SL_MIN, ATR_SL_MAX, ATR_TP_MIN, ATR_TP_MAX, ATR_TP_K_MULT, ATR_SL_MIN_ACCEL, ATR_TP_MIN_ACCEL, ATR_SL_MIN_INIT, ATR_SL_MAX_INIT, SL_PCT_FALLBACK, TP_PCT_FALLBACK, STOP_LOSS_DEFAULT, SL_PCT_MIN, ATR_K_*, PHASE_TIER_*, K_PHASE_* |
| `position_manager.py` | Sole ATR engine: `_collect_atr_updates()`, `_persist_atr_levels()`, `check_atr_tp_sl_hits()`, `_execute_atr_bulk_updates()` (kill-switched off) |
| `hl-sync-guardian.py` | Guardian: reads DB, orphan detection, Step 10 ATR disabled |
| `decider_run.py` | Defers to position_manager (non-pump), pump uses signal_gen PUMP_* constants |
| `self_close_watcher.py` | UNPROTECTABLE coins only (empty set) |
| `tpsl_utils.py` | Canonical ATR price computation for self_close_watcher and guardian |