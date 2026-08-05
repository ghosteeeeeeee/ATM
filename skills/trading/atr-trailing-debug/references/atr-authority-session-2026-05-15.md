# ATR TP/SL Authority — Session 2026-05-15 Confirmation

## T's Explicit Directive
- **position_manager** is the SOLE authority on setting TP/SL based on values in hermes_constants
- **HL TP/SL orders should be DISABLED** — verify this is the case
- **Guardian** reads values set by position_manager; its job is orphan detection only
- **decider_run** computes initial ATR TP/SL for new trades using `ATR_SL_MIN_INIT` / `ATR_SL_MAX_INIT` from hermes_constants — then position_manager takes over

## Verified Kill Switches

### HL TP/SL Orders — DISABLED ✅
```python
# position_manager.py:87
ATR_HL_ORDERS_ENABLED = False
```
`_execute_atr_bulk_updates()` is dead code (returns `{'disabled...'}` immediately).
Guardian does NOT push SL/TP orders to Hyperliquid. Hermes self-closes via `check_atr_tp_sl_hits()`.

### Guardian Step10 ATR Reconcile — DISABLED ✅
sync-guardian.log: `"Step10 ATR reconcile DISABLED — position_manager is sole ATR engine"`

### self_close_watcher.timer — MASKED/INACTIVE ✅
```
systemctl status hermes-self-close-watcher.timer
→ Unit hermes-self-close-watcher.timer could not be found.
```
`self_close_watcher.py` never runs as a daemon. `UNPROTECTABLE_COINS = frozenset()` (empty).

## Confirmed Data Flow

```
decider_run (signal entry, non-pump):
  → sl=0, tp=0 → brain.py → DB (stop_loss=0, target=0)
  → position_manager._collect_atr_updates() next cycle
  → writes real SL/TP via _persist_atr_levels()

decider_run (signal entry, pump):
  → uses PUMP_SL_PCT / PUMP_TP_PCT (signal_gen.py, NOT hermes_constants — pending move)

position_manager._collect_atr_updates() every 1 minute:
  → _force_fresh_atr() → atr_pct
  → _atr_sl_k_scaled() → k
  → sl_pct = k × atr_pct
  → tp_pct = k × 1.25 × atr_pct
  → _persist_atr_levels() → DB (single UPDATE for both SL+TP)

check_atr_tp_sl_hits() every cycle:
  → reads stop_loss / target from in-memory dict
  → closes trade if price crosses SL/TP

guardian:
  → reads SL/TP from DB only (no independent ATR computation)
  → orphan detection only
  → Step10 ATR reconcile: DISABLED
```

## Pending Changes (from T's directive)

1. **PUMP_SL_PCT / PUMP_TP_PCT** — move from signal_gen.py to hermes_constants. Pump mode should use `ATR_SL_MIN_INIT` / `ATR_TP_MIN` instead of fixed 1.5%/2.5%.
2. **`_compute_dynamic_sl` / `_compute_dynamic_tp`** in position_manager — dead code, never called. `_collect_atr_updates()` is the sole computation path. Consider removing to avoid confusion.
3. **ZK SHORT TP fix** — when `lowest_price = 0` (uninitialized) for SHORT, TP should use `_entry` as reference price (same as SL), not `current_price`.

## Constants Must Come From hermes_constants

No hardcoded ATR values anywhere. All TP/SL computation must import from hermes_constants:
- `ATR_SL_MIN`, `ATR_SL_MAX` — trailing floors/caps
- `ATR_TP_MIN`, `ATR_TP_MAX` — TP floors/caps
- `ATR_TP_K_MULT = 1.25` — canonical TP/SL ratio
- `ATR_SL_MIN_INIT`, `ATR_SL_MAX_INIT` — new trade initial values
- `ATR_K_LOW_VOL / _NORMAL_VOL / _HIGH_VOL` — k tiers (1.0 / 0.75 / 0.5)
- `ATR_PCT_LOW_THRESH = 0.01`, `ATR_PCT_HIGH_THRESH = 0.03` — k tier boundaries