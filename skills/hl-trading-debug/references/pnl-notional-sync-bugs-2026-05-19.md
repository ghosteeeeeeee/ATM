# PnL Sync: 4 Bugs Found → 4 Bugs FIXED (2026-05-19)

**Context:** System had inflated profits and deflated losses. Confirmed 4 bugs in the self-close path. **All 4 fixed. Syntax verified. Awaiting trial run.**

---

## Bug 1 — `get_db_open_trades()` SELECT missing `hl_notional_usdt` (HIGH)

**File:** `hl-sync-guardian.py` line 676
```python
"SELECT id, token, direction, entry_price, leverage, amount_usdt, paper FROM trades WHERE status = 'open' AND exchange = 'Hyperliquid' ..."
```
`hl_notional_usdt` is NOT selected. `db_trade` dict never has it.

**Impact:** `close_position_hl()` self-close (line 3253) uses `amount_usdt` ($50) instead of actual HL notional (~$10). All PnL calculations off by ~5x.

**Fix:** Add `hl_notional_usdt` to SELECT, parse as 8th column in `parts[]`.

---

## Bug 2 — Self-close PnL uses `amount_usdt` not `hl_notional_usdt` (HIGH)

**File:** `hl-sync-guardian.py` lines 3253-3264
```python
amount_usdt = db_trade.get('amount_usdt', 50.0)  # db_trade has NO hl_notional_usdt
...
computed_pnl_pct = round(realized_pnl / amount_usdt * 100, 4)  # divides by $50 not ~$10
```
All 3 branches (realized_pnl path, hl_exit_px path, curr proxy path) use signal-level `amount_usdt`.

**Fix:** After Bug 1 fix, look up `hl_notional_usdt` from `db_trade` and use as `calc_notional`.

---

## Bug 3 — Self-close UPDATE never writes `hype_realized_pnl_pct` (HIGH)

**File:** `hl-sync-guardian.py` lines 3278-3288
```python
UPDATE trades SET
    ...
    pnl_pct=%s,   # ← price-based PnL%, uses wrong $50 notional
    pnl_usdt=%s,
    hype_realized_pnl_usdt=%s   # ← realized_pnl_value (HL ground truth)
    # ← hype_realized_pnl_pct column NEVER written → stays NULL for all self-closes
```

**Fix:** Add `hype_realized_pnl_pct=%s` to UPDATE and pass `computed_pnl_pct`.

---

## Bug 4 — `hermes-trades-api.py` silent local constant redefinition (LOW)

**File:** `hermes-trades-api.py` lines 15-22
```python
try:
    from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST, DEFAULT_TRADE_SIZE_USDT
    ...
except Exception:
    ...
    DEFAULT_TRADE_SIZE_USDT = 50.0  # ← silent fallback, bypasses hermes_constants
```

If import fails, `DEFAULT_TRADE_SIZE_USDT` gets a local redefinition instead of failing visibly. Silent fallback bypasses the single source of truth.

**Fix:** Remove local fallback definition. If `hermes_constants` fails to import, let it raise.

---

## Full Trade Path (what actually happens today)

1. **signal_compactor** → fires signal → `decider_run`
2. **decider_run** → `brain._place_hl_trade()` → `mirror_open()`
3. **mirror_open** (hyperliquid_exchange.py:876):
   - `size_usdt = _get_trade_size_usdt()` → max(withdrawable×0.07, $10) + $0.10 buffer ≈ $10.10
   - `sz = size_usdt / live_price` (rounded up to szDecimals)
   - `place_order()` → HL fills → `mirror_get_entry_fill()` → `total_sz` + `entry_price`
   - Returns: `total_sz` (actual coin units), `entry_price` (actual fill), `notional_usdt = size_usdt` (~$10.10)
4. **brain.add_trade()** (brain.py:483): `hl_notional = result.get("notional_usdt")` → INSERT writes `hl_notional_usdt=~10.10`
5. **position_manager** → runs ATR trailing, monitors TP/SL
6. **Self-close fires** → `close_position_hl()`:
   - `db_trade = get_db_open_trades()` → NO `hl_notional_usdt` in SELECT → `amount_usdt=$50`
   - `realized_pnl` from HL fill (correct)
   - `computed_pnl_pct = realized_pnl / 50.0 * 100` → 1/5th of correct value
   - `UPDATE`: writes `hype_realized_pnl_usdt` (correct) but NOT `hype_realized_pnl_pct` (NULL)
7. **Orphan close** → `_close_orphan_paper_trade_by_id()`:
   - SELECT correctly fetches `amount_usdt, leverage, hl_notional_usdt` (line 2668) → calc_notional works
   - But if `add_orphan_trade()` INSERT used `amount_usdt` for `hl_notional_usdt` (it does, line 759), it's still ~$10 notional

---

## What Was Already Fixed (2026-05-18 per pnl-sync-plan.md)

- ✅ Phase 1: `DEFAULT_TRADE_SIZE_USDT` and `HL_MIN_NOTIONAL_USDT` in hermes_constants
- ✅ Phase 2: 12 hardcoded `$50` defaults replaced with constant
- ✅ Phase 3a: `brain.py:close_trade()` — uses `hl_notional_usdt` for PnL calc
- ✅ Phase 3b: `position_manager.py:close_paper_position()` — uses `calc_notional`, fees fixed
- ✅ Phase 3c: `hl-sync-guardian.py:_close_position_from_signal()` — uses `hl_notional_usdt`
- ✅ Bug #1 (position_manager.py:904): Fees now use `calc_notional * leverage` not `amount_usdt * leverage`
- ✅ Bug #2 (hl-sync-guardian.py:749): `add_orphan_trade()` INSERT includes `hl_notional_usdt`
- ✅ Bug #3 (hl-sync-guardian.py:2666): `_close_orphan_paper_trade_by_id()` reads `hl_notional_usdt`
- ✅ Bug #4 (hl-sync-guardian.py:1401): Flip trade INSERT includes `hl_notional_usdt`
- ✅ Bug #5 (backfill_orphan_hl_prices.py:147): Uses `calc_notional` for fallback PnL

---

## What's FIXED (all 4 resolved 2026-05-19)

| # | File | Line | Severity | Bug | Fix |
|---|------|------|----------|-----|-----|
| 1 | hl-sync-guardian.py | 676 | HIGH | SELECT missing `hl_notional_usdt` | Add to SELECT + parse 8th column |
| 2 | hl-sync-guardian.py | 3253 | HIGH | Self-close PnL uses `amount_usdt` not `hl_notional_usdt` | Look up `hl_notional_usdt` → `calc_notional` |
| 3 | hl-sync-guardian.py | 3286 | HIGH | UPDATE never writes `hype_realized_pnl_pct` | Add column to UPDATE |
| 4 | hermes-trades-api.py | 21 | LOW | Local `DEFAULT_TRADE_SIZE_USDT = 50.0` fallback | Remove local redefinition |

---

## Diagnostic Query

```sql
-- Check how many trades have hype_realized_pnl_pct = NULL (should be 0 after fixes)
SELECT close_reason, COUNT(*) FROM trades
WHERE status='closed' AND hype_realized_pnl_pct IS NULL
GROUP BY close_reason ORDER BY COUNT(*) DESC;

-- Check self-close PnL accuracy (realized vs computed)
SELECT token, direction, pnl_usdt, hype_realized_pnl_usdt,
       CASE WHEN pnl_usdt != 0 THEN ROUND(hype_realized_pnl_usdt / pnl_usdt, 2) END as ratio
FROM trades WHERE status='closed'
  AND close_reason LIKE 'guardian%'
  AND hype_realized_pnl_usdt IS NOT NULL
ORDER BY close_time DESC LIMIT 20;
```