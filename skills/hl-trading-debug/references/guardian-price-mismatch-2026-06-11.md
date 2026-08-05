# Guardian Price Mismatch Bugs — June 11 2026
# Root cause: hype_cache entry_px and mid prices used instead of actual HL fill prices

## Bug 1 — sync_pnl_from_hype: float-str type crash (FIXED)
**Symptom**: Every guardian cycle logs `[FAIL] sync_pnl_from_hype failed: unsupported operand type(s) for -: 'float' and 'str'` starting ~17:30 June 11.
**Root cause**: `prices.get(token, entry)` returned a string from the prices dict, passed directly to SQL, then to `compute_live_pnl` as a string.
**Fix** (hl-sync-guardian.py ~line 1517):
```python
# BEFORE
prices.get(token, entry) if prices else entry
# AFTER
float(prices.get(token, entry) or entry) if prices else float(entry)
```
**Effect**: PnL sync was dead for the entire rate-limit window. Cut-loser and stale-rotation logic also skipped.

---

## Bug 2 — Path B orphan INSERT silently dies on duplicate key (FIXED)
**Symptom**: AAVE SHORT closed @ 63.57 on HL, but no DB record. Guardian log shows `Failed to create guardian_orphan record for AAVE`.
**Root cause**: Two guardian cycles race on the same orphan. One INSERT wins. The other hits `trades_trade_id_key` duplicate key in the `except` block — which only logs and sleeps, never falling through to find-and-close the existing record. The HL close SUCCEEDED, the DB record was never created or closed.
**Fix** (hl-sync-guardian.py ~line 3717): Use `INSERT ... ON CONFLICT (trade_id) DO NOTHING RETURNING id`. If `fetchone()` returns `None`, fall through to find the existing record and close it. Third branch handles genuine gaps using `nextval('trades_id_seq')` to avoid hardcoded `lev*1000000` collision.
**Same root cause**: 100+ duplicate-key failures across May-June 2026, all Path B.

---

## Bug 3 — Stale self-close record ignores direction change (FIXED)
**Symptom**: AVNT had stale LONG record (11:56 open, closed 12:16). When SHORT opened at 13:44, guardian's `_check_hard_stops` detected entry price mismatch and refreshed — but used the NEW direction's SHORT SL/TP values on the existing LONG record. Two SHORT opens (13:44, 14:14) never recorded in DB.
**Root cause**: `_check_hard_stops` stale refresh at ~line 3017 only checked `entry_delta > 0.001`. It never checked if direction changed. A LONG→SHORT flip meant the refreshed SL was WRONG (above entry instead of below).
**Fix**: Added `direction_changed = (stored_direction.upper() != direction.upper())` check. If direction flipped, invalidate and recalculate SL/TP from scratch.

---

## Bug 4 — hl_entry_price never synced from HL (PARTIALLY FIXED)
**Symptom**: UNI SHORT: entry_price=2.5356 (DB), hl_entry_price=2.5000 (HL actual). PEOPLE LONG: entry_price=0.005406 (DB/hype_cache), actual HL fill=0.005427. PnL calculations use wrong entry price.
**Root cause**: `reconcile_hype_to_paper` only wrote `hl_entry_price` when `entry_price` changed by >0.1%. Since hype_cache `entry_px` matched the (wrong) DB value, delta was 0% — `hl_entry_price` was never updated.
**Fix applied**: `reconcile_hype_to_paper` now always writes `hl_entry_price = entry_px` on every cycle (not conditional on delta). The 0.1% gate still protects `entry_price` itself from spurious updates.
**Still pending**: The `_poll_open_fill_once` function was added but not yet wired into the orphan creation path. Orphan creation code at ~line 1203+ is unreachable due to `continue` at ~line 1199.

---

## Key Data — June 11 2026 Trades
```
PEOPLE LONG  open=17:34:07  entry=0.005406  HL_fill=0.005427  delta=+0.39%  ← hype_cache stale
UNI SHORT    open=17:38:07  entry=2.5356    HL_fill=2.5000    delta=-1.43%  ← hype_cache stale
AAVE SHORT   close=17:01:13 exit=63.153    ← DB missing entirely (Path B INSERT died)
AVNT SHORT   13:44 open+close MISSING from DB (stale-refresh loop bug)
AVNT SHORT   14:14 open+close MISSING from DB (same bug)
```

## hype_cache entry_px behavior
`hype_cache` is written by `position_manager` (pipeline). It stores `entry_px` from HL's `/info` endpoint. This value can differ from the actual fill price by:
- Cached estimate vs market order fill (systematic small gap)
- Previous position's entry price if coin was reopened
- Zero if position was opened before cache warmed up

`hl_cache.json` stores positions keyed by coin, with `entry_px` field. Current values (June 11 17:49 UTC):
- UNI: `{}` (no open position)
- PEOPLE: `{'size': 1870.0, 'direction': 'LONG', 'entry_px': 0.005406, ...}` (open, but entry_px ≠ HL fill 0.005427)

## PostgreSQL schema — relevant columns
```sql
entry_price      -- guardian's estimated/signal price (can be wrong)
hl_entry_price  -- HL's actual fill price (should match HL, often 0 or stale)
hl_exit_price   -- HL's actual close fill price
pnl_usdt        -- computed from entry_price/exit_price (wrong if entry_price wrong)
hype_realized_pnl_usdt -- HL ground truth (correct)
```

## Diagnostic queries
```sql
-- Find trades where hl_entry_price is 0 or very different from entry_price
SELECT id, token, direction, entry_price, hl_entry_price,
       ROUND((hl_entry_price - entry_price) / entry_price * 100, 4) AS hl_delta_pct,
       open_time
FROM trades
WHERE hl_entry_price = 0
   OR abs(hl_entry_price - entry_price) / NULLIF(entry_price, 0) > 0.001
ORDER BY open_time DESC LIMIT 20;

-- Find open trades with missing hl_entry_price
SELECT id, token, entry_price, hl_entry_price, status, open_time
FROM trades
WHERE status = 'open' AND (hl_entry_price = 0 OR hl_entry_price IS NULL);

-- Recent closed trades with suspicious PnL
SELECT id, token, direction, entry_price, hl_entry_price, exit_price,
       pnl_pct, pnl_usdt, close_reason, open_time, close_time
FROM trades
WHERE open_time >= '2026-06-11'
ORDER BY open_time;
```
