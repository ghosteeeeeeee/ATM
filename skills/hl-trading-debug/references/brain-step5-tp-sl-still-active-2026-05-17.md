# GALA TP/SL Orders Placed on HL — brain.py Step 5 Still Active
**Date:** 2026-05-17
**Symptom:** 2 reduceOnly TP/SL orders (oid 429801128806 TP=0.003328, oid 429801107059 SL=0.003464) placed on Hyperliquid for GALA SHORT trade #10091 at 14:20:11-12 UTC. Position is managed LOCALLY — no HL trigger orders should exist.

## Root Cause

**`brain.py` `add_trade()` Step 5 is LIVE and placing TP/SL on HL.**

When trade #10091 opened, `brain.py` called:
- `place_sl()` → SL oid 429801107059 at 0.003464 (14:20:11.923 UTC)
- `place_tp()` → TP oid 429801128806 at 0.003328 (14:20:12.657 UTC)

Lines 541-543 in `brain.py`:
```python
from hyperliquid_exchange import place_sl as hl_place_sl, place_tp as hl_place_tp
```
These are called in `add_trade()` Step 5 after `mirror_open` + DB INSERT.

## What Was Disabled vs What Wasn't

| Component | Status | What It Controls |
|-----------|--------|-------------------|
| `position_manager._execute_atr_bulk_updates()` | ✅ DISABLED 2026-05-15 | Trailing/ongoing TP/SL updates to HL |
| `hl-sync-guardian` Step 10 (ATR reconcile) | ✅ DISABLED 2026-04-15 | Periodic SL/TP sync from DB to HL |
| `cascade_flip.py` | ✅ DISABLED | Cascade flip re-entry TP/SL |
| `pump_hunter.py` | ✅ DISABLED (`PUMP_HUNTER_ENABLED=False`) | Pump signal TP/SL |
| **`brain.py` Step 5** | ❌ **STILL ACTIVE** | **Initial TP/SL placement when trade opens** |

## Why `hl_sl_order_id` / `hl_tp_order_id` Are NULL

PostgreSQL shows `hl_sl_order_id=NULL, hl_tp_order_id=NULL` for trade #10091. The orders were placed on HL but the order IDs were never written back to the DB — the update code at lines 548-553 either failed silently or was structured such that the orders were placed without recording the IDs.

## The Fix

In `brain.py` `add_trade()`, wrap or remove the Step 5 `place_sl`/`place_tp` calls. Since `position_manager._execute_atr_bulk_updates` is the designated TP/SL authority and is disabled (TP/SL managed locally via DB), `brain.py` should not be placing any HL orders.

Immediate: Cancel the 2 GALA orders on HL (oids 429801128806, 429801107059).

## Diagnostic Commands

```bash
# Check if any HL orders exist for a token
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_orders
orders = get_open_orders()
for o in orders:
    print(o['token'], o['oid'], o['side'], o['triggerCondition'], o['price'], o['reduceOnly'])
"

# Check trade's order ID fields in PostgreSQL
psql brain -c "SELECT trade_id, token, hl_sl_order_id, hl_tp_order_id FROM trades WHERE token='GALA' ORDER BY trade_id DESC LIMIT 5;"

# Find all trades with non-NULL HL order IDs (proves Step 5 was ever called)
psql brain -c "SELECT trade_id, token, hl_sl_order_id, hl_tp_order_id FROM trades WHERE hl_sl_order_id IS NOT NULL OR hl_tp_order_id IS NOT NULL LIMIT 20;"
```

## See Also
- `references/atr-tp-sl-authority-2026-05-15.md` — ATR TP/SL authority architecture
- `references/hl-db-insert-silent-failure.md` — brain.py silent failure patterns
