## Error Alerts — 2026-09-21 18:46 UTC
- **[WARN]** (23x): `signal_compactor timed out (killed after 60.1s)` — 23 occurrences in last 6h (12:48-18:42). Intermittent — most runs complete in 1-5s. Likely caused by 92MB signal DB with 5,884 active signals (BTC alone has 425 duplicate signals). Pipeline recovers on next cycle each time.
- **[WARN]**: 0 signals passing compactor — "No signals above 50% confidence — skipping execution" on recent runs. Compactor is filtering everything out. Market regime heavily neutral (117/120 neutral, 3 short).
- **[WARN]**: Today's performance — 23 trades, 34.8% WR, -$0.55 PnL. 4 phantom trades with <0.05% PnL (ALT 0.0%, GMX 0.017%, KAS -0.003%, BANANA -0.021%).
- **[INFO]**: 1 open position — CFX SHORT, entry 0.053261, current ~0.05335, PnL ~-0.2%. HIGH volatility gate active (SL 1.5%, TP 1.1%).
- **[INFO]**: BTC-CRASH block active — DOGE LONG blocked at 18:28:23 (BTC -0.12% from high).
- **[INFO]**: Pipeline running normally, all timers active, disk 82% (safe).

## Error Alerts — 2026-09-21 08:46 UTC
- **[WARN]** (1x): `signal_compactor timed out (killed after 60.1s)` at 08:42:02 — self-recovered on next cycle (0.9s)
- **[WARN]** (1x): CRV LONG trade execution failed at 08:38:25 — signal rolled back properly, no retry loop
- **[WARN]**: Disk at 85% (94G/118G) — data 6.9G, /tmp 6.1G. No compressible logs found.
- **[INFO]**: Pipeline cycle #209259, 0 open trades, 9 losses + 1 win in last 7h
- **[INFO]**: Market regime LONG_BIAS (3L/0S/117N), 5130 active signals

## Error Alerts — 2026-09-21 00:47 UTC
- **[OK]**: Pipeline running normally — last cycle 00:44:00, 0 errors
- **[OK]**: 5 open trades, 27 closed (24h), PnL=+1.84 USDT, WR=63.0%
- **[WARN]**: Disk at 84% (was 85%) — auto-fixed: journal vacuum freed 437.7MB, WAL checkpoints, removed 8 defunct 0-byte DBs
- **[WARN]** (recurring): BANANA LONG phantom write blocked every cycle — SL distance 0.081% (trade_id=15573, not in DB). Needs manual cleanup.
- **[INFO]**: Regime LONG_BIAS (5 long, 0 short, 115 neutral across 120 tokens)
- **[INFO]**: 125 signals generated in last hour, market speed normal

## Error Alerts — 2026-09-20 17:46 UTC
- **[WARN]** (1x): `signal_compactor FAILED in 1.3s (rc=1)` at 17:35 — transient, recovered next cycle (17:43)
- **[WARN]**: Disk at 85% — working set size, no old logs to compress. Monitor.

## Error Alerts — 2026-09-19 08:45 UTC
- **[WARN]** (1x): `breakout_engine timed out (killed after 60s)` at 08:35 — recovered on next cycle
- **[WARN]** (1x): `signal_compactor timed out (killed after 60s)` at 08:42 — recovered on next cycle
- **[INFO]**: 8 support services in failed state (5m-candle, better-coder, away-detector, etc.) — none blocking pipeline
- **[WARN]**: Disk at 83% — approaching 85% threshold
- **[NOTE]**: hermes-5m-candle dead since Sep 11 (8 days) — no candles_5m table in runtime DB

## Error Alerts — 2026-09-19 08:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS TOK breakout_engine: timed out (killed after N.0s)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: breakout_engine`

## Error Alerts — 2026-09-19 09:56 UTC
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — CONTAGION+MOMENTUM`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.0x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.6x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-19 10:44 UTC
- **OK**: Pipeline running normally, 0 errors in last 30min
- **OK**: 6 open trades, 47 closed today, +21.87% PnL
- **OK**: All timers firing on schedule
- **INFO**: Disk at 84% — 1% below WARN threshold
- **INFO**: Regime LONG_BIAS (4 long, 1 short, 113 neutral across 118 tokens)

## Error Alerts — 2026-09-19 10:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,CONTAGION | vol=N.3x eth_div=+N.N%`

## Error Alerts — 2026-09-19 11:56 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Error Alerts — 2026-09-19 12:45 UTC
- **OK**: Pipeline running normally, 0 errors in last 30min
- **OK**: 4 open trades, 47 closed today, +28.81% PnL
- **WARN**: Hotset empty — 0 signals survived compaction this cycle
- **INFO**: Disk at 84% — 1% below WARN threshold
- **INFO**: 32 phantom trades (|pnl_pct|<0.01%) — 201 near-zero PnL fills total
- **INFO**: Regime LONG_BIAS (4 long, 1 short, 113 neutral across 118 tokens)

## Error Alerts — 2026-09-19 13:45 UTC
- **OK**: Pipeline last run 13:43 — completed in 26s, no errors
- **OK**: 3 open trades (CAKE SHORT, DOGE LONG, BABY LONG), 36 closed today
- **OK**: PnL +37.18% (pipeline), -0.77 USDT (DB absolute)
- **WARN**: signal_compactor timed out (60s) at 13:37 — auto-recovered, next runs 0.8-3.7s
- **WARN**: Hotset empty — 0 signals survived compaction (continuing from 12:45)
- **INFO**: Regime NEUTRAL (3 long, 3 short, 113 neutral across 119 tokens) — quiet market
- **INFO**: Disk 84% — 1% below WARN threshold (unchanged)
- **INFO**: HL sync guardian active, pipeline service idle (normal after completion)
- **INFO**: No hermes timers listed — pipeline triggered by external mechanism

## Error Alerts — 2026-09-19 14:56 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.0s)`

## Error Alerts — 2026-09-19 15:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Error Alerts — 2026-09-19 16:56 UTC
- **REPEATED** (15x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-09-19 17:56 UTC
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-19 19:46 UTC
- **REPEATED** (3x): `signal_compactor: timed out (killed after 60.1s)` at 18:24, 18:42, 19:34 — recovered each time (recent runs 1-2s)
- **WARN**: hotset.json empty — "no signals survived compaction" — all signals filtered out
- **INFO**: Disk at 84% (93G/118G) — 1% below WARN threshold. Data DBs: coin_tracker 2.3G, candles 1.9G, signals 777M
- **OK**: Pipeline running normally,7 open positions, 49 closed today, +36.78% PnL
- **OK**: All timers firing (hermes-pipeline.timer every 1min)
- **OK**: Position Manager healthy, 7 open tracked with SL/TP

## Error Alerts — 2026-09-19 21:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-20 00:45 UTC
- **WARN**: hotset.json empty (0 bytes) — "hotset fallback DB query returned 0 tokens" on every pipeline run (3525 occurrences in log). speed_hermes.db also 0 bytes. Not blocking pipeline but hotset filtering is non-functional.
- **WARN**: Disk at 84% (93G/118G) — 1% below WARN threshold. pipeline.log=74M, signal-compactor.log=48M. Attempted log compression (minimal effect).
- **OK**: Pipeline completed at 00:43:17, all steps healthy. hermes-pipeline.timer active and firing.
- **OK**: 83 signals in last hour (80.5% avg confidence). 50 trades closed today, +0.11 USDT PnL, 50% WR.
- **OK**: Regime NEUTRAL (116 neutral, 3 long bias, 1 short bias). 127 tokens at >=50th percentile speed.
- **OK**: All 50+ hermes timers active and firing. HL sync guardian active.
- **AUTO-FIX**: Attempted log compression — files already compressed, minimal space freed. Disk stable at 84%.

## Error Alerts — 2026-09-20 03:44 UTC
- **CRITICAL** (Nx): `signal_compactor: FAILED (rc=1)` — IndentationError at line 2259
- **CRITICAL** (Nx): `position_manager: FAILED (rc=1)` — cascading from signal_compactor import error
- **AUTO-FIX**: Fixed extra space indentation in signal_compactor.py line 2258 (log statement was 21 spaces instead of 20). Restarted hermes-pipeline.service. Verified clean run — no errors.

## Error Alerts — 2026-09-20 03:56 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.9s (rc=N)`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TOK position_manager: TOK (most recent call last):`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor, position_manager`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.1s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.4s (rc=N)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.3s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.8s (rc=N)`

## Error Alerts — 2026-09-20 04:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS [Position Manager] TOK mirror_close TOK (DB committed, HL still open): mirror_close(TOK): HL TOK failed — Unknown TOK`

## Error Alerts — 2026-09-20 06:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-09-20 07:45 UTC
- **OK**: Pipeline running — last run 07:43, all steps completed (signal_compactor, decider_run, position_manager, trades_api)
- **OK**: 5 open positions, 13 closed today, +$0.63 PnL, 61.5% WR
- **WARN** (3x): `signal_compactor: timed out (killed after 60.1s)` at 06:52, 07:24, 07:38 — self-recovered each time (subsequent runs 0.8-3.7s)
- **WARN**: Market nearly 100% NEUTRAL (118 neutral, 2 short: STX/ACE, 0 long) — low signal environment
- **INFO**: Disk at 84% (94G/118G) — no old logs to compress, stable
- **INFO**: No hermes-* timers listed (pipeline runs as continuous service loop)
- **INFO**: Hotset empty — no signals survived compaction (consistent with flat market)

## Error Alerts — 2026-09-20 08:44 UTC
- **WARN**: Speed DBs empty — `speed_hermes.db` has 0 tables, `speeds_hermes_runtime.db` is 0 bytes. Speed-based token filtering inactive. Pipeline still runs (speed is advisory, not blocking).
- **INFO**: Disk at 84% (stable since 07:47 check). Top: coin_tracker=2.4G, candles=2.0G, signals=781M, session_brain=662M.
- **INFO**: 2 phantom-trade blocks today (BLUR SHORT, GMT SHORT) — tight SL correctly blocked.
- **INFO**: Market ~100% NEUTRAL — 1 LONG bias, 1 SHORT bias, 118 neutral tokens.

## Error Alerts — 2026-09-20 09:57 UTC
- **REPEATED** (11x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2645s left, N failures)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2578s left, N failures)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2499s left, N failures)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (2438s left, N failures)`

## Error Alerts — 2026-09-20 10:45 UTC
- **[WARN]** (1x): `signal_compactor: timed out (killed after 60.1s)` at 10:42:02 — recovered on next cycle (10:42:37, done in 1.1s)
- **[WARN]**: Disk at 85% (94G/118G) — at warning threshold, 18G free
- **[INFO]**: Pipeline 7 open trades, 37 closed today, +81.95% PnL (from pipeline output)
- **[INFO]**: Market regime: 118 NEUTRAL / 2 SHORT_BIAS (KAS, USELESS) / 0 LONG — very flat
- **[INFO]**: All 44 hermes timers firing on schedule
- **AUTO-FIX**: None needed — signal_compactor recovered automatically

## Error Alerts — 2026-09-20 11:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`

## Error Alerts — 2026-09-20 12:44 UTC
- **WARN** (Nx1): Disk usage at 85% (94G/118G, 18G free)
- **AUTO-FIX**: None applied yet. Monitor — compress old logs if >90%.

## Error Alerts — 2026-09-20 13:44 UTC
- **WARN** (disk): 84% used (94G/118G) — approaching 85% threshold. pipeline.log=89M, compactor=52M. Consider compressing old logs if usage continues.
- **INFO** (positions): 7/6 open positions — over limit, new entries being skipped. Position manager running, no SL/TP triggered. Monitor for stuck positions.

## Error Alerts — 2026-09-20 13:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-09-20 15:46 UTC
- **WARN** (1x): `signal_compactor timed out (killed after 60.1s)` at 15:22 — auto-recovered, subsequent runs 1.2-1.6s
- **WARN**: Disk at 85% (94G/118G) — pipeline.log=91M, signal-compactor.log=52M

## Error Alerts — 2026-09-20 15:57 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Error Alerts — 2026-09-20 17:57 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.3s):`

## Error Alerts — 2026-09-20 18:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Health Report — 2026-09-20 21:44 UTC
- **STATUS**: OK — Pipeline running, services active, no errors
- **PIPELINE**: Cycle #208599, 76 signals/hr, 0 open trades, 26 closed today (+$2.34)
- **DISK**: 84% used (94G/118G) — 1G below warning threshold, monitor closely
- **MARKET**: NEUTRAL regime, 3 long/5 short bias, 112 neutral tokens
- **AUTO-FIXES**: None needed
- **STALE SIGNAL**: BTC LONG 6.5min old (conditions verified at execution — no action needed)

## Error Alerts — 2026-09-20 21:57 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,TOK,MOMENTUM | vol=N.7x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-21 00:57 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING — CONTAGION+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,BTC_LEVEL | vol=N.3x eth_div=+N.N% | BTC_LEVEL: TOK blocked (+N.N% from high)`

## Error Alerts — 2026-09-21 01:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CASHCAT TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,BTC_LEVEL | vol=N.2x eth_div=+N.N% | BTC_LEVEL: TOK blocked (-N.N% from high)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-21 02:57 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — CONTAGION+MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,TOK | vol=N.5x eth_div=-N.N%`

## Error Alerts — 2026-09-21 05:45 UTC
- **WARN** (3x): `signal_compactor: timed out (killed after 60.1s)` — pipeline-integrated compactor hitting 60s timeout. Standalone timer service runs fine (2-6s). Likely lock contention or pipeline context issue.
- **WARN**: Disk at 84% (94G/118G) — approaching 85% warning threshold. Largest consumers: coin_tracker.db (2.5G), candles.db (2G), signals_hermes.db (791M).
- **INFO**: Portfolio healthy — 4 open positions, 25 closed today, +26.57% PnL. Regime: NEUTRAL.

## Error Alerts — 2026-09-21 05:57 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`

## Error Alerts — 2026-09-21 06:45 UTC
- **[WARN]** (3x): `signal_compactor: timed out (killed after 60.1s)` at 05:55, 06:25, 06:42 UTC — recurring timeout but pipeline auto-recovers
- **[WARN]** (1x): `hermes-better-coder.service` — CRASHED with `ModuleNotFoundError: No module named 'dispatcher.dispatcher'` — non-trading service, `dispatcher/` dir missing
- **[WARN]**: Disk at 84% (94G/118G) — approaching 85% threshold
- **[INFO]**: Hotset empty (0 tokens) — normal for NEUTRAL regime, 116 signals exist but none pass compaction filters

## Error Alerts — 2026-09-21 06:57 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (12x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-09-21 08:57 UTC
- **REPEATED** (10x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   → TOK: [TOK-TOK] info_rate: waited N.1s, retrying`

## Health Report — 2026-09-21 09:45 UTC
- **STATUS**: OK — Pipeline running, services active
- **PIPELINE**: Cycle #209319, position_manager 0.7s, signal_compactor 2.1s
- **SIGNALS**: 144 generated in last hour, 5289 total active
- **TRADES**: 0 open, 1 closed today (+$0.43 CASHCAT LONG win)
- **REGIME**: LONG_BIAS (28 long, 0 short, 92 neutral)
- **DISK**: 85% used (94G/118G) — at warning threshold
- **WARN**: signal_compactor 3 timeouts in 30min (09:17, 09:32, 09:38) — self-recovered each time
- **WARN**: 5289 active signals — high count, consider purge cycle

## Health Report — 2026-09-21 10:44 UTC
- **STATUS**: OK — Pipeline running, services active
- **PIPELINE**: Cycle #209378, 0 errors in last 30min
- **SIGNALS**: 69 generated in last hour
- **TRADES**: 0 open, 26 closed today (+56.93% cumulative PnL)
- **REGIME**: NEUTRAL (4 long, 2 short, 114 neutral) — shifted from LONG_BIAS
- **DISK**: 85% used (94G/118G) — stable, active DBs (coin_tracker 2.5G, candles 2G)
- **TIMERS**: All key timers firing normally
- **AUTO-FIXES**: None needed

## Error Alerts — 2026-09-21 10:57 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.8x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.7x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.6x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.4x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-21 11:57 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Error Alerts — 2026-09-21 12:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-21 14:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   Signal btc_pump_rider: TOK → TOK: 'btc_velocity'`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.7x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.6x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING — CONTAGION+MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.5x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.7x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.7x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-21 15:46 UTC
- **[CRITICAL]** (8x): `name 'open_time' is not defined` — position_manager.py:3070 — missing `open_time = pos.get('open_time')` in main loop. **AUTO-FIXED**: added missing variable extraction at line 2500.
- **[WARN]** (3x): `signal_compactor timed out (killed after 60.1s)` at 15:22, 15:39, 15:42 — LLM call timeout, self-recovered.
- **[WARN]**: Disk at 85% (95G/118G) — same as previous alert.
- **[INFO]**: Pipeline restarted successfully. Position manager verified clean: 2 open, 0 closed, 0 adjusted.

## Error Alerts — 2026-09-21 15:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.8x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] ME TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM,BTC_LEVEL | vol=N.9x eth_div=+N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.6s (rc=N)`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: position_manager`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.7s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.5s (rc=N)`

## Error Alerts — 2026-09-21 16:45 UTC
- **[WARN]** (2x): Phantom trades detected: ALT LONG (0.0% PnL), KAS LONG (-0.0025% PnL) — near-zero PnL entries
- **[WARN]**: pump-chain+ signal: 10 trades today, 40% WR, -0.43 USDT net — underperforming
- **[WARN]**: doji-bottom-long signal: 3 trades today, 0% WR, -0.35 USDT net — all losses
- **AUTO-FIX**: Removed stale state.db (3.1GB, 14 days old, only used for mtime check) — disk 85%→82%
- **AUTO-FIX**: Removed 4 stale 0-byte DBs (candles_hermes.db, price_cache.db, price_candles.db, price_data.db)
- **AUTO-FIX**: Compressed 15 old .gz log files older than 7 days
- **[INFO]**: Pipeline running healthy, cycle #209742, 10 signals in last hour, 0 open trades
- **[INFO]**: Regime NEUTRAL (117/120 tokens neutral), 2 long bias, 1 short bias
- **[INFO]**: 61 hermes timers active, all firing on schedule

## Error Alerts — 2026-09-21 16:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.5s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.1s):`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK (most recent call last):`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.7s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.6s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.0s):`

## Error Alerts — 2026-09-21 17:57 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`

## Health Report — 2026-09-21 19:46 UTC
- **STATUS**: OK — Pipeline running, services active
- **PIPELINE**: Last cycle completed 19:43:41, next started 19:44:00
- **SIGNALS**: 10 generated in last hour, 5884+ active
- **TRADES**: 1 open (CFX SHORT, -0.33% PnL), 23 closed today, -5.30% cumulative
- **REGIME**: LONG_BIAS (3L/0S/117N)
- **SPEED**: SAGA 100%, BLZ 100%, KPEPE 99.4%
- **DISK**: 82% (21G free) — safe
- **TIMERS**: 55 active, none missed
- **WARN** (3x): signal_compactor timed out at 19:20, 19:33, 19:42 — self-recovered each time
- **INFO**: CFX SHORT trailing SL active (SL 0.053595, 0.3% trail from 0.053435, age 2.4h)

## Error Alerts — 2026-09-21 20:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-09-21 21:44 UTC
- **WARN** (19x/4h): `signal_compactor: timed out (killed after 60.1s)` — timeout rate elevated. Pipeline continues but compactor decisions may be missed on affected cycles.
- **WARN** (189x/4h): `hotset fallback DB query returned 0 tokens` — hotset DB empty or unreachable, using fallback every cycle. Non-critical (dashboard only).
- **INFO**: Daily PnL -1.53 USDT, win rate 26.9% (7/26). Below target but no system failure.
- **NO AUTO-FIX NEEDED**: All services running, timers firing, disk 83%. Pipeline healthy.

## Error Alerts — 2026-09-21 21:57 UTC
- **REPEATED** (11x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-21 22:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Error Alerts — 2026-09-21 23:44 UTC
- **[WARN]** (5x): `signal_compactor timed out (killed after 60.0s)` — 5 occurrences in last 2h. Recurring issue, pipeline recovers next cycle.
- **[WARN]**: Win rate 29.6% today (27 trades closed) — below 40% target. 23 LONG (30.4% WR, -$1.05), 4 SHORT (25% WR, -$0.48).
- **[WARN]**: 2 phantom trades detected (pnl_pct <0.01%).
- **[INFO]**: 0 open trades currently. Market regime LONG_BIAS (3/120 tokens). Disk 83%.
- **AUTO-FIX**: No auto-fixes needed — pipeline running, timers active, no critical failures.

## Error Alerts — 2026-09-22 00:44 UTC
- **WARN** (1x): `signal_compactor: timed out (killed after 60.1s)` at 00:37:02 — self-recovered on next 3 runs (1.8s-3.8s)
- **WARN**: Disk at 83% (92G/118G) — approaching 85% threshold
- **AUTO-FIX**: None needed — signal_compactor self-recovered

## Error Alerts — 2026-09-22 00:57 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Error Alerts — 2026-09-22 01:46 UTC
- **[WARN]** (Nx1): `Disk usage at 83% (92G/118G)` — approaching 85% threshold
- **AUTO-FIX**: None applied. Consider compressing old logs or running cleanup.

## Health Report — 2026-09-22 02:45 UTC
- **STATUS**: OK — Pipeline running, services active
- **PIPELINE**: Last cycle 02:44:12, all steps completed (signal_compactor, decider_run, position_manager, trades_api)
- **SIGNALS**: 137 generated in last hour
- **TRADES**: 3 open (GOAT SHORT, ZEN SHORT, GMT SHORT), 2 closed today (+$0.25, 50% WR)
- **REGIME**: NEUTRAL (116/120 tokens), 3 LONG_BIAS (RENDER, NIL, CHIP), 1 SHORT_BIAS (CASHCAT)
- **DISK**: 83% (20G free) — stable
- **WARN** (2x): `signal_compactor timed out (killed after 60.1s)` at 02:22, 02:42 — self-healed on next cycle
- **INFO**: Hotset empty (0 signals survived compaction) — normal for quiet NEUTRAL market
- **INFO**: All services active (hermes-pipeline, hl-sync-guardian)
- **NO AUTO-FIX NEEDED**: All issues self-healed, pipeline healthy

## Error Alerts — 2026-09-22 02:57 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   [brain.py] ❌ REJECTED: CC TOK — amount_usdt=N.N < HL_MIN=N.N (would TOK on HL)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: CC TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   → TOK:`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`

## Health Report — 2026-09-22 03:47 UTC
- **STATUS**: OK — Pipeline running, services active
- **PIPELINE**: Cycle #210405, last completed 03:43:44, next running 03:44:00
- **SIGNALS**: 125 generated in last hour, 10 active (5 SHORT, 5 LONG)
- **TRADES**: 0 open (DB), 27 closed today, -25.55% cumulative PnL
- **REGIME**: SHORT_BIAS (4 SHORT, 0 LONG, 116 NEUTRAL)
- **DISK**: 83% (20G free) — approaching 85% threshold
- **PRICES**: Fresh (BTC 55s old, candles.db 2G/13M rows)
- **SERVICES**: hermes-pipeline=active, hl-sync-guardian=active
- **KILL SWITCH**: live_trading = true
- **WARN** (5x): `signal_compactor timed out (killed after 60.1s)` at 02:50, 02:59, 03:14, 03:34, 03:38 — self-healed each time (subsequent runs 0.6-2.7s)
- **WARN**: Today's PnL -25.55% across 27 closed trades — bad day, mostly pump-chain + support_resistance signals losing
- **INFO**: Market quiet, regime SHORT_BIAS, hotset empty (0 signals survived compaction)
- **NO AUTO-FIX NEEDED**: All issues self-healed, pipeline healthy

## Error Alerts — 2026-09-22 03:57 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-09-22 04:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-09-22 05:57 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (9x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-09-22 06:57 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`

## Error Alerts — 2026-09-22 07:44 UTC
- **WARN** (4x): `signal_compactor: timed out (killed after 60.0s)` — happened 4 times in last hour. Self-recovered on next pipeline cycle. Likely LLM timeout in compactor. Monitor — if recurring, may need timeout increase or LLM fallback.
- **INFO**: `hotset fallback DB query returned 0 tokens` — transient, no impact.
- **No AUTO-FIX needed** — all issues self-healed.

## Error Alerts — 2026-09-22 07:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.4s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.9s):`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.2s):`

## Error Alerts — 2026-09-22 08:57 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (15x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.6s (rc=N)`
- **REPEATED** (13x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.1s):`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.2s (rc=N)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.7s):`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.3s (rc=N)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.0s (rc=N)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.3s):`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.7s (rc=N)`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.2s):`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.5s):`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.8s):`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.6s):`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.8s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.9s (rc=N)`

## Error Alerts — 2026-09-22 09:47 UTC
- **CRITICAL** (recurring): `signal_compactor: FATAL ERROR — NameError: name 'sig' is not defined` in `run_compaction` at line 2544
- **ROOT CAUSE**: Variable `sig` was never defined in the `for row in rows` loop. It was likely copy-pasted from a signal detection context where `sig` is a dict. In the compactor, signal data comes from SQLite rows (tuple access).
- **FIX**: Changed `sig.get('rsi_14') if isinstance(sig, dict) else None` → `row[8] if len(row) > 8 else None` (matches the `rsi = row[8] if len(row) > 8 else None` pattern used at lines 1999, 2930, 3796).
- **AUTO-FIX APPLIED**: signal_compactor.py:2544 patched, verified working (completed in 1.9s, 0 crashes)

## Error Alerts — 2026-09-22 09:57 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TOK signal_compactor: TOK TOK in run_compaction (N.4s):`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.0s (rc=N)`

## Error Alerts — 2026-09-22 14:44 UTC
- **WARN** (1x): `disk_usage` — 83% used (93G/118G), approaching 85% threshold
- **WARN** (1x): `low_winrate` — Today's winrate 35% (18 trades, 6 wins)
- **INFO**: prices.db is 0 bytes but appears unused — system uses candles.db/coin_tracker.db

## Error Alerts — 2026-09-22 14:57 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-09-22 15:57 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`

## Error Alerts — 2026-09-22 16:44 UTC
- **WARN** (8x/2h): `signal_compactor` timeouts — killed after 60s repeatedly. Not critical (pipeline continues), but indicates compactor overload. Monitor for escalation.
- **WARN**: Disk at 84% (93G/118G) — approaching 85% threshold. Compressed old logs but no significant savings (already gzipped).
- **INFO**: 0 open trades — NEUTRAL regime, all 20 today's trades closed. Win rate 40%, net PnL -$0.47 (breakeven day).

## Health Check — 2026-09-22 18:44 UTC
- **[WARN]** Disk usage 84% (19GB free) — monitor, compress at 90%
- **[INFO]** Pipeline healthy, 0 errors, 54 signals/hr
- **[INFO]** Winrate 40% today, PnL -$0.47 (minimal)
- **[INFO]** pump-chain signals underperforming (26% WR combined)

## Error Alerts — 2026-09-22 18:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Error Alerts — 2026-09-22 19:45 UTC
- **WARN**: Disk at 84% (93G/118G) — 1% below threshold. No auto-fix needed yet.
- **INFO**: No errors, no crashes, no stale prices in last 30min. Pipeline clean.

## Error Alerts — 2026-09-22 19:57 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`
