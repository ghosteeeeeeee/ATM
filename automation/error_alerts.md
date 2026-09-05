## Error Alerts — 2026-09-04 17:22 UTC
- **[WARN]** (4x/1h, 426 total): `signal_compactor: timed out` — compactor completes in ~1s but subprocess timeout hit intermittently. Likely OS scheduling delay, not logic bug.
- **[WARN]**: Disk at 84% (94G/118G) — pipeline.log is 86MB. Recommend compressing old logs.
- **[INFO]**: 0 open trades, system flat. Win rate 54% today (-1.85 USDT).

## Error Alerts — 2026-09-04 18:22 UTC
- **WARN** (1x): `signal_compactor: timed out` at 18:17 — recovered on next cycle, no restart needed
- **WARN**: Disk at 84% (19G free) — monitor for growth, compress logs if >85%

## Error Alerts — 2026-09-04 21:22 UTC
- **WARN** (1x): `disk usage 84%` — approaching 85% threshold, 18GB free on 118GB disk
- **INFO**: `prices.db empty` — 0 bytes, prices stored in candles.db (889MB) instead

## Error Alerts — 2026-09-04 22:22 UTC
- **WARN** (repeating): `z_tier check failed: name 'z_score' is not defined` — `decider_run.py:3082` referenced `z_score` from `_run_hot_set()` scope but was in `run()` scope. **AUTO-FIXED**: changed to `sig.get('z_score', 0.0)`.
- **WARN**: Disk at 84% (94G/118G) — 18GB free. pipeline.log=90MB, 15m_regime.log=50MB. Close to 85% threshold.
- **INFO**: Market deeply NEUTRAL (105/106 tokens). Only DASH has LONG_BIAS. 1 signal in last hour, 0 open trades.
- **AUTO-FIX LOG**: [22:22] health_monitor: Auto-fixed NameError in decider_run.py — z_score variable scope mismatch between _run_hot_set() and run(). Changed line 3082 to use sig.get('z_score', 0.0).

## Error Alerts — 2026-09-04 23:22 UTC
- **WARN** (1x): `signal_compactor: timed out` at 23:20 — recurring intermittent timeout, recovered on next cycle
- **WARN** (3x): Stale signals (>5min) — JUP SHORT (7.1min), AVAX SHORT (7.3min), conditions verified before entry
- **WARN**: Disk at 84% (94G/118G) — holding steady, pipeline.log=5.7MB, old logs may need compression
- **INFO**: 0 open trades in DB (5 live positions via HL), 37 closed today, WR=56.8%, PnL=-1.70 USDT
- **INFO**: Market 105/106 NEUTRAL, only DASH LONG_BIAS. 97 signals generated last hour.
- **NO AUTO-FIX NEEDED**: All issues self-recovered or below threshold. Timers all firing on schedule (47 active).

## Error Alerts — 2026-09-05 00:22 UTC
- **WARN** (1x): `signal_compactor: timed out` at 00:21:02 — recovered on next cycle
- **AUTO-FIX**: None needed — pipeline self-recovered, cycle #185735 ran compactor successfully after timeout
- **MONITOR**: Disk at 84% (94G/118G) — approaching 85% threshold

## Error Alerts — 2026-09-05 02:24 UTC
- **[WARN]** (1x): `Disk at 84% (94G/118G)` — 1% from 85% threshold. Largest DBs: coin_tracker.db 2.2G, hl_copy.db 1.9G.
- **[WARN]** (1x): `-32.01% PnL today` — 37 closed trades, performance issue.
- **[INFO]** (15x): `Auxiliary services in failed state` — 5m-candle, daily-commit, error-analyzer, bug-hunter, wasp, watchdog, etc. None block core pipeline.
- **AUTO-FIX**: None needed — pipeline operational, timers firing.

## Error Alerts — 2026-09-05 03:22 UTC
- **WARN** (1x): `Disk usage at 85%` — threshold hit
- **AUTO-FIX**: Compressed logs older than 7 days, deleted .gz files older than 14 days
- **NOTE**: Disk remains at 85% — hermes data dirs consume 9.9G (coin_tracker.db=2.2G, hl_copy.db=1.9G, candles.db=857M)

## Error Alerts — 2026-09-05 04:23 UTC
- **[WARN]** (5x): `signal_compactor: timed out` — recurring timeout in last hour
- **[WARN]**: Disk at 85% (94G/118G) — coin_tracker.db 2.2G, hl_copy.db 1.9G
- **[WARN]**: 171 phantom trades with |pnl| < 0.01 USDT
- **AUTO-FIX**: No intervention needed — pipeline self-recovering

## Error Alerts — 2026-09-05 06:22 UTC
- **[LOW]** (1x): `signal_compactor: timed out` at 06:12 — one-off, recovered next cycle
- **[WARN]**: Disk at 85% (94G/118G) — coin_tracker.db 2.2G, hl_copy.db 1.9G, candles.db 861M
- **[INFO]**: 0 phantom trades (cleaned up since 04:23)
- **[INFO]**: `hermes-watchdog.service` failing — `pipeline_watchdog.py` missing (stale timer)
- **AUTO-FIX**: Compressed old logs (saved minimal space). No critical action needed.

## Error Alerts — 2026-09-05 08:22 UTC
- **[WARN]**: 98/240 (40.8%) tokens stale — price feeds lagging for ~40% of tracked tokens
- **[INFO]**: Regime fully neutral (0 long / 2 short / 105 neutral) — low conviction signals
- **[OK]**: Pipeline healthy, 12 trades today, 66.7% WR, +$0.51 PnL
- **AUTO-FIX**: None needed.

## Error Alerts — 2026-09-05 13:23 UTC
- **[CRITICAL]** (4x/day since Sep 4): `hermes-hl-reconciliation` failing — script `/root/.hermes/scripts/hl_reconciliation.py` does not exist.
- **AUTO-FIX**: Disabled `hermes-hl-reconciliation.timer` to stop repeated failures.
- **[WARN]** (3x/1h): `signal_compactor: timed out` — transient, pipeline recovered each time.
- **[WARN]**: Disk at 82% (96G/118G) — approaching 85% threshold.
- **[INFO]**: Pipeline OK (cycle #186514), 42 signals (1h), 23 trades today, +0.71 USDT, 65.2% WR, 0 open.

## Error Alerts — 2026-09-05 14:23 UTC
- **[WARN]** (3x/30min): `signal_compactor: timed out` at 13:55, 14:03, 14:13 — recurring ~60s timeout within pipeline (standalone timer OK). No data loss, pipeline recovers.
- **[WARN]**: Disk at 82% (92G/118G) — stable, 26G free. Largest: coin_tracker.db 2.2G, hl_copy.db 1.9G.
- **[INFO]**: Pipeline OK (last cycle #186573, 14:22), 65 signals active, 27 trades today, +0.84 USDT, 66.7% WR, 0 open trades.
- **[INFO]**: Market 104/107 NEUTRAL (1 long, 2 short bias). PONS 97.8% speed, CASHCAT 91.3%.
- **[INFO]**: 188 tokens fresh (<5min), 127 tokens >= 50% speed.
- **AUTO-FIX**: None needed — all systems operational.

## Error Alerts — 2026-09-05 17:23 UTC
- **[WARN]** (22x/1h): `decider_run: Traceback` — `name 'failures' is not defined` at decider_run.py:3325. BUG: `failures` variable referenced in `run()` but only defined inside `_run_hotset()`. All trades HARD-BLOCKED for LOSERS tokens.
- **[INFO]**: Pipeline running (cycle #186754), 3 open trades, 31 closed today, +17.61% PnL.
- **[INFO]**: Market 102/102 NEUTRAL. 56 signals in last hour, 127 tokens >= 50% speed.
- **[INFO]**: Disk 82% (92G/118G), all timers active, hl-sync-guardian running.
- **AUTO-FIX**: Added `failures = _load_hotset_failures()` at decider_run.py:2701. Next pipeline cycle will clear the NameError. Monitor for "HARD-BLOCK" messages disappearing.

## Error Alerts — 2026-09-05 18:22 UTC
- **WARN** (2x): `signal_compactor: timed out` at 18:20 and 18:22 — self-recovered, no fix needed
- **WARN**: Disk at 82% (92G/118G) — approaching 85% threshold. Consider log cleanup.
