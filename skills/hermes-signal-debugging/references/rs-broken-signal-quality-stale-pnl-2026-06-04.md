# rs-broken Signal Quality — Stale PnL Bug (2026-06-04)

## Trigger

"rs-s-broken signal quality LOSS on winning trade" — AXS SHORT showed Signal Quality `LOSS (conf=91, pnl=-0.01%)` but HL mirror_close returned +1.18% profit (pnl_usdt=+$0.1297).

## Root Cause

`_record_signal_outcome` in `close_paper_position()` (position_manager.py:1160) fires BEFORE `mirror_close` backfills `hype_realized_pnl_usdt` (line 1169-1174). The signal quality log uses the stale PnL computed from `current_price` that hasn't been updated by sync since the trade opened.

The 12-second gap between `mirror_open` (21:42:07) and `mirror_close` (21:42:19) means no sync cycle has run to update the position's `current_price`. The PnL at close time is computed from the pre-entry price.

## Fix Required

1. In `close_paper_position`: call `_record_signal_outcome` AFTER mirror_close backfill completes, not before
2. In `_record_signal_outcome`: accept `hype_realized_pnl_usdt` as override when available (ground truth > stale DB)
3. In `_record_ab_close` (line 1158): same — prefer `hype_realized_pnl_usdt` when set

## Differential Diagnosis

When Signal Quality shows small LOSS (e.g. -0.01%, -0.05%) on a trade that closed in <15s:
1. Check pipeline.log for `mirror_close` entry — positive `hl_realized_pnl` = real profit, stale signal quality
2. Check `hype_realized_pnl_usdt` in trade record — positive value confirms bug
3. Loss cooldown set from stale PnL blocks next valid signal incorrectly

## See Also

- `references/signal-quality-stale-pnl-2026-06-04.md` in `hl-trading-debug` skill — full root cause cascade, code line references, fix sequence