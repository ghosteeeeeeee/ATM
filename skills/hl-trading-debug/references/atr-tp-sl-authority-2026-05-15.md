# ATR TP/SL Authority — 2026-05-15 Audit (v2)

## Decision
`position_manager` is SOLE authority for ATR-based TP/SL. All other components read from DB or defer.

## Verified Disabled / Not Used

| File | Check | Result |
|------|-------|--------|
| position_manager.py:90 | `ATR_HL_ORDERS_ENABLED = False` | ✅ HL TP/SL orders disabled |
| position_manager.py:2427 | `_execute_atr_bulk_updates()` not called (kill switch gate) | ✅ |
| hl-sync-guardian.py:3939 | `Step10 ATR reconcile DISABLED` comment | ✅ Guardian never recomputes ATR |
| hl-sync-guardian.py:1060-1061 | "SL/TP owned by position_manager" | ✅ Guardian orphan path doesn't touch SL/TP |
| self_close_watcher.timer | `systemctl status: masked, inactive` | ✅ Daemon never runs |
| self_close_watcher.py | `UNPROTECTABLE_COINS = frozenset()` | ✅ No coins routed through tpsl_utils |
| decider_run.py | Non-pump: `sl=0, tp=0` → brain.py defers | ✅ |

## No Independent ATR Computation Found

- `tpsl_utils` consumers: `hl-sync-guardian.py` (UNPROTECTABLE path) + `self_close_watcher.py` (masked timer) — both dormant
- `UNPROTECTABLE_COINS = frozenset()` — empty, so no live tpsl_utils execution path
- `breakout_engine.py` lines 315-316 compute `stop`/`target` as signal-level (entry price ± atr*k), NOT trade-level SL/TP management
- `decider_run.py` does NOT compute ATR SL/TP for new trades — passes `sl=0, tp=0`

## tpsl_utils Wiring — Verified Correct but Dormant

- `compute_atr_sl_price()` and `compute_atr_tp_price()` match position_manager's `_atr_multiplier()` tier logic 100% (8/8 test cases)
- `self_close_watcher.timer` is masked — the only live consumer (`hl-sync-guardian._check_and_close_breached_trades()`) has empty UNPROTECTABLE_COINS
- **Unused utility functions in position_manager:** `_compute_dynamic_sl()` and `_compute_dynamic_tp()` are defined but never called. `_collect_atr_updates()` is the active computation path.

## Constants — hermes_constants.py (Single Source of Truth)

```python
# Initial entry SL/TP
ATR_SL_MIN_INIT    = 0.005   # 0.50% floor
ATR_SL_MAX_INIT    = 0.010   # 1.0% cap
SL_PCT_FALLBACK    = 0.015   # 1.5%
TP_PCT_FALLBACK    = 0.08    # 8%

# Trailing SL/TP
ATR_SL_MIN         = 0.005   # 0.50%
ATR_SL_MAX         = 0.010   # 1.0%
ATR_TP_MIN         = 0.015   # 1.5%
ATR_TP_MAX         = 0.050   # 5.0%
ATR_TP_K_MULT      = 1.25

# Acceleration phase
ATR_SL_MIN_ACCEL   = 0.007   # 0.70%
ATR_TP_MIN_ACCEL   = 0.010   # 1.0%
```

## Known Issues

### 1. PUMP_SL_PCT / PUMP_TP_PCT not in hermes_constants
- **Location**: signal_gen.py:1221-1222
- **Values**: `PUMP_SL_PCT = 0.015` (1.5%), `PUMP_TP_PCT = 0.025` (2.5%)
- **Problem**: These don't match ATR_SL_MIN_INIT (0.50%) / ATR_TP_MIN (1.5%). Pump mode has its own fixed values unrelated to ATR tiers.
- **Fix needed**: Either add to hermes_constants OR make pump use ATR_INIT values

### 2. Guardian orphan path hardcodes ATR values (lines 1012-1021)
- Guardian computes fallback SL/TP inline instead of reading from DB
- Context: orphan created without position_manager ATR values
- Not critical since position_manager overwrites within 1 min

### 3. Unused `_compute_dynamic_sl` / `_compute_dynamic_tp` in position_manager
- Defined but never called. `_collect_atr_updates()` is the active path.
- Consider removing to avoid confusion

## Diagnosis Commands
```bash
# Verify ATR_HL_ORDERS_ENABLED kill switch
grep "ATR_HL_ORDERS_ENABLED" /root/.hermes/scripts/position_manager.py

# Verify self_close_watcher timer is masked (inactive)
systemctl status hermes-self-close-watcher.timer

# Verify no HL TP/SL orders in recent pipeline runs
grep "_execute_atr_bulk_updates" /root/.hermes/logs/pipeline.log 2>/dev/null | tail -5

# Verify guardian Step 10 is disabled
grep "Step10 ATR reconcile DISABLED" /root/.hermes/logs/hl-sync-guardian.log 2>/dev/null | tail -3

# Check position_manager is writing SL/TP to DB
psql brain -c "SELECT token, stop_loss, target, atr_managed FROM trades WHERE status='open'" 2>/dev/null
```

## Files Involved
- `position_manager.py` — sole ATR engine
- `hl-sync-guardian.py` — orphan detection, reads DB
- `decider_run.py` — defers ATR, pump has fixed values
- `hermes_constants.py` — single source of truth
- `tpsl_utils.py` — canonical ATR price computation (dormant)
- `signal_gen.py` — PUMP_SL_PCT/PUMP_TP_PCT (outlier, not in hermes_constants)