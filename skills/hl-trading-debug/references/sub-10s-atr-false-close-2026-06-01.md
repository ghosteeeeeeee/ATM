# Sub-10-Second ATR Closes — False atr_sl_hit (2026-06-01)

## The Bug

26 trades closed in under 10 seconds with `close_reason = atr_sl_hit`. In every case examined,
the price data **doesn't support that SL was actually hit**.

Example — IP SHORT (2026-05-31 19:18):
- Entry: $0.42547, SL: $0.40480 (3.8% away), current_price at close: $0.42554 (0.02% away)
- Trade closed in 1.8 seconds with `atr_sl_hit`
- SL was never breached — price nearly identical to entry

## Root Cause Cascade (Verified)

```
1. sync_pnl_from_hype crashes at Step 5 (hl-sync-guardian.py:1587 exception handler)
   Exception logged: [FAIL] sync_pnl_from_hype failed: unsupported operand type(s) for -: 'float' and 'str'

2. The 'float(row['f'] or 0)' claim in the investigation was WRONG — that pattern does not exist.
   The float() calls at lines 1485-1486 ARE properly guarded with explicit float() coercion.
   The string likely comes from the prices dict passed to sync_pnl_from_hype — if prices.json
   stores string values and the dict is built without coercion, compute_live_pnl(entry_price_hl,
   curr_price_hl, direction) at line 1488 calls pnl_utils.compute_live_pnl which does
   (entry_price - current_price) / entry_price * 100. If curr_price_hl is a string, float - str
   fires at pnl_utils.py:59.

3. When crash fires, the entire Step 5 loop ABORTS. The UPDATE at lines 1493-1498 never fires
   for ANY position that cycle. ALL positions keep their previous cycle's current_price (stale).

4. position_manager runs in the SAME guardian cycle (Step 6). It reads current_price from the
   in-memory positions dict (refreshed earlier from hype_cache.get_allMids()). With all prices
   stale, if any stale price happens to be at or past the SL level → false atr_sl_hit fires.

5. position_manager.close_paper_position() called with atr_sl_hit reason → sub-10s close.
```

**Guardian must be restarted** to pick up the float coercion fix (already in code, not restarted).

**Closing marker mechanism is insufficient** — `_save_closing_marker` runs before `market_close`
and prevents signal_compactor from racing, but it does NOT protect against `check_atr_tp_sl_hits()`
firing in the **same guardian cycle** within the same process. The check must be added to
`position_manager.check_atr_tp_sl_hits()` caller (line 2400 in position_manager.py):
```python
atr_hits = check_atr_tp_sl_hits([pos])
for hit in atr_hits:
    if _is_closing_marker_active(token):  # ADD THIS CHECK
        continue  # guardian is closing this token — skip ATR check
    ...
```

## Why IP Closed at 19:18

Signal-compactor inserted IP trade into DB at 19:18:06. At 19:18:11, rate-limit hit (HL returned {}),
so `sync_pnl_from_hype` crashed and never updated `current_price`. The IP trade's `current_price`
stayed stale from the previous cycle. When `check_atr_tp_sl_hits()` ran next cycle, stale price
was near/below SL → immediate false close in 1.8s.

## BCH at 01:09 (Different Bug — Correct Behavior)

BCH SHORT closed in 2.5s with `guardian_orphan` — **this is correct** for an orphan. Guardian
detected BCH on HL but not in DB, closed the HL position. The duplicate key error on
`record_closed_trade()` is a separate bug: it generates a new UUID instead of using the
`existing_id` passed to it.

## What the Investigation Got Wrong

1. Claimed `float(row['f'] or 0)` at line 1485 caused the crash — **doesn't exist in the file**
2. Claimed the float-str fix was already in place — **the explicit float() coercion at lines 1485-1486
   IS in place**, but the crash still propagates because the exception at line 1587 catches the
   error from the prices dict not being coerced before being passed to sync_pnl_from_hype
3. The stale-price mechanism IS correct — just the specific coercion point is different than claimed

## Diagnostic Query

```sql
SELECT token, direction, entry_price, exit_price, stop_loss, current_price,
       close_reason, duration_sec,
       ROUND((current_price - entry_price)::numeric, 6) AS price_move
FROM trades
WHERE close_reason = 'atr_sl_hit'
  AND duration_sec < 10
ORDER BY close_time DESC;
```

For each row, `price_move` should be negative for a SHORT (price went up = bad) and the
magnitude should be ≥ SL distance. If `price_move ≈ 0` or positive, it's a false atr_sl_hit.

## Fix Priority

1. **Restart hl-sync-guardian** — picks up the float coercion fix already in code
2. **Add closing-marker check to position_manager** — before firing atr_sl_hit,
   check `_is_closing_marker_active(token)` from hl-sync-guardian; if guardian is
   closing the token, skip the ATR check (position_manager.py line ~2400)
3. **Make sync_pnl_from_hype per-position resilient** — wrap loop body in try/per-position
   so one bad position doesn't crash the entire Step 5
4. **Trace the actual float-str source** — add debug logging at the exact crash site
   to identify which specific field is a string and why
5. **Fix record_closed_trade duplicate UUID** — accept and use `existing_id` when passed;
   don't generate a new UUID when closing an existing paper trade