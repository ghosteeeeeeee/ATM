# Signal Quality False Loss — June 2026

## The Bug

`_record_signal_outcome` inside `close_paper_position` fires BEFORE `mirror_close` backfills `hype_realized_pnl_usdt`. Result: profitable exits logged as losses.

AXS SHORT June 4 21:42:
- HL realized_pnl = +$0.1297 (+1.18%) — genuine profit
- Signal Quality logged: `LOSS (conf=91, pnl=-0.01%)`
- Loss cooldown set from wrong data — streak=2 blocked for 0.3h

SUSHI SHORT June 4 21:41:
- HL realized_pnl = -$0.0080 (-0.0724%) — genuine small loss
- Signal Quality logged: `LOSS (conf=90, pnl=-0.09%)` — over-reported loss magnitude

## Root Cause

`close_paper_position` sequence (position_manager.py ~940):
1. Writes close_time + status='closed' to DB
2. Calls `_record_signal_outcome` with `pnl_pct` from DB columns (stale — set by `refresh_current_prices` 60s prior)
3. Fires `mirror_close` async (up to 60s polling)
4. mirror_close result handler backfills `hype_realized_pnl_usdt` at ~line 1127

Step 2 fires before step 4 completes — Signal Quality log uses stale PnL.

## Also Affected

`_record_ab_close` (called at line 1158) uses stale `pnl_usdt` for win/loss classification even when `hype_realized_pnl_usdt` is available.

## Fix Direction

Use `hype_realized_pnl_usdt` as ground truth when available. Fall back to DB pnl_pct only when hype_realized_pnl_usdt is not yet set.

## Archive DB Pattern

Sub-10s trades with positive PnL but exit_reason=atr_sl_hit — all likely false-loss classified:
- CAKE LONG: +0.14%
- ETHFI LONG: +0.04%
- ASTER LONG: +0.08%
- MORPHO SHORT: +0.07%
- FIL SHORT: +0.04%
- UNI LONG: +0.02%
- SUI LONG: +0.02%