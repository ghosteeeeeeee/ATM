# Health Report — 2026-09-18 16:44 UTC

## PIPELINE: OK
- Status: running (last cycle 16:43:22)
- Signals (1h): 18 active
- Trades: 1 open (NOT), 0 closed today
- Errors: 0 pipeline errors

## MARKET
- Regime: 3 LONG / 2 SHORT / 122 NEUTRAL
- Speed: ~normal (93 coins tracked)

## SYSTEM
- Timers: 30+ active, all firing on schedule
- Disk: 85% (95G/118G) — at threshold
- Data DBs: coin_tracker 2.2G, candles 1.9G, signals 765M
- Logs: 145M total

## AUTO-FIXES APPLIED
- [CRITICAL] Disabled hermes-coding-mcp.service — crash-looping 509K times (script missing)
- Compressed old log files (no space recovered — data DBs dominate)

## ALERTS
- [CRITICAL] hermes-coding-mcp.service crash-looping 509K+ restarts — script run_mcp_server.py missing. DISABLED.
- [WARN] 9 services in failed state (defunct scripts/modules): 5m-candle, away-detector, better-coder, bug-hunter, git-release, mtf-macd-tuner, session-brain-rebuild, trading-checklist, upgrade-implementer
- [WARN] momentum_cache stale 528h (22 days) — momentum filters may be degraded
- [WARN] Disk at 85% — at threshold, data DBs are main consumers
- [INFO] pullback-entry- signal 20% WR (5 trades, -$0.60) — underperformer
