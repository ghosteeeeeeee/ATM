# Ghost Trade Debug Reference (2026-05-16)

## GALA Ghost Trade — RESOLVED

**Trade #10013:** `token=GALA, direction=LONG, entry_price=0.003465, stop_loss=null, exit_price=0, pnl_pct=-100.0, close_reason=zscore_pump_SL, signal=zscore_pump, is_guardian_close=f`

**Root cause:** Old standalone `zscore_pump_hunter.py` created DB records without stop_loss via `_create_brain_record()` (INSERT has no `stop_loss` column), then closed them with fake -100% PnL when its local SL triggered. The local `zscore-pump.json` had `stop_price=0.0031234` but PostgreSQL never received it.

**Fix applied:**
```
hermes_constants.py line 567:
  ZSCORE_PUMP_ENABLED = False
```

**Verification:**
- `hermes-zscore-pump-hunter.service` — found in `ps aux` as failed/terminated, but no unit file in `/etc/systemd/system/` (service definition never installed)
- Process was SIGTERM'd at 2026-05-16 05:30:08 UTC — never restarted
- Old standalone line 437: `if not ZSCORE_PUMP_ENABLED: log("ZSCORE_PUMP_ENABLED=False — block zscore_pump from firing")` — block fires on next invocation
- `zscore-pump.json` (old standalone position file): 0 open positions, 98 closed
- No systemd, cron, or timer referencing `zscore_pump_hunter.py`

**New pipeline:** `signals/zscore_pump.py` → `add_signal()` → `signals_hermes_runtime.db` → `signal_compactor` → `tpsl_utils` for proper SL/TP management. Has independent killswitches `ZSCORE_PUMP_PLUS_ENABLED` / `ZSCORE_PUMP_MINUS_ENABLED`.

---

## SUI Ghost Trade — OPEN (deferred)

**Trade #10051:** `token=SUI, direction=LONG, entry_price=1.064, stop_loss=1.0923` (SL ABOVE entry = instant trigger)

**Symptom:** Initial SL set at/below entry price, instantly triggered.

**Likely cause:** `compute_atr_sl_tp` anchor bug when `is_new_trade` gate is bypassed. SL should use `INIT_SL_PCT` from `hermes_constants` for new trades, not current price as anchor.

**Status:** Not addressed — deferred to next session.