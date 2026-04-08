# ATR + TP/SL Issues — Implementation Plan
**Date:** 2026-04-08
**Status:** PLANNING — Awaiting Orchestrator Assignment

---

## Context / Problem Statement

Two critical bugs remain in the ATM trading system:

1. **ATR TP/SL don't move with the trade in one direction** — TP/SL must move UP for longs (and DOWN for shorts), tracking favorable price movement. Currently `place_tp`/`place_sl` in `hyperliquid_exchange.py` only PLACE orders, never UPDATE them.

2. **TP/SL from ATR are not being updated on HL every minute** — `hl-sync-guardian.py` runs every 60s but does NOT update HL TP/SL orders. It only places SL/TP once at entry (via `brain.py` line ~417). The guardian needs to periodically refresh TP/SL on HL to implement trailing stops and lock in profit.

**Root Cause:** There is no `cancel_or_update_tp` / `cancel_or_update_sl` mechanism to modify an existing HL TP/SL order when price moves favorably.

---

## Goal

Implement a surgical TP/SL updater that:
- Runs inside `hl-sync-guardian.py` sync loop (every 60s)
- Minimizes HL API calls (rate limit risk)
- Only updates when TP/SL need to move in the favorable direction
- Batches cancel + new order into single API call where possible

---

## Architecture

```
hl-sync-guardian.py  (60s loop)
  sync()
    reconcile_hype_to_paper()      ← existing
    sync_pnl_from_hype()           ← existing
    reconcile_paper_to_hype()       ← existing
    reconcile_tp_sl()       ← NEW: update TP/SL that need to move
```

`reconcile_tp_sl()`:
1. Fetch open HL positions + their current prices
2. Fetch open paper trades from DB (`exchange='Hyperliquid'`, `status='open'`)
3. For each open paper trade with TP/SL:
   - Compute new ATR-based TP/SL using `_compute_dynamic_sl()` from `decider-run.py`
   - Compare new TP/SL vs current HL order price
   - If LONG and new SL > current SL → move SL up (cancel + replace)
   - If LONG and new TP > current TP → move TP up (cancel + replace)
   - Same logic for SHORT (inverse direction)
4. Batch cancel/replace into minimal API calls
5. Log each update with reason

---

## Files to Change

### 1. `/root/.hermes/scripts/hyperliquid_exchange.py`
**Changes:**
- Add `cancel_tp(coin: str, oid: int) → dict` — cancel TP by order ID
- Add `cancel_sl(coin: str, oid: int) → dict` — cancel SL by order ID
- Add `replace_tp(coin: str, direction: str, new_tp_price: float, size: float) → dict` — cancel old TP + place new TP in one call
- Add `replace_sl(coin: str, direction: str, new_sl_price: float, size: float) → dict` — cancel old SL + place new SL
- Both use existing `cancel_bulk_orders` + `place_order` primitives

### 2. `/root/.hermes/scripts/decider-run.py`
**Changes:**
- Extract `_compute_dynamic_sl()` to be importable (it already is — function is already module-level)
- Extract `_get_atr()` for use by the guardian (also module-level, already importable)
- These are already at module scope — no changes needed if imported from `decider_run`

### 3. `/root/.hermes/scripts/hl-sync-guardian.py`
**Changes:**
- Add `reconcile_tp_sl()` function (~100-150 lines)
- Call it from `sync()` function
- Import `_compute_dynamic_sl` from `decider_run`
- Fetch open HL positions with `get_open_hype_positions_curl()` (existing)
- Track current HL TP/SL order IDs in `_RECONCILED_STATE_FILE` or a new file
- Only update if movement direction is favorable (unidirectional)
- Rate limit: track `last_tp_sl_update_{token}` with 30s cooldown per token

### 4. `/root/.hermes/scripts/brain.py`
**Minor:** When `place_tp`/`place_sl` succeeds, record the HL `order_id` in the trade record (new DB column `hl_sl_order_id`, `hl_tp_order_id`). This enables surgical cancel+replace.

---

## Database Schema Change

```sql
ALTER TABLE trades ADD COLUMN hl_sl_order_id BIGINT NULL;
ALTER TABLE trades ADD COLUMN hl_tp_order_id BIGINT NULL;
```

---

## Reconciliation Logic Detail

### `reconcile_tp_sl()` pseudocode

```
FOR each open HL position:
    token = position.coin
    direction = position.side (LONG/SHORT)
    current_price = position.entryPx or mark price

    paper_trade = find_open_paper_trade(token, direction)
    if not paper_trade:
        continue

    current_sl = paper_trade.stop_loss
    current_tp = paper_trade.target
    new_sl = _compute_dynamic_sl(token, direction, current_price)
    new_tp = compute_tp(token, direction, current_price)  # same ATR logic for TP

    sl_order_id = paper_trade.hl_sl_order_id
    tp_order_id = paper_trade.hl_tp_order_id

    # LONG: SL and TP only move UP (favorable)
    if direction == 'LONG':
        if new_sl > current_sl:
            replace_sl(token, direction, new_sl, position.size, sl_order_id)
        if new_tp > current_tp:
            replace_tp(token, direction, new_tp, position.size, tp_order_id)

    # SHORT: SL and TP only move DOWN (favorable)
    else:  # SHORT
        if new_sl < current_sl:
            replace_sl(token, direction, new_sl, position.size, sl_order_id)
        if new_tp < current_tp:
            replace_tp(token, direction, new_tp, position.size, tp_order_id)

    UPDATE trades SET stop_loss=new_sl, target=new_tp WHERE id=paper_trade.id
```

---

## Rate Limiting Strategy

- **Global HL API budget:** ~60 calls/min (conservative estimate)
- **Guardian budget:** ~20 calls/min (leaving headroom for other scripts)
- **Per-token cooldown:** 30s between TP/SL updates for same token
- **Batch cancel:** If both SL and TP need replacing, cancel both first, then place both — saves 1 round trip
- **Only update changed orders:** Skip if no movement needed (compare to 6 decimal places)

---

## Key Edge Cases

| Scenario | Handling |
|----------|----------|
| HL TP/SL order already filled between check | Guardian detects via `get_open_hype_positions_curl` — if position gone, skip update |
| Rate limit hit | Log warning, skip remaining updates this cycle, retry next cycle |
| New TP would cross current price (for LONG) | Clamp to `current_price * 0.9995` (0.05% buffer) |
| Token not in `_HL_TICK_DECIMALS` | Fall back to 6 decimals |
| DB read fails | Log error, skip token |
| Cancel fails (order already gone) | Proceed to place new order anyway |

---

## Testing Plan

1. **Unit test `reconcile_tp_sl` logic** with mock HL positions
2. **Dry-run test** — `guardian --dry` should log what it WOULD do without executing
3. **Verify `cancel_bulk_orders` + `place_order` sequence** doesn't race with fills
4. **Monitor rate limits** after deployment for 30 min

---

## Orchestrator Assignment

Once planning is approved, delegate to **Code Expert** (hyperliquid_exchange.py + hl-sync-guardian.py changes) and **Devops** (DB schema migration + systemd service restart if needed).

---
