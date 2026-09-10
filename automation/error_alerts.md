## Error Alerts — 2026-09-10 08:23 UTC
- **[INFO]** Pipeline running, last cycle 08:22:48, 1 transient error
- **[INFO]** Signals: 49 generated in last hour, 0 above 50% confidence (NEUTRAL regime)
- **[INFO]** Trades: 4 open (exchange), 10 closed today, +$0.81 PnL, 60.0% WR
- **[WARN]** (1x): `signal_compactor: timed out` at 08:22 — self-recovered on next cycle
- **[WARN]** Disk at 83% (93G/118G) — 2% from 85% threshold
- **AUTO-FIX**: None needed — transient compactor timeout self-recovered

## Error Alerts — 2026-09-10 06:25 UTC
- **[CRITICAL]** (10+): `[RR-ENGINE] DB persist failed: schema "np" does not exist` — numpy.float64 not adapted by psycopg2, every TRAIL_SL update failing since ~05:54 UTC
- **[WARN]** (7x): `signal_compactor: timed out` in last hour — compactor stalling, signals not being compacted
- **[INFO]** Pipeline running, 3 open positions, +85.73% PnL today
- **[INFO]** Signals: 78 generated in last hour
- **[INFO]** Trades: 3 open (exchange), 7 tracked in signal_outcomes, 57.1% WR
- **[WARN]** Disk at 84% (19G free) — 1% from threshold
- **AUTO-FIX**: Fixed RR-ENGINE numpy bug — wrapped `new_sl` with `float()` in position_manager.py:2495 and :1332 ✅ VERIFIED — TRAIL_SL persisting successfully post-restart
- **AUTO-FIX**: Compactor timeouts not auto-fixable — likely DB lock contention or slow query

## Error Alerts — 2026-09-10 04:25 UTC
- **[INFO]** Pipeline running, cycle #193193, 0 errors
- **[INFO]** Signals: 28 generated in last hour
- **[INFO]** Trades: 0 open, 42 closed (24h), 61.9% WR, +$4.11 PnL
- **[WARN]** Disk at 84% (94G/118G) — 1% from threshold. Big 3 logs total ~187MB
- **[INFO]** hl-copy timer dead (no fire in 3 weeks), atr-sl-updater never fired
- **AUTO-FIX**: Compressed 4 inactive log files (~15MB freed)

## Error Alerts — 2026-09-10 03:24 UTC
- **[INFO]** Pipeline running, 60 cycles/hr, 0 errors
- **[INFO]** Signals: 44/hr, hotset: 0 (market neutral)
- **[INFO]** 0 open trades, 0 crashes
- **[WARN]** Disk at 84% (19G free) — approaching threshold
- **AUTO-FIX**: None needed — no critical issues

## Error Alerts — 2026-09-10 05:22 UTC
- **[WARN]** (1x): `hermes-5m-candle.service` FAILED — missing script `_aggregate_5m.py` (since Sep 8 15:23 UTC)
- **[WARN]** (1x): `hermes-coding-mcp.service` crash loop — missing script `run_mcp_server.py`
- **[WARN]** (2x): `signal_compactor` timeouts at 04:59, 05:14 (transient)
- **[WARN]** Disk at 84% (19G free) — approaching 85% threshold
- **[WARN]** 3 phantom trades today (<0.01% PnL): ADA SHORT -$0.009, ARB SHORT -$0.0059, CRV SHORT +$0.0046
- **INFO** `prices.db` and `prices_hermes.db` both 0 bytes — candles.db (1GB) is the active price store
- **AUTO-FIX**: Restarted `hermes-coding-mcp.service` (will likely fail again — missing script)
- **AUTO-FIX**: `hermes-5m-candle.service` not restarted — missing script needs manual fix or systemd unit update

## Health Check — 2026-09-10 14:24 UTC
- **INFO**: Pipeline running normally, 0 errors in last 30m
- **INFO**: 20 trades today, 60% WR, $1.04 PnL, 0 open
- **INFO**: Regime NEUTRAL, 64.6% tokens fast, candles fresh
- **MONITOR**: Disk at 83% (93G/118G) — watch for threshold
- **MONITOR**: prices.db / prices_hermes.db are 0 bytes — may be intentional (candles.db active)
