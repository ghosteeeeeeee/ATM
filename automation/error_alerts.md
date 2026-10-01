# Error Alerts

## Error Alerts — 2026-09-30 00:48 UTC
- **WARN** (1): `Disk at 85% (95G/118G)` — coin_tracker.db=3.3G, candles.db=2.2G, /var/log=3.4G
  - **AUTO-FIX (01:48)**: Vacuumed journal logs, freed 1.0G. Now 84% (94G/118G).
- **WARN** (Nx): `Phantom trade_id=15705 (BTC LONG)` — closed every cycle by UNIVERSAL_MAX_HOLD but persists. SL distance only 0.052% from entry.
  - **AUTO-FIX**: None. Known zombie trade. Requires manual DB cleanup or guardian code fix.

## Error Alerts — 2026-09-30 01:48 UTC
- **WARN** (1): `position_manager: FAILED in 0.8-3.5s (rc=1)` — every pipeline cycle for 30+ minutes. ATR SL/TP updates and position closes ARE completing successfully. rc=1 appears to be benign exit code from guardian lock contention, not a real failure.
  - **AUTO-FIX**: None. Work completes despite rc=1. Monitor for actual missed position management.
- **WARN** (1): `Loss cooldowns extreme` — COMP:LONG streak=83 (1.5h cooldown), ALGO:SHORT streak=43 (1.5h cooldown). These pairs are generating persistent losses.
  - **AUTO-FIX**: None. Loss cooldowns are working as designed. These pairs need signal quality review.
- **INFO**: `Market regime` — 10 LONG_BIAS, 0 SHORT, 106 NEUTRAL. Hotset empty — no signals survived compaction above 50% confidence. 5 active signals (SAGA, KLUNC, JUP, ETC, KPEPE). 19 trades in last 24h, 57.9% win rate, $0.30 PnL.

## Error Alerts — 2026-09-30 02:46 UTC
- **WARN** (Nx): `hermes-coding-mcp` in restart loop — 670,138 restarts, script missing (`run_mcp_server.py`)
- **AUTO-FIX**: Stopped + disabled `hermes-coding-mcp.service`
- **WARN**: Disk 84% used (19G free of 118G)
- **WARN**: BTC LONG loss streak=13 (1.5h cooldown active)
- **INFO**: Position manager "FAILED" = Guardian lock (hl-sync-guardian running). NOT a crash — working as designed.

## Error Alerts — 2026-09-30 04:58 UTC
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.1s (rc=N)`

## Error Alerts — 2026-09-30 06:46 UTC
- **WARN** (1x): `disk 84%` — 18G free of 118G, approaching 85% threshold. Monitor.
- **INFO**: Market entirely neutral (116/116 tokens). 0 open trades. No signals above 50% confidence. Pipeline healthy, just quiet.

## Error Alerts — 2026-09-30 07:46 UTC
- **WARN** (1x): `disk 84%` — 18G free of 118G, 1% below 85% threshold. Sustained since 00:48.
- **WARN** (5x): `phantom trades` — 5 trades with |pnl|<0.01 in last 24h (SOL, SAGA, KAS, ADA, ZEN). All from yesterday, 0 open phantoms now. Not actionable.
- **INFO**: Pipeline OK — 30 cycles/30min, 0 errors, 141 signals/1h, 56 tokens. Timers 54 active. Prices fresh (<1min). Market NEUTRAL (115/116). No auto-fixes needed.

## Error Alerts — 2026-09-30 08:46 UTC
- **WARN** (2x): `hermes-1m-candle.timer INACTIVE`, `hermes-5m-candle.timer INACTIVE` — candle collection timers stopped. 15m regime, auto-1hr, archive timers still active. May be intentional (manual stop) or timer expiry. Check if candles are still collecting via price_collector.
- **WARN** (1x): `disk 84%` — sustained at 84% since 00:48 (8 hours). 18G free. Below threshold but not decreasing. Consider log rotation if it doesn't drop.
- **INFO**: Pipeline running, 0 open trades, 0 signals last hour. Market entirely NEUTRAL (115/116 tokens). Prices fresh (1.6min). 0 errors in logs. No auto-fixes applied — candle timers may be intentional pause.

## Error Alerts — 2026-09-30 09:48 UTC
- **WARN** (1x): `disk 85%` — was 94G/118G used. AUTO-FIX: vacuumed journald (~1GB freed) → 84% (93G/118G). Still near threshold; compress >2d logs next cycle if it creeps back.
- **WARN** (1x): `hermes-1m-candle.timer` + `hermes-5m-candle.timer` INACTIVE. NOT an outage — `hermes-price-collector` is writing candles directly (1m age 1.2min, 5m age 3.2min). Standalone candle aggregator services are redundant; 5m-candle.service failed 2026-09-27. No data gap.
- **WARN** (1x): `hermes-bug-hunter.service` FAILED 09:45 — real findings: hardcoded passwords (4 files), dead imports of defunct `signal_gen`/`ai_decider` (4 files), trade freq 0.2/hr. Not auto-fixed (needs code changes).
- **WARN** (1x): `hermes-git-release.service` FAILED 08:59 — `update-git.py --dry-run` exit 1. Backup/seed zip not running. Not auto-fixed.
- **INFO**: 8 non-trading units were in failed state (5m-candle, away-detector, better-coder, brain-auditor, bug-hunter, git-release, mtf-macd-tuner, trading-checklist). Cleared via `reset-failed`. Trading path unaffected.
- **INFO**: Pipeline healthy — 0 errors/30min, 116 signals/1h, 0 open trades, 1 closed today (continuum-osc+ LONG -$0.02). Market LONG_BIAS (6 long / 0 short / 110 neutral). Speed 126/241 ≥50th pct. Prices fresh. Timers firing (pipeline, price-collector, signal-compactor, watchdog all on schedule).
- **INFO**: `prices_hermes.db` is a 0-byte empty file (Aug 10 artifact). Live prices flow through price_history + candles.db. Harmless but confusing — candidate for deletion.

## Error Alerts — 2026-09-30 13:48 UTC
- **WARN** (1x): `disk 84%` — 93G/118G used, 19G free. Sustained since 00:48 (13h). No logs >7d to compress; journald already vacuumed (212MB). Below 85% threshold. Monitor.
- **WARN** (4x): non-trading services failed — `hermes-5m-candle`, `hermes-better-coder`, `hermes-brain-auditor`, `hermes-git-release`. AUTO-FIX: `reset-failed` applied. 5m-candle is redundant (price_collector writes candles directly); git-release dry-run failure known from 09:48 alert.
- **INFO** (1x): `hermes-trading-checklist` exit-2 — BY DESIGN when it flags items, not a crash. Flags: signals DB 11385 rows (checklist cleanup threshold), pipeline_recent "unclear output" (multiline log parse false-positive), 0 decisions written in 2h (compactor produced no new decisions — possible quiet market or check later). AUTO-FIX: `reset-failed`.
- **INFO**: `systemctl list-timers hermes-*` returns 0 — GLOB QUIRK, not missing timers. Full `list-timers --all | grep hermes` shows 67 hermes timers, pipeline/price-collector/signal-compactor/watchdog/15m-regime all firing on schedule.
- **INFO**: Pipeline healthy — completed 13:45:35 (LIVE), 0 errors/30min, 0 tracebacks, Position Manager 0 open / 0 closed this cycle, Portfolio 20 closed today. 60 signals/1h (support_resistance dominant). Regime LONG_BIAS (14 long / 1 short / 101 neutral, 116 tokens). Speed 127/241 ≥50th pct. Prices fresh (13:45:30, 86 tokens). Open trades: 0. Phantom trades 24h: 0. No auto-fixes needed on trading path.

## Error Alerts — 2026-09-30 15:47 UTC
- **WARN** (1): `Disk 85% (95G/118G)` — approaching critical. Main consumers: coin_tracker.db=3.3G, candles.db=2.3G, hl_copy.db=345M.
  - **AUTO-FIX**: Compressed 17 log files >7 days (gzip). Disk unchanged — growth is DBs, not logs.
- **WARN** (1): `Hotset empty — 0 approved signals` — compactor filters blocking all candidates (LONG-RSI-BLOCK oversold freefall, CONFLUENCE-GATE, RSI-CEILING). Market SHORT_BIAS (1L/5S/110N of 116). Filters working as designed (BANANA lesson: no oversold longs). Not a pipeline failure.
  - **AUTO-FIX**: None. No signals to execute; position manager still managing 2 open trades (DOT LONG, COMP SHORT) with trailing SLs.
- **INFO**: Pipeline healthy. Timers firing (pipeline 20s ago, price-collector 58s ago). 0 errors in 30min logs. No phantom trades. No crashes/tracebacks.

## Error Alerts — 2026-09-30 15:58 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   → TOK: TOK ceiling: N.N > N`

## Error Alerts — 2026-09-30 16:49 UTC
- **WARN** (3x): position_manager `[FATAL] Guardian already running` at 16:37/16:40/16:41 — lock contention with hl-sync-guardian, NOT a crash. Guardian healthy (9h uptime). Position manager succeeded on subsequent cycles (16:42/16:44/16:46+). Working as designed (next-cycle retry). No auto-fix required.
- **WARN** (1x): disk **86%** (96G/118G, 16G free). AUTO-FIX: vacuumed journald (freed 255MB). Logs only 162M total — growth is DBs (coin_tracker.db 3.4G, candles.db 2.3G, signals_hermes.db 925M, session_brain.db 850M). No logs >7d to compress. Monitor; DB growth is structural.
- **INFO** (6x): non-trading services failed — 5m-candle (redundant), better-coder, ceo, git-release (known dry-run fail), trading-checklist (exit-2 by design), weather-station-api. AUTO-FIX: reset-failed applied. Trading path unaffected.
- **INFO**: Pipeline healthy. 89 signals/1h (pump-chain 65), 7 executed. 3 open trades (LDO/BLUR/DOT LONG, all green), 15 closed today, +55.2% PnL. Regime LONG_BIAS (11L/0S/105N). Speed 53% tokens >=50th pct. Prices fresh (0.3min, 86 tokens). Core timers firing every 1min. 0 phantom-like tiny-PnL outliers flagged.

## Error Alerts — 2026-09-30 17:58 UTC
- **REPEATED** (28x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: position_manager`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.6s (rc=N)`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.7s (rc=N)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.3s (rc=N)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.5s (rc=N)`

## Error Alerts — 2026-09-30 18:58 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.1s (rc=N)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.4s (rc=N)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   → TOK: TOK floor: N.N < N`

## Error Alerts — 2026-09-30 20:58 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.5s (rc=N)`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.3s (rc=N)`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.4s (rc=N)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.9s (rc=N)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.6s (rc=N)`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.0s (rc=N)`
- **REPEATED** (11x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.7s (rc=N)`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.2s (rc=N)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.8s (rc=N)`

## Error Alerts — 2026-09-30 23:58 UTC
- **REPEATED** (9x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.2s (rc=N)`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.5s (rc=N)`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] CC TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-01 00:58 UTC
- **REPEATED** (59x): `Oct N N:N:N python3[TOK]: [coin_tracker] Done: N coins processed, N skipped, N errors`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.3s (rc=N)`
- **REPEATED** (48x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: position_manager`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.1s (rc=N)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.0s (rc=N)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.2s (rc=N)`
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.7s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] CC TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.6s (rc=N)`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.8s (rc=N)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.9s (rc=N)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.4s (rc=N)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.5s (rc=N)`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-01 01:48 UTC
- **WARN** (1x): Disk `/` at 86% used (118G, 17G free). Logs only 182M — bulk is DBs: coin_tracker.db 3.3G, candles.db 2.3G + WAL 1.5G, mtf_macd_tuner.db 1.3G, signals_hermes.db 888M, session_brain.db 830M.
- **AUTO-FIX**: journal vacuum (0B free — already tight); attempted candles WAL checkpoint (busy, active DB); no idle large logs to gzip. No DB vacuum run (data loss risk) — CEO decision needed.
- **WARN** (2x): `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` enabled but inactive (OnBootSec=24h/72h; up 46d so they wait for next boot). Not calendar-scheduled.
- **WARN** (1x): `hermes-atr-sl-updater.timer` unit not found (stale reference).
- **NOTE**: hotset empty + decisions table stale since 2026-04-13 while signals_1h=60 — compaction/filter path is rejecting all signals (expected if confidence gates working; worth review).
- **NOTE**: Prior error_alerts entries contain broken redaction (`TOK` placeholders) from error analyzer — analyzer regex/log-pipeline issue, not runtime.

## Error Alerts — 2026-10-01 01:58 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.9s (rc=N)`

## Error Alerts — 2026-10-01 02:58 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.3s (rc=N)`
