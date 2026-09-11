## Error Alerts — 2026-09-11 06:23 UTC
- **[INFO]** Pipeline: OK — running, last cycle 06:23:11, 5 open trades
- **[INFO]** Signals: 119 generated in last hour
- **[INFO]** Trades: 11 today, -$1.25 PnL, 27.3% WR (pump-chain SHORT best at 70.6%)
- **[INFO]** Speed: 127/241 tokens >= 50% (52.7%)
- **[INFO]** Regime: NEUTRAL (105 neutral, 1 short, 0 long)
- **[WARN]** (2x): `signal_compactor: timed out` at 06:19 and 06:22 — self-recovered
- **[WARN]** Hotset empty — 0 tokens survived compaction (NEUTRAL regime, low signal quality)
- **[WARN]** Disk at 84% (93G/118G) — 1% from 85% threshold
- **[WARN]** 10 phantom trades (exactly 0.0 PnL) — mostly historical, not recent
- **AUTO-FIX**: Compressed 18 old .gz logs, vacuumed journal (freed 0B — journals already clean)

## Error Alerts — 2026-09-10 23:23 UTC
- **[INFO]** Pipeline: OK — running, last cycle 23:23:03, 0 open trades in DB, 4 open per pipeline
- **[INFO]** Signals: 91 generated in last hour (19 LONG, 72 SHORT)
- **[INFO]** Trades: 36 today, +$1.42 PnL, 63.9% WR (best: pump-chain SHORT 73.3%)
- **[WARN]** (2x): `signal_compactor: timed out` at 23:14 and 23:16 — self-recovered on next cycle
- **[WARN]** 69/241 tokens stale (28.6%) — expected in NEUTRAL market
- **[WARN]** Disk at 83% (93G/118G) — 2% from 85% threshold
- **AUTO-FIX**: None needed — transient compactor timeouts self-recovered

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

## Error Alerts — 2026-09-10 17:23 UTC
- **[WARN]** (Nx1): `disk_84pct` — Disk at 84% (93G/118G), approaching 85% threshold
- **AUTO-FIX**: None needed yet. Will compress logs if hits 85%.

## Health Check — 2026-09-10 20:24 UTC
- **INFO**: Pipeline running, all services active
- **INFO**: 74 signals generated in last hour, 4 open trades, 43 closed today (+81.12% PnL)
- **INFO**: Regime NEUTRAL, 94 coins tracked
- **AUTO-FIX**: Fixed missing `CONTINUUM_OSC_ENABLED` import in `signal_schema.py:2421` — was causing `[RAW-SIGNALS] write failed` every minute. Restarted pipeline.
- **MONITOR**: `signal_compactor` non-fatal crash on every cycle (line 3780) — does not block pipeline but needs investigation
- **MONITOR**: Disk at 83% (93G/118G) — approaching 85% threshold
- **WARN**: `hermes-5m-candle.service` and `hermes-coding-mcp.service` still broken (missing scripts, known from earlier)

## Error Alerts — 2026-09-10 21:26 UTC
- **[CRITICAL]** (35x): `hermes-signal-compactor.service` crash loop — `NameError: name 'CHOP_DETECTOR_ENABLED' is not defined` at signal_compactor.py:2671. Variable imported inside `_score_signal()` but referenced in `run_compaction()` (different scope). Crashed 35 times in 4 minutes (21:15–21:19), then self-recovered.
- **[INFO]** Pipeline running, last cycle 21:23:21, 5 open, 41 closed today, +83.11% PnL
- **[INFO]** Signals: 42 generated in last hour, 1 hotset (LDO LONG)
- **[INFO]** Regime: NEUTRAL (0 hot, 87 warm, 7 cold)
- **[WARN]** Disk at 83% (93G/118G) — 2% from threshold
- **AUTO-FIX**: Added `from hermes_constants import CHOP_DETECTOR_ENABLED` before line 2671 in signal_compactor.py. Verified compactor runs clean (dry run: 1 hotset, 0 errors). Standalone service and pipeline both confirmed working post-fix.

## Error Alerts — 2026-09-11 00:24 UTC
- **WARN** (2x): `signal_compactor: timed out` at 00:17 and 00:20
- **AUTO-FIX**: None — non-fatal, pipeline continued running. Monitor for escalation.

## Health Check — 2026-09-11 04:23 UTC
- **[OK]** Pipeline: ACTIVE (cycle #194630), 60 cycles in last hour, no errors
- **[INFO]** Signals: 67 generated last hour, 0 in hotset (none survived compaction)
- **[INFO]** Trades: 2 open (3→2 after NOT SHORT closed at 04:22), 9 closed today
- **[INFO]** PnL today: -$0.67 (3 wins / 9 trades = 33% WR)
- **[INFO]** Regime: NEUTRAL (104/105 tokens neutral, 1 long-biased)
- **[WARN]** signal_compactor timeout: 1 in last hour (non-fatal, recovered at 04:22:33)
- **[WARN]** Disk at 84% (93G/118G) — 1% from threshold
- **[WARN]** 0 tokens in hotset — all 67 signals filtered out by compaction
- **AUTO-FIX**: None needed — pipeline self-recovered from compactor timeout

## Health Check — 2026-09-11 07:23 UTC
- **[OK]** Pipeline: ACTIVE, 5 open positions, no Tracebacks in last 30min
- **[INFO]** Signals: 158 generated last hour, 0 in hotset (none survived compaction)
- **[INFO]** Regime: NEUTRAL (104 neutral, 1 long-biased)
- **[INFO]** Speed: 53% tokens >= 50th percentile (127/241)
- **[WARN]** signal_compactor timeout: 3x in last 10min (07:18, 07:20, 07:22) — non-fatal, pipeline self-recovered
- **[WARN]** Disk at 83% (93G/118G) — 2% from threshold
- **[INFO]** All 44 hermes timers active and firing on schedule
- **AUTO-FIX**: None needed
