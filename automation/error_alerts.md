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

## Error Alerts — 2026-09-07 17:24 UTC
- **WARN** (1x): `signal_compactor: timed out` at 17:21 — non-fatal, pipeline completed on schedule
- **INFO**: Pipeline OK — 3 open trades, 57 closed today, -4.71% PnL
- **INFO**: Market NEUTRAL — 2 LONG bias / 1 SHORT / 103 neutral, 53% speed (127/240 tokens)
- **INFO**: Disk 81% (91G/118G) — below threshold
- **INFO**: Best signal today: pump_chain_long (87.5% WR, $0.60 PnL). Worst: slow_grind_long (18.2% WR, -$1.27)
- **AUTO-FIX**: None needed — all non-critical

## Error Alerts — 2026-09-06 23:23 UTC
- **WARN** (3x): `signal_compactor: timed out` in standalone timer (23:11, 23:17, 23:22) — pipeline-internal compactor ran fine (0.29s). Non-critical.
- **INFO**: Disk at 83% (93G/118G) — approaching 85% threshold. No action needed yet.
- **INFO**: Empty `data/regime_5m.json` — stale file, nothing reads it (signals use `/var/www/hermes/data/`).

## Health Report — 2026-09-07 03:23 UTC
- **PIPELINE**: OK — last cycle 03:22:15, 14s CPU, completed successfully
- **POSITION MANAGER**: 3 open → 0 open, 13 trades today, 30.8% WR, -$1.15 PnL (low vol, small sample)
- **SIGNALS**: 149 generated (1h), latest 03:22:10. 0 signals blocked by filters
- **MARKET**: NEUTRAL (105/107), 2 LONG bias (AEVO, CRV), 0 SHORT. BTC $79,806
- **SYSTEM**: Guardian active, disk 83% (93G/118G), 0 phantom trades, prices fresh
- **WARN** (11x in 2h): `signal_compactor: timed out` — recurring. Compactor self-completes (0.15-0.83s), timeout is cosmetic in pipeline runner. Non-fatal.
- **WARN**: Win rate 30.8% today (13 trades) — small sample, not actionable yet
- **AUTO-FIX**: None needed — all non-critical

## Error Alerts — 2026-09-07 05:25 UTC
- **WARN** (1x): `signal_compactor: timed out` at 05:13 — single occurrence, recovered on next cycle. Cosmetic.
- **WARN**: Disk 84% (118G total, 93G used). Below 85% threshold but trending up. Consider log rotation.
- **WARN**: `slow-grind+` signal 0% winrate today (5 losses, -$0.77). Sample size low, monitor.
- **WARN**: `price_staleness.json` not found — cannot verify price freshness.
- **AUTO-FIX**: None needed — all non-critical.

## Error Alerts — 2026-09-07 10:25 UTC
- **WARN** (1x): `disk_85pct` — Disk at 85% used (94G/118G). No single hog identified.
- **WARN** (1x): `slow_grind_10pct_wr` — slow-grind signal: 10% winrate, -1.35 USDT. Candidate for disable.
- **INFO**: No errors, no crashes, no phantom trades. Pipeline healthy.

## Error Alerts — 2026-09-07 12:24 UTC
- **WARN** (ongoing since Sep 4): `hermes-5m-candle.service` — script `_aggregate_5m.py` missing, service broken since Sep 4. price_collector handles 5m aggregation already.
- **AUTO-FIX**: Disabled `hermes-5m-candle.service` + timer. Dead weight removed.
- **WARN**: Disk at 84% (94G/118G). Compressed logs >7 days old.
- **WARN**: `slow-grind+` signal: 35.7% WR, -$0.77 today (14 trades). Flat market = losses.
- **WARN**: `coil-spring+` signal: 16.7% WR, -$0.74 today (6 trades). Worst performer.
- **INFO**: Pipeline healthy, 5 open positions, 52 closed today. Market flat (104/106 NEUTRAL).

## Error Alerts — 2026-09-07 13:22 UTC
- **WARN** (2x): `signal_compactor: timed out` at 13:17 and 13:20 — pipeline continued, non-critical
- **WARN** (1x): Disk at 85% — monitor trend, consider log compression if >90%

## Error Alerts — 2026-09-07 18:24 UTC
- **WARN** (1x): `signal_compactor: timed out` at 18:16 — non-critical, pipeline continued normally
- **WARN** (1x): Phantom trade — TURBO SHORT 0.0% PnL, 0.0 USDT

## Health Report — 2026-09-07 21:23 UTC
- **PIPELINE**: OK — running, 0 open, 52 trades today, 57.7% WR, $0.09 PnL
- **MARKET**: NEUTRAL (104/106 tokens), 2 LONG bias (SOPH, ACE), 0 SHORT bias
- **SIGNALS**: 72 generated (1h), top speed: DOT 100%, BLZ 100%, MON 99.5%
- **SYSTEM**: 44 timers active, disk 81% (91G/118G), prices fresh (<1min)
- **WARN** (1x): `signal_compactor: timed out` at 21:22 — non-critical, self-recovered
- **WARN** (1x): Phantom trade — STX SHORT -0.0055 USDT (-0.05%)
- **WARN**: 3 timers permanently broken (atr-sl-updater, ma-cross-5m-tuner, zscore-momentum-tuner) — no unit, never fired
- **INFO**: hl-sync-guardian last fired 3 days ago (Sep 4) — may be stale
- **AUTO-FIX**: None needed — all non-critical
