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
