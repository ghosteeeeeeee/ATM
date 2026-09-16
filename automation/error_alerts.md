## Error Alerts — 2026-09-15 12:44 UTC
- **[OK]** Pipeline: running, cycle #200919, 0 errors in pipeline itself
- **[OK]** Timers: 65 hermes timers active and firing
- **[OK]** Disk: 81% (22G free) — under threshold
- **[WARN]** YGG SHORT trade failed (12:37:29) — mirror_open RC=1, stderr empty (HYPE exchange). Signal NOT rolled back. Attempted twice, both failed.
- **[WARN]** 8 non-critical services in failed state: 5m-candle, away-detector, better-coder, bug-hunter, git-release, mtf-macd-tuner, signal-reporter, trading-checklist
- **[WARN]** momentum_cache.db: 0 bytes, empty since Sep 12
- **[INFO]** Signals: 62 generated last hour, 66,610 total
- **[INFO]** Trades: 11 closed today, -1.06 USDT, 45.5% WR, 0 open
- **[INFO]** Regime: NEUTRAL (1 long bias, 126 neutral)
- **[INFO]** Speed: 127/241 tokens >= 50th percentile
- **INFO** pipeline.log: 109MB — large, consider rotation

## Error Alerts — 2026-09-15 11:43 UTC
- **[OK]** Pipeline: running, last cycle 11:42:34, 0 errors
- **[OK]** Trades: 29 closed today, +12.43% PnL, 4 open positions
- **[OK]** Timers: all active and firing on schedule
- **[OK]** Disk: 81% (22G free) — under threshold
- **[WARN]** Signals DB: 66,548 signals accumulating (no cleanup running)
- **[WARN]** momentum_cache.db: 0 bytes, 451h stale — file empty since Sep 12
- **[WARN]** 9 services in failed state (non-critical: 5m-candle, away-detector, better-coder, bug-hunter, git-release, mtf-macd-tuner, session-brain-rebuild, signal-reporter, trading-checklist)
- **[WARN]** trading-checklist: exited status=2 (INVALIDARGUMENT) — momentum_cache check failed
- **[INFO]** Regime: 127 tokens, all NEUTRAL
- **[INFO]** Open: 4 positions (W SHORT, SUSHI SHORT, STX SHORT, +1)

## Error Alerts — 2026-09-12 16:25 UTC
- **[INFO]** Pipeline: OK — running, last cycle 16:23:19, 0 errors
- **[INFO]** Signals: 106 generated last hour (healthy flow)
- **[INFO]** Trades: 25 today, 60% WR, PnL=-$0.31 (flat market)
- **[INFO]** Open positions: 5/5 (HL copy trades — new entries skipped by design)
- **[INFO]** Regime: 1 LONG (MET), 0 SHORT, 104 NEUTRAL — flat market
- **[INFO]** Speed: 0 tokens >= 50% — no momentum
- **[INFO]** Timers: 60+ active, all critical timers firing
- **[INFO]** Disk: 78% (87G/118G)
- **[WARN]** 1 phantom trade — NEAR LONG rr-struct+ PnL=$0.006 (negligible)
- **AUTO-FIX**: None needed

## Error Alerts — 2026-09-12 14:24 UTC
- **[INFO]** Pipeline: OK — last run 14:23:20, exit 0, next cycle ~20s
- **[INFO]** Signals: 109 generated last hour, 67,583 total (healthy flow)
- **[INFO]** Trades: 0 open (DB), 21 closed today ($0.29 PnL, 66.7% WR)
- **[INFO]** Regime: 105/105 tokens NEUTRAL, 0 LONG, 0 SHORT
- **[INFO]** Timers: 30+ hermes timers active, all firing on schedule
- **[INFO]** Disk: 78% (87G/118G) — 7% from 85% threshold
- **[INFO]** Services: hermes-pipeline oneshot (inactive=normal), hl-sync-guardian active
- **[INFO]** No errors, no tracebacks, no crashes in last 30 min
- **[WARN]** Stale signals persist: SEI SHORT (10min), BLUR SHORT (10min), ALT LONG (10min) — all blocked by max-positions (5/5), system verifying conditions before entry
- **AUTO-FIX**: None needed — all systems nominal

## Error Alerts — 2026-09-12 09:24 UTC
- **[INFO]** Pipeline: OK — running, cycle #196381, 0 errors, 0 tracebacks
- **[INFO]** Signals: 71 generated last hour, 0 survived compaction (market NEUTRAL)
- **[INFO]** Trades: 0 open, 18 closed today ($0.19 PnL, 66.7% WR)
- **[INFO]** Regime: 111/112 NEUTRAL, 0% tokens >= 50th percentile
- **[WARN]** 10 services in "failed" state — all non-critical (auxiliary services)
- **INFO** Disk at 78% (26G free), all timers active, no auto-fixes needed

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

## Error Alerts — 2026-09-11 09:23 UTC
- **[WARN]** (7x): `signal_compactor: timed out` — non-fatal, pipeline continues. May indicate high load.
- **[WARN]**: Disk at 84% (19G free) — 1% from 85% threshold. Monitor.
- **[WARN]**: Today PnL -23.65% across 45 closed trades. Worst: pullback-entry- (37.5% WR), pump-chain+ (28.6% WR).
- **[INFO]**: Market regime all NEUTRAL across 105 tokens — low conviction environment.

## Error Alerts — 2026-09-11 12:23 UTC
- **[INFO]** Pipeline: OK — running, last cycle 12:23:09, 2 open positions (eth, imx), 0 approved signals
- **[INFO]** Signals: 0 passed compaction (all blocked by confluence gate / R:R filter / neutral regime)
- **[INFO]** Trades: 27 today, -$2.12 PnL, 37.0% WR (LONG 36.4%, SHORT 37.5%)
- **[INFO]** Regime: 100% NEUTRAL (105 tokens neutral, 0 long, 0 short)
- **[WARN]** (2x): `signal_compactor: timed out` at 12:19 and 12:22 — self-recovered on next cycle
- **[WARN]** Disk at 83% (93G/118G) — 2% from 85% threshold
- **[WARN]** candles.db at 976MB — growing, may contribute to disk pressure
- **[WARN]** metrics_collector.py missing — timer firing but script not found (repeated errors)
- **AUTO-FIX**: None needed — compactor timeouts self-recovered, pipeline running normally

## Error Alerts — 2026-09-11 14:24 UTC
- **WARN** (3x): `signal_compactor: timed out` at 13:55, 13:59, 14:02 — recurring ~every 4 min but pipeline recovers each cycle
- **WARN**: Today's winrate 38.9% (36 closed trades, -$1.65 PnL)
- **INFO**: No auto-fixes needed — pipeline self-recovers from compactor timeouts

## Error Alerts — 2026-09-11 15:55 UTC
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-09-11 16:55 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (16x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — CONTAGION+MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.6x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,TOK,MOMENTUM,BTC_LEVEL | vol=N.6x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.8x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.7x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING — CONTAGION+MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **REPEATED** (5x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.9x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-11 17:55 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-11 18:24 UTC
- **[WARN]** (Nx): Disk at 84% used (93G/118G) — within 1% of 85% threshold
- **[WARN]** (1x): 1 phantom trade detected (ABS pnl_pct < 0.01) in last 24h
- **[INFO]** (49x): 49 stale price tokens flagged — likely low-activity coins

## Error Alerts — 2026-09-11 18:55 UTC
- **REPEATED** (13x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.7x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — TOK+MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.9x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.6x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.7x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-11 21:23 UTC
- **WARN** (14x): `hermes-* services in failed state` — all auxiliary (better-coder, bug-hunter, ceo-dashboard, etc.), not blocking trading
- **WARN** (2x): `hermes-coding-mcp, hermes-metrics auto-restart loops` — not blocking pipeline
- **INFO**: 120/120 tokens NEUTRAL regime — flat market, low signal volume expected

## Error Alerts — 2026-09-11 21:55 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-11 22:55 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.9x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING — CONTAGION+MOMENTUM`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.8x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.1x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — CONTAGION+MOMENTUM`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (4x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-12 00:55 UTC
- **REPEATED** (10x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-12 01:55 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-09-12 07:55 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   → TOK:`

## Error Alerts — 2026-09-12 10:55 UTC
- **REPEATED** (6x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-12 15:23 UTC
- **INFO** (2x): `Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument` — benign systemd warning, no operational impact. Pipeline restarted cleanly.

## Error Alerts — 2026-09-12 15:55 UTC
- **REPEATED** (4x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-12 17:24 UTC
- **WARN** (1x): `hermes-hl-sync-guardian.timer` last fired 35h ago (Sep 11 06:30). Service active but timer stale.
- **INFO**: hermes-pipeline.timer, hermes-price-collector.timer disabled — likely running via other triggers.
- **INFO**: Hotset empty — 104/106 tokens NEUTRAL. Normal in low-volatility regime.

## Error Alerts — 2026-09-12 17:55 UTC
- **REPEATED** (4x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (9x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-12 18:24 UTC
- **OK**: Pipeline health check passed. No issues found.
- Pipeline last run: 18:23:28 UTC (clean)
- 154 signals, 5 open trades, 40 closed today
- Disk: 78%, all timers firing, no phantoms

## Error Alerts — 2026-09-12 20:55 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`
- **REPEATED** (4x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-13 02:24 UTC
- **[INFO]** Pipeline: OK — running, last cycle 02:23:43, 0 errors, 25.7s CPU
- **[INFO]** Signals: 118 generated last hour (healthy flow)
- **[INFO]** Trades: 0 open, 3 closed today (-$0.21 PnL, 33.3% WR)
- **[INFO]** Regime: LONG_BIAS (3 long / 0 short / 104 neutral)
- **[INFO]** Speed: 52.7% tokens >= 50th percentile (127/241)
- **[INFO]** Timers: 0 active (pipeline runs via service, not timer)
- **[INFO]** Disk: 78% used (87G/118G)
- **[INFO]** Prices: 94 tokens tracked, 0 errors
- **[WARN]** hotset fallback DB query returning 0 tokens each cycle (non-critical, hotset.json works)
- **AUTO-FIX**: None needed — all systems nominal

## Error Alerts — 2026-09-13 03:55 UTC
- **REPEATED** (4x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-13 04:25 UTC
- **[WARN]** (1x): `hermes-5m-candle.service` failed — `_aggregate_5m.py` not found (dead since Sep 11)
- **AUTO-FIX**: Disabled `hermes-5m-candle.timer`. Candles still populated by price_collector/fetch_binance_candles paths.
- **[WARN]** (1x): Phantom trade — NOT SHORT pullback-entry- with 0.0% PnL at 00:31 UTC
- **[INFO]** Hotset empty — market NEUTRAL regime, no signals survived compaction

## Health Check — 2026-09-13 05:25 UTC
- **WARN**: trend_purity+ LONG: 0% WR on 3 trades today (-0.74 USDT) — signal performance degraded
- **INFO**: 31 phantom trades historically (spread over 7 weeks, no recent spike)
- **INFO**: systemd "Failed to kill control group" — benign cleanup artifact
- **AUTO-FIX**: None required

## Error Alerts — 2026-09-13 06:55 UTC
- **REPEATED** (6x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-13 07:55 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-13 08:55 UTC
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-09-13 09:55 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-13 13:55 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.5x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.1x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.8x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.9x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.0x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-13 14:55 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **REPEATED** (10x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.6x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.9x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.9x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-13 15:55 UTC
- **REPEATED** (11x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (13x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction:`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK (most recent call last):`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`

## Error Alerts — 2026-09-13 19:55 UTC
- **REPEATED** (8x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (25x): `Sep N N:N:N python3[TOK]: TS   TS [TOK]   ⚠️ [SL-TOK-TOK] TOK for TOK: name 'sqlite3' is not defined`

## Error Alerts — 2026-09-13 20:25 UTC
- **CRITICAL** (FIXED): `⚠️ [SL-ZONE-EXIT] Error for FOGO/ETH: name 'sqlite3' is not defined` — Missing `import sqlite3` in position_manager.py SL-ZONE-EXIT handler. Added `import sqlite3 as _sqlite3_slz` + local alias. Verified fixed — zero errors on next pipeline run.
- **INFO** Pipeline: OK — running every 1m, last cycle 20:25:24, 0 errors post-fix
- **INFO** Trades: 31 closed today, PnL=+$0.17 (flat market, low volume)
- **INFO** Signals: 10 generated last hour (normal flow)
- **INFO** Open: 0 (all positions closed)
- **INFO** Regime: NEUTRAL (122 tokens scanned)
- **INFO** Token speeds: 127/241 >= 50th percentile (53% high-speed)
- **INFO** Disk: 79% used (24G free)
- **INFO** Timers: hermes-pipeline.timer active, firing every 1m
- **INFO** Auto-fix: Applied `sqlite3` import fix to position_manager.py line 2510

## Error Alerts — 2026-09-13 20:55 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.0s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.4s):`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Error Alerts — 2026-09-13 21:25 UTC
- **[INFO]** Pipeline: OK — running, last cycle 21:23:19, 0 errors
- **[INFO]** Signals: 108 generated last hour (healthy flow)
- **[INFO]** Trades: 31 closed today, 54.8% WR, PnL=+$0.17 (+31.53%)
- **[INFO]** Open positions: 7 (HL) — signals skipped by max-position limits
- **[WARN]** 45% tokens stale (109/241) — price collector may need tuning
- **[WARN]** 11 failed services — mostly non-critical (5m-candle, away-detector, better-coder, etc.)
- **AUTO-FIX**: Disabled hermes-metrics.service — missing script metrics_collector.py, 4.8MB error log spam cleared

## Error Alerts — 2026-09-13 22:55 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-13 23:55 UTC
- **REPEATED** (4x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-14 00:55 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-09-14 01:55 UTC
- **REPEATED** (3x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`

## Error Alerts — 2026-09-14 02:55 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-14 03:25 UTC
- **[WARN]** (1x): `signals table bloat: 68,701 active signals, 51,932 older than 7 days — no cleanup mechanism`
- **[WARN]** (1x): `signal_history table empty (0 rows) — archive mechanism not functioning`
- **[INFO]** Pipeline: OK — running, last cycle 03:24:25, 0 errors, 0 tracebacks
- **[INFO]** Signals: 105 generated last hour (healthy flow)
- **[INFO]** Trades: 1 open (CAKE LONG), 46 closed today, +27.86% PnL
- **[INFO]** Timers: 10 active, all firing on schedule
- **[INFO]** Disk: 79% used (24G free)
- **[INFO]** Kill switch: LIVE TRADING ENABLED

## Error Alerts — 2026-09-14 03:55 UTC
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-14 04:55 UTC
- **REPEATED** (6x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   → TOK:`

## Error Alerts — 2026-09-14 05:24 UTC
- **[INFO]** Pipeline: OK — running every 1m, last cycle 05:23:25, 0 errors
- **[INFO]** Signals: 127 generated last hour (healthy flow)
- **[INFO]** Trades: 10 closed today, 40% WR, PnL=-$0.72 (flat market)
- **[INFO]** Open positions: 5 (NEO SHORT, JUP SHORT, BCH LONG, KAS LONG, +1)
- **[INFO]** Regime: NEUTRAL (1 LONG: LTC, 0 SHORT, 122 neutral)
- **[INFO]** Speed: 0% tokens >= 50th percentile (flat market, expected)
- **[INFO]** Hotset empty — no signals survived compaction (NEUTRAL regime)
- **[INFO]** Timers: 57 active, all firing on schedule
- **[INFO]** Disk: 80% used (89G/118G) — 5% from 85% threshold
- **[INFO]** Prices: 94 tokens, fresh (05:23)
- **[INFO]** 8 failed services — all auxiliary/known (5m-candle, away-detector, better-coder, bug-hunter, git-release, mtf-macd-tuner, trading-checklist, session-brain-ingest)
- **AUTO-FIX**: None needed — pipeline healthy

## Error Alerts — 2026-09-14 05:55 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   [brain.py] ❌ REJECTED: TOK TOK — amount_usdt=N.N < HL_MIN=N.N (would TOK on HL)`

## Error Alerts — 2026-09-14 06:56 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,TOK,MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-14 07:56 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`

## Error Alerts — 2026-09-14 08:56 UTC
- **REPEATED** (12x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   → TOK:`

## Error Alerts — 2026-09-14 09:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`

## Error Alerts — 2026-09-14 10:44 UTC
- **REPEATED** (2x): `[BTC-CRASH] ALT SHORT BLOCKED — WARNING: BTC level: -0.51% from high, +0.05% from low — blocking SHORT entries` (expected, safety filter)
- **CRITICAL** (1x): `hermes-coding-mcp.service` crash-looping — 465,434 restarts, script `run_mcp_server.py` missing. **AUTO-FIX**: stopped + disabled service.
- **WARN** (1x): `hermes-5m-candle.service` failed — script `_aggregate_5m.py` missing (2 days dead). Can't disable (static unit). Needs manual cleanup.
- **WARN** (1x): `hermes-away-detector.service` failed — 1 week dead. Needs manual cleanup.
- **WARN** (1x): `momentum_cache` stale — 426h old (17.75 days), 193 tokens.
- **INFO**: Pipeline completed OK — 8 open, 45 closed today, -33.84% PnL. Regime: NEUTRAL.

## Error Alerts — 2026-09-14 10:56 UTC
- **REPEATED** (6x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-09-14 12:56 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`

## Error Alerts — 2026-09-14 13:56 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.9x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — CONTAGION+MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.7x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-14 14:56 UTC
- **REPEATED** (4x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — TOK+CONTAGION+MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: TOK,CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,BTC_LEVEL | vol=N.7x eth_div=+N.N% | BTC_LEVEL: TOK blocked (-N.N% from high)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.0x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.0x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-14 15:56 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.2x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-14 17:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-14 18:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.4x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.3x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-14 19:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-14 20:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-14 21:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.7x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.9x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.6x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-14 23:43 UTC
- **WARN** (Nx): `hermes-1m-candle.timer DISABLED` — 1-minute candle collection stopped
- **WARN** (Nx): `hermes-5m-candle.timer DISABLED` — 5-minute candle collection stopped
- **INFO** (1x): `phantom trade` — JUP SHORT with 0.0085% PnL (near-zero)
- **INFO**: Pipeline log at 96MB — recommend compression of old logs

## Error Alerts — 2026-09-14 23:56 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,BTC_LEVEL | vol=N.7x eth_div=-N.N% | BTC_LEVEL: TOK blocked (-N.N% from high)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,BTC_LEVEL | vol=N.7x eth_div=-N.N% | BTC_LEVEL: TOK blocked (-N.N% from high)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (10x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-09-15 00:44 UTC
- **[WARN]** Disk at 81% (90G/118G) — approaching 85% threshold. No old logs to compress.
- **[INFO]** Market regime: 122/124 NEUTRAL, 0 fast tokens. Pipeline correctly producing 0 executions. No action needed.

## Error Alerts — 2026-09-15 01:44 UTC
- **[WARN]**: Disk at 81% (90G/118G) — 4% from 85% threshold
- **[WARN]**: Hotset fallback DB query returned 0 tokens at 01:42:43
- **[INFO]**: Today's PnL -38.21% (40 closed trades) — elevated loss day

## Error Alerts — 2026-09-15 01:56 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.8x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-15 05:44 UTC
- **WARN** (3x): Pre-existing failed services — `hermes-5m-candle`, `hermes-away-detector`, `hermes-bug-hunter` reference missing scripts. Not blocking pipeline. Suggest: disable or fix unit files.
- **WARN** (1x): All 127 tokens at >=50th percentile speed — distribution may need reset.

## Error Alerts — 2026-09-15 05:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-09-15 07:56 UTC
- **REPEATED** (12x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-15 14:56 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,BTC_LEVEL | vol=N.1x eth_div=+N.N% | BTC_LEVEL: TOK blocked (-N.N% from high)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.6x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-15 15:56 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-15 16:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   → TOK:`

## Error Alerts — 2026-09-15 17:43 UTC
- **[WARN]**: `[hotset] fallback DB query returned 0 tokens` — hotset fallback empty, non-blocking
- **[INFO]**: rr-struct-v2+ LONG — 4 trades, 0% win rate, -0.79 PnL today
- **[INFO]**: pipeline.log 115M — approaching retention threshold

## Error Alerts — 2026-09-15 18:45 UTC
- **WARN** (3x): `PHANTOM-WRITE` blocked SL adjustment — ETH SHORT (dist=0.112%), SUPER SHORT (dist=0.056%) — SL too tight to entry, guardian can't tighten further
- **WARN** (1x): `TRADE FAILED: MET SHORT` — signal not rolled back (prevents retry loop)
- **WARN**: Disk at 81% (91G/118G) — approaching 85% threshold
- **INFO**: 33.3% win rate today (6W/12L) — rough session, 18 closed trades
- **AUTO-FIX**: None required — pipeline healthy, all timers firing

## Error Alerts — 2026-09-15 18:56 UTC
- **REPEATED** (5x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-15 19:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — CONTAGION+BTC_LEVEL`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,BTC_LEVEL | vol=N.6x eth_div=+N.N% | BTC_LEVEL: TOK blocked (-N.N% from high)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-15 20:56 UTC
- **REPEATED** (8x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.0x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-15 22:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-16 00:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: BIGTIME TOK — signal TOK rolled back (prevents retry loop)`

## Error Alerts — 2026-09-16 01:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: IO TOK — signal TOK rolled back (prevents retry loop)`
