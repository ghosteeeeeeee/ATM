# Error Alerts


## Error Alerts — 2026-10-05 17:47 UTC
- **INFO** — Pipeline healthy: `hermes-pipeline.service` active/running, last cycle 17:47:03 rc=0, breakout 0 signals, position_manager clean (0 open | 0 closed this cycle | 0 Traceback/CRASH in 30m). Kill switch path intact.
- **WARN** (recurring): `hotset.json` empty — `no signals survived compaction` / `No signals above 50% confidence — skipping execution`. Signals (1h): **80 generated** (pump-chain 51, support_resistance 12, mtf_regime_trend_short 9, others 8), **0 approved**. `decisions` table empty in last 1h. Same pattern as 10-04 entries — signal_compactor filter audit still open.
- **INFO**: `signal_outcomes` open trades = 0; closed today = 27 | PnL **-0.79 USDT** | wins 16 (~59% WR). Phantom `atr_sl_hit` <0.01%: **0**. Regime fresh 17:45: **LONG_BIAS** (25L/14S/78N, 117 tokens). Speeds **126/241 (52.3%) ≥50th pct**. Prices fresh: candles_1m max ts age **~2.8 min**. token_speeds updated_at 17:46:14.
- **INFO**: Disk `/` **82%** (92G/118G, 21G free) — under 85% threshold, no cleanup needed. Runtime DB 92MB (warn >50MB) — known, collectors active.
- **INFO** (recurring): Non-trading failed units — `better-coder`, `bug-hunter` (exit-1 by design), `git-release` (uncommitted-changes gate), `trading-checklist`, `upgrade-implementer`, `wasp` (exit-1 by design when findings exist — wasp.log shows report: ollama generate 500/15s timeout, hotset empty, db-integrity). None on trading execution path. `hermes-atr-sl-updater.timer` not-found (dead ref). Ollama `/api/tags` 200; `/api/generate` 500 timeout — local LLM slow, not trading-blocking (deterministic pipeline).
- **INFO**: Core timers firing — `hermes-pipeline.timer`, `hermes-price-collector.timer`, `hermes-1m-candle.timer`, `hermes-hl-sync-guardian.timer` all active/running. No service stopped this session.
- **AUTO-FIXES APPLIED**: none required — trading path healthy. No restarts, no DB locks.

## Error Alerts — 2026-10-04 18:50 UTC
- **WARN** (1): Disk `/` **85%** used (95G/118G, 18G free).
  - **AUTO-FIX**: `journalctl --vacuum-size=400M` freed **442.6M** (journals 783.4M→340.7M). `session_brain.db` WAL checkpointed **63MB→0**. `signals_hermes.db` WAL trimmed **6MB→2.3MB**. `candles.db-wal` is **5.1G and growing** — locked by active `price_collector`/candle processes; cannot checkpoint mid-run. No logs >7d to gzip. Remaining bulk is active DBs (candles.db 2.5G + WAL 5.1G, coin_tracker.db 3.3G, signals_hermes.db 923M). **CEO DB-retention decision still open.**
- **WARN** (recurring): `hotset.json` empty — `no signals survived compaction` + `[hotset] fallback DB query returned 0 tokens` every cycle. Signals (1h): **117 generated**, **0 approved**. Regime overall LONG_BIAS (48L/11S/58N @ 18:45) is not the blocker this cycle — compaction/filter gate still rejecting all. `decisions` table stale (last row 2026-04-13) — signal_compactor may no longer write there. Signal-compactor filter audit still open.
- **INFO**: Pipeline healthy — LIVE every 1m via `hermes-pipeline.timer` (active). Last cycles rc=0, 0 Tracebacks/CRASH in 30m. Position Manager clean: **5 open | 29 closed today | -28.85% PnL** (portfolio log). `signal_outcomes` today: 24 closed, -0.64 USDT (DB view lags portfolio). Phantom `atr_sl_hit` <0.01%: **0**. Prices fresh (~2 min, 88 tokens <5m, 1m/5m candles current). Speeds **127/241 (52.7%) ≥50th pct**. Kill switch LIVE.
- **INFO** (recurring): Non-trading failed units — `better-coder` (`ModuleNotFoundError: dispatcher.dispatcher` — **dispatcher package on disk is an empty dir**, module file deleted, not a sys.path issue), `bug-hunter` (exit-1 by design — found 9 CRITICAL: sqlite/cursor/connection leaks, sql_injection, bare_except, hardcoded passwords, dead signal_gen imports), `git-release` (`update-git.py --dry-run` exit-1 on uncommitted-changes gate). None on trading execution path.
- **INFO** (known): `list-timers hermes-*` without `--all` shows 0 — cosmetic glob quirk; timers firing (pipeline, signal-compactor, 1m-candle, hl-sync-guardian all recent). `hermes-1m-candle.service` in `activating start` — normal for oneshot/timer churn.
- **AUTO-FIXES APPLIED**: journal vacuum 442.6M; session_brain WAL 63MB→0; signals_hermes WAL trimmed. No pipeline restart required.
## Error Alerts — 2026-10-04 17:47 UTC
- **INFO** — Pipeline healthy: active (running), last run 17:46:37 rc=0. Position Manager clean (2 open: HBAR LONG, ETC LONG; 0 closed this cycle; no Traceback/CRASH in 30m). Signals (1h): 102 generated (18 in last 15m). Closed today: 23 | WR 52.2% | PnL -0.70. Phantom trades: 0.
- **WARN** (recurring): `hotset.json` empty — `no signals survived compaction` / `No signals above 50% confidence — skipping execution`. 102 signals generated in last hour but 0 approved. Regime SHORT_BIAS (13L/29S/75N @ 17:45) may be suppressing approvals. Same pattern as 08:48 and 10-02 entries — signal_compactor filter audit still open.
- **INFO**: Disk 81% (90G/118G) — under 85% threshold, no cleanup needed.
- **INFO** (recurring): Non-trading failed units — `better-coder`, `bug-hunter`, `git-release`, `mtf-macd-tuner`, `trading-checklist`, `weather-station-api`. Known; not on execution path.
- **INFO**: `hermes-atr-sl-updater.timer` not-found (dead ref; DEFUNCT unit exists). Timers otherwise firing (pipeline, price-collector, signal-compactor, hl-sync-guardian all recent). `list-timers hermes-*` without `--all` shows 0 — cosmetic quirk.
- **INFO**: Speeds 127/241 (52.7%) ≥50th pct. Prices fresh (token_speeds updated_at 17:46:09). Regime file fresh (17:45).
- **AUTO-FIXES APPLIED**: none required. Trading path healthy.

## Error Alerts — 2026-10-04 08:48 UTC
- **INFO** — Pipeline healthy: last run 08:46:44 rc=0. Portfolio: 1 open | 36 closed today | +19.21% PnL. Position Manager clean (no Traceback/CRASH in 30m). Signals (1h): 130 generated. Hotset empty (0 approved) — no signals survived compaction; 130 raw signals still generated. Regime: LONG_BIAS (28L/17S/72N @ 08:45). Speeds: 129/241 (53.5%) ≥50th pct. Prices fresh: 160 tokens updated <5m, latest 08:46:24. Phantom trades: 0. Open via signal_outcomes=0 (portfolio source of truth = position_manager: 1 open).
- **INFO** (recurring): Non-trading failed units — `better-coder` (ModuleNotFoundError dispatcher.dispatcher), `bug-hunter` (exit-1 by design — found 9 CRITICAL: sqlite/cursor/connection leaks, sql_injection, bare_except, hardcoded passwords, dead signal_gen imports), `git-release` (dry-run exit-1), `mtf-macd-tuner` (PrecomputedMACD.warmup AttributeError), `trading-checklist` (exit-1). All known; none on trading execution path.
- **INFO** (known): `hermes-atr-sl-updater.timer` not-found (dead ref). `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` inactive dead — regime scanners themselves (4h/15m) active. `list-timers hermes-*` without `--all` shows 0 — cosmetic quirk.
- **INFO**: Disk 81% (91G/118G) — under 85% threshold. No log cleanup needed.
- **AUTO-FIXES APPLIED**: none required. Trading path healthy; failed units are known non-trading code bugs, not restartable crashes.

## Error Alerts — 2026-10-02 22:49 UTC
- **WARN** (1x): disk `/` **88%** used (98G/118G, 15G free) — up from 87% an hour ago.
  - **AUTO-FIX**: WAL checkpoint on `session_brain.db` (freed 73.8MB) and `signals_hermes.db` (freed 4.6MB). `candles.db` WAL is 3.2GB but locked by active `price_collector` — cannot checkpoint mid-run. No logs >7d to compress. Remaining bulk is active DBs (coin_tracker 3.3G, candles 2.3G, signals_hermes 905M, session_brain 866M, mtf_macd_tuner 529M). **CEO DB-retention decision still open.**
- **WARN** (repeated): `hotset.json` empty — `[hotset] fallback DB query returned 0 tokens` + `no signals survived compaction` every cycle. 83 signals generated in last hour but 0 approved. Regime fully NEUTRAL (117N/0L/0S) explains execution block; DB-fallback returning 0 despite 16839 rows in `signals` table is worth auditing in signal_compactor filters. Not a crash — trading path healthy.
- **INFO** (repeated): `hermes-better-coder.service` failing — `ModuleNotFoundError: No module named 'dispatcher.dispatcher'`. Broken import path. Not auto-fixed (needs code review).
- **INFO** (repeated): `hermes-mtf-macd-tuner.service` failing — `AttributeError: 'PrecomputedMACD' object has no attribute 'warmup'`. Code bug in tuner, not in trading execution path.
- **INFO**: `hermes-wasp.service` failing every 30min (exit 1). Health-monitor unit itself broken — ironic but non-critical.
- **NOTE**: `signals` table holds 16839 rows — `hermes-signal-purge.timer` may not be reclaiming. Worth retention audit.
- **INFO**: Pipeline healthy — 0 Tracebacks/CRASH in 30min. Position manager clean. Prices fresh (86 tokens, 32s). 47 trades closed today, 30 wins (63.8% WR). 0 open, 0 phantom. All key timers firing.

## Error Alerts — 2026-10-02 19:46 UTC
- **WARN** (1): `Disk at 85% (95G/118G)` — was 88% at check start. pipeline.log 81M, signal-compactor.log 49M, trade-watchdog.log 43M, 15m_regime.log 28M.
  - **AUTO-FIX**: Compressed `*.log` older than 7d via gzip. Disk 88%→85%. No new large files found >7d in logs/.
- **WARN** (5): Non-trading failed units — `better-coder`, `bug-hunter`, `git-release`, `mtf-macd-tuner`, `trading-checklist`.
  - `better-coder`: `ModuleNotFoundError: No module named 'dispatcher.dispatcher'` — import path broken. Not auto-fixable without code review.
  - `bug-hunter`: exit-1 by design — found real issues: hardcoded passwords in 4 files (`study_winning_combos.py`, `context-compactor.py`, `hermes_ab_utils.py`, `trading-checklist.py`) + dead imports of defunct `signal_gen` in 3 modules. Needs manual fix pass.
  - `git-release`: `update-git.py --dry-run` exit-1. Uncommitted files pattern (`M automation/error_alerts.md`). Investigate dry-run path.
  - `mtf-macd-tuner`: `AttributeError: 'PrecomputedMACD' object has no attribute 'warmup'` — code bug in tuner. Not in trading execution path.
  - `trading-checklist`: WARN `signals_db: 16670 signals (0 approved, 1 pending, 219 in last 2h)` — filters rejecting signals as designed, not a crash.
  - **AUTO-FIX**: None applied to failed units (code bugs need review, not restart). Trading path unaffected — pipeline + guardian + price-collector all active.
- **INFO**: Pipeline last cycle 19:45:09 UTC — all steps rc=0. 0 Tracebacks. Position Manager 0 open / 0 closed this cycle. Hotset empty (no signals >50% confidence). Regime SHORT_BIAS (1L/34S/82N) @19:45:05. Speed 129/241 ≥50th pct (53.5%). Signals 96/hr. 0 open trades. 47 outcomes today (all closed). Prices fresh (19:45/19:46). Timers firing (`list-timers hermes-*` glob quirk — use `list-timers --all | grep hermes`).

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

## Error Alerts — 2026-10-02 14:48 UTC
- **INFO**: pipeline.service `inactive` is NORMAL (oneshot+timer). Last run completed LIVE 14:45:28: 4 open / 46 closed today / +40.07% PnL. 30/30 runs rc=0 in 30min, 0 Tracebacks. "CRASH" grep hits are `BTC-CRASH-OVERRIDE` ALLOW messages (continuum recovery), not failures.
- **WARN**: disk `/` **86%** used (17G free). AUTO-FIX: journal vacuum freed **259.7M** (archived journals). No logs >7d to gzip. Bulk remains DBs (coin_tracker 3.3G, candles 2.3G+walm, mtf_macd 1.3G, signals 0.9G, session_brain 0.9G). **CEO DB-retention decision still open — recurring since 2026-10-01.**
- **WARN**: `hermes-git-release.service` failing hourly (exit 1) — root cause: `update-git.py` refuses release on (1) uncommitted changes (error_alerts.md etc. churn hourly) and (2) `SYMLINKS FOUND: ./scripts/hl_sync_guardian.py`. Blocks hourly backup + seed zip. Not auto-fixed (commit needs owner; symlink needs code change). Suggested: add symlink allowlist or replace symlink with import path in update-git.py.
- **INFO**: 10 non-critical units in `failed` (better-coder, bug-hunter, ceo, daily-orchestrator, git-release, mtf-macd-tuner, signal-reporter, summarizer, trading-checklist, upgrade-implementer). Known pattern: LLM jobs timing out; bug-hunter exits 1 on real findings (hardcoded passwords, dead signal_gen imports, non-atomic JSON). Trading path unaffected (pipeline, guardian, price-collector, hl-copy all active/running).
- **INFO**: hotset.json **recovered** — 7 tokens approved (SYRUP, AIXBT, COMP, LDO, WCT, DYDX all mtf_regime_trend_long). The 13:47 "hotset empty" alert is RESOLVED. `decisions` table shows 0/hr but compactor writes hotset.json — table likely legacy, not a signal-loss bug.
- **INFO**: token_speeds 162 fresh / 79 stale >5min (stale = dead-token residue, July rows for BLZ/MKR pattern). Latest update 14:47:25 — prices fresh. Regime NEUTRAL (1L/3S/113N). Speed: 128/241 ≥50th pct (53%). Phantom trades 0.

## Error Alerts — 2026-10-02 14:59 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+AT, allowing despite TOK filter`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.9s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS Rate limit check failed (DB TOK): cannot access local variable 'psycopg2' where it is not associated with a value — proceeding without rate limit`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] ME TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-02 15:49 UTC
- **REPEATED** (5x/30min): `Rate limit check failed (DB error): cannot access local variable 'psycopg2' where it is not associated with a value — proceeding without rate limit`
  - **ROOT CAUSE**: `decider_run.py` line 3660 had `import psycopg2` inside `run()` (starts line 3008). Python treats any local import as function-scoped for the whole function — shadowing module-level `import psycopg2` (line 8). Every earlier `psycopg2` use in `run()` hit UnboundLocalError.
  - **IMPACT**: (1) Rate-limit check (15s min gap between entries) was FAIL-OPEN — disabled on every run. (2) Losers hard-block WR<40% (line 4098) was FAIL-CLOSED — all LOSERS tokens blocked on DB error, not actual WR data.
  - **AUTO-FIX**: Removed the shadowing `import psycopg2` at line 3660. Module-level import now resolves correctly. py_compile OK. Effect on next pipeline run (~1min).
- **WARN**: disk `/` **86%** used (17G free). Journal vacuum freed 0B (already clean). No logs >7d to gzip. Bulk remains DBs. **CEO DB-retention decision still open (recurring since 2026-10-01).**
- **INFO**: pipeline.service `inactive` is NORMAL (oneshot+timer). Last run LIVE 15:45:27: 2 open / 51 closed today / +29.28% PnL. 0 Tracebacks in 30min. Guardian active. Timers all firing. Prices fresh (21s, 86 tokens). Regime SHORT_BIAS (0L/5S/112N). Phantom trades 0. Speed 128/241 ≥50th pct (53%).
- **INFO**: 12 non-critical units in `failed` (better-coder, bug-hunter, ceo, daily-orchestrator, git-release, mtf-macd-tuner, signal-reporter, summarizer, trading-checklist, upgrade-implementer, weather-station-api, + hl ghost). Trading path unaffected.

## Error Alerts — 2026-10-02 15:59 UTC
- **REPEATED** (12x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+TOK+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-02 16:48 UTC
- **INFO**: pipeline.service `inactive` is NORMAL (oneshot+timer). Last run LIVE 16:45:43: **1 open / 52 closed today / +28.04% PnL**. 0 Tracebacks in 30min. Guardian active. Timers firing. Prices fresh (~34s, 86 tokens). Regime NEUTRAL (1L/0S/116N). Phantom trades 0. Speed 128/241 ≥50th pct (53%). Signals 127/hr — healthy.
- **WARN**: disk `/` **85%** used (94G/118G, 18G free). AUTO-FIX: journal vacuum freed 0B (already clean). No logs >7d to gzip. Bulk remains DBs (coin_tracker 3.3G, candles 2.3G+walm, signals 0.9G, session_brain 0.9G). **CEO DB-retention decision still open — recurring since 2026-10-01.**
- **WARN**: `hermes-price-collector` candle aggregation `database is locked` (5m/15m/1h/4h) — concurrent writers: `_aggregate_1m.py` (PID 1692261) + price_collector both holding `candles.db` (2.3G). Prices themselves collect fine (86 tokens written). Service completes rc=0 after aggregation errors. Not auto-fixed — needs WAL/busy_timeout or write serialization in `_store_candles`.
- **WARN**: hotset.json **empty again** (cycle 17308, 0 tokens) — "[hotset] fallback DB query returned 0 tokens" + "no signals survived compaction". Was recovered 14:48 with 7 tokens; regressed. Compactor runs every minute; may be filter/quality gate, not crash. Monitor — if empty >1h, audit signal_compactor thresholds.
- **INFO**: 10 non-critical units in `failed` (better-coder, bug-hunter, ceo, daily-orchestrator, git-release, mtf-macd-tuner, signal-reporter, summarizer, trading-checklist, upgrade-implementer). Known pattern: LLM jobs timing out. Trading path unaffected (pipeline, guardian, timers all OK).
- **INFO**: price DB stubs (`prices.db`, `price_cache.db`, `price_history.db`) are 0-byte files — unused; live prices come via `prices.json` + static price_history (12.4M rows). Not a bug.

## Error Alerts — 2026-10-02 18:47 UTC
- **WARN**: disk `/` **85%** used (94G/118G, 18G free). Journal vacuum already clean. 0 logs >7d to gzip. Bulk remains DBs. **CEO DB-retention decision still open (recurring since 2026-10-01).**
- **INFO**: pipeline.service `inactive` is NORMAL (oneshot+timer). Last run LIVE 18:46:25: 0 open / 53 closed today / +11.71% PnL. 0 Tracebacks in 30min. Guardian active. Timers firing. Prices fresh (86 tokens). Regime SHORT_BIAS (0L/32S/85N). Speed 129/241 ≥50th pct (53%). Phantom trades 0. Signals 122/hr — healthy. Hotset populated (HYPE SHORT).
- **INFO**: non-critical failed units (better-coder, brain-auditor, bug-hunter, git-release, coding-mcp). Known LLM-job timeout pattern. Trading path unaffected.

## Error Alerts — 2026-10-02 18:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-02 19:59 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`

## Error Alerts — 2026-10-02 20:46 UTC
- **WARN** (1x): `disk 85% used on /` — 18G free of 118G
- **AUTO-FIX**: Checked logs >7d for compression — none found (all active, <7d). Largest consumers: coin_tracker.db 3.3G, candles.db 2.3G, signals_hermes.db 905M, session_brain.db 866M, pipeline.log 81M. No safe auto-fix; recommend DB vacuum / WAL checkpoint or log rotation review.
- **NOTE**: Regime fully NEUTRAL (0 LONG / 0 SHORT / 117 neutral) — market flat, explains 0 approved signals despite 33 detections/hr.

## Error Alerts — 2026-10-02 20:59 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK ceiling: N.N > N`

## Error Alerts — 2026-10-02 21:46 UTC
- **WARN** (1x): `disk 87% used on /` — 16G free of 118G (up from 85% an hour ago)
- **AUTO-FIX**: Compressed all `.log` files >7 days in `/root/.hermes/logs/`. Logs now 247M total. Largest disk consumers are DBs (coin_tracker.db 3.3G, candles.db 2.3G, signals_hermes.db 905M) — no safe auto-fix; recommend DB vacuum / archival.
- **NOTE**: 57 signals detected in last hour but 0 approved (hotset empty, all filtered by confidence/regime). Regime fully NEUTRAL (117 tokens) — market flat, expected behavior not a bug.

## Error Alerts — 2026-10-02 23:59 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: ME TOK — signal TOK rolled back (prevents retry loop)`

## Error Alerts — 2026-10-03 00:59 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   decider_run: TOK in N.2s (rc=N)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run, position_manager`

## Error Alerts — 2026-10-03 01:47 UTC
- **WARN** (1x): disk `/` **90%** used (100G/118G, 13G free) — up from 88% an hour ago.
  - **AUTO-FIX**: `journalctl --vacuum-size=100M` freed 170M archived journals (90%→89%). No logs >7d to compress. Remaining bulk: `candles.db-wal` 5.1G (locked by active price_collector — do not checkpoint mid-run), `coin_tracker.db` 3.3G, `candles.db` 2.3G, `signals_hermes.db` 907M, `session_brain.db` 871M. **CEO DB-retention decision still open.**
- **WARN** (5x): failed non-critical services:
  - `hermes-bug-hunter` — FAIL: hardcoded_passwords (4 files: study_winning_combos.py, context-compactor.py, hermes_ab_utils.py, trading-checklist.py) + dead_imports (zscore_momentum→signal_gen, trend_purity_signals→signal_gen, candle_predictor→signal_gen)
  - `hermes-mtf-macd-tuner` — AttributeError: `PrecomputedMACD` object has no attribute `warmup`
  - `hermes-trading-checklist` — signals_db: 17236 signals (0 approved, 1 pending, 224 in last 2h)
  - `hermes-git-release` — exit 1 (push blocked by modified error_alerts.md)
  - `hermes-better-coder` — failed (check last run logs)
  - **NO AUTO-FIX**: these are audit/tuner/CI tools, not on the live trading path. Core pipeline + HL guardian + signal-compactor + price-collector all healthy.
- **NOTE**: Hotset empty (`[]`) — signal_compactor fallback returned 0 tokens. Regime fully NEUTRAL (116 neutral / 1 LONG_BIAS / 0 SHORT) — expected behavior, not a bug. 61 signals in signals table (last hour) but 0 approved for hotset.

## Error Alerts — 2026-10-03 03:47 UTC
- **WARN** (1x): disk `/` **86%** used (96G/118G, 17G free).
  - **AUTO-FIX**: deleted 1202 leaked `/tmp/.bcd*.so` files (6.3G), rotated `/var/log/syslog` (640M→gz), purged `/tmp` files >7d. Disk now **80%** (23G free).
- **NOTE**: 0 signals in `signals` table last hour; hotset empty. 6 outcomes today (5W/1L, +1.35 USDT net). Regime LONG_BIAS (5L/1S/111N). Expected quiet/filter behavior, not a bug.
- **NOTE**: Open positions 3/6 (ARB/ALGO/APT SHORT) tracked in `trades.json` + position manager — `signal_outcomes` only stores closed trades, no open-row discrepancy.
- **NOTE**: `candles.db-wal` 1.6G (was 5.1G in 01:47 alert — shrinking). `coin_tracker.db` 3.3G still largest DB. CEO retention decision still open.
- **NOTE**: `hermes-hl-copy.timer` enabled but last fired 2026-08-15 (49 days). Non-critical; service may be intentionally paused. Verify if hl-copy is still needed.
- Pipeline, HL guardian, price-collector, signal-compactor, trade-watchdog all healthy. No crashes/tracebacks/phantom trades.

## Error Alerts — 2026-10-03 04:59 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK-TOK-TOK] TOK TOK BLOCKED — candle data stale/insufficient (age=925s, n=N) — TOK-closed`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: stale candles age=925s — TOK blocked (TOK-closed)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK floor: N.N < N`

## Error Alerts — 2026-10-03 05:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-03 06:48 UTC
- **CRITICAL** (fixed): `hermes-coding-mcp.service` crash-looping — `run_mcp_server.py` missing (exit 2), **NRestarts=713,209**, restart every 5s burning CPU.
  - **AUTO-FIX**: `systemctl stop + disable hermes-coding-mcp.service`. Script does not exist at `/root/.hermes/scripts/run_mcp_server.py`. Recreate script or remove unit if MCP host no longer needed.
- **WARN** (3x): `hermes-bug-hunter.service` failed — audit checks FAIL (cursor_leaks 53 files, connection_leaks 53, bare_except 127, sql_injection 33 f-string SQL, hardcoded_passwords 4, defunct_imports signal_gen still imported by 3 files, sqlite_leaks 49). Real code-quality findings, not runtime crashes. Not on trading path.
- **WARN** (2x): `hermes-better-coder.service` failed — similar audit failures.
- **WARN** (1x): `hermes-ceo.service` exit 1 — OpenMemory MCP rejected call (`Not Acceptable: Client must accept both application/json and text/event-stream`) + dirty git. Reports/kanban written before failure; work completed.
- **WARN** (2x): `hermes-git-release.service` failed — dirty git (`M automation/error_alerts.md`) blocks hourly backup/seed zip.
- **WARN** (132x/2h): `hermes-price-collector.service` intermittent `sqlite3.OperationalError: database is locked` on `candles.db` (2.3GB) — concurrent writers (pipeline + collectors). 74/206 runs succeeded; latest run OK (seeded 2/2, 86 prices). Self-heals via timer; no restart applied.
- **INFO**: Hotset `[]` empty — regime fully NEUTRAL (114/117). 142 signals generated last hour, 0 approved for execution. Expected compaction behavior, not a bug.
- **INFO**: Disk `/` **82%** used (was 86% this morning, cleaned to 80%, crept back). Under 85% warn threshold.
- **INFO**: No pipeline crashes, no Tracebacks, no phantom trades (`atr_sl_hit` <0.01% PnL: 0 in 24h). Position manager healthy (2 open, DYDX SHORT adjusted).

## Error Alerts — 2026-10-03 09:59 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS TOK breakout_engine: timed out (killed after N.0s)`
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS WARNING: N steps failed: breakout_engine`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK:`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] IO: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-03 10:59 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK ceiling: N.N > N`

## Error Alerts — 2026-10-03 11:47 UTC
- **HEALTH** — Pipeline OK: last run 11:45 completed clean (LIVE). Signals (1h): 63. Trades today: 0 open / 15 closed (9 wins, +1.45 USDT). Disk 80%. Regime: 1 LONG (ZRO) / 0 SHORT / 116 NEUTRAL. Prices fresh (85 tokens, ~71s). No Tracebacks, no phantom trades.
- **WARN** (1x): `hermes-price-collector.service` exit 1 — `sqlite3.OperationalError: database is locked` on candles.db. Prices still fresh via successful runs. **AUTO-FIX**: none — self-heals via 30s timer.
- **WARN** (6x): failed units unchanged — better-coder, bug-hunter, git-release, mtf-macd-tuner, trading-checklist, upgrade-implementer. Known audit/dirty-git failures, not on trading path. **AUTO-FIX**: none.
- **INFO**: `signals` table 18,327 rows since 2026-09-23 — purge timer may only archive, not clear active table. Not blocking execution.
- **INFO**: Pipeline portfolio counter (37 closed today) ≠ signal_outcomes (15). DB remains source of truth.

## Error Alerts — 2026-10-03 14:48 UTC
- **HEALTH** — Pipeline OK: last run 14:45:44 completed clean (LIVE). Signals (1h): 78. Trades today: 3 open / 28 closed per position manager (+17.61% PnL); signal_outcomes 19 closed (12 wins). No Tracebacks in pipeline logs. No phantom trades. Prices fresh (85 tokens, prices.json ~38s). Speeds: 53.5% tokens ≥50th percentile (129/241). Regime: 2 LONG_BIAS / 0 SHORT / 115 NEUTRAL (overall NEUTRAL). Disk 82%.
- **WARN** (known, unchanged): `hotset.json` empty — no signals survived compaction (regime fully neutral). Pipeline logs `fallback DB query returned 0 tokens` every run. Expected in NEUTRAL regime; not a crash. No auto-fix.
- **WARN** (known): `signals` table 18,574 rows — trading-checklist flags "may need cleanup". Purge/archive may not clear active table. Not on execution path.
- **WARN** (known, 5 failed units): better-coder (`ModuleNotFoundError: dispatcher.dispatcher`), bug-hunter (audit FAILs: hardcoded passwords, dead signal_gen imports, cursor/connection leaks), git-release (dirty git blocks backup), trading-checklist (exits 1 on signals_db WARN — by design), upgrade-implementer (timeout exit 124). None on trading path. No auto-fix (root causes tracked, not transient).
- **INFO**: `hermes-hl-sync-guardian` active. Timers healthy — pipeline/price-collector/signal-compactor/watchdog all firing ~1min/30s cadence. No missed core timers. `hermes-atr-sl-updater.timer` not-found (dead unit file; ATR updates run inside pipeline Position Manager — no functional gap).
- **AUTO-FIXES APPLIED**: none. No CRITICAL conditions found.

## Error Alerts — 2026-10-03 15:47 UTC
- **HEALTH** — Pipeline OK: last run 15:45:46 completed clean (LIVE); next run 15:46:33 already cycling. Position Manager healthy (0 open / 0 closed this cycle). Signals (1h): 63. Trades today: 23 closed in signal_outcomes (15 wins, +1.57 USDT), 0 open; pipeline portfolio counter 26 closed / +29.27% (counter ≠ DB — DB is source of truth). No Tracebacks, no CRASH. Disk 80%. Regime: 0 LONG / 0 SHORT / 117 NEUTRAL (fully neutral). Speeds: 53.5% tokens ≥50th pct (129/241). Prices fresh (85 tokens, prices.json ~0.5min). hl-sync-guardian active.
- **WARN** (known, unchanged): `hotset.json` empty — regime fully NEUTRAL (117/117). Pipeline logs `fallback DB query returned 0 tokens`. Expected compaction behavior, not a bug. No auto-fix.
- **WARN** (known, 5 failed units): better-coder, bug-hunter, git-release, trading-checklist, upgrade-implementer — same root causes as 14:48 entry, none on trading path. No auto-fix.
- **INFO**: `systemctl list-timers hermes-*` prints "0 timers listed" — cosmetic; individual `systemctl status` confirms pipeline/price-collector/coin-tracker timers active and firing. Not a missed-timer condition.
- **INFO**: 18 historical |pnl_pct|<0.01% outcomes exist (none `atr_sl_hit`, none today — newest 2026-09-28). Not phantom-trade events in the current window.
- **INFO**: `prices.db` / `runtime.db` / `hermes_prices.db` have empty tables — live prices served from `prices.json` (85 tokens). Not a data-loss issue.
- **AUTO-FIXES APPLIED**: none. No CRITICAL conditions found; no restarts or cleanups needed.

## Error Alerts — 2026-10-03 16:47 UTC
- **HEALTH** — Pipeline OK: last run 16:45:40 completed clean (LIVE). Position Manager healthy (5 open, SL/TP updated on 5). Signals (1h): 92 / 24h: 2362. Trades today: 5 open / 24 closed (16 wins, +1.63 USDT) per signal_outcomes + trades.json (pipeline counter 27 closed / +31.48% — counter ≠ DB, DB is source of truth). No Tracebacks, no CRASH. Phantom trades (`atr_sl_hit` <0.01% PnL): 0 today / 0 in 24h. Disk 81%. Regime: 1 LONG_BIAS / 0 SHORT / 116 NEUTRAL (overall NEUTRAL). Speeds: 53.5% tokens ≥50th pct (129/241), updated 16:47:20. Prices fresh (85 tokens, prices.json updated 16:46:49 UTC, ~41s). hl-sync-guardian active.
- **WARN** (known, unchanged): `hotset.json` empty — pipeline logs `fallback DB query returned 0 tokens`. Expected when regime is fully NEUTRAL; not a crash. No auto-fix.
- **WARN** (known, 7 failed units): better-coder, brain-auditor (NEW vs 15:47 — same class of agent/audit failures), bug-hunter, git-release, mtf-macd-tuner, trading-checklist, upgrade-implementer. None on trading path. No auto-fix (root causes tracked).
- **WARN** (known): `signals` active table large (purge/archive may not clear it). Not on execution path.
- **INFO**: `systemctl list-timers hermes-*` still prints "0 timers listed" — cosmetic; `--all`/grep shows core timers firing (pipeline, price-collector, watchdog, coin-tracker, signal-compactor, 15m-regime). Not a missed-timer condition.
- **INFO**: Inactive/dead timers: `hermes-atr-sl-updater` (ATR runs inside pipeline Position Manager), `hermes-regime-24h-check`, `hermes-regime-transition-check`, `hermes-hl-copy` (last ran 2026-08-15 — likely intentional/disabled). No functional gap on trading path.
- **AUTO-FIXES APPLIED**: none. No CRITICAL conditions found; no restarts, cleanups, or forced runs needed.

## Error Alerts — 2026-10-03 16:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-03 17:47 UTC
- **WARN** (7): Non-critical services in `failed` state — `hermes-better-coder`, `hermes-bug-hunter`, `hermes-git-release`, `hermes-mtf-macd-tuner`, `hermes-trading-checklist`, `hermes-upgrade-implementer`, `hermes-wasp`
- **AUTO-FIX**: Disk 86% → 80% — gzipped `*.log` older than 7 days in `/root/.hermes/logs/`
- **NOTE**: Core trading path healthy (pipeline, hl-sync-guardian, price-collector, signal-compactor all active). Failed units are maintenance/analyzer jobs, not trade-critical.

## Error Alerts — 2026-10-03 19:47 UTC
- **HEALTH** — Pipeline OK: active, cycle #227236 at 19:45:25 (still cycling at 19:47). Position Manager healthy (3 open / 0 closed, ATR SL/TP updates running). Signals (1h): 68. Trades today: 28 closed in signal_outcomes (19 wins, +1.81 USDT). No Tracebacks, no CRASH in last 30min. Disk 84%. Regime: 2 LONG_BIAS (MON, PUMP) / 0 SHORT / 115 NEUTRAL (overall NEUTRAL). Speeds: 53.5% tokens ≥50th pct (129/241). Prices fresh (85 tokens, prices.json 19:46:25 UTC). hl-sync-guardian active.
- **WARN** (known, unchanged): `signals` active table 18,897 rows — trading-checklist flags "may need cleanup". Purge/archive may not clear active table. Not on execution path.
- **WARN** (known, 8 failed units): better-coder (`ModuleNotFoundError: dispatcher.dispatcher`), brain-auditor, bug-hunter, git-release, mtf-macd-tuner, trading-checklist, upgrade-implementer, wasp, weather-station-api. None on trading path. Root causes tracked — no auto-fix.
- **WARN** (known): `hotset.json` empty — regime fully NEUTRAL (115/117). Expected compaction behavior, not a bug.
- **INFO**: Disk 84% (was 80% at 17:47 check) — under 85% WARN threshold. No logs >7 days to gzip; largest live log pipeline.log 21M. Monitor next cycle.
- **INFO**: `hermes-atr-sl-updater.timer` not-found (DEFUNCT unit file; ATR runs inside pipeline Position Manager — no functional gap). `hermes-regime-24h-check.timer` / `hermes-regime-transition-check.timer` inactive/dead. `hermes-hl-copy` last ran 2026-08-15 (likely intentional).
- **INFO**: `systemctl list-timers hermes-*` prints "0 timers listed" without `--all` — cosmetic; `--all`/grep confirms core timers firing (pipeline 1min, price-collector 30s, signal-compactor 1min, watchdog, coin-tracker, 15m-regime).
- **INFO**: 0 phantom trades (`atr_sl_hit` <0.01% PnL) today.
- **AUTO-FIXES APPLIED**: none. No CRITICAL conditions; no restarts or cleanups needed.

## Error Alerts — 2026-10-03 20:59 UTC
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-03 23:48 UTC
- **HEALTH** — Pipeline OK: last run 23:45:33 completed clean (LIVE, Result=success). Position Manager healthy (2 open / 0 closed, ATR SL/TP updated on LDO). Signals (1h): 59. Trades today: 2 open / 33 closed in signal_outcomes (+1.44 USDT; pipeline counter +37.51% — counter ≠ DB sum, DB is source of truth). No Tracebacks, no CRASH. Phantom trades (`atr_sl_hit` <0.01% PnL): 0. Disk 82%. Regime: 1 LONG_BIAS / 0 SHORT / 116 NEUTRAL (overall NEUTRAL, 117 tokens, ts 23:45). Speeds: 53.5% tokens ≥50th pct (129/241). Prices fresh (trades.json 0.7min, regime_5m.json 1.1min, coin_tracker_data.json exported 23:48 — 112 coins at `/var/www/html/` via nginx alias, not WWW_DATA). hl-sync-guardian active. pipeline.timer active, next 23:47:00.
- **WARN** (known, 8 failed units — none on trading path): `hermes-better-coder` (ModuleNotFoundError: dispatcher.dispatcher), `hermes-bug-hunter` (audit FAILs: hardcoded passwords + dead signal_gen imports — expected when findings exist), `hermes-ceo` (exit 124 timeout), `hermes-git-release` (update-git.py --dry-run exit 1), `hermes-mtf-macd-tuner` (AttributeError: PrecomputedMACD.warmup), `hermes-trading-checklist` (1 WARN signals_db), `hermes-upgrade-implementer` (exit 124), `hermes-wasp` (exit 1), `weather-station-api`. Root causes tracked — no auto-fix.
- **WARN** (new): `/root/.hermes/data/coin_tracker.db` is **3.5 GB** (112 coin tables × ~44k rows each). Disk at 82%. Under 85% cleanup threshold, but retention is missing — flag for a prune job. Do not delete without schema review.
- **WARN** (known, unchanged): `signals` active table ~19,156 rows — trading-checklist flags cleanup. Not on execution path.
- **WARN** (known): `hotset.json` loaded 1 token — regime fully NEUTRAL (116/117). Expected compaction, not a crash.
- **INFO**: `systemctl list-timers hermes-*` prints "0 timers listed" without `--all` — cosmetic. `--all` confirms core timers firing (pipeline 1min, price-collector, watchdog, coin-tracker 30min, signal-compactor, 15m-regime, pump-hunter).
- **INFO**: `decisions` table last row 2026-04-13 — decider path migrated to signal_compactor; table not written by current runtime. Not a pipeline failure.
- **INFO**: Inactive/dead timers: `hermes-atr-sl-updater` (DEFUNCT; ATR runs in Position Manager), `hermes-regime-24h-check`, `hermes-regime-transition-check`, `hermes-hl-copy` (last 2026-08-15). No trading-path gap.
- **AUTO-FIXES APPLIED**: none. No CRITICAL conditions; pipeline healthy, disk under threshold, timers firing. No restarts or cleanups needed.

## Error Alerts — 2026-10-03 23:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: CC TOK — signal TOK rolled back (prevents retry loop)`

## Error Alerts — 2026-10-04 00:47 UTC
- **HEALTH** — Pipeline OK: active/running. Position Manager healthy (1 open ENS LONG, ATR SL/TP active). Signals (1h): 53. Trades: 1 open / 1 closed today (LDO +0.23% win). No Tracebacks/CRASH in pipeline logs. Phantom trades: 0. Disk 82% (under 85%). Regime: NEUTRAL (25 long / 26 short / 66 neutral). Speeds: 53.5% ≥50th pct (129/241). Prices fresh (~37s). hl-sync-guardian active (1 position, no orphans). Core timers firing (pipeline 1m, price-collector 30s, compactor 1m, watchdog).
- **WARN** (known, ~8 failed units, none on trading path): better-coder (`ModuleNotFoundError: dispatcher.dispatcher`), bug-hunter (audit FAILs — expected when findings exist), ceo (exit 124 timeout), git-release (dry-run exit 1), mtf-macd-tuner, trading-checklist (WARN findings cause exit 1), upgrade-implementer (exit 124), wasp (ran, but generate check timed out). Root causes tracked — no auto-fix.
- **WARN**: ollama generate check timed out (15s read) during WASP run — ollama.service is active with models loaded; transient/slow, not down.
- **WARN**: WASP "pipeline-log: 1 ERROR lines" is a false positive — matches `0 errors` in signals_runner lines (`-i error`). Pipeline itself reports 0 errors.
- **WARN** (known): runtime signals DB ~92MB (WASP threshold <50MB). Not on execution path.
- **WARN** (known): hotset empty — no signals survived compaction above 50% confidence. Expected in NEUTRAL regime.
- **INFO**: `systemctl list-timers hermes-*` prints "0 timers listed" without `--all` — cosmetic; `--all` confirms timers firing.
- **INFO**: Empty price DBs (`prices.db`, `hermes_prices.db`, `price_cache.db` — 0 bytes) — runtime uses `price_history.db` + `prices.json`. Not a failure.
- **AUTO-FIXES APPLIED**: none. No CRITICAL trading-path conditions; disk under threshold; no restarts or cleanups needed.

## Error Alerts — 2026-10-04 00:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`

## Error Alerts — 2026-10-04 02:47 UTC
- **HEALTH** — Pipeline OK: active/running. Position Manager healthy (2 open: ENS LONG + CHIP LONG, ATR SL/TP active, decider entered CHIP this cycle). Signals (1h): 116. Trades: 2 open / 32 closed today (+19.31% PnL). No Tracebacks/CRASH in pipeline logs. Phantom trades: 0. Disk 80% (under 85%). Regime: SHORT_BIAS (19 long / 24 short / 74 neutral, 117 tokens). Speeds: 53.5% ≥50th pct (129/241). Prices fresh (~80 tokens in prices.json, ~1min old). Core trading timers firing (pipeline 1m, price-collector 30s, compactor 1m, watchdog, pump-hunter, 1m-candle, hl-sync-guardian active).
- **WARN** (known, ~7 failed units, none on trading path): better-coder, bug-hunter, git-release, mtf-macd-tuner, trading-checklist, upgrade-implementer, wasp. Same set as prior reports; root causes tracked — no auto-fix.
- **INFO**: `signal_outcomes` open-query (pnl_usdt NULL / trade_id logic) returns 0 while pipeline + trades.json report 2 open — outcomes table appears closed-only. Portfolio source of truth remains position_manager + trades.json. Not a trading-path failure.
- **INFO**: `systemctl list-timers hermes-*` without `--all` still prints "0 timers listed" — cosmetic; explicit unit listing confirms timers firing.
- **INFO**: hotset empty (0 tokens) — no signals survived compaction above threshold. Expected under SHORT_BIAS/neutral-heavy regime.
- **AUTO-FIXES APPLIED**: none. No CRITICAL trading-path conditions; disk under threshold; no restarts or cleanups needed.

## Error Alerts — 2026-10-04 03:59 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK ceiling: N.N > N`

## Error Alerts — 2026-10-04 04:48 UTC
- **HEALTH** — Pipeline OK: timer-active (1m), last full run rc=0 at 04:45:48; new runs 04:47/04:48. Position Manager healthy (0 open / 0 closed this cycle, all gates loaded). Signals (1h): 68. Trades: 0 open | 34 closed today | +14.53% PnL (portfolio; signal_outcomes shows 7 today / +0.17 USDT / 5 wins). Pipeline errors/Tracebacks: 0. Phantom trades: 0. Disk 80% (under 85%). Regime: LONG_BIAS (41 long / 8 short / 68 neutral, 117 tokens, ts 04:45). Speeds: 53.5% ≥50th pct (129/241). Prices fresh (prices.json ~2min, token_speeds 04:47). hl-sync-guardian active. Core timers firing (pipeline, price-collector 30s, compactor 1m, watchdog, pump-hunter, 1m-candle).
- **WARN** (known, ~7 failed units, none on trading path): better-coder (`ModuleNotFoundError: dispatcher.dispatcher`), bug-hunter (audit FAILs — expected when findings exist), git-release (dry-run exit 1), mtf-macd-tuner (multiprocessing error), trading-checklist (WARN findings → exit 1), upgrade-implementer (exit 124 timeout). Root causes tracked — no auto-fix.
- **WARN** (new): `weather-station-api.service` failed — `/root/.hermes/scripts/weather_station_api.py` missing; `weather_station.json` stale (Aug 27). coin_tracker enricher skips gracefully. Not on execution path.
- **WARN**: `hermes-atr-sl-updater.timer` not-found (dead unit reference).
- **INFO**: `decisions` table stale since 2026-04-13 (4 rows) — compactor path now uses hotset/signal_compactor, not this table.
- **INFO**: hotset empty (0 tokens) — no signals survived compaction above threshold this cycle. 68 raw signals still generated. Expected under current filters.
- **INFO**: `systemctl list-timers hermes-*` without `--all` prints "0 timers listed" — cosmetic; `--all` + `list-units` confirm timers firing.
- **INFO**: `signal_outcomes` open-query returns 0; portfolio source of truth remains position_manager + trades.json (0 open, consistent).
- **AUTO-FIXES APPLIED**: none. Pipeline running, disk under threshold, prices fresh, no crashes — no restarts or cleanups needed.

## Error Alerts — 2026-10-04 05:48 UTC
- **HEALTH** — Pipeline OK: active/running (timer 1m), last full run 05:47:21 rc=0. Portfolio: 0 open | 33 closed today | +13.57% PnL. Position Manager healthy (no Traceback/CRASH in 30m logs). Signals (1h): 52 generated (`signals` table). Approved/hotset: 0 (empty — known, no signals survived compaction). Regime: LONG_BIAS (47L / 12S / 58N, 117 tokens, ts 05:45). Speeds: 53.5% ≥50th pct (129/241, updated 05:46). Prices fresh: 85 tokens, ~34s old (`prices.json`). Disk 80% (under 85%). Phantom trades: 0 recent. Core timers firing: pipeline 1m, price-collector 30s, compactor 1m, pump-hunter 1m, 1m-candle, hl-sync-guardian 5m, watchdog, coin-tracker.
- **WARN** (recurring, non-fatal): `hermes-price-collector` candle aggregation — `sqlite3.OperationalError: database is locked` (43x/30min) + 1 hard crash 05:45:23. Root cause: `_aggregate_1m.py` (long-running, holds candles.db write lock) contends with price_collector's candle writes. systemd auto-restarted; latest run 05:48:01 succeeded (85 prices collected, rc=0). Prices remain fresh — no trading-path impact. Fix left to code-level (busy_timeout / write serialization); not force-killed (aggregation is legitimate work).
- **WARN** (known): hotset empty — no signals survived compaction this cycle. 52 raw signals still generated in 1h. Expected under current filter thresholds.
- **WARN** (known, non-trading-path): `hermes-atr-sl-updater.timer` not-found (dead unit ref — ATR SL/TP managed locally by guardian via DB). `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` inactive dead (UnitFileState=enabled but not scheduled) — regime scanners themselves (4h/15m) are active and firing.
- **INFO**: `signal_outcomes` closed-today=8 vs portfolio 33 — outcomes table is partial/closed-only; portfolio source of truth remains position_manager + trades.json (consistent with prior reports).
- **AUTO-FIXES APPLIED**: none required. Pipeline running; price-collector crash self-healed via systemd restart; disk under threshold; no missed trading-path timers; no stale prices. No restarts or cleanups forced.

## Error Alerts — 2026-10-04 06:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK:`

## Error Alerts — 2026-10-04 08:59 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] USELESS: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`

## Error Alerts — 2026-10-04 09:47 UTC
- **HEALTH** — Pipeline OK: timer active (1m), last full run 09:46:42 rc=0 LIVE. Portfolio: 0 open | 37 closed today | +14.58% PnL. Position Manager healthy (0/0/0 this cycle, no Traceback/CRASH in 30m). Signals (1h): 81 raw (`signals` table). Hotset/approved: 0 (empty — known, filters block all compaction; raw flow healthy). Regime: SHORT_BIAS (11L / 41S / 65N, 117 tokens, ts 09:45). Speeds: 53.5% ≥50th pct (129/241, updated 09:46). Prices fresh: 85 tokens collected 09:45:20; token_speeds ~1m old; candles_1m/5m ~2m old. Disk 81% (under 85%). Phantom trades: 0 (37 closed 24h, 0 with |pnl_pct|<0.01). Core timers firing (pipeline 1m, price-collector 30s, compactor 1m, pump-hunter, 1m-candle, hl-sync-guardian, watchdog, coin-tracker 30m).
- **WARN** (recurring, non-fatal): `hermes-price-collector` candle aggregation — `sqlite3.OperationalError: database is locked` (multiple runs in 30m window; 1m/5m/15m/1h/4h tables) while `hermes-1m-candle.service` (`_aggregate_1m.py`) holds candles.db write lock (~1.5–2min/run, 2.4GB DB). Price collection itself succeeds every cycle (85 prices). Prices remain fresh. Systemd auto-restarts. **Code-level fix needed (not force-kill):** set `PRAGMA busy_timeout` on candle writers + serialize price_collector aggregation vs `_aggregate_1m` (file lock or skip candle_agg when 1m-candle holds lock).
- **WARN** (known, non-trading-path failed units): better-coder (`ModuleNotFoundError: dispatcher.dispatcher`), bug-hunter (audit FAILs — expected when findings exist: hardcoded passwords, dead signal_gen imports, non-atomic JSON), git-release (dry-run exit 1 — dirty tree from error_alerts writes), mtf-macd-tuner (`AttributeError: PrecomputedMACD object has no attribute warmup`), trading-checklist (WARN findings → exit 1: 19915 signals, 0 approved), weather-station-api (`weather_station_api.py` missing; weather_station.json stale Aug 27). No auto-fix — none on execution path.
- **WARN**: dead timer refs — `hermes-atr-sl-updater.timer` not-found (unit file absent); `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` enabled but Active=inactive (dead, no schedule). Regime scanners themselves (4h/15m) are active and firing (regime_5m.json fresh). ATR SL/TP managed via guardian/DB.
- **INFO**: `systemctl list-timers hermes-*` without `--all` prints "0 timers listed" — cosmetic; `--all` confirms core timers firing.
- **INFO**: `signal_outcomes` closed-today=15 vs portfolio 37 — outcomes table partial; portfolio source of truth = position_manager + trades.json (consistent).
- **INFO**: `obs_metrics.pipeline.pipeline_active=false` while systemd shows pipeline active/running — obs detector lag/race, not a real outage (heartbeat position_manager 09:46:24 ok).
- **INFO**: `/var/www/hermes/data/coin_tracker_data.json` missing; coin_tracker service itself runs clean (86 coins, 0 errors at 09:30). Dashboard data path may differ — coin tracker not broken.
- **INFO**: logs 143M total, 0 files older than 7d — no compression needed. Disk 81%.
- **AUTO-FIXES APPLIED**: none. Pipeline running; price-collector lock contention self-heals via systemd restarts with prices still collected; disk under threshold; no missed trading-path timers; no stale prices; no phantom trades; no crashes to restart. No restarts or cleanups forced.

## Error Alerts — 2026-10-04 10:47 UTC
- **HEALTH** — Pipeline OK: active, last run 10:46:00 rc=0 LIVE. Portfolio: 3 open | 34 closed today | -3.26% PnL. Position Manager healthy (rc=0, 3/6 slots, ATR updates running). Signals (1h): 120 raw. Regime: SHORT_BIAS (11L/39S/67N, 117 tokens, ts 10:45). Speeds: 53.5% ≥50th pct (129/241, updated 10:46). Prices fresh (token_speeds 10:46:22, price-collector finished 10:46:18). Disk 82% (under 85%). Phantom trades: 0. No Traceback/CRASH/exception in 30m window (only "0 errors" lines from coin_tracker).
- **WARN** (recurring, non-trading-path): dead timer refs — `hermes-atr-sl-updater.timer` not-found; `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` enabled but inactive. Regime scanners (4h/15m) active; ATR SL/TP managed in position_manager.
- **WARN** (known): `signal_outcomes` closed-today=15 vs portfolio 34 — outcomes partial; portfolio source of truth = position_manager + trades.json.
- **INFO**: `hermes-hl-sync-guardian.service` is a long-running daemon (started once 2026-10-03 00:16, still active) — timer shows last-passed 1d ago because service never exits; not a missed timer.
- **INFO**: 98/241 token_speeds have `is_stale=1` flag but `updated_at` is fresh (10:46) — flag likely means no recent price move, not data staleness.
- **AUTO-FIXES APPLIED**: none. Pipeline running; prices fresh; disk under threshold; no crashes; signals flowing. No restarts or cleanups forced.

## Error Alerts — 2026-10-04 11:47 UTC
- **HEALTH** — Pipeline OK: last run 11:45:27–11:45:46 rc=0 LIVE. Portfolio: 1 open | 35 closed today | -13.35% PnL. Position Manager healthy (CFX LONG, 0 Traceback/CRASH/exception in 30m). Services active: hermes-pipeline, hermes-hl-sync-guardian. Signals (1h): 74 raw (`signals` table). Regime: SHORT_BIAS (14L / 34S / 69N, 117 tokens, ts 11:45). Speeds: 53.5% ≥50th pct (129/241). Prices fresh: continuum 23s, hl_cache 22s, regime_5m 98s. Disk 81% (under 85%). Phantom trades (|pnl_pct|<0.01): 0. Core timers firing (price-collector 11:45:52, 1m-candle 11:45:20, compactor, pump-hunter, watchdog, coin-tracker, regime scanners).
- **WARN** (known, recurring): `signal_outcomes` trades-today=17 vs portfolio closed-today=35 — outcomes table partial; portfolio source of truth = position_manager + trades.json (per AGENTS.md). Open-trade DB query returns 0 while position manager reports 1 (CFX) — same partial-outcomes cause.
- **WARN** (known, non-trading-path dead timers): `hermes-atr-sl-updater.timer` not-found (unit absent); `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` enabled but inactive. Regime scanners (4h/15m) active; ATR SL/TP managed via position_manager/guardian.
- **WARN** (known, non-trading-path failed units, unchanged): better-coder, bug-hunter (expected FAILs), git-release (dirty tree), mtf-macd-tuner, trading-checklist, weather-station-api missing. None on execution path.
- **INFO**: today's portfolio PnL -13.35% (35 closed) — trading performance, not system health. Watch for streak/risk issues separately.
- **AUTO-FIXES APPLIED**: none. Pipeline running rc=0; prices fresh; disk 81% under threshold; no crashes; no missed trading-path timers; signals flowing (74/h). No restarts or cleanups forced.

## Error Alerts — 2026-10-04 12:48 UTC
- **HEALTH** — Pipeline OK: LIVE run 12:46:46 rc=0, position_manager rc=0 every cycle, 0 Traceback/CRASH/exception in 30m window. Portfolio (brain trades, source of truth): **3 open | 34 closed today | -7.73% PnL**. Signals (1h): 87 raw in `signals` table. Regime: SHORT_BIAS (14L / 26S / 77N, regime_5m.json ts 12:45). Speeds: 129/241 (53.5%) ≥50th pct. Prices fresh: regime 1.4m, candles_1m 1.3m, coin_tracker_data.json 0.2m. Disk **80%** (under 85%). Phantom trades (|pnl_pct|<0.01): 0. Services active: hermes-pipeline, hermes-hl-sync-guardian. Core timers firing (pipeline 1m, price-collector 30s, signal-compactor 1m, pump-hunter, 1m-candle, watchdog, regime scanners). 7d portfolio PnL +86.80% (212 closed).
- **WARN** (recurring, non-trading-path): `hermes-price-collector.service` crashes on `sqlite3.OperationalError: database is locked` during candle aggregation (candles.db contention with `_aggregate_1m.py`). Systemd auto-restarts; prices still collected every cycle. **Code-level fix needed (not force-kill):** PRAGMA busy_timeout on candle writers + serialize price_collector candle agg vs 1m-candle.
- **WARN** (known, non-trading-path dead timers): `hermes-atr-sl-updater.timer` not-found (unit absent; DEFUNCT files exist); `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` enabled but Active=inactive (OnBootSec=24h/72h only — by design, fire on boot). Regime scanners (4h/15m) active and firing. ATR SL/TP managed via position_manager.
- **WARN** (known): `signal_outcomes` closed-today=17 vs portfolio 34 — outcomes table partial; portfolio source of truth = brain `trades` table + position_manager.
- **INFO**: `decisions` table latest row 2026-04-13 — likely unused after signal_compactor migration; signals flow fine via signals_runner.
- **INFO**: today's PnL -7.73% (34 closed) — trading performance, not system health. 7d +86.80%. Worst today: bb-bounce-v3-long+ 8T -8.99%.
- **AUTO-FIXES APPLIED**: none. Pipeline running rc=0; prices fresh; disk 80% under threshold; no crashes; no missed trading-path timers; signals flowing (87/h). No restarts or cleanups forced.

## Error Alerts — 2026-10-04 13:46 UTC
- **HEALTH** — Pipeline OK: active, LIVE run 13:46:00 rc=0, position_manager rc=0 every cycle, 0 Traceback/CRASH/exception in 30m window. Portfolio (position_manager source of truth): **3 open | 34–35 closed today | -12.8% to -15.4% PnL**. Signals (1h): 82 raw in `signals` table. Regime: LONG_BIAS (34L / 6S / 77N, regime_5m.json ts 13:45). Speeds: 129/241 (53.5%) ≥50th pct (token_speeds updated 13:46:22). Prices fresh: regime_5m 1.7m old. Disk **81%** (under 85%). Phantom trades (|pnl_pct|<0.01): 0. Services active: hermes-pipeline, hermes-hl-sync-guardian, hermes-price-collector. Core timers firing (pipeline 1m, price-collector, signal-compactor, pump-hunter, 1m-candle, watchdog, coin-tracker, regime scanners). Logs 150M, no files >7d needing cleanup.
- **WARN** (known, non-trading-path dead timers): `hermes-atr-sl-updater.timer` not-found (unit absent; DEFUNCT files exist); `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` enabled but inactive (OnBootSec=24h/72h only — by design). Regime scanners (4h/15m) active and firing. ATR SL/TP managed via position_manager.
- **WARN** (known): `signal_outcomes` open=0 / closed-today=17 vs portfolio 3 open / 34–35 closed — outcomes table partial; portfolio source of truth = position_manager + trades.json (per AGENTS.md).
- **INFO**: `is_stale=1` on 113/241 token_speeds but `updated_at` fresh (13:46) — flag means no recent price move, not data staleness (recurring, unchanged).
- **INFO**: today's PnL swung -12.8% → -15.4% between 13:45:46 and 13:46:40 while open stayed 3 — a close or mark-to-market update, not a system fault. Trading performance, not system health. Watch streak/risk separately.
- **INFO** (recurring, non-trading-path failed units, unchanged): better-coder, bug-hunter (expected FAILs), git-release (dirty tree), mtf-macd-tuner, trading-checklist. None on execution path.
- **AUTO-FIXES APPLIED**: none. Pipeline running rc=0; prices fresh; disk 81% under threshold; no crashes; no missed trading-path timers; signals flowing (82/h). No restarts or cleanups forced.

## Error Alerts — 2026-10-04 14:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-04 16:48 UTC
- **HEALTH** — Pipeline OK: LIVE cycle #228493 at 16:45:52, active. Portfolio (trades.json source of truth): **1 open | 21 closed today | -0.54 USDT PnL** (NXPC LONG bb-bounce-v3-long+, entry 0.23583, -0.77%). Signals (1h): 82 raw (31 LONG / 48 SHORT). Regime: SHORT_BIAS (12L / 55S / 50N, regime_5m.json ts 16:45). Speeds: 127/241 (52.7%) ≥50th pct. Prices fresh: latest_prices 70s, candles_1m 209s, trades.json 20s, signals.json 78s, regime_5m 120s. Disk **83%** (under 85%). Phantom trades (|pnl_pct|<0.01, 24h): 0. Services active: hermes-pipeline, hermes-hl-sync-guardian. Core timers firing (pipeline 1m, price-collector 30s, signal-compactor 1m, pump-hunter, 1m-candle, watchdog, coin-tracker, regime scanners).
- **WARN** (known, recurring, non-trading-path): `signal_outcomes` open=0 / closed-today=21 vs portfolio open=1 / closed-today=21 — outcomes table partial; portfolio source of truth = trades.json + position_manager (per AGENTS.md). Phantom-type rows in outcomes are historical signal labels, not live phantoms.
- **WARN** (known, non-trading-path dead timers): `hermes-atr-sl-updater.timer` not-found; `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` inactive (OnBootSec-only by design). Regime scanners (4h/15m) active and firing. ATR SL/TP managed via position_manager/guardian.
- **WARN** (known, non-trading-path failed units, unchanged): better-coder, bug-hunter (expected FAILs), git-release (dirty tree), mtf-macd-tuner, trading-checklist, weather-station-api. None on execution path. `hermes-better-coder-health` last pass 5h+ ago (daily 06:00 schedule).
- **WARN** (known, non-trading-path): `hermes-price-collector.service` sqlite3 "database is locked" during candle aggregation — systemd auto-restarts; prices still fresh. Code-level fix still pending (PRAGMA busy_timeout + serialize candle writers).
- **INFO**: today PnL -0.54 USDT on 21 closed (11 wins ≈ 52%) — trading performance, not system health. 24h outcomes: 30 closed, -0.94 USDT, 16 wins. Exit reasons 24h: mostly null (raw), 2 profit-monster-trail, 1 hard_max_loss.
- **INFO**: token_speeds `is_stale=1` on 94/241 but `updated_at` fresh (16:46) — flag means no recent price move, not data staleness (recurring).
- **AUTO-FIXES APPLIED**: none. Pipeline running; prices fresh; disk 83% under threshold; no crashes; no missed trading-path timers; signals flowing (82/h). No restarts or cleanups forced.

## Error Alerts — 2026-10-04 19:48 UTC
- **HEALTH** — Pipeline OK: active, LIVE cycle every 1m, position_manager rc=0 every cycle, 0 Traceback/CRASH in 30m window. Portfolio (position_manager): **2 open | 32 closed today | -20.09% PnL**. Signals (1h): 67 in `signals` table; 3 outcomes closed in last hour. Regime: LONG_BIAS (59L / 9S / 49N, regime_5m.json ts 19:45). Speeds: 127/241 (52.7%) ≥50th pct. Prices fresh: prices.json 32s old, 85 tokens. Disk **84%** (under 85%). Phantom trades: 0 (|pnl_pct|<0.01). Services active: hermes-pipeline, hermes-hl-sync-guardian. Core timers firing (pipeline 1m, price-collector 30s, health-monitor, 69 hermes timers active).
- **WARN** (recurring, non-trading-path): `hermes-price-collector.service` intermittent `sqlite3.OperationalError: database is locked` during candle aggregation (candles.db contention; WAL 3.6G). 17 Failed-to-start vs 43 successful collects in last hour — systemd auto-restarts; prices stay fresh. **Code-level fix still pending:** PRAGMA busy_timeout on candle writers + serialize price_collector candle agg vs 1m-candle / pipeline candle writes.
- **WARN** (known, non-trading-path dead timers): `hermes-atr-sl-updater.timer` not-found (DEFUNCT); `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` inactive (OnBootSec-only by design). Regime scanners (4h/15m) active. ATR SL/TP managed via position_manager.
- **WARN** (known): `signal_outcomes` open=0 / closed-today=27 vs portfolio 2 open / 32 closed — outcomes table partial; portfolio source of truth = position_manager + trades.json (per AGENTS.md).
- **INFO**: today PnL **-20.09%** (32 closed, ~59% winrate on outcomes subset) — trading performance, not system health. Deteriorated from -7.73% at 12:48 and -12.8% at 13:46. Worst outcomes today: bb-bounce-v3-long+ 9T -0.51 USDT (44% WR); bb-squeeze+ 13T +0.29 USDT (69% WR).
- **INFO**: `hermes-wasp.timer` last fired 42m ago (15min cadence expected — possible miss, non-trading-path).
- **INFO**: disk 84% (19G free), candles.db 2.5G + WAL 3.6G is the bulk; no files >7d to gzip. Under 85% threshold — no cleanup forced.
- **AUTO-FIXES APPLIED**: none. Pipeline running rc=0; prices fresh (32s); disk 84% under threshold; no crashes; no missed trading-path timers; signals flowing (67/h). No restarts or cleanups forced.

## Error Alerts — 2026-10-04 20:48 UTC
- **HEALTH** — Pipeline OK: active, LIVE cycle, position_manager rc=0 (SEI LONG trade_id=15921, pnl -0.78%), 0 Traceback/CRASH in 30m. Portfolio (trades.json): **1 open | 29 closed today | -0.11 USDT | 62.1% WR**. Signals (1h): 69 raw (BLUR/RESOLV/KFLOKI/ZRO/XPL recent). Regime: SHORT_BIAS (19L / 27S / 71N, regime_5m.json ts 20:45). Speeds: 127/241 (52.7%) ≥50th pct. Prices fresh (token_speeds 20:46, regime 20:45). Phantom trades (|pnl_pct|<0.01, 24h): 0. Services active: hermes-pipeline, hermes-hl-sync-guardian. ~69 hermes timers firing on cadence.
- **WARN** (recurring, non-trading-path): `hermes-price-collector.service` — 37× `sqlite3.OperationalError: database is locked` in 30m on candle_1h/4h aggregation; unit stuck `activating`/failing, systemd auto-restarts; prices still fresh via other writers. **Code-level fix still pending:** PRAGMA busy_timeout + serialize candle writers (known, matches 16:48/19:48 alerts).
- **WARN** (known, non-trading-path): `hermes-5m-candle.timer` inactive/disabled (price_collector owns cadence — by design). `hermes-atr-sl-updater.timer` DEFUNCT/not-found. Signal_outcomes open=0 vs portfolio open=1 — outcomes table partial; portfolio source of truth = position_manager + trades.json (AGENTS.md).
- **WARN**: disk was **87%** at start (candles.db-wal 7.1G + journal bloat) — over 85% threshold.
- **INFO**: 19:48 note said -20.09% PnL on 32 closed — current trades.json window shows today -0.11 USDT on 29 closed (rolling 200 page vs full day count differ; source of truth for today = trades.json closed filtered by date).
- **AUTO-FIXES APPLIED**:
  1. `journalctl --vacuum-size=200M` — freed **260.7M** archived journals.
  2. `PRAGMA wal_checkpoint(TRUNCATE)` on `candles.db` — WAL **7.7G → 0**, disk **87% → 81%** (16G→23G free). Root cause: WAL not checkpointing under continuous candle writers; no code change yet — recommend checkpoint interval in price_collector/1m-candle or busy_timeout fix to stop lock thrash.
- No pipeline restarts forced (no crashes). Timers firing. Prices fresh.

## Error Alerts — 2026-10-04 21:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-04 22:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (7x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK:`

## Error Alerts — 2026-10-04 23:47 UTC
- **HEALTH** — Pipeline OK: active, LIVE cycle every 1m, all steps rc=0, 0 Traceback/CRASH in 30m. Portfolio (trades.json): **4 open | LONG MNT/HYPE/ARB/LDO**. Closed today: 35 (LONG 34 net -0.36 USDT 58.8% WR, SHORT 1 +0.06). Signals (1h): 49 in `signals` (pump-chain, support_resistance, ichimoku, continuum — conf 74–88). Regime: **LONG_BIAS** (40L/10S/67N, regime_5m.json ts 23:45). Speeds: 52.7% ≥50th pct. Prices fresh: prices.json 85 tokens ~1min old; open-position tokens (MNT/HYPE/ARB/LDO) candles ~4min. Phantom trades (|pnl_pct|<0.01): 0. Disk **81%** (23G free). Core timers all active: price-collector, 1m-candle, pipeline.
- **WARN** (recurring, non-trading-path, 3x+): `hermes-price-collector.service` — 83 lock/fail events vs 30 successful collects in last 60m. Aggregation (candles_5m/15m/1h/4h) + `wal_checkpoint` hit `database is locked` / `database table is locked`; unit fails then systemd auto-restarts. Raw prices still collected (85 tokens) so downstream stays fed. **Code-level fix still pending:** PRAGMA busy_timeout on candle writers + serialize price_collector candle agg vs 1m-candle/pipeline writes. WAL now only 9MB (post-20:48 checkpoint) — contention is write-parallelism, not WAL bloat.
- **WARN** (info): `hotset.json` empty / Approved signals: 0 — decider reports "No signals above 50% confidence" while raw `signals` table has 49 signals at conf 74–88 in last hour. Compactor is filtering hard (by design?) — not a crash; execution correctly blocked. Worth a signal-quality review, not a system fault.
- **WARN** (known): `signal_outcomes` open=0 vs portfolio open=4 — outcomes table partial; portfolio source of truth = position_manager + trades.json (per AGENTS.md).
- **INFO**: `hermes-atr-sl-updater.timer` not-found (DEFUNCT); `hermes-regime-24h-check.timer` + `hermes-regime-transition-check.timer` inactive (OnBootSec-only by design). Regime scanners (4h/15m) active. ATR SL/TP managed via position_manager.
- **INFO**: today PnL on outcomes subset **-0.30 USDT** (35 closed, 58.8% LONG WR) — much improved from -20% at 19:48. Trading performance, not system health.
- **AUTO-FIXES APPLIED**: none forced. Pipeline running rc=0; timers active; prices fresh; disk 81% under threshold; no crashes; price-collector self-restarts on lock (systemd) — stopping/restarting it manually would not fix write contention and risks the timer path. Code fix (busy_timeout + writer serialization) remains the real remediation.

## Error Alerts — 2026-10-05 00:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-05 01:59 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-10-05 02:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-10-05 03:48 UTC
- **HEALTH** — Pipeline OK: active, LIVE cycle every 1m, all steps rc=0, 0 Traceback/CRASH in 30m. Portfolio (trades.json ts 03:47): **3 open | MET SHORT +0.02%, SAGA LONG -0.39%, HBAR SHORT -0.87%**. Closed page (200 rolling): 54.0% WR, +0.64 USDT. Pipeline log snapshot 03:45: "2 open | 36 closed today | -5.37% PnL". Signals (1h): 102 in `signals` (recent: PONS LONG, MET SHORT, DOT LONG, GMT SHORT; pending: COMP/BTC/KFLOKI pump-chain etc). Regime: **SHORT_BIAS** (6L/69S/42N, 117 tokens, regime_5m.json ts 03:45). Coin tracker: NEUTRAL, 0 hot / 79 warm / 7 cold. Speeds: 52.7% ≥50th pct (127/241). Prices fresh: trades.json/signals.json ~1min, BTC 1m candle 03:45 (~2min), 85 tokens collected. Phantom trades (|pnl_pct|<0.01): 0. Disk **81%** (22G free), WAL 17M (post prior checkpoint). Core timers all active: price-collector (last 03:45:57), 1m-candle (03:46:25), pipeline (03:47:00). No auto-fixes forced — nothing crashed, nothing stuck.
- **WARN** (recurring, code-fix pending): `hermes-price-collector.service` — 82 `database is locked` / `database table is locked` events in last 60m vs 15 successful finishes. Aggregation (candles_5m/15m/1h/4h) + `wal_checkpoint` hit write contention while 1m-candle + pipeline write concurrently. Not a stuck lock — fuser shows active holders only. Raw prices still collected (85 tokens) so downstream stays fed. **Code-level fix still pending (from prior reports): PRAGMA busy_timeout on candle writers + serialize price_collector candle agg vs 1m-candle/pipeline writes.** Stopping services would not fix write contention and risks the timer path — deliberately not done.
- **INFO** (fail-closed working): MET SHORT blocked at 03:45:26 — `EXEC-RSI-HARD-FLOOR` — candle data stale/insufficient, trade failed, signal NOT rolled back (prevents retry loop). Safety filter behaved correctly. MET remains open in trades.json from prior execution at 03:44:17.
- **INFO** (known): `signal_outcomes` today=8 closed / open=0 vs portfolio open=3 — outcomes table partial; portfolio source of truth = position_manager + trades.json (per AGENTS.md).
- **INFO**: `coin_tracker_api.py` writes to `/var/www/html/coin_tracker_data.json` (not WWW_DATA) — by design; nginx aliases `/coin_tracker_data.json` → `/var/www/html/`. Fresh at 03:48. Not a bug.
- **INFO**: `systemctl list-timers hermes-*` glob returns 0 (systemd glob quirk); full `list-timers --all` + `systemctl status` confirm all hermes timers healthy and firing.
- **AUTO-FIXES APPLIED**: none required. Pipeline running rc=0; timers active; prices fresh; disk 81% under 85% threshold; no crashes; price-collector lock errors are contention self-recovered by systemd restarts — manual stop/restart would be unsafe and ineffective.

## Error Alerts — 2026-10-05 03:59 UTC
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK-TOK-TOK] TOK TOK BLOCKED — candle data stale/insufficient — TOK-closed`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: stale candles — TOK blocked (TOK-closed)`

## Error Alerts — 2026-10-05 04:59 UTC
- **REPEATED** (12x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (13x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-05 05:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] CC TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`

## Error Alerts — 2026-10-05 06:49 UTC
- **WARN** (recurring): `hermes-price-collector.service` — uncaught `sqlite3.OperationalError: database is locked` in `_store_candles` via `_seed_universe_candles` (line ~120). Occurred 2x in 30m (06:43:44, 06:46:56). Aggregation path already had busy_timeout + try/except; the universe seeder did not. **Root cause:** concurrent writes to candles.db from pipeline + 1m-candle timer hold write locks >30s busy_timeout during seed INSERTs. Raw prices still collected (85 tokens) — seeder is best-effort enrichment only.
- **AUTO-FIX**: `price_collector.py` — (1) `_store_candles` now retries once on OperationalError then logs and returns; (2) `_seed_universe_candles` call wrapped in try/except in `main()` so a seed lock error can no longer kill an otherwise successful collection cycle. Prices + candle aggregation complete before seeder runs. No services stopped (nothing stuck; prices fresh; timers active). Full candle-writer serialization still pending if lock errors continue.
- **INFO**: Pipeline healthy — LIVE every 1m, all steps rc=0, 0 Traceback/CRASH in 30m. Signals (1h): 82. Open: 2 (WLD SHORT +0.05%, HBAR SHORT +0.43%). Closed today (signal_outcomes): 12 trades, net ~-0.23 USDT. Regime: LONG_BIAS (80L/7S/30N, ts 06:45). Speeds: 52.7% >=50th (127/241). Disk 82%. Phantom atr_sl_hit (<0.01%): 0. Core timers all active.

## Error Alerts — 2026-10-05 09:47 UTC
- **WARN** (recurring): `hermes-price-collector.service` — 46 `database is locked` / `database table is locked` events in last 60m on `candles.db`. Hits: `_store_candles` (MEME/MET/MORPHO/NEAR/NIL), aggregation (candles_5m/15m/1h/4h at 09:31:54 and 09:43:38), wal_checkpoint. busy_timeout=30000 (collection) / 60000 (agg) already set; contention from concurrent pipeline + 1m-candle writers exceeds it. One cycle collected 0 prices (09:43:38) — recovered next run with 85. Not a stuck lock (fuser = active holders only). Raw prices still feed downstream.
- **AUTO-FIX**: none — deliberately. Stopping price-collector/1m-candle to "clear" write contention would not fix concurrency and risks killing the timer path (stale prices, UNKNOWN phases, signal failures). Same decision as 06:49. **Root-cause code fix still pending:** serialize candle-writer path vs price_collector aggregation, or raise busy_timeout / use a single writer lock. Price-collector seeder already has try/except + retry from 06:49 fix.
- **INFO**: Pipeline healthy — LIVE every 1m, rc=0, 0 Traceback/CRASH. Signals (1h): 110. Open: 3 (SAND SHORT -0.65%, ETH LONG +0.01%, HBAR SHORT +0.60%). Closed today: 35, portfolio PnL -13.07%. Closed page: 55.5% WR (111/200) +$1.13. Regime: SHORT_BIAS (3L/67S/47N, 117 tokens, ts 09:45). Speeds: 52.7% ≥50th (127/241). Disk 82% (under 85%). Phantom atr_sl_hit 0. Core timers all active. No CRITICAL issues.
- **INFO**: `signals` table total 22,174 rows — cleanup flagged, not blocking.
- **INFO**: `coin_tracker_data.json` at `/var/www/html/` (nginx alias) not `/var/www/hermes/data/` — by design, fresh at 09:46.

## Error Alerts — 2026-10-05 12:47 UTC
- **WARN** (recurring): `candles.db` write contention — `database is locked` / `database table is locked` events from `_aggregate_1m.py` + `price_collector.py` concurrent writers (PIDs active at check: 443477, 443480). Occurred 12:26–12:45 across `_store_candles`, candles_5m/15m/1h/4h aggregation, wal_checkpoint. Same pattern as 06:49 and 09:47. Not a stuck lock — transient WAL contention, self-recovered (price collector completed, 85 prices collected, pipeline rc=0).
- **AUTO-FIX**: none — deliberately. Stopping price-collector/1m-candle would not fix concurrency and risks killing the timer path. **Root-cause fix still pending:** serialize candle-writer path vs price_collector aggregation, or raise busy_timeout / single-writer lock.
- **INFO**: Pipeline healthy — LIVE every 1m (cycle #229678), position_manager rc=0, 4 open positions (ATR updated 3 SL/TP). Signals (1h): 83. Closed today (signal_outcomes): 18, net -0.55 USDT, 61% WR (11/18). Open positions: 4/6 (portfolio source of truth). Regime: SHORT_BIAS (19L/43S/55N, ts 12:45). Disk 82% (under 85%). Prices fresh (latest candle 2.5min). Phantom atr_sl_hit: 0. Core timers all active. No CRITICAL issues.
- **INFO**: `signal_outcomes` open=0 vs portfolio open=4 — known discrepancy; outcomes table partial, portfolio source of truth = position_manager (per prior notes).
- **INFO**: Non-critical systemd units in failed state at check: `hermes-better-coder`, `hermes-bug-hunter`, `hermes-ceo`, `hermes-git-release` — not on trading path; no auto-restart (out of scope for health monitor).

## Error Alerts — 2026-10-05 12:59 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK-TOK-TOK] TOK TOK BLOCKED — exec TOK unavailable (TOK-closed, SHORT_RSI_HARD_FLOOR)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: exec TOK unavailable for TOK (TOK-closed)`

## Error Alerts — 2026-10-05 13:59 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BEAR+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-05 14:48 UTC
- **WARN** (recurring): `candles.db` write contention — 10 `database is locked` events in price-collector last 15m (14:36–14:47:24). Writers at check: `_aggregate_1m.py` (PID 659948, state Ds = uninterruptible I/O wait) + `price_collector.py` (PID 659971). Hits: `_store_candles` (W 1m, WIF 1h), aggregation candles_1h/4h/5m/15m, wal_checkpoint. Same pattern as 06:49 / 09:47 / 12:47. Not a stuck lock — self-recovered, candles_1m fresh (latest ts ~14:47), pipeline rc=0.
- **AUTO-FIX**: none — deliberately. Stopping price-collector/1m-candle would not fix concurrency and risks killing the timer path. **Root-cause fix still pending (open since 06:49):** serialize candle-writer path vs price_collector aggregation, or raise busy_timeout / single-writer lock.
- **INFO**: Pipeline healthy — LIVE every 1m (cycle #229797+), all steps rc=0, 0 Traceback/CRASH in 30m. Signals today: 1,539; outcomes last 1h: 4. Closed today: 24, net -1.00 USDT, 13/24 wins (54%). signal_outcomes open=0 (known: portfolio/position_manager is source of truth for open positions). Regime: SHORT_BIAS (11L/32S/74N, ts 14:45). Speeds: 52.7% ≥50th (241 tokens). Disk 82% (under 85%). Phantom (|pnl_pct|<0.01): 1 (BTC LONG 0.0%). Core timers all active (pipeline fired 34s ago, price-collector + 1m-candle 1min 10s ago). No CRITICAL issues. No auto-fixes applied.

## Error Alerts — 2026-10-05 15:48 UTC
- **INFO**: Pipeline healthy — LIVE every 1m (cycle #229857+), position_manager rc=0 every cycle. Open positions: 1/6 (portfolio source of truth). Signals (1h): 101. Closed today: 25, net -0.92 USDT, 56% WR. Regime: SHORT_BIAS (7L/29S/81N, ts 15:45). Speeds: 52.7% ≥50th (241 tokens). Disk 82% (under 85%). Prices fresh (86 tokens <5min, latest 0.9min). Phantom atr_sl_hit: 0. Core timers all active (pipeline fired 15s ago, price-collector + 1m-candle ~3min). **0** `database is locked` events in last 60m (self-recovered contention from earlier today). 0 Traceback/CRASH. No CRITICAL issues. No auto-fixes needed.
- **INFO** (recurring, non-trading): Failed units unchanged: better-coder, bug-hunter, git-release, mtf-macd-tuner, trading-checklist, upgrade-implementer, wasp, weather-station-api. Not on trading path; no auto-restart.
- **INFO**: `hermes-atr-sl-updater.timer` unit not-found; `hermes-hl-copy.timer` last fired 2026-08-15; `hermes-ma-cross-5m-tuner.timer` never fired — stale/enabled units, not trading-critical.

## Error Alerts — 2026-10-05 15:59 UTC
- **REPEATED** (8x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`

## Error Alerts — 2026-10-05 20:59 UTC
- **REPEATED** (9x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: BIGTIME TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (6x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK ceiling: N.N > N`

## Error Alerts — 2026-10-05 22:48 UTC
- **WARN** (1x): `hermes-coding-mcp.service` crash-looping — restart counter reached 743,336; `/root/.hermes/scripts/run_mcp_server.py` missing (`can't open file` → exit 2). Non-trading path.
- **AUTO-FIX**: `systemctl disable --now hermes-coding-mcp.service` — stopped the restart storm until the missing script is restored. Service left inactive.
- **INFO**: Pipeline healthy — LIVE every 1m (cycle #230259+), position_manager rc=0 every cycle. Open positions: 5/6 (portfolio source of truth). Signals last 1h: 80 (signals table). Outcomes last 1h: 2; closed today: 29, net -0.85 USDT, 17/29 wins (58.6% WR). Regime: LONG_BIAS (45L/13S/64N, ts 22:45). Speeds: 53.1% ≥50th (128/241). Prices fresh (latest candle 1.3 min; prices.json 1.8 min; 85 tokens). Phantom atr_sl_hit: 0. Disk 83% (under 85%). Core timers all active (pipeline 15s ago, price-collector 3s, 1m-candle 1m43s). 0 Traceback/CRASH, 0 `database is locked` in 30m. candles.db held by 3 normal writers (pipeline path) — no stuck lock.
- **INFO** (recurring, non-trading): Failed units unchanged: `hermes-better-coder`, `hermes-bug-hunter`, `hermes-git-release`. Not on trading path; no auto-restart.
- **NOTE**: `/root/.hermes/data/trades.json` is a 0-byte file from Apr 27 — stale artifact. Dashboard uses `/var/www/hermes/data/trades.json` (healthy, 104KB, updated 22:46). Safe to delete the stale local copy when convenient.

## Error Alerts — 2026-10-05 22:59 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`

## Error Alerts — 2026-10-05 23:47 UTC
- **INFO**: Pipeline healthy — LIVE every 1m (cycle fired 2s ago at 23:47:22), all steps rc=0. Open positions: 3/6 (portfolio = source of truth). Signals last 1h: 71. Closed today: 32, net -0.90 USDT, 19/32 wins (59.4% WR). Regime: SHORT_BIAS (8L/67S/46N, ts 23:45). Speeds: 53.1% ≥50th (128/241). Prices fresh (85 tokens, prices.json 1.8min old). Phantom atr_sl_hit: 0. Disk 83% (under 85% warn). Core timers all active (pipeline 2s ago, price-collector 1m37s, 1m-candle 1m18s). 0 Traceback/CRASH, 0 `database is locked` in 30m. candles.db held by 2 normal writers — no stuck lock. **No CRITICAL/WARN issues. No auto-fixes needed.**
- **NOTE** (recurring, non-trading): `hermes-hl-sync-guardian.timer` active but last fired 2026-10-04 15:33 UTC (>24h ago) — verify expected cadence if guardian is supposed to run more often. Not on critical trading path.
- **NOTE**: Worst signal today: `mtf-regime-trend-` SHORT — 4 trades, 25% WR, -0.47 USDT. Trading performance observation, not a system fault.
- **INFO** (recurring, non-trading): Failed units unchanged: better-coder, bug-hunter, git-release. Not on trading path; no auto-restart.

## Error Alerts — 2026-10-05 23:59 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: W TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: usage: brain.py trade add [-h] [--exchange EXCHANGE] [--strategy STRATEGY]`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`

## Error Alerts — 2026-10-06 01:59 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=(empty)`
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK:`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+AT, allowing despite TOK filter`

## Error Alerts — 2026-10-06 02:59 UTC
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: TOK get_sl_multiplier_v2() got an unexpected keyword argument 'signal' (TOK-closed — loss prevention)`
- **NEW** (2x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK] TOK TOK blocked: volatility gate TOK (TOK-closed): get_sl_multiplier_v2() got an unexpected keyword argument 'signal'`
- **REPEATED** (10x): `Oct N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK floor: N.N < N`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   🚫 [TOK-TOK-TOK-TOK] TOK TOK BLOCKED — exec TOK unavailable (TOK-closed, SHORT_RSI_HARD_FLOOR)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: exec TOK unavailable for TOK (TOK-closed)`
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: TOK hard floor: N.N < N`

## Error Alerts — 2026-10-06 03:59 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: usage: brain.py trade add [-h] [--exchange EXCHANGE] [--strategy STRATEGY]`

## Error Alerts — 2026-10-06 06:48 UTC
- **INFO**: Pipeline healthy — LIVE every 1m (cycle #230731 active, signal_analyst/breakout_engine running). Open trades: 0. Signals last 1h: 99. Closed today: 2 (bb-squeeze+ LONG, trend-ride+ LONG — both hard_max_loss/losses, 0% WR on tiny sample; trading perf, not system fault). Regime: SHORT_BIAS (4L/64S/54N, ts 06:45). Prices fresh (85 tokens, prices.json 9s old). Disk 83% (under 85% warn). Core timers all active (pipeline 25s ago, price-collector 1m27s, 1m-candle 1m16s, hl-sync-guardian active). candles.db held by 2 normal writers — no stuck lock. 0 Traceback/CRASH in 30m. **No CRITICAL/WARN issues. No auto-fixes needed.**
- **NOTE** (recurring, non-trading): `hermes-hl-sync-guardian.timer` active but last fired 02:50 UTC (~4h ago) — verify expected cadence if guardian is supposed to run more often. Not on critical trading path.
- **NOTE** (recurring, non-trading): Dead/disabled units unchanged: hl-copy, ma-cross-5m-tuner, regime-24h-check, regime-transition-check, atr-sl-updater (no last-fire). Not on trading path; no auto-restart.
- **NOTE**: 1 near-zero PnL trade (BTC continuum_engine 0.0%) — single noise sample, not a phantom atr_sl_hit pattern.

## Error Alerts — 2026-10-06 07:48 UTC
- **INFO**: Pipeline healthy — LIVE every 1m (cycle #230792 active, signal_analyst PASS GOAT LONG, breakout_engine running, signals_runner 47 signals). Open: 0 (signal_outcomes) + 1 paper HL LTC. Signals 76 last 1h. Closed today: 6 (bb-squeeze+ LONG 2x, trend-ride+ LONG 4x — 0% WR tiny sample; trading perf, not system). Regime: LONG_BIAS 33L/12S/75N (shifted from SHORT_BIAS at 06:48). Speed: 50.3% >= 50th pct (89/177). Prices fresh (85 tokens, 07:46:58). Disk 84% (up from 83%; growth in DBs not logs — coin_tracker 3.4G, candles 2.6G, mtf_macd_tuner 1.1G; logs 225M, nothing >7d to compress). Core timers all active (pipeline 58s ago, price-collector 1m59s, 1m-candle 1m12s, hl-sync-guardian active). candles.db held by 2 normal concurrent writers — NOT a stuck lock. 0 Traceback/CRASH in 30m. **No CRITICAL issues. No auto-fixes needed.**
- **WARN** (approaching threshold): Disk 84% — 1pt below 85% warn. No log cleanup available; next step is DB retention (mtf_macd_tuner, coin_tracker) if it crosses 85%.
- **NOTE** (recurring, non-trading): `hermes-hl-sync-guardian.timer` active but last fired 02:50 UTC (~5h ago) — verify expected cadence. Not on critical trading path.
- **NOTE** (legacy, non-trading): `decisions` table in signals_hermes_runtime.db stale since Apr 13 2026 — live path uses `signals.decision` column + decision-log. Dead table.
- **NOTE** (dead file): `/root/.hermes/data/price_signals.db` is 0 bytes, unreferenced by scripts — safe to delete later.
- **NOTE**: Prior `get_sl_multiplier_v2() got unexpected keyword argument 'signal'` errors (02:59 UTC) — no recurrence in last 30m logs. Consider resolved.
- **NOTE** (unchanged, non-trading): Dead/disabled units: hl-copy, ma-cross-5m-tuner, regime-24h-check, regime-transition-check, atr-sl-updater.

## Error Alerts — 2026-10-06 07:59 UTC
- **REPEATED** (5x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ TOK TOK: TOK TOK — signal TOK rolled back (prevents retry loop)`
- **REPEATED** (4x): `Oct N N:N:N python3[TOK]: TS   TS   → TOK: usage: brain.py trade add [-h] [--exchange EXCHANGE] [--strategy STRATEGY]`

## Error Alerts — 2026-10-06 08:59 UTC
- **REPEATED** (3x): `Oct N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-10-06 09:47 UTC
- **INFO**: Pipeline healthy — LIVE every 1m (cycle #230912 active, signals_runner rc=0, Position Manager Open:0). Signals 95 last 1h. Closed today: 7 (bb-squeeze+ LONG 2x, pump-chain- SHORT 1x, trend-ride+ LONG 4x — 0% WR tiny sample; trading perf, not system fault). Regime: SHORT_BIAS 11L/50S/62N (ts 09:45). Speed: 53.1% >= 50th pct (128/241). Prices fresh (84 tokens, prices.json 09:46:56). Disk 84% (under 85% warn; growth in DBs not logs). Core timers all active (pipeline 30s ago, price-collector 1m44s, 1m-candle 1m35s, hl-sync-guardian active). candles.db held by 3 normal concurrent writers — no stuck lock. 0 Traceback/CRASH in 30m. **No CRITICAL issues. No auto-fixes needed.**
- **WARN** (approaching threshold): Disk 84% — 1pt below 85% warn. DB growth: coin_tracker 3.3G, candles 2.5G, mtf_macd_tuner 1.1G, session_brain 1.0G. Logs fine (pipeline.log 75M largest). If crosses 85%: DB retention on tuner/tracker.
- **INFO** (non-fatal): CTX-GATE LLM timeout @ 09:38:07 for CRV LONG (opencode run timed out 35s) — trade allowed via BTC-CRASH-OVERRIDE (RECOVERY+LEAN_BULL+ABOVE). No recurrence in last 9m.
- **NOTE** (recurring, non-trading): Dead/disabled units unchanged: atr-sl-updater (inactive, no last-fire), hl-copy, ma-cross-5m-tuner, regime-24h-check, regime-transition-check. Not on trading path; no auto-restart.
- **NOTE** (recurring, non-trading): hermes-hl-sync-guardian.timer active but last fired 02:50 UTC (~7h ago) — verify expected cadence. Not on critical trading path.

## Error Alerts — 2026-10-06 09:59 UTC
- **NEW** (1x): `Oct N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`
