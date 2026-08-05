# STALE_ROTATION Cascade + PHANTOM_CLOSE Backfill Fix — 2026-06-12

## STALE_ROTATION `_check_stale_rotation` Bugs (G1/G2/G3)

**File:** hl-sync-guardian.py ~lines 2008–2045

**Bug:** `_check_stale_rotation` bypassed `_close_paper_trade_db` and did a direct UPDATE, introducing 3 bugs simultaneously:

| # | Bug | Consequence |
|---|-----|-------------|
| G1 | Used stale pre-close `pnl_pct` (computed from `_sync_pnl_from_hype` at rotation decision time) not actual close PnL | PnL recorded incorrectly in DB |
| G2 | Never called `_record_loss_cooldown` | Losing trades can re-enter immediately |
| G3 | Never called `_clear_reconciled_token` | Token stuck in reconciled state, blocked from re-reconciliation |

**Fix:** Replaced direct UPDATE with `_close_paper_trade_db(trade_id, token, exit_price, 'STALE_ROTATION')` which handles all three correctly.

**Also fixed:** `rate_data` possibly unbound — `rate_data = {}` was inside the try block. If the file read raised an exception, `_update_rate()` would raise `NameError`. Moved `rate_data = {}` before the try block.

**Also fixed:** Rate limit update now happens BEFORE the HL close (via `_update_rate()` helper), so the rate limit persists even if the HL close fails.

## PHANTOM_CLOSE Backfill — `_get_hl_exit_price` Never Returns 0

**File:** hl-sync-guardian.py `_retry_phantom_close_fills()` lines 469–553

**Bug:** The backfill query had `WHERE exit_price = 0` — but `_get_hl_exit_price` **never returns 0**:
1. Polls HL fills 6 times × 5s = 30s total
2. If no fills found, falls back to `hype_cache.get_allMids()` current market price
3. Only falls back to the provided `fallback_price` if that also fails

Since the guardian stores `current_price` (a valid market price, never 0) as the fallback, `_get_hl_exit_price` always returns a positive number. The `WHERE exit_price = 0` condition was always false → backfill never ran.

**Fix:** Removed `AND exit_price = 0` from both:
- SELECT WHERE clause (line ~495)
- UPDATE WHERE clause (line ~541)

Now any `PHANTOM_CLOSE` trade will be retried regardless of its stored exit price.

## Key Lesson

`_get_hl_exit_price` is designed as an aggressive fallback system:
- **Never returns 0 or None** for a coin that exists in the market
- The `exit_price == 0` condition in the PHANTOM_CLOSE backfill was based on a wrong assumption about what `_get_hl_exit_price` could return
- Any guardian close path that calls `_get_hl_exit_price` will always produce a valid `exit_price > 0`

## Verification

```bash
python3 -m py_compile /root/.hermes/scripts/hl-sync-guardian.py && echo "Syntax OK"
```

All 6 bugs from this session committed to git SHA `c4da355`.
