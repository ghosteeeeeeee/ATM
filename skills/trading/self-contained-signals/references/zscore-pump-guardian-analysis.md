# zscore_pump Hunter — Guardian Compatibility Analysis

**Date:** 2026-05-04  
**Context:** Planning Guppy MMA signal, needed to verify if existing self-management pattern works without guardian ATR conflict.

## The Question

Could `zscore_pump_hunter` trades get closed by the guardian's ATR trailing stop before the signal's own exit fires? If so, the same would happen to Guppy.

## Findings

### How zscore_pump Positions Flow

```
zscore_pump_hunter.py
    ├── scan_and_fire()           → reads candles.db, detects zscore momentum
    ├── execute_zscore_trade()    → mirror_open() → HL opens real position
    ├── add_zs_position()         → writes /var/www/hermes/data/zscore-pump.json
    │                             → writes brain.trades with signal='zscore_pump'
    └── check_and_close_positions() → reads own JSON (NOT brain DB)
                                    → checks zscore crosses 0 OR SL/TP hit
                                    → mirror_close() → HL closes position
                                    → updates own JSON + brain DB
```

### Guardian's Role — Orphan Cleanup Only

`hl-sync-guardian.py` does NOT run ATR trailing stops. That is in `position_manager.py`'s `check_atr_tp_sl_hits()`.

Guardian's actual jobs:
1. Reconcile HL ↔ paper DB (orphan detection)
2. Sync realized PnL from HL → brain DB
3. Close orphaned paper trades

Guardian never reads `zscore-pump.json`. It only knows about `brain.trades`.

### position_manager ATR Stop — Runs Separately

`position_manager.py` has its own loop calling `check_atr_tp_sl_hits()` which closes positions based on `stop_loss`/`target` columns.

Key: zscore_pump SETS its own `stop_loss`/`target` in brain DB:
```sql
INSERT INTO trades (
    ...
    signal='zscore_pump',
    sl_distance=0.03,   -- 3% SL (not ATR-based)
    trailing_activation=0.01,
    trailing_distance=0.01,
    is_guardian_close=FALSE,
    guardian_closed=FALSE
)
```

So: if guardian's ATR system somehow reached a zscore_pump position first, it would close it at zscore_pump's own 3% SL — which happens to match what zscore_pump wanted anyway.

### The Idempotency Check

```python
# zscore_pump check_and_close_positions():
mirror_close(token, direction)  # closes on HL

# Guardian orphan handler (next cycle):
# - Queries HL → no position found (already closed by zscore_pump)
# - Finds brain DB row → marks 'HL_CLOSED'
# Safe: mirror_close() is idempotent — no error if already closed
```

`mirror_close()` returns `{"success": True}` even if no position exists. No conflict possible.

## Conclusion

The self-contained pattern is **safe from guardian interference** because:

1. Guardian doesn't track own JSON tracker files — only brain DB rows
2. Guardian orphan cleanup only fires when HL ↔ brain DB disagree
3. Self-contained system writes both simultaneously — no orphan gap
4. Self-contained system closes via own logic first → HL position gone → guardian finds no orphan
5. `mirror_close()` is idempotent — double-close is safe

## Practical Implication for Guppy

Guppy should be built exactly as a zscore_pump clone:
- Own JSON tracker: `/var/www/hermes/data/guppy-tracker.json`
- Own systemd timer: `hermes-guppy.timer` 
- Own exit: fast group flip → `mirror_close()`
- Brain DB writes with `signal='guppy'`, `is_guardian_close=FALSE`

Guardian will never interfere. It becomes a free orphan cleanup service for free.
