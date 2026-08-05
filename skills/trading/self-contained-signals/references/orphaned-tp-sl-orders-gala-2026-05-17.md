# Orphaned TP/SL Orders — GALA Incident 2026-05-17

## What Happened

GALA SHORT trade opened via `brain.py` `add_trade()` at 14:20. `brain.py` immediately placed:
- TP at 0.003328 (reduceOnly, oid 429801128806)
- SL at 0.003464 (reduceOnly, oid 429801107059)

Position closed (reason unknown — market close, signal close, or manual). 
TP/SL orders remained live on Hyperliquid with no position to close.

**Current state (live HL data):**
```
Total open orders: 2 (both GALA)
- TP 0.003328, oid 429801128806, reduceOnly, side=B
- SL 0.003464, oid 429801107059, reduceOnly, side=B
Account positions: NONE
```

## Root Cause

`brain.py`'s `add_trade()` (lines 542-543) calls `place_sl()` and `place_tp()` synchronously when opening a trade, storing order IDs in `hl_sl_order_id`/`hl_tp_order_id` columns. There is **no cleanup path** — when a position closes (via any mechanism), the TP/SL orders are not cancelled.

`brain.py` does NOT have a function to cancel orphaned TP/SL orders when a position disappears.

## The Gap in Guardian

The guardian's orphan handler (`check_orphaned_trades`) only handles cases where:
1. HL position exists but no brain DB row → close via market
2. brain DB row exists but no HL position → mark brain DB as closed

It does NOT check for "brain DB row has `hl_tp_order_id` set but no HL position" and cancel those orders.

## Fix Required

Two-part fix needed:

### 1. Guardian: Cancel TP/SL orders for brain DB rows with no HL position

In `hl-sync-guardian.py`'s orphan handler, add:
```python
# Cancel any open TP/SL orders for the orphaned trade
if trade['hl_sl_order_id']:
    cancel_result = exchange.cancel-order(trade['hl_sl_order_id'])
if trade['hl_tp_order_id']:
    cancel_result = exchange.cancel-order(trade['hl_tp_order_id'])
```

### 2. Brain: Cancel TP/SL orders when trade is closed externally

In `close_position.py` or wherever external closes happen, add:
```python
# Cancel any open TP/SL reduceOnly orders
exchange.cancel-order(brain_row['hl_sl_order_id'])
exchange.cancel-order(brain_row['hl_tp_order_id'])
```

## Related Code

- `brain.py` lines 539-553: `add_trade()` places TP/SL via `hl_place_sl`/`hl_place_tp`
- `hyperliquid_exchange.py` line 1413: `place_tp()` — creates reduceOnly trigger order
- `hyperliquid_exchange.py` line 1481: `place_sl()` — creates reduceOnly trigger order
- `hyperliquid_exchange.py` lines 1885-1960: `replace_tp()`/`replace_sl()` — modify existing TP/SL
- `hl-sync-guardian.py` orphan handler at ~line 607: `check_orphaned_trades()` — needs TP/SL cleanup

## Live HL Order IDs (GALA — for manual cancellation if needed)

- TP order: `429801128806` (price 0.003328, size 2955)
- SL order: `429801107059` (price 0.003464, size 2955)

## Prevention

When any code closes a position (guardian, position_manager, manual, market fill), it must also cancel any associated open TP/SL orders. This should be a standard cleanup pattern, not an optional step.