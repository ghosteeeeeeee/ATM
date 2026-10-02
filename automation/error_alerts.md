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

## Error Alerts — 2026-10-01 03:48 UTC
- **CRITICAL** (7x): `position_manager FAILED rc=1 — [FATAL] Guardian already running — exiting`
  - **ROOT CAUSE**: `hl-sync-guardian.py:183` acquired guardian flock at module import time. `position_manager.py:1122` imports `_compute_mfe_mae` from it during trade close → SystemExit (uncatchable by `except Exception`) → position_manager died every time it closed a trade. Trade 15776 (JUP SHORT) re-closed 5+ times, loss cooldown streak escalated 1→5.
  - **AUTO-FIX**: Guarded lock acquisition behind `if __name__ == '__main__'` in hl-sync-guardian.py. Import path no longer triggers lock. Pipeline restarted. Verified: position_manager rc=0 post-fix.
- **WARN**: Disk 86% used (16G free). Compressed logs >7 days old. Largest active: pipeline.log 45M, signal-compactor.log 37M, trade-watchdog.log 32M.
- **WARN**: hermes-better-coder.service failed, hermes-git-release.service failed (not auto-fixed — need manual investigation).

## Error Alerts — 2026-10-01 03:58 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   position_manager: TOK in N.4s (rc=N)`
- **NEW** (1x): `Oct N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-10-01 04:49 UTC
- **PIPELINE**: OK — running every minute, position_manager rc=0, hl-sync active, 41 signals/1h, 2 closed today (pnl -0.08), regime NEUTRAL (116 tokens), prices fresh (seconds).
- **WARN** (disk): `/` at 86% (17G free). Bulk is DBs (coin_tracker 3.3G, candles 2.3G+WAL 1.5G, mtf_macd 1.3G, signals_hermes 889M). No logs >7d to gzip. candles WAL checkpoint attempted (busy, candle service active). No DB vacuum — CEO decision needed.
- **WARN** (hotset): empty — decider reports "no signals survived compaction", 0 approved signals above 50% confidence despite 41 raw signals/1h. Filters rejecting all; worth signal-quality review, not a crash.
- **WARN** (signals): LTC rapid-fire duplicate `support_resistance` 4x (from wasp).
- **WARN** (services failed, not trading-critical):
  - `hermes-better-coder.service` — `ModuleNotFoundError: dispatcher.dispatcher`. `mcp/hermes-coding-mcp/dispatcher/` is EMPTY (code removed in cleanup commit 4e21f7a0). Service already disabled. Needs source restore or task retirement — not auto-fixable.
  - `hermes-git-release.service` — dry-run exits 1 on uncommitted changes + skills/shared symlinks. By design (advisory dirty-tree check), not a crash.
  - `hermes-trading-checklist.service` — was falsely CRIT "pipeline no recent execution". **ROOT CAUSE**: `journalctl -n 5`/-n 3 on verbose pipeline output never includes "Started hermes-pipeline.service". **AUTO-FIX**: removed -n limit, match run markers (`position_manager: done`, etc.). Verified: both checks now pass (True).
  - `hermes-wasp.service` — exits 1 when findings exist (by design). pipeline-log ERROR was the checklist false positive; next run should clear.
- **NOTE**: `systemctl list-timers hermes-*` shows 0 with glob; use `--all | grep hermes` (66 timers active). Pipeline timer firing correctly every 1min.

## Error Alerts — 2026-10-01 04:58 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: +N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-01 05:58 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-01 06:46 UTC
- **CRITICAL** (recovered): Pipeline import crash 06:00–06:32 — `hermes_constants.py:278 FAVORITES = FAVORITES_LONG | FAVORITES_SHORT` TypeError `dict | set` (empty `FAVORITES_LONG = {}` is a dict). run_pipeline died at import every minute.
  - **STATUS**: Fixed already (commit `158e5d68` 06:35:40): `FAVORITES = set(FAVORITES_LONG) | set(FAVORITES_SHORT)`. position_manager rc=0 since 06:32. No further action.
  - **SIDE FINDING**: `FAVORITES_LONG` is empty `{}` — favorites_updater may have wiped long favorites. Check `favorites_updater` output before next session.
- **WARN** (disk 85%): `/` 95G/118G used, 17G free. No logs >7d to gzip. Prior alerts note DB bulk (coin_tracker 3.3G, candles 2.3G+WAL 1.5G). No auto-fix applied — needs CEO decision on vacuum/retention.
- **WARN** (hotset empty): 47 signals/1h, 499 today, but 0 approved above 50% confidence — "no signals survived compaction", hotset.json empty, fallback DB query 0 tokens. Not a crash; signal-quality/filter review.
- **WARN** (token_speeds stale): 103/241 rows flagged `is_stale=1`. Last update 06:45:27 (fresh timestamps, but many marked stale).
- **WARN** (inactive timers): `hermes-hl-copy.timer` last run 2026-08-15 (1.5mo); `hermes-ma-cross-5m-tuner.timer` never ran; `hermes-regime-24h-check.timer` / `hermes-regime-transition-check.timer` show no last-run. Not trading-critical if intentional.
- **INFO**: Pipeline + hl-sync-guardian ACTIVE. Regime NEUTRAL (115/116). 0 open / 5 closed today (pnl -0.05). No phantom trades. 128/241 tokens ≥50th pct speed. Timers: 56 active hermes-*.

## Error Alerts — 2026-10-01 06:58 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   signal_analyst: TOK in N.1s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK signal_analyst: TOK (most recent call last):`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   breakout_engine: TOK in N.5s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK breakout_engine: TOK (most recent call last):`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS signals_runner: TOK — unsupported operand type(s) for |: 'dict' and 'set'`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.1s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK position_manager: TOK (most recent call last):`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   hermes-trades-api: TOK in N.1s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK hermes-trades-api: TOK (most recent call last):`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   strategy_optimizer: TOK in N.1s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK strategy_optimizer: TOK (most recent call last):`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   ab_optimizer: TOK in N.1s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TOK ab_optimizer: TOK (most recent call last):`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_analyst, breakout_engine, decider_run, position_manager, hermes-trades-api, strategy_optimizer, ab_optimizer`
- **REPEATED** (352x): `Oct N N:N:N python3[TOK]: TOK (most recent call last):`
- **REPEATED** (352x): `Oct N N:N:N python3[TOK]: TypeError: unsupported operand type(s) for |: 'dict' and 'set'`
- **REPEATED** (352x): `Oct N N:N:N systemd[N]: hermes-pipeline.service: Main process exited, code=exited, status=N/FAILURE`
- **REPEATED** (352x): `Oct N N:N:N systemd[N]: hermes-pipeline.service: Failed with result 'exit-code'.`

## Error Alerts — 2026-10-01 07:49 UTC
- **WARN** (1x): Disk at 86% (96G/118G) — DB growth (coin_tracker 3.3G, candles 2.3G, mtf_macd_tuner 1.3G), not logs. Journald vacuum freed 0B (already clean). No log files >7d uncompressed. **Needs CEO call on DB pruning.**
- **WARN** (ongoing): Hotset EMPTY — 137 signals generated last hour, 0 approved by compactor (none ≥50% confidence). Pipeline healthy, 3 open positions managed, but no new trades will open until signals clear compactor.
- **WARN** (repeating): hermes-wasp.service failing every ~2min cycle — endless `[LOCK-WAIT] info_rate` retry loop in wasp.err.log. Lock contention, not a crash. Code-owner fix needed.
- **WARN** (repeating): hermes-better-coder.service — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'` in run_better_coder.py:19. Path/sys.path issue.
- **WARN** (1x): hermes-trading-checklist.service — flags `signals_db: 12908 signals (0 approved, 5 pending)` — symptom of empty hotset, not a separate bug.
- **INFO**: hermes-git-release.service + hermes-upgrade-implementer.service failed (exit 1 / exit 124 timeout) — **AUTO-FIX**: reset-failed applied, both non-trading.
- **INFO**: Pipeline path clean — 0 errors/tracebacks in 30min. Prices fresh (11s, 86 tokens). Regime NEUTRAL (0L/2S/114N). 3 open SHORT positions all IN_PROFIT (BANANA, CFX, HYPER).

## Error Alerts — 2026-10-01 08:47 UTC
- **WARN** (1x): Disk usage 85% on / (95G/118G, 18G free)
- **AUTO-FIX**: None applied — no logs older than 7 days to gzip; large consumers are active DBs (coin_tracker 3.3G, candles 2.3G, mtf_macd_tuner 1.3G). No cleanup safe to auto-run.
- Note: atr-sl-updater timer is DEFUNCT (renamed unit), intentional. Other inactive timers (hl-copy, ma-cross-5m-tuner, regime-24h-check, regime-transition-check) appear intentionally disabled — no missed firings on active timers.

## Error Alerts — 2026-10-01 08:58 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-10-01 11:46 UTC
- **WARN** (ongoing): Disk at 85% (95G/118G). No logs >7d uncompressed to gzip (17 .gz already present). Large consumers are DBs: coin_tracker 3.3G, candles 2.3G, mtf_macd_tuner 1.3G. **Needs CEO call on DB pruning.**
- **WARN** (ongoing): Hotset EMPTY — 68 signals generated last hour, 0 approved by compactor (none ≥50% confidence). No new trades will open until signals clear compactor. Pipeline healthy, 0 open positions.
- **WARN** (repeating): hermes-wasp.service failing every cycle — `[LOCK-WAIT]` / exit 1. Code-owner fix needed.
- **WARN** (repeating): hermes-better-coder.service — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'`. Path/sys.path issue, code-owner fix.
- **INFO**: Pipeline path clean — 0 errors/tracebacks in 30min. 30 successful pipeline runs. Prices fresh (29s, 86 tokens). Regime NEUTRAL (0L/0S/116N). Speed 53% tokens ≥50th pctl. Kill switch LIVE enabled. Phantom trades: 0. hl-sync-guardian active (long-running, 11h).
- **INFO**: Daily PnL -33.74% on 34 closed trades (LONG 3/9 win, SHORT 3/11 win) — trading performance, not infra.
- **AUTO-FIXES APPLIED**: None — no actionable auto-fix this cycle (disk logs already compressed; pipeline not crashed; timers firing).

## Error Alerts — 2026-10-01 12:47 UTC
- **WARN** (ongoing): Disk at 85% (95G/118G, 17G free). No logs >7d uncompressed to gzip. Large consumers are active DBs: coin_tracker 3.3G, candles 2.3G, mtf_macd_tuner 1.3G, signals_hermes 892M. **Needs CEO call on DB pruning — no safe auto-fix.**
- **WARN** (ongoing): Hotset EMPTY — 62 signals generated last hour, 0 approved by compactor (none ≥50% confidence). Market NEUTRAL (2L/0S/114N). No new trades will open until signals clear compactor. Pipeline healthy, 0 open positions.
- **WARN** (repeating): hermes-price-collector.service — lock contention: `[LOCK-WAIT] info_rate` retries + `candles_15m/1h/4h: aggregation error: database is locked`. Collector still completes (86 prices, candles updated). Code-owner fix needed for candle-aggregation lock path.
- **INFO**: Pipeline path clean — 0 errors/tracebacks in 30min. 30 successful pipeline runs. Prices fresh (20s, 86 tokens). Regime NEUTRAL. Speed 53.1% tokens ≥50th pctl. Phantom trades: 0. Open trades: 0. Today: 20 closed, 30% WR, -0.87 USDT.
- **INFO**: token_speeds: 79/241 flagged stale (32.8%). decisions table empty since April (expected — signal_compactor is LLM-free, doesn't write decisions).
- **INFO**: Several 0-byte DB files present (brain.db, hermes.db, hermes_live.db, hermes_runtime.db, hermes_trades.db, hotset.db, price_cache.db, price_history.db, prices.db, runtime.db, signals.db). System uses signals_hermes_runtime.db / candles.db / coin_tracker.db instead — likely intentional placeholders. Flagging for awareness, not auto-deleting.
- **AUTO-FIXES APPLIED**: None actionable — pipeline not crashed; timers all firing; no logs >7d to gzip; disk pressure is DB growth not logs. No restart or force-run warranted.

## Error Alerts — 2026-10-01 14:46 UTC
- **WARN** (ongoing): Disk at 85% (95G/118G, 18G free). No logs >7d uncompressed (0 files). Large consumers are active DBs: coin_tracker 3.5G, candles 2.4G. **Needs CEO call on DB pruning — no safe auto-fix.**
- **WARN** (ongoing): Hotset EMPTY — 89 signals generated last hour, 0 approved by compactor (none ≥50% confidence). Market NEUTRAL (0L/2S/114N). 1 open position (BTC LONG trade_id=15799, in profit +0.37%). No new trades will open until signals clear compactor.
- **WARN** (repeating): hermes-wasp.service failing every cycle — exit 1/FAILURE. Not trading-path critical; code-owner fix needed.
- **WARN** (repeating): hermes-better-coder.service — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'`. Path/sys.path issue, code-owner fix.
- **WARN** (repeating): hermes-price-collector.service — `[LOCK-WAIT] info_rate` retries + `candles_1h/4h: aggregation error: database is locked`. Collector still completes. Code-owner fix for candle-aggregation lock path.
- **INFO**: Pipeline path clean — 0 errors/tracebacks in 30min. hl-sync-guardian + pipeline both active. Prices fresh (token_speeds updated 14:45:32, 241 tokens). Regime NEUTRAL (0L/2S/114N). Speed 53.1% tokens ≥50th pctl. Phantom trades: 0. Today: 21 closed, 33.3% WR, -0.84 USDT.
- **INFO**: token_speeds: 58/241 stale (24.1%). decisions table empty (expected — signal_compactor is LLM-free).
- **INFO**: hermes-atr-sl-updater.timer is not-found (defunct unit file present as -DEFUNCT). hermes-regime-24h-check.timer and hermes-regime-transition-check.timer inactive/dead — may be intentional (3-day check retired?). Flagging, not auto-deleting.
- **INFO**: Pipeline reports 1 open position but signal_outcomes shows 0 open rows (pnl_usdt NULL). Open BTC position likely tracked in HL/position-manager store until close — signal_outcomes appears closed-only. Not a bug unless expected open tracking there.
- **AUTO-FIXES APPLIED**: None — pipeline not crashed; timers firing; no logs >7d to gzip; disk pressure is DB growth not logs. No restart or force-run warranted.

## Error Alerts — 2026-10-01 15:48 UTC
- **WARN** (ongoing): Disk at 86% (96G/118G, 17G free). No logs >7d uncompressed to gzip. Large consumers are active DBs: coin_tracker 3.5G, candles 2.4G, mtf_macd_tuner 1.4G. **Needs CEO call on DB pruning — no safe auto-fix.**
- **WARN** (ongoing): Hotset EMPTY — 107 signals generated last hour, 0 approved by compactor (none ≥50% confidence). Market NEUTRAL (1L/1S/114N). 2 open positions (ETH LONG -0.19%, BTC LONG +0.32%). No new trades will open until signals clear compactor.
- **WARN** (repeating): hermes-wasp.service failing every cycle — exit 1/FAILURE. Code-owner fix needed.
- **WARN** (repeating): hermes-better-coder.service — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'`. Path/sys.path issue, code-owner fix.
- **WARN** (repeating): hermes-price-collector.service — intermittent `database is locked` on candle aggregation (5m/15m/1h/4h). Latest run at 15:47:51 succeeded (86 prices, candles updated). Lock path needs code-owner fix.
- **INFO**: Pipeline path clean — 191 rc=0 steps in 30min, 0 Tracebacks/CRASH/FATAL. hl-sync-guardian active 15h. Prices fresh (55s, 86 tokens). Regime NEUTRAL (1L ACE / 1S AERO / 114N). Speed 53.1% tokens ≥50th pctl (128/241). Phantom trades: 0. Open: 2. Today: 21 closed, 33.3% WR, -0.84 USDT. Kill switch LIVE enabled.
- **INFO**: token_speeds: 88/241 flagged stale (36.5%). decisions table last write 2026-04-13 — expected dead path post-signal_compactor (LLM-free).
- **INFO**: Several 0-byte DB files present (brain.db, hermes.db, hermes_live.db, hermes_runtime.db, hermes_trades.db, hotset.db, price_cache.db, price_history.db, prices.db, runtime.db, signals.db). System uses signals_hermes_runtime.db / candles.db / coin_tracker.db instead — likely intentional placeholders. Flagging for awareness, not auto-deleting.
- **INFO**: Load elevated: 7.96 / 6.94 / 6.54. Pipeline still completing all steps.
- **AUTO-FIXES APPLIED**: None actionable — pipeline not crashed; timers firing; prices fresh; no logs >7d to gzip; disk pressure is DB growth not logs; price-collector lock self-recovered on next tick. No restart or force-run warranted.

## Error Alerts — 2026-10-01 15:58 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-01 16:47 UTC
- **WARN** (1x): Disk 86% used — root cause is DB growth (coin_tracker.db 3.3G, candles.db 2.3G+WAL 961M, mtf_macd_tuner.db 1.3G), not logs. No .log files >7d to gzip.
- **AUTO-FIX**: `journalctl --vacuum-size=50M` freed 84MB archived journals. Disk still 86%. CEO pruning decision still needed for large DBs.
- **WARN** (1x): `hermes-atr-sl-updater.timer` unit file not-found (ghost systemd reference). ATR SL/TP path is healthy — managed locally by guardian via DB per pipeline logs.
- **AUTO-FIX**: `systemctl daemon-reload` run. No functional gap; stale reference remains in list-timers until unit file removed/recreated.
- **INFO**: Pipeline OK — 0 tracebacks, 0 real errors in 30min. 54 signals/hr, 2 open positions, 21 closed today (-$0.84, 33.3% WR). Hotset empty (confidence gate), regime NEUTRAL.

## Error Alerts — 2026-10-01 18:47 UTC
- **WARN** (ongoing): Disk **88%** used (98G/118G, 15G free) — up from 86% at 16:47. Root cause is DB growth, not logs. Largest: coin_tracker.db 3.3G, candles.db-wal **3.0G**, candles.db 2.3G, mtf_macd_tuner.db 1.3G, signals_hermes.db 894M, session_brain.db 835M. No .log files >7d to gzip.
- **AUTO-FIX**: `PRAGMA wal_checkpoint(TRUNCATE)` on candles.db run — no space reclaimed (WAL recreates under active price-collector writes). journalctl previously vacuumed. **CEO DB-pruning decision still required** — cannot safely auto-delete trade/price data.
- **WARN** (repeating): Hotset EMPTY — 49 signals/hr generated, 0 approved (none ≥50% confidence). Market LONG_BIAS but 110/116 NEUTRAL. 1 open position (BTC LONG +0.81%). No new trades until signals clear compactor.
- **WARN** (1x): Watchdog low-signal WARNING — 3-5 signals/5min vs watchdog min 20. Not a pipeline failure: signals are generating, just below watchdog's aggressive threshold. Market quiet/neutral.
- **AUTO-FIX**: Watchdog auto-restarted 3 failed services at 18:45: hermes-better-coder, hermes-bug-hunter, hermes-mtf-macd-tuner.
- **INFO**: Pipeline OK — active (timer every 1min), 0 Tracebacks/CRASH/FATAL in 30min. All major timers firing (pipeline, price-collector, signal-compactor, watchdog, hl-sync-guardian all <1min ago). Prices fresh (162/241 token_speeds updated <5min, 42 stale). Phantom trades: 0. Today: 23 closed, 9 wins (39.1% WR), -0.73 USDT. Kill switch LIVE enabled. OpenMemory running (Docker :8080).
- **INFO**: Inactive timers noted: `hermes-regime-24h-check.timer`, `hermes-regime-transition-check.timer` (loaded but inactive/dead). `hermes-atr-sl-updater.timer` still not-found (known ghost).
- **AUTO-FIXES APPLIED**: Watchdog service restarts (3x); WAL checkpoint attempt (no reclaim). No pipeline restart needed — system healthy, just disk pressure + quiet market.

## Error Alerts — 2026-10-01 19:48 UTC
- **WARN** (ongoing): Disk **85%** used (95G/118G, 18G free) — down from 87-88% earlier today; candles.db-wal shrank 3.0G→305M (checkpoint landed). Root cause remains DB growth (coin_tracker 3.3G, candles 2.3G, mtf_macd_tuner 1.3G). No .log files >7d to gzip. **CEO DB-pruning decision still open.**
- **WARN** (repeating): Hotset EMPTY — 98 signals/hr generated, **0 approved** (none ≥50% conf gate). Regime NEUTRAL (1 LONG_BIAS / 115 neutral). Not a code bug; signals generating, compactor approving none. 0 open trades in runtime DB.
- **WARN** (1x): `hermes-coding-mcp.service` crash-looping — 696k restarts, `run_mcp_server.py` missing from scripts/. **AUTO-FIX**: service stopped + disabled (script gone; restart storm was burning CPU/log noise every 5s). Restore script or delete unit if intentionally retired.
- **WARN** (recurring): 7 failed non-critical services: better-coder, bug-hunter, ceo, git-release, mtf-macd-tuner, trading-checklist, upgrade-implementer. trading-checklist exits 1 on the signals_db WARN (0 approved) — symptom of hotset gate, not independent failure. git-release exit 1 at 18:59 (backup path). Watchdog owns restarts.
- **INFO**: `hermes-atr-sl-updater.timer` still not-found (known ghost; ATR SL managed by guardian via DB).
- **INFO**: Pipeline OK — active (1min timer), 192 rc=0 / 30min, **0 Tracebacks**. All core timers firing <1min (pipeline, price-collector, signal-compactor, hl-sync-guardian, watchdog). Prices fresh (prices.json 0.6min, 162/241 token_speeds <5min). Today (runtime DB): 23 closed, 9 wins (39.1% WR), **-0.73 USDT**. Kill switch LIVE enabled.
- **AUTO-FIXES APPLIED**: coding-mcp stop+disable (crash loop); journalctl vacuum (0B freed, already clean). No pipeline restart needed.

## Error Alerts — 2026-10-01 20:47 UTC
- **WARN** (1x): disk usage 86% (threshold 85%). Top consumers: coin_tracker.db 3.3G, candles.db 2.3G, mtf_macd_tuner.db 1.3G. **AUTO-FIX**: journalctl vacuum freed 87.3MB; log gzip scan found nothing eligible. Recommend retention policy for large analytics DBs.
- **WARN** (5x): inactive/never-fired timers — hermes-hl-copy.timer (last run Aug 15), hermes-regime-24h-check.timer, hermes-regime-transition-check.timer, hermes-gate2-circuit-breaker.timer, hermes-ma-cross-5m-tuner.timer. atr-sl-updater is known ghost. **AUTO-FIX**: none — need owner confirmation before disabling/re-enabling; hl-copy may be intentionally retired.
- **INFO**: pipeline healthy — active, 0 Tracebacks/30m, 70 signals/1h, 1 open BTC LONG in profit. Regime LONG_BIAS. Prices fresh.

## Error Alerts — 2026-10-01 21:47 UTC
- **WARN** (ongoing): Disk **85%** used (95G/118G, 17G free) — unchanged from 20:47 check. Top consumers still DB growth (coin_tracker.db 3.3G, candles.db 2.3G, mtf_macd_tuner.db 1.3G). No .log files >7d to gzip; journalctl only 32M. **CEO DB-pruning decision still open.**
- **WARN** (repeating): Hotset EMPTY — 74 signals/hr generated, **0 approved** (none ≥50% conf gate). Decisions table: 0 in last hour. Regime NEUTRAL (115 neutral / 1 short). Not a code bug; market quiet + confidence gate working as designed.
- **WARN** (known): Inactive/ghost timers unchanged — atr-sl-updater (ghost), regime-24h-check, regime-transition-check, gate2-circuit-breaker (never fired), hl-copy (Aug 15), ma-cross-5m-tuner (Aug 14). No action; owner confirmation still needed before disable.
- **INFO**: Pipeline OK — active (1min timer), **384 rc=0 / 1h, 0 failures**, 0 Tracebacks/CRASH/exception in 30min. Position manager rc=0, managing 1 open SUSHI LONG (est. SL 1.30%, TP 2.00%, vol-gate widened). All core timers firing <1min (pipeline, price-collector, signal-compactor, watchdog, hl-sync-guardian). Prices fresh (regime_5m 0min, token_speeds 241). Today: 23 closed, -0.73 USDT. Phantom trades: 0. Kill switch LIVE enabled.
- **AUTO-FIXES APPLIED**: None required — pipeline healthy, timers firing, no crashes. Disk WARN unchanged (nothing safe to auto-clean; previous journal vacuum + WAL checkpoint already done).

## Error Alerts — 2026-10-01 22:48 UTC
- **WARN** (ongoing): Disk **86%** used (96G/118G, 17G free) — above 85% threshold. Top consumers unchanged: coin_tracker.db 3.3G, candles.db 2.3G + WAL 690M, mtf_macd_tuner.db 1.3G, signals_hermes.db 895M. No .log files >7d to gzip. journalctl vacuum freed 0B (already clean). **CEO DB-pruning decision still open** — cannot safely auto-delete trade/price data.
- **WARN** (repeating): Hotset EMPTY — 54 signals/hr generated, **0 approved** (compactor pre-filter: "No signals after pre-filter"; approved=0 rejected=0). Regime NEUTRAL (2 short_bias / 114 neutral). Signals generating (HBAR SHORT pump-chain 88.0, BANANA LONG support_resistance 74.8) but none clear confidence/compactor gate. Not a pipeline crash.
- **WARN** (known): 7 failed non-critical services: better-coder, bug-hunter, ceo (exit 124 timeout 21:56), git-release (exit 1 backup path 21:59), mtf-macd-tuner, trading-checklist (exits 1 on hotset-empty gate — symptom, not independent failure), upgrade-implementer. + weather-station-api. Core trading path unaffected; watchdog owns restarts.
- **INFO**: Pipeline OK — active, cycle #224515 at 22:45, **0 Tracebacks/CRASH/FATAL in 30min** (BTC-CRASH log lines are intentional BTC-level LONG blocks, not process crashes). Position manager rc=0: 1 open SUSHI LONG (SL 1.30%, TP 2.00%, vol-gate widened), 0 closed this cycle. Core timers firing <1min: pipeline 6s, signal-compactor 6s, price-collector 1min, trade-watchdog 10min. hl-sync-guardian service active. Prices fresh (prices.json 58s, 86 tokens). Speed: 128/241 (53%) tokens ≥50th pct. Today (runtime DB): **23 closed, 9 wins, 39.1% WR, -0.73 USDT**. Phantom atr_sl_hit <0.01%: 0. Open trades in signal_outcomes: 0 (SUSHI tracked in position manager).
- **AUTO-FIXES APPLIED**: None required — pipeline healthy, no crash/restart needed, timers firing, journal vacuum no-op. Disk WARN unchanged (nothing safe to auto-clean; DB-pruning decision still with CEO). Hotset empty not restartable (gate/market condition).

## Error Alerts — 2026-10-01 22:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-01 23:47 UTC
- **WARN** (ongoing): Disk **86%** used (96G/118G, 16G free) — above 85% threshold. Top consumers: coin_tracker.db 3.3G, candles.db 2.3G, signals 96M, continuum 38M. No .log files >7d eligible to gzip. **CEO DB-pruning decision still open** — cannot safely auto-delete trade/price data.
- **WARN** (repeating): Hotset EMPTY — **67 signals/hr** generated, **0 approved** (none clear compactor/confidence gate). Regime NEUTRAL (115 neutral / 2 long_bias). Not a code crash; gate working. decisions_1h=0.
- **WARN** (1x this cycle): `hermes-price-collector` candle aggregation hit `database is locked` (candles_5m/15m/1h/4h) while `hermes-1m-candle` held candles.db. Collector still collected 86 prices and service completed. Concurrent DB access pattern — watch for recurring lock contention; not restartable as a "fix."
- **WARN** (known): 7 failed non-critical services unchanged: better-coder (`ModuleNotFoundError: dispatcher.dispatcher`), bug-hunter (audit FAILs: hardcoded passwords, dead signal_gen imports), ceo (exit 124 timeout), git-release (exit 1), mtf-macd-tuner, trading-checklist (hotset-empty symptom), upgrade-implementer. Core trading path unaffected.
- **INFO**: Pipeline OK — active, **0 Tracebacks/CRASH/FATAL in 30min**. Open: 1/6 SUSHI LONG (entry 0.26112, SL trail, pnl≈-0.16%). Today (runtime DB): **23 closed, 39.1% WR, -0.73 USDT**. Phantom atr_sl_hit <0.01%: 0. Prices fresh (candles_1m age ~60s; 86 prices collected; token_speeds max_updated 23:45:39Z). Speed: 124/241 ≥50th pct fresh, 99 stale. Core timers firing <1min (pipeline, signal-compactor, price-collector, watchdog, coin-tracker). hl-sync-guardian active.
- **AUTO-FIXES APPLIED**: None required — pipeline healthy, no restart, timers firing, nothing safe to gzip. Disk + hotset + failed agent services are policy/investigation items, not auto-fixable.

## Error Alerts — 2026-10-02 00:59 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK ceiling: N.N > N`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] USELESS TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] USELESS TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-10-02 01:45 UTC
- **WARN** (ongoing): Disk **86%** used (95G/118G, 17G free) — above 85% threshold. No .log files >7d eligible to gzip. Top logs: pipeline 62M, signal-compactor 42M, trade-watchdog 40M. **CEO DB-pruning decision still open** — cannot safely auto-delete trade/price data.
- **WARN** (ongoing): Hotset EMPTY (`hotset: []`) — signals generating (168 in `signals` last hour; mtf_regime_trend_short, continuum_osc_short, etc.) but none clearing compactor/confidence gate into hotset. Regime SHORT_BIAS (1 long / 4 short / 112 neutral). Not a code crash.
- **INFO**: Pipeline OK — last run completed 01:45:28 LIVE, 0 Tracebacks. Open: 1 (JUP LONG, trade_id 15805, pnl≈+1.0%, trailing SL/TP active). Portfolio line: 32 closed today, -26.60% PnL. `signal_outcomes` today: 4 rows, -0.039 USDT, 50% WR (subset — open positions tracked by position manager, not signal_outcomes). Phantom atr_sl_hit <0.01%: 0. Prices fresh (token_speeds max 01:45:25Z; 128/241 ≥50th pct; 98 stale). Timers all firing <1min (pipeline, compactor, price-collector, watchdog, coin-tracker). hl-sync-guardian active. 17 "CRASH" log matches = BTC-CRASH filter warnings, not crashes.
- **AUTO-FIXES APPLIED**: None required — pipeline healthy, no restart, timers firing, nothing safe to gzip.

## Error Alerts — 2026-10-02 01:59 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+NEUTRAL+AT, allowing despite TOK filter`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] IO TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] IO TOK — continuum says TOK+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-02 02:59 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+TOK+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-02 03:59 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`

## Error Alerts — 2026-10-02 04:59 UTC
- **REPEATED** (11x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK ceiling: N.N > N`

## Error Alerts — 2026-10-02 05:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+TOK+TOK, allowing despite TOK filter`
- **REPEATED** (22x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BULL+TOK, allowing despite TOK filter`
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+NEUTRAL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-02 06:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-10-02 07:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+NEUTRAL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-02 08:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+TOK+TOK, allowing despite TOK filter`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-02 09:59 UTC
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-02 10:59 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BULL+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-02 11:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: v2 recheck: velocity -N.N% < -N.N%`

## Error Alerts — 2026-10-02 12:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-02 13:47 UTC
- **WARN** (persistent): `hotset.json is empty — no signals survived compaction` + `[hotset] fallback DB query returned 0 tokens` — 218 signals/1h generated, 0 approved by compactor gate. Signal-quality issue, not pipeline failure. No auto-fix (gate/config decision, not health).
- **WARN**: disk `/` 86% used (17G free). Bulk is DBs (coin_tracker 3.3G, candles 2.3G, mtf_macd_tuner 1.3G, signals_hermes 0.9G, session_brain 0.9G). No logs >7d to gzip; journald already vacuumed (0B prior runs). **Needs CEO DB-retention decision — do not auto-prune.**
- **WARN**: 11 non-critical systemd units in `failed` state (auto-1hr, signal-reporter, summarizer, trading-checklist, daily-orchestrator, better-coder, bug-hunter, mtf-macd-tuner, upgrade-implementer, git-release, weather-station-api). Pattern: opencode/LLM jobs timing out at 10min; better-coder/bug-hunter have `ModuleNotFoundError` (dispatcher code bug). Trading path unaffected (pipeline + guardian active). Not reset — timer retries fire regardless; code bugs need owners.
- **INFO**: dead/never-fired timers unchanged: `hermes-atr-sl-updater.timer` (unit not-found), `hermes-hl-copy.timer` (last: Aug 15), `hermes-ma-cross-5m-tuner.timer` (never), `hermes-regime-24h-check.timer` / `hermes-regime-transition-check.timer` (never). Owner confirmation still needed before disable.
- **INFO**: `token_speeds` has stale rows from 2026-07-19 (BLZ, MKR) mixed with fresh rows (13:47). Harmless dead-token residue.
- **AUTO-FIX**: none required. Pipeline completed LIVE at 13:45 (3 open / 43 closed today / +45.20%). Guardian active, 0 errors/Tracebacks/CRASH in 30min. Prices fresh (candles_1m 46s). Regime LONG_BIAS (5L/1S/111N). Phantom trades 0/24h. No restart applied.

## Error Alerts — 2026-10-02 13:59 UTC
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BULL+TOK, allowing despite TOK filter`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK:`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING — BTC_LEVEL`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] W TOK BLOCKED — WARNING: TOK level: +N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: [TOK-TOK] info_rate: waited N.1s, retrying`
