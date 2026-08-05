# MORPHO SHORT #10430 — Rapid 3s Close — BUG CONFIRMED

**Date:** 2026-05-22
**Token:** MORPHO
**Direction:** SHORT
**Trade ID:** 10430 (PostgreSQL)
**Signal:** `rs-r456,zscore-pump-`
**Open:** 2026-05-22 23:52:07.427 UTC (guardian, pid 2616901)
**Close:** 2026-05-22 23:52:10.597 UTC (position_manager, pid 2616990)
**Duration:** 3.17 seconds
**Entry price (HL fill):** $1.9448
**Exit price:** $1.9447
**Stop loss (DB):** $1.9133 (1.62% below entry)
**PnL:** +$0.00 / +0.0051%
**Close reason:** `atr_sl_hit`

---

## Why This Is a Bug

Price at close ($1.9447) was **$0.0001 BELOW entry** — the SHORT direction was **profitable**. The price moved in the trader's favor, yet the position was stopped out with `atr_sl_hit`.

This rules out a genuine SL hit. The stored SL was $1.9133 — price at close was nowhere near it.

**Root hypothesis:** `check_atr_tp_sl_hits()` uses a stale `current_price` for MORPHO — either `0`, `None`, or a pre-entry price that doesn't reflect the actual HL fill. When the stale price is compared against the SL, it incorrectly triggers `atr_sl_hit`.

---

## Key Evidence

| Value | Price |
|---|---|
| Entry (HL fill) | $1.9448 |
| Exit | $1.9447 |
| SL | $1.9133 |
| Direction of move | SHORT PROFITABLE by $0.0001 |

---

## Diagnostic Query

```bash
PGPASSWORD='Brain123' psql -h /var/run/postgresql -U postgres -d brain \
  -c "SELECT id, token, direction, entry_price, exit_price, stop_loss, target, current_price, pnl_pct, pnl_usdt, close_reason, open_time, close_time FROM trades WHERE token='MORPHO' ORDER BY open_time DESC LIMIT 3;"
```

If `current_price` is NULL, 0, or a pre-entry value → confirmed bug in `check_atr_tp_sl_hits` stale price path.

---

## Relevant Code Paths

- `position_manager.check_atr_tp_sl_hits()` — sets `hit='atr_sl_hit'`, calls `close_paper_position()`
- `position_manager.close_paper_position()` — fetches current_price with fallback: `current_price = float(row['current_price'] or entry_price)`. If `current_price` is 0 or None, uses entry_price as fallback
- `refresh_current_prices()` — updates `current_price` for open positions from HL API; may not run before `check_atr_tp_sl_hits` fires for a newly opened position

---

## UNPROTECTABLE Coins Context

MORPHO is in `UNPROTECTABLE_COINS = {'AAVE', 'MORPHO', 'ASTER', 'PAXG', 'BTC', 'AVNT'}`.
These coins bypass guardian's `_check_and_close_breached_trades` (Step 11 in guardian sync) but are still processed by position_manager's `check_atr_tp_sl_hits`. The guardian writes to `tpsl_self_close` table but position_manager reads from `trades.stop_loss` in PostgreSQL.

---

## Fix Required

1. **Guard in `check_atr_tp_sl_hits`**: Skip positions where `current_price` is None or 0 — use `is not None` check, not falsy check
2. **Guard by position age**: Skip positions opened < 10 seconds ago (compare `open_time` to `datetime.utcnow()`)
3. **Guardian + position_manager race**: When guardian opens a position and writes to DB, position_manager's `refresh_current_prices` may not have fetched HL prices yet. Add a check: if `current_price` hasn't been updated since the position was opened (or is 0/None), skip the breach check until next cycle

---

## User Insisted This Was a Bug

T: "the audit.log showed 7 seconds so it is a bug, find the bug!" — T was correct. The price moved favorably and still closed. The prior session's conclusion ("not a bug, genuine SL hit") was wrong — it assumed adverse price movement, but price moved in the SHORT direction.