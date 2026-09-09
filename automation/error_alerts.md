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

## Health Report — 2026-09-08 17:23 UTC
- **PIPELINE**: OK — last ran 17:22 UTC, completed normally. 3 open, 71 closed today, -37.16% PnL
- **MARKET**: NEUTRAL regime (102/104), 2 SHORT bias, 0 LONG bias
- **SIGNALS**: 125 generated (1h) — healthy volume
- **SYSTEM**: 50+ timers active, disk 82% (92G/118G), prices fresh (2min ago)
- **WARN** (2x in 30min): `signal_compactor: timed out` — recurring, non-fatal. Pipeline completes despite timeouts.
- **WARN**: 4 phantom trades today (<0.01 USDT PnL) — BANANA, SAND, USUAL, ICP
- **WARN**: Disk at 82% — approaching85% threshold, compress logs if rising
- **INFO**: pipeline.log at94MB — will need rotation soon
- **AUTO-FIX**: None needed — all issues non-critical, system self-recovers

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

## Error Alerts — 2026-09-07 23:25 UTC
- **WARN** (1x): `signal_compactor` timeout at 23:21:02 — transient, recovered on next run
- **WARN** (ongoing): `chop_detector.py:155` — `CHOP_DETECTOR_BTC_MOM_THRESHOLD` import fails → defaults to conservative (is_flat=True), non-critical
- **INFO**: Pipeline healthy — 61 trades today, +13.56% PnL, 4 open positions
- **INFO**: Disk at 81% (91G/118G) — below 85% threshold
- **AUTO-FIX**: None needed — all non-critical

## Error Alerts — 2026-09-08 04:23 UTC
- **WARN** (4x): `signal_compactor` timeout at 04:18 and 04:21 — recurring, pipeline still completes successfully
- **INFO**: Pipeline healthy —12 trades today, 2 closed (+0.04 USDT), 5 open positions
- **INFO**: Disk at 82% (91G/118G) — below 85% threshold
- **INFO**: Timers all firing on schedule —48 active hermes timers
- **INFO**: Market regime — 3 LONG_BIAS, 2 SHORT_BIAS, 100 NEUTRAL (overall: NEUTRAL)
- **AUTO-FIX**: Compressed 17 old log files (saved ~30MB)

## Error Alerts — 2026-09-08 05:23 UTC
- **[WARN]** (1x): `signal_compactor: timed out` at 05:20:02 — recovered on next cycle
- **[WARN]**: Disk at 82% (21G free) — approaching threshold
- **[INFO]**: 15+ auxiliary services in failed state (non-critical)
- **AUTO-FIX**: None needed — pipeline healthy, signal_compactor self-recovered

## Error Alerts — 2026-09-08 06:24 UTC
- **[CRITICAL]** (42x in 30min): `EMA300_DIP_SHORT_MAX_EMA_SLOPE` NameError in `decider_run.py:3515` — constant used but not imported
- **AUTO-FIX**: Added missing import in `decider_run.py:3472`. Restarted pipeline. Verified fix — no more EMA300 errors.
- **[WARN]** (1x): `signal_compactor: timed out` at 06:18:02 — recurring, non-fatal
- **INFO**: Pipeline healthy — 0 open, 21 closed today, 130 signals/hr, 82% disk
- **INFO**: Market NEUTRAL (1 LONG_BIAS, 1 SHORT_BIAS, 103 neutral), BTC $78,590

## Error Alerts — 2026-09-08 09:23 UTC
- **[INFO]**: Pipeline healthy — 5 open, 64 closed today, +53.11% PnL
- **[WARN]** (1x): `signal_compactor: timed out` at 09:19:02 — recurring pattern, self-recovered
- **[INFO]**: Disk at 82% (91G/118G) — approaching 85% threshold
- **[INFO]**: 48 hermes timers active, all firing on schedule
- **INFO**: Market NEUTRAL (103 neutral, 1 long bias), 137 signals/hr
- **AUTO-FIX**: None needed — all systems nominal

## Error Alerts — 2026-09-08 15:24 UTC
- **CRITICAL** (1): `hermes-5m-candle.service repeatedly failing (exit code)`
- **AUTO-FIX**: Attempted restart — failed with same exit code, needs manual investigation
- **WARN** (1): `signal_compactor timeout at 15:18:02`
- **AUTO-FIX**: Pipeline still completed; no action needed unless recurring
- **WARN** (1): `FIL LONG blocked in cooldown (2 failures, ~59 min remaining)`
- **AUTO-FIX**: None — cooldown is expected behavior after failures
- **WARN** (1): `20+ auxiliary services in failed state`
- **AUTO-FIX**: None — services like bug-hunter, better-coder, wasp are non-critical

## Health Report — 2026-09-08 18:23 UTC
- **[WARN]** (1x): `signal_compactor: timed out` — one-off timeout, pipeline recovered, no action needed
- **[WARN]** (1x): Disk at 82% (21G free) — compressed old logs (>1 day)
- **[INFO]** Pipeline ran 18:22:32 UTC, completed 18:22:34. 5/5 positions open, 71 closed today, -40.10% PnL. 109 signals in last hour. All timers firing.

## Health Report — 2026-09-08 19:23 UTC
- **[WARN]** (1x): `signal_compactor: timed out` at 19:19:02 — recovered on next cycle (19:19:33). Recurring pattern, non-fatal.
- **[WARN]**: Disk at 83% (92G/118G) — compressed old logs (>3 days), stable
- **[INFO]** Pipeline ran 19:22:19 UTC, completed 19:22:33. 0 open, 74 closed today, -56.79% PnL. Hotset empty (no signals above 50% confidence).
- **[INFO]** Market: 3 SHORT bias, 0 LONG bias, 104 tokens scanned. Regime NEUTRAL-leaning.
- **[INFO]** 53 timers active, all firing on schedule. No crashes, no phantom trades.
- **AUTO-FIX**: None needed — all issues non-critical, system self-recovers

## Health Report — 2026-09-08 22:23 UTC
- **[CRITICAL]** (1x): Portfolio PnL at **-96.28%** (PostgreSQL `trades` table). Dropped from -40% at 18:23 → -56% at 19:23 → -96% at 22:23. 5 open positions with heavy unrealized losses dragging total PnL.
- **[WARN]** (1x): Hotset empty — no signals survived compaction. 0 signals above 50% confidence. System is managing 5 open positions but not entering new ones.
- **[WARN]** (1x): `signal_compactor: timed out` — recurring pattern, self-recovered. Non-fatal.
- **[INFO]** Pipeline ran 22:22:33 UTC, completed normally. 5/5 positions open, 69 closed today. Position manager healthy (0 closed, 0 adjusted this cycle).
- **[INFO]** Market: 104 tokens scanned, regime NEUTRAL (103 neutral, 1 long bias). Speed data unavailable (schema mismatch).
- **[INFO]** 55 timers active, all firing on schedule. No crashes, no phantom trades.
- **[INFO]** Disk at 83% (92G/118G) — stable, below 85% threshold.
- **[INFO]** Live trading enabled (`hype_live_trading.json`: true).
- **AUTO-FIX**: None applied — PnL issue requires manual review of open positions and risk parameters. No system failures to restart.

## Error Alerts — 2026-09-08 23:23 UTC
- **[WARN]** (5x): Near-zero PnL trades (<$0.01) — phantom trade candidates: ATOM/LONG, BANANA/SHORT, SAND/LONG, USUAL/LONG, ICP/LONG
- **[WARN]** (1x): Max positions reached (5/5) — KAS SHORT signal skipped at 23:22
- **AUTO-FIX**: None required — pipeline healthy

## Error Alerts — 2026-09-09 01:23 UTC
- **CRITICAL** (4x): `signal_compactor timed out` — recurring every ~10min for last hour
- **WARN**: Disk at 83% (92G/118G) — approaching 85% threshold
- **INFO**: Pipeline completed successfully at 01:22:35, 5 open positions, -97.56% daily PnL

## Error Alerts — 2026-09-09 04:24 UTC
- **WARN** (1x): `signal_compactor: timed out` — recovered on next run (04:22:33)
- **WARN** (1x): Phantom trade detected — ABS(pnl_pct) < 0.01% in last 24h
- **INFO**: Disk at 83% (118G, 20G free) — approaching 85% threshold

## Error Alerts — 2026-09-09 05:23 UTC
- **[WARN]** (Nx): `CTX-GATE blocking 100% of signals — 115 signals generated, 0 executed. LLM NAY on CRV, POL: "setup is actively harmful"`
- **[WARN]** (1x): `hermes-hl-sync-guardian last fired ~12h ago (2026-09-08 16:37 UTC)`
- **AUTO-FIX**: none needed — pipeline and timers healthy

## Error Alerts — 2026-09-09 15:24 UTC
- **WARN** (N=5): `signal_compactor: timed out` in pipeline — recurring, not blocking
- **WARN**: 72,466 active signals backlog (since Aug 10) — signal_purge underperforming
- **WARN**: Disk at 83% — approaching 85% threshold, compress old logs
- **INFO**: Pipeline "5 open/37 closed/-29%" vs DB "0 open/22 closed/+$0.97" — timing mismatch between exchange positions and DB records
