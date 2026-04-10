# HL Close Order Mirroring — Plan
**Date:** 2026-04-09 22:50 UTC
**Status:** PHASE 1 COMPLETE ✅

---

## Situation Assessment

### Orphaned orders — CLEANED UP
All 6 stale HL orders (IMX × 2, ASTER × 4) were cancelled 2026-04-09 22:52 UTC via `cancel_all_open_orders()`.

| Token | # Orders Cancelled | Reason |
|-------|-------------------|--------|
| IMX | 2 | Stale limit sell orders (old SL levels) |
| ASTER | 4 | Stale limit sell orders accumulated from repeated order placement without cleanup |

### Architecture after cleanup
```
Internal ATR close (source of truth)
  → check_atr_tp_sl_hits() detects hit
  → close_paper_position() closes DB position
  → cancel_all_open_orders() removes any HL orders for that token
  → mirror_close() market-closes on HL (best effort)

HL has 0 open orders for open positions.
Internal ATR system is the only exit trigger.
```

---

## What's in Place

### Internal ATR Close Pipeline (done)
1. **`_collect_atr_updates()`** — computes fresh ATR SL/TP each cycle using z-score/speed-adaptive k
2. **`_persist_atr_levels()`** — writes new SL/TP to brain DB (NEW)
3. **`check_atr_tp_sl_hits()`** — reads FROM DB, closes if price crossed SL/TP
4. **`cancel_all_open_orders(token)`** — called after internal close, removes any orphaned HL orders
5. **`mirror_close()`** — market exits on HL (best effort, not required for internal close)

### Kill Switch
`ATR_HL_ORDERS_ENABLED = False` — HL SL/TP trigger order path disabled. All close decisions made internally.

### What Stops a Position
| Exit Trigger | Mechanism | Speed |
|-------------|-----------|-------|
| ATR SL hit | Internal check → DB close → market mirror | ~1 min (pipeline cycle) |
| ATR TP hit | Internal check → DB close → market mirror | ~1 min |
| Wave turn exit | z-score extreme + acceleration reversing | ~1 min |
| Stale winner | Flat >15min in profit | ~1 min |
| Stale loser | Flat >30min in loss | ~1 min |
| Cascade flip | Loss >-0.25% armed, >-0.50% triggered | ~1 min |
| MACD flip | MTF MACD alignment reversal | ~1 min |

### Gap if Hermes/HL is Down
If the pipeline stops, no internal closes fire, no market mirror goes out. HL position stays open until pipeline resumes. This is the trade-off of Option C.

---

## Future: HL Trigger Orders as Secondary (Option B — Future Only)

Only re-enable if we want HL as a redundant failsafe (not the primary close path).

**Requirements:**
1. Track OIDs per trade_id so we can cancel before placing new ones (prevent accumulation)
2. Use trigger orders: `triggerPx=X, isMarket=True, tpsl="sl"|"tp", reduceOnly=True`
3. Run cancel + place in same cycle (one batch cancel, one batch place)
4. Keep `check_atr_tp_sl_hits()` as primary — HL orders as backup only

**Implementation (when ready):**
- Re-enable `_execute_atr_bulk_updates()` with `ATR_HL_ORDERS_ENABLED=True`
- Before placing new orders for a token, cancel all existing reduceOnly orders for that token
- Track OIDs in a dict: `{trade_id: [sl_oid, tp_oid]}`

---

## Current HL Order State
- Open positions: 10 (all LONG)
- HL open orders for those tokens: **0** (clean)
- All exits handled internally
