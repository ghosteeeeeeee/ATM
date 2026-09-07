## Error Alerts — 2026-09-06 12:24 UTC
- **WARN** (2d): `hermes-5m-candle.service` — script _aggregate_5m.py missing → AUTO-FIX: disabled timer
- **WARN** (ongoing): `hermes-coding-mcp.service` — script run_mcp_server.py missing, crash-looping → AUTO-FIX: disabled timer
- **WARN** (5min): `hermes-away-detector.service` — script away_detector.py missing → AUTO-FIX: disabled timer
- **WARN**: Disk at 83% (92G/118G) — monitor, compress logs if >85%
- **AUTO-FIX**: Cleaned 8,439 stale phantom trade records (NULL trade_id, Aug 4)

## Error Alerts — 2026-09-06 13:23 UTC
- **WARN** (3x in 30min): `signal_compactor: timed out` — recurring, non-fatal. Pipeline completes despite timeouts.
- **INFO**: Disk at 83% (92G/118G) — approaching threshold
- **INFO**: 40% tokens stale (96/240) — recently updated, flagged as non-moving (by design)
- **AUTO-FIX**: None needed — all issues non-critical

## Error Alerts — 2026-09-06 19:22 UTC
- **WARN** (4x in 30min): `signal_compactor: timed out` — recurring, non-fatal. Compactor self-recovers on next cycle.
- **WARN** (3x): `NEAR LONG rejected` — amount_usdt=7.7 < HL_MIN=11.0. Sizing issue, not a crash.
- **WARN**: `ROLLBACK FAILED: sig# already claimed by another process` — race condition between pipeline instances.
- **INFO**: Disk at 83% (92G/118G) — approaching threshold
- **INFO**: Regime NEUTRAL, 0 open trades, 27 trades today (bb-bounce 88.9% WR, coil-spring 50% WR)
- **AUTO-FIX**: None needed — pipeline healthy, all issues non-critical

## Health Report — 2026-09-06 21:23 UTC
- **PIPELINE**: OK — running, 4 open → 0 open, 30 trades today, 66.7% WR, $0.09 PnL
- **MARKET**: NEUTRAL regime, 2 LONG bias / 0 SHORT / 105 neutral, 2% speed
- **SIGNALS**: 119 generated (1h), latest ONDO slow_grind_long (88.0)
- **SYSTEM**: 30+ timers active, disk 83% (93G/118G), no phantom trades
- **WARN** (3x in 30min): `signal_compactor: timed out` — non-fatal, self-recovers
- **WARN**: Regime fully NEUTRAL (105/107 tokens) — low volatility environment
- **AUTO-FIX**: None needed — all non-critical

## Error Alerts — 2026-09-06 23:23 UTC
- **WARN** (3x): `signal_compactor: timed out` in standalone timer (23:11, 23:17, 23:22) — pipeline-internal compactor ran fine (0.29s). Non-critical.
- **INFO**: Disk at 83% (93G/118G) — approaching 85% threshold. No action needed yet.
- **INFO**: Empty `data/regime_5m.json` — stale file, nothing reads it (signals use `/var/www/hermes/data/`).
