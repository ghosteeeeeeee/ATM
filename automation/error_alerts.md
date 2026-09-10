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
