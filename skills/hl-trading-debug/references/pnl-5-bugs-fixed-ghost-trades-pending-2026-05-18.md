# PnL Sync — 5 Bugs Fixed + Ghost Trades Pending (2026-05-18)

## 5 Bugs Fixed ✅ (2026-05-18)

| # | File | Line | Bug | Fix |
|---|------|------|-----|-----|
| 1 | position_manager.py | 904 | Fees calculated from `amount_usdt × leverage` instead of `calc_notional × leverage` — 7x fee inflation | `calc_notional × leverage` (actual HL notional ~$7 vs signal-level ~$50) |
| 2 | hl-sync-guardian.py | 749 | `add_orphan_trade()` INSERT missing `hl_notional_usdt` — orphan trades always fell back to $50 inflated notional | Added `hl_notional_usdt = amount_usdt` column to INSERT |
| 3 | hl-sync-guardian.py | 2666 | `_close_orphan_paper_trade_by_id()` fetches `amount_usdt` but NOT `hl_notional_usdt` — even if column were populated, wouldn't use it | SELECT now fetches `hl_notional_usdt` → `calc_notional`; PnL math uses `calc_notional` in both Tier 1 (HL realized) and Tier 2 (price-based) branches |
| 4 | hl-sync-guardian.py | 1401 | Cascade flip trade INSERT missing `hl_notional_usdt` — flips use `place_order()` directly (not `mirror_open()`), so `amount` from `sz * price` approximates HL notional | Added `hl_notional_usdt = amount` to flip trade INSERT |
| 5 | backfill_orphan_hl_prices.py | 147 | Backfill PnL uses `amount_usdt` not `calc_notional` — backfilled orphans still inflated | SELECT now fetches `amount_usdt, hl_notional_usdt` → `calc_notional`; PnL uses `calc_notional` |

All files compile clean: `python3 -m py_compile position_manager.py hl-sync-guardian.py backfill_orphan_hl_prices.py`

---

## Ghost Trades — Root Cause Identified (NOT YET FIXED)

**Pattern:** HL shows open/close pairs ~10s apart, ~$10 USDC notional, real loss -$0.01 to -$0.13.

**Root cause chain:**
1. HL orphan position detected by `reconcile_hype_to_paper()`
2. `add_orphan_trade()` called → `INSERT ... WHERE NOT EXISTS` condition is FALSE (another open trade for same token already exists from a previous failed cycle) → INSERT returns 0 rows → `row = cur.fetchone()` → returns `None`
3. `_mark_hl_reconciled()` never called → `trade_id = None`
4. `_close_orphan_paper_trade_by_id(None, token, ...)` → `WHERE id=NULL` → no match → UPDATE does nothing → DB trade stays open
5. `market_close()` already closed the HL position
6. Next cycle: orphan recovery runs again → same pattern → ghost trades accumulate

**Why it's NOT the PnL inflation bug:** Ghost trades are a record-keeping bug — positions opened on HL are never recorded in DB, so the DB shows no trade while HL shows an open+close pair.

**Pending fix (NOT YET APPLIED):**
- Option A: `add_orphan_trade()` returns `(trade_id, reason)` tuple — caller distinguishes "already exists" from "created" and skips close when trade already exists
- Option B: `_close_orphan_paper_trade_by_id()` falls back to `WHERE token=%s AND direction=%s AND status='open'` when `trade_id is None`
- Option C (simplest): in `reconcile_hype_to_paper()`, if `add_orphan_trade()` returns None, fetch existing `id` for that token and close that trade instead of skipping

**Why pending:** `add_orphan_trade()` returns `None` for BOTH "INSERT failed" and "INSERT didn't execute because condition was false" — the same `None` for two very different situations. The fix requires distinguishing between them.

---

## Architecture — PnL Hierarchy at Close

```
calc_notional = hl_notional_usdt if set else amount_usdt

Tier 1: hype_realized_pnl_usdt from HL fill polling → use directly
Tier 2: hl_notional_usdt × price_change_pct         → accurate for new trades
Tier 3: amount_usdt × price_change_pct               → legacy, inflated (pre-migration trades only)
```

`pnl_pct` at close = `pnl_usdt / calc_notional × 100` — matches HL actual return %.

`amount_usdt` stays signal-level (represents what the signal intended, NOT actual HL execution).
`hl_notional_usdt` stores actual HL USDT notional at open.

---

## Key Constants (hermes_constants.py)

```python
DEFAULT_TRADE_SIZE_USDT = 50.0   # signal-level intent only, NOT for PnL math
HL_MIN_NOTIONAL_USDT = 11.0      # HL minimum (~$10) + $1 buffer
```

---

## Files Modified

- `/root/.hermes/scripts/hermes_constants.py`
- `/root/.hermes/scripts/position_manager.py` (Bug #1)
- `/root/.hermes/scripts/hl-sync-guardian.py` (Bugs #2, #3, #4)
- `/root/.hermes/scripts/backfill_orphan_hl_prices.py` (Bug #5)
- `/root/.hermes/scripts/brain.py` (Phase 3a — close_trade PnL hierarchy)
- `/root/.hermes/scripts/hyperliquid_exchange.py` (mirror_open returns notional_usdt)