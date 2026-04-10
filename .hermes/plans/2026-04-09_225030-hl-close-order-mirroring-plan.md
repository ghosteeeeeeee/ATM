# HL Close Order Mirroring — Plan
**Date:** 2026-04-09 22:50 UTC
**Status:** PLANNING ONLY

---

## Situation Assessment

### Orphaned orders currently on HL
| Token | # Orders | Size each | Type | Trigger | Status |
|-------|----------|-----------|------|---------|--------|
| ASTER | 4 | 16.0 | reduceOnly SELL | None | STALE — old SL/TP levels |
| IMX | 2 | 68.6 | reduceOnly SELL | None | Possibly stale |

All 6 are `side=A` (ASK = SELL), `reduceOnly=true`, no trigger price. These are limit orders placed when `ATR_HL_ORDERS_ENABLED=True` — they were never cancelled when we switched to internal ATR close and disabled the HL path.

### Why they CAN interfere
1. **Asterisk (ASTER)** has 4 orders × 16.0 = 64 units of sell pressure sitting on HL at old SL levels. If price drops to those levels, HL will close the position BEFORE our internal `check_atr_tp_sl_hits()` fires (which runs every 1 min via pipeline).

2. **IMX** has 2 orders × 68.6 = 137.2 units. Same issue.

3. **Race condition**: HL fills the order → position closes → `hl-sync-guardian` sees the HL position gone but DB still open → ghost position → corrupts stats.

### Why they MIGHT not interfere (current state)
- These are limit orders with NO trigger price — they are resting limit orders, not stop-loss triggers
- `side=A` means they will only fill if someone else is buying at that price (taker side)
- ReduceOnly means they won't open new shorts, but they DO act as sell walls
- If the position is closed internally first (via `check_atr_tp_sl_hits()`), the HL orders become orphaned — then they sit there until cancelled

### Core problem we need to solve
The architecture is now:
```
Internal ATR close (DB) + market mirror to HL (via mirror_close)
↑ We control this
```
But we also have old HL SL/TP limit orders sitting there from when we DID use the HL order path. These need to be either:
- A) Cancelled outright
- B) Kept alive and updated as ATR levels change (preferred if we can make it work)

---

## Options

### Option A: Cancel All Orphaned HL Orders (Clean Break)
**Approach:** On pipeline startup (or next cycle), find all reduceOnly orders for tokens with open positions and cancel them. Let internal ATR hit detection handle all closes, mirror to HL via market order.

**Pros:** Simple, eliminates race condition entirely
**Cons:** We lose the "free" HL-side SL protection. If Hermes crashes, pipeline stalls, or is offline, HL positions won't auto-close.
**Verdict:** Not ideal — leaves HL unprotected.

### Option B: Keep HL Orders Live + Update Them Each Cycle (Preferred)
**Approach:**
1. Keep the existing `_collect_atr_updates()` → `_persist_atr_levels()` → `check_atr_tp_sl_hits()` internal path
2. When `ATR_HL_ORDERS_ENABLED=True` (kill switch re-enabled), `_execute_atr_bulk_updates()` writes updated SL/TP to HL — but this requires the order to have a trigger price, which our current HL order format lacks
3. Instead: use `cancel_bulk_orders` + `place_bulk_orders` each cycle with `tpsl="sl"` / `tpsl="tp"` trigger orders

**Problem with current order format:** The existing orders have `limitPx=price, reduceOnly=true` — these are LIMIT orders, not TRIGGER orders. Trigger orders require `triggerPx` + `isMarket=True` + `tpsl="sl"|"tp"`. The HL API distinguishes:
- Limit close: `limitPx=X, reduceOnly=true, orderType={limit:{...}}` — fills when price reaches X
- Trigger close: `triggerPx=X, isMarket=True, tpsl="sl", reduceOnly=true` — triggers market close when price crosses X

**Decision needed:** Are trigger orders the right approach? Or is market-close-via-mirror_close the better path and we just need to cancel all reduceOnly limit orders for open positions?

### Option C: Hybrid (Cancel Stale, Keep Internal as Source of Truth)
**Approach:**
1. Cancel all existing reduceOnly orders for tokens with open positions (clean slate)
2. Keep `ATR_HL_ORDERS_ENABLED=False` (internal close only)
3. When position closes internally, `mirror_close()` fires a market close on HL — this is our HL exit
4. Accept that if Hermes is down, HL positions won't auto-close until it comes back

**Verdict:** This is the current state. Option C works but means we need to cancel the existing stale orders.

---

## Recommended Path: Option C (with cleanup) + Future Option B as Upgrade

### Step 1: Cleanup — Cancel All Existing Orphaned HL Orders
Run once: for every reduceOnly order on HL for a token that has an open position in brain DB, cancel it.

```python
# In position_manager.py or a new cleanup function
def cancel_stale_hl_orders_for_open_positions():
    """
    Cancel all reduceOnly limit orders on HL for tokens that have open positions.
    This is a one-time cleanup to remove orphaned orders from when we used the HL path.
    After this, internal ATR hit detection + mirror_close(market) is the only exit path.
    """
```

### Step 2: Internal ATR Close + Market Mirror (current, keep)
`check_atr_tp_sl_hits()` closes internally → `mirror_close()` markets out on HL.

### Step 3: Future — Add HL Trigger Orders as Secondary Protection (Option B)
If we want HL-side protection, re-enable `_execute_atr_bulk_updates()` with proper trigger orders:
- Place trigger SL: `triggerPx=SL_PRICE, isMarket=True, tpsl="sl", reduceOnly=True`
- Place trigger TP: `triggerPx=TP_PRICE, isMarket=True, tpsl="tp", reduceOnly=True`
- These are "fire and forget" — they trigger a market close at the right price
- Internal ATR detection still runs first; if internal closes first, cancel the HL orders before they fire

**Challenge:** Need to track which OIDs belong to which trade_id so we can cancel them cleanly. Current `_execute_atr_bulk_updates()` tried to do this by matching trigger price — this is the right approach but needs to handle the case where price has already moved and the order doesn't match exactly.

---

## Open Questions

1. **How did the 4 ASTER orders accumulate?** Did the old code place new SL/TP orders every cycle without cancelling the old ones? Should add a guard that cancels existing orders for a token before placing new ones.

2. **Should we use trigger orders at all?** Given that `mirror_close()` works reliably (market close), maybe the cleanest architecture is: internal ATR close (source of truth) + market mirror to HL (only exit). No HL trigger orders at all. Simpler, no race condition, no stale order problem.

3. **Do the existing orders have trigger prices we missed?** Our earlier query showed `triggerPx=None` and `orderType={}` — but maybe that's just how `open_orders` returns them for non-trigger orders. If they DO have trigger conditions, we need to know what those trigger prices are.

4. **Rate limit concern:** `cancel_bulk_orders` and `place_bulk_orders` each count against HL's rate limits. If we do this every cycle for 10 positions, we need to chunk carefully.

---

## Proposed Plan (to implement)

### Phase 1: Cleanup (run now, one-time)
- [ ] Add `cancel_stale_hl_orders_for_open_positions()` function
- [ ] It queries all open positions from brain DB, gets all HL reduceOnly orders, finds matches by token, cancels them all
- [ ] Run it once on next pipeline cycle startup (or manually now)
- [ ] Verify: 0 orphaned orders after running

### Phase 2: Ensure Internal Close + Market Mirror (already done, verify)
- [ ] Confirm `check_atr_tp_sl_hits()` fires for ATR SL/TP hits
- [ ] Confirm `mirror_close()` called after internal close
- [ ] Confirm `cancel_all_open_orders()` called for the token after internal close (removes any orphaned HL orders)

### Phase 3: Monitoring (ongoing)
- [ ] Log all HL order placements/cancellations to trading.md
- [ ] Track how many positions have HL orders vs internal-only closes
- [ ] After X weeks of clean operation, decide if HL trigger orders are worth re-enabling

### Files to Change
- `position_manager.py` — add `cancel_stale_hl_orders_for_open_positions()`
- `brain/trading.md` — document the new architecture
