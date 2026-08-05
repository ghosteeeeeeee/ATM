# ZK Trade ATR SL/TP Flow — Confirmed (2026-05-15)

## ZK SHORT Trade (id=9884)

- **Opened**: 2026-05-15 05:25:07
- **Signal**: `ema-angle-,rs-r30` (ema-angle SHORT + rs-r30)
- **Entry**: 0.01752600
- **SL**: 0.01764868 — 0.70% above entry (protective for SHORT ✓)
- **TP**: 0.01704681 — 2.73% below entry (profit target for SHORT ✓)
- **`atr_managed=True`**, `hl_sl_order_id=null`, `hl_tp_order_id=null` (HL TP/SL orders disabled)

## ATR SL/TP Computation Path

1. `decider_run.py` fires `ema-angle-,rs-r30` signal
2. `decider_run.py:621-624`: non-pump mode → passes `sl=0, tp=0` to `brain.py trade add`
3. `brain.py` stores `stop_loss=0, target=0` in DB initially
4. Next pipeline minute → `position_manager._collect_atr_updates()`:
   - Fetches ATR(14) for ZK
   - `atr_pct = ATR / entry`
   - k from `_atr_sl_k_scaled()` (phase tier)
   - `sl_pct = k × atr_pct`, `effective_sl_pct = max(sl_pct, ATR_SL_MIN_INIT=0.50%)`
   - SHORT: `new_sl = round(entry × (1 + effective_sl_pct), 8)` → 0.01764868
   - SHORT: `new_tp = round(entry × (1 - k_tp × atr_pct), 8)` → 0.01704681
   - `_persist_atr_levels()` writes SL=0.01764868, TP=0.01704681 to DB
5. `hl-sync-guardian` reads from DB only — orphan detection, no ATR computation
6. Guardian breach detector: `_check_and_close_breached_trades()` compares `current_price` vs stored `stop_loss`/`target`

## Implied ATR Validation

- SL 0.70% = k × ATR_pct → implied ATR = 0.70% (k=1.0 for initial/new trade)
- TP 2.73% = k_tp × ATR_pct (k_tp=1.25) → implied ATR = 2.19%
- Both within `ATR_SL_MIN_INIT=0.50%` / `ATR_SL_MAX_INIT=1.0%` and `ATR_TP_MIN=1.5%` / `ATR_TP_MAX=5.0%` ✓

## Confirmation: tpsl_utils is Dormant

- `self_close_watcher.timer`: masked, inactive
- `UNPROTECTABLE_COINS = frozenset()`: empty — no tpsl_utils execution path
- `hl-sync-guardian._check_and_close_breached_trades()` only fires for UNPROTECTABLE coins
- `tpsl_utils` is imported but never called in live operation

## HL TP/SL Orders Confirmed Disabled

```python
# position_manager.py:90
ATR_HL_ORDERS_ENABLED = False  # Kill switch — HL orders disabled
```

`hl_sl_order_id=null` and `hl_tp_order_id=null` in DB confirm no HL orders were placed.