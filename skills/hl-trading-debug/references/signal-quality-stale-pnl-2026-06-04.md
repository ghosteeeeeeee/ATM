# Signal Quality Stale PnL Bug — 2026-06-04

## The Event

AXS SHORT opened at 21:42:07 on pipeline run, closed at 21:42:19 (12s) via `atr_sl_hit` → `close_paper_position` → `mirror_close`.

HL returned **realized profit**: `+$0.1297 (+1.18%)`
Signal Quality log showed: `accel-300-,rs-s-broken SHORT AXS: LOSS (conf=91.00, pnl=-0.01%)`

Loss cooldown set from WRONG data — streak=2 blocked for 0.3h.

## Root Cause Chain

`close_paper_position` at position_manager.py line ~940:

1. Writes `close_time` to DB, sets `status='closed'` at line ~943
2. Calls `_record_signal_outcome(token, pnl_pct, pnl_usdt, signal, conf)` at line ~950
   - At this point `pnl_pct` and `pnl_usdt` come from the trade's DB columns
   - Those were set by `refresh_current_prices` on the PREVIOUS cycle (60s earlier)
   - Current price has reverted toward entry by the time exit is processed
   - The `compute_live_pnl(entry_price, current_price, direction)` gives -0.01%
3. Calls `mirror_close` at line ~960 — fires async, polls HL fills for up to 60s
4. `mirror_close` returns `(exit_price, realized_pnl)` ~12s later
5. Result handler backfills `hype_realized_pnl_usdt=+$0.1297` at line ~1127

**Problem**: `_record_signal_outcome` already fired at step 2 — Signal Quality log is written with stale data before ground truth is available.

## SUSHI Same-Pattern Close

```
21:41:07  SUSHI SHORT opened
21:41:19  atr_sl_hit → close_paper_position → mirror_close fires
21:41:19  Signal Quality: accel-300-,rs-r52 SHORT SUSHI: LOSS (conf=90.00, pnl=-0.09%)
21:41:31  mirror_close returns: HL exit $0.2031, pnl=-$0.0080 (-0.0724%)
21:41:31  Backfilled HL realized_pnl=-0.0080 (-0.0724%)
```

SUSHI was a real loss but Signal Quality over-reported it (-0.09% vs -0.0724%) — same stale PnL issue.

## Code Location

`position_manager.py` around line 940 — inside `close_paper_position`:

```python
# Line ~943: DB close
cursor.execute("UPDATE trades SET status='closed', close_time=%s WHERE id=%s", (ts, trade_id))

# Line ~950: _record_signal_outcome fires with STALE pnl_pct
_record_signal_outcome(token, pnl_pct, pnl_usdt, signal, conf)

# Line ~960: mirror_close fires async
mirror_close(token, direction, entry_price, size, lev, ...)
# ... result handler ~12s later at line ~1127:
cursor.execute("UPDATE trades SET hype_realized_pnl_usdt=%s WHERE id=%s", (pnl_usdt, trade_id))
```

## Fix Required

In `_record_signal_outcome`, check if `hype_realized_pnl_usdt` is already set in the trade record before using `pnl_pct` from DB. When available, compute the corrected pnl_pct from hype_realized_pnl_usdt / calc_notional * 100.

Alternative: pass `hype_realized_pnl` from `mirror_close` return value to `_record_signal_outcome` so it uses ground truth instead of stale DB data.

## Archive DB Pattern — Sub-10s Closes

All guardian_orphan pattern (May 19):
- ETH SHORT: 6.0s, pnl=0.0%
- AAVE SHORT: 6.0s, pnl=-0.0024
- GALA SHORT: 6.0s, pnl=-0.0061
- AXS SHORT: 6.0s, pnl=-0.0157
- AVAX LONG: 6.3s, pnl=-0.0148

atr_sl_hit pattern (May 15-18):
- DYDX SHORT: 3.7s, pnl=-0.023
- AXS SHORT: 3.8s, pnl=-0.596
- ETHFI LONG: 3.6s, pnl=+0.041
- CAKE LONG: 2.9s, pnl=+0.140

Note: many atr_sl_hit closes with positive PnL suggest the stale price issue is systemic, not just for the June 4 AXS event.