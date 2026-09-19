# Error Alerts

## Error Alerts — 2026-09-17 23:44 UTC
- **WARN** (1x): `disk_usage` — disk at 84% (19G free), approaching 85% threshold. Monitor and compress old logs if it rises.
- **INFO**: `macro_gate_reduce` — macro gate REDUCE active (wr=20% < 30), system correctly throttling entries.

## Error Alerts — 2026-09-17 13:43 UTC
- **OK**: Pipeline health check passed. No WARN or CRITICAL issues detected.
- Pipeline running (cycle #203864), 10 active signals, 0 open trades, 83% disk.
- Auto-fixes applied: none needed.

## Error Alerts — 2026-09-17 13:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.2s (rc=N)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.1s (rc=N)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TOK position_manager: TOK (most recent call last):`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   hermes-trades-api: TOK in N.1s (rc=N)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TOK hermes-trades-api: TOK (most recent call last):`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run, position_manager, hermes-trades-api`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.2s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   Signal bb_bounce_v2_short: TOK → TOK: cannot import name 'get_all_latest_prices' from 'signal_schema' (/root/.hermes/scripts/signal_schema.py)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   Signal bb_bounce_v3_long: TOK → TOK: unexpected indent (signal_schema.py, line N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   Signal return_exhaustion_short: TOK → TOK: cannot import name 'get_all_latest_prices' from 'signal_schema' (/root/.hermes/scripts/signal_schema.py)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.1s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor, decider_run, position_manager, hermes-trades-api`

## Error Alerts — 2026-09-17 14:56 UTC
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-17 16:56 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-17 18:45 UTC
- **[WARN]** Disk at 83% (93G/118G) — approaching 85% threshold
- **[INFO]** Winrate 18.75% (1h window) — signal_analyst REDUCE gate active
- **[INFO]** 16 trades closed today, -1.76 USDT PnL

## Error Alerts — 2026-09-17 19:56 UTC
- **REPEATED** (6x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-17 20:44 UTC
- **WARN** (32x): `phantom_trades` — trades with <0.01% PnL in signal_outcomes
- **WARN** (1x): `macro_gate_reduce` — signal analyst macro gate: REDUCE (wr=20% < 30)
- **INFO** (4x): `systemd_kill_group` — "Failed to kill control group" — cosmetic, no impact

## Error Alerts — 2026-09-18 00:44 UTC
- **[WARN]** Disk at 84% (19G/118G) — approaching 85% threshold
- **AUTO-FIX**: Compressed 11 old log files (freed ~50MB)
- **[INFO]** Market extremely quiet — 126/127 tokens NEUTRAL, only BABY has LONG_BIAS
- **[INFO]** Pipeline healthy — 44 signals generated in last hour, 0 errors

## Error Alerts — 2026-09-18 01:45 UTC
- **WARN** (1x): Disk at 84% — 1% from 85% threshold. Monitor for cleanup.
- **INFO**: Macro gate REDUCING signals — 24h win rate 20% (below 30% threshold). System self-protecting.
- **INFO**: open-skies+ signal type 0% WR (4 trades, -$0.62) — potential underperformer to review.

## Error Alerts — 2026-09-18 03:44 UTC
- **WARN** (9x): Services in failed state — hermes-5m-candle, hermes-away-detector, hermes-better-coder, hermes-bug-hunter, hermes-git-release, hermes-mtf-macd-tuner, hermes-session-brain-daily-rebuild, hermes-trading-checklist, hermes-upgrade-implementer
- **ROOT CAUSE**:
  - hermes-5m-candle: missing script `_aggregate_5m.py`
  - hermes-bug-hunter: missing script `bug_hunter.py`
  - hermes-better-coder: missing module `dispatcher.dispatcher`
  - hermes-away-detector: missing script
  - hermes-git-release: dry-run exit code 1 (non-critical)
  - hermes-mtf-macd-tuner: error during execution
  - hermes-session-brain-daily-rebuild: rebuild failure
  - hermes-trading-checklist: missing script
  - hermes-upgrade-implementer: missing script
- **IMPACT**: Monitoring/automation services degraded. Pipeline (signal_gen, decider, position_manager) running OK.
- **AUTO-FIX**: Cannot auto-fix — requires code-level fixes or script restoration.
- **WARN** (32x): Phantom trades in history (pnl_pct < 0.01%) — pre-existing, not new
- **WARN** (1x): Disk at 84% — 1% from 85% threshold. Monitor for cleanup.
- **INFO**: Market quiet — 117/127 tokens NEUTRAL, 10 LONG_BIAS, 0 SHORT_BIAS. 0 trades closed today.

## Error Alerts — 2026-09-18 03:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: +N.N% from high, +N.N% from low — blocking TOK entries`
- **REPEATED** (4x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-18 04:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`

## Error Alerts — 2026-09-18 05:44 UTC
- **WARN** (9x): Services in failed state — hermes-5m-candle (CRITICAL), hermes-away-detector, hermes-better-coder, hermes-brain-auditor, hermes-bug-hunter, hermes-git-release, hermes-mtf-macd-tuner, hermes-trading-checklist, hermes-upgrade-implementer
- **WARN** (32x): Phantom trades — trades with near-zero PnL (|pnl_pct| < 0.01%)
- **WARN**: Disk at 84% — approaching 85% threshold
- **AUTO-FIX**: None applied — services require investigation before restart

## Error Alerts — 2026-09-18 08:43 UTC
- **WARN** (2x): `systemd_kill_group` — `Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument` — non-critical cleanup issue, pipeline continues running normally
- **WARN**: `daily_pnl` — 19 trades closed today with -39.35% cumulative PnL. Short trades (pullback-entry-) mostly losing. Winrate on closed: 5/19 = 26% — below 50% threshold
- **WARN**: `disk_usage` — disk at 84% (94G/118G), approaching 85% threshold. Compress logs if >85%
- **INFO**: Pipeline healthy, all core components running, 0 open trades, 20 signals generated in last hour

## Error Alerts — 2026-09-18 10:44 UTC
- **WARN**: Disk at 84% (19G free) — 1% below 85% threshold
- **NOTE**: pullback-entry SHORT signal: 0% win rate (4 losses, -0.62 USDT today) — may need filter review
- **AUTO-FIX**: none required

## Error Alerts — 2026-09-18 14:44 UTC
- **OK**: Pipeline health check passed. All core services running.
- Pipeline: active, last cycle 14:43 (2 open, 0 closed, 17 today)
- Timers: 30+ active, all firing on schedule
- Disk: 85% (at threshold — 85G used of 118G)
- Regime: 5m scanner OK (13 LONG bias, 114 neutral), 4h scanner OK (next at 17:04)
- Signals: 71 active, 71 generated in last hour
- Phantom trades: 2 in last 24h (SUSHI +0.006, BABY +0.008) — negligible
- Auto-fixes: compressed old logs (>7d). mtf_macd_tuner.db (384MB) candidate for cleanup.
- **WARN**: disk at 85% threshold — monitor. coin_tracker.db (2.2G) and candles.db (1.9G) are largest data files.

## Health Check — 2026-09-18 15:44 UTC
- **PIPELINE**: OK — running, 0 errors, last cycle 15:43:23
- **Trades (24h)**: 25 total, ~68% WR, +$0.96 net
  - volume-breakout-long: 11 trades, 72.7% WR, +$1.08
  - pullback-entry: 5 trades, 20% WR, -$0.60 (worst performer)
- **Open positions**: 1 (HYPER LONG, +0.05%)
- **Regime**: LONG_BIAS (8 long-bias, 119 neutral, 0 short)
- **Disk**: 85% (18G free) — driven by data DBs, not logs
- **Auto-fix**: compressed logs >1d (no space recovered — data DBs dominate)
- **INFO**: pullback-entry- signal 20% WR over 24h — monitor

## Error Alerts — 2026-09-18 15:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.2x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`

## Error Alerts — 2026-09-18 16:44 UTC
- **CRITICAL** (1x): `hermes-coding-mcp.service` crash-looping — restart counter at **509,088**. Script `run_mcp_server.py` missing.
- **AUTO-FIX**: Disabled `hermes-coding-mcp.service` to stop crash loop.
- **WARN** (9x): Services in failed state — hermes-5m-candle, hermes-away-detector, hermes-better-coder, hermes-bug-hunter, hermes-git-release, hermes-mtf-macd-tuner, hermes-session-brain-daily-rebuild, hermes-trading-checklist, hermes-upgrade-implementer
- **WARN**: `momentum_cache` stale — 528h old (22 days). Momentum-based filters may be degraded.
- **WARN**: Disk at 85% (95G/118G) — at threshold
- **INFO**: Pipeline OK — running, 1 open trade (NOT), 0 closed today
- **INFO**: Regime NEUTRAL (122 tokens), 3 LONG bias, 2 SHORT bias
- **INFO**: 18 signals active, latest at 16:36:15
- **INFO**: systemd kill control group error — cosmetic, no impact

## Error Alerts — 2026-09-18 17:56 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`

## Health Check — 2026-09-18 18:43 UTC
- **PIPELINE**: OK — running, 0 errors, last cycle 18:43:02
- **Trades (24h)**: 20 closed, 70% WR, +$1.30 USDT
- **Open positions**: 0 (all flat)
- **Regime**: NEUTRAL (4 long bias, 1 short bias, 122 neutral)
- **Disk**: 85% (18G free) — at threshold. coin_tracker.db (2.2G), candles.db (1.9G), state.db (3.1G) dominate
- **Auto-fix**: none required
- **WARN**: Disk at 85% threshold — data DBs (not logs) are the cause. Monitor.

## Error Alerts — 2026-09-18 18:56 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-09-18 19:44 UTC
- **WARN** (1x): `Disk at 85%` — 95G/118G used. coin_tracker.db=2.2G, candles.db=1.9G.
- **AUTO-FIX**: Journal vacuumed to 500MB → freed 2G. Disk now 83%. Logs compressed (150M total).
- **INFO**: BTC-CRASH warning blocking HEMI LONG — risk management working as intended.

## Error Alerts — 2026-09-18 20:56 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-18 22:45 UTC
- **WARN** (1x): `ATOM mirror_close FAILED` — HL API rejected reduce-only order (would increase position). DB committed but HL position still open. Requires manual reconciliation.
- **WARN** (2x): Phantom trades (|pnl| < 0.01 USDT) — HYPER btc-pump-rider+ ($0.0016), SUSHI volume-breakout-long+ ($0.0064). Negligible impact.
- **INFO**: systemd `Failed to kill control group` errors at 22:18/22:20 — non-critical cleanup issue, pipeline recovered fine.

## Error Alerts — 2026-09-18 22:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS [Position Manager] TOK mirror_close TOK (DB committed, HL still open): mirror_close(TOK): HL TOK failed — Reduce only order would increase position. asset=N`

## Error Alerts — 2026-09-18 23:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] BIGTIME TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Health Check — 2026-09-19 00:43 UTC
- **WARN** (Nx): Stale signals (GRASS, STX, INJ) exceeding 5min threshold — caught by verification
- **INFO**: INJ LONG blocked in cooldown (2 failures, ~52min remaining)
- **INFO**: 0 open trades, 1 closed today (-$0.30)
- **NO AUTO-FIX NEEDED**

## Error Alerts — 2026-09-19 00:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3139s left, N failures)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK BLOCKED — TOK in cooldown (3079s left, N failures)`
