## Error Alerts — 2026-08-12 16:39 UTC
- **[WARN]** (1x): `trades.json is 0 bytes` — pipeline reports 6 open trades in journal, but trades.json is empty. Write failure or truncation. Needs investigation.
- **[WARN]** (1x): `signals_runner [SLOW]: ~5min per cycle` — not a crash but signals_runner consistently slow.

---

## Error Alerts — 2026-08-12 17:40 UTC
- **[WARN]** (Nx): `coin_tracker` intermittent errors — `_read_candles` not defined, `no such table: agg_scores`, `no such table: _coin_registry`, NoneType. Most runs succeed (888/892), but sporadic failures. Root cause: missing tables/functions hit during certain processing branches.
- **[WARN]** (Nx): `coin_tracker` 891 errors in 2 consecutive runs (17:26, 17:34) — only 1 coin processed, 891 errors. Likely a DB connection issue causing cascading failures. Self-recovered.
- **[INFO]** (5 services): `hermes-bug-hunter`, `hermes-hl-volume`, `hermes-mtf-macd-tuner`, `hermes-trading-checklist`, `hermes-upgrade-implementer` — all in `failed` state. Non-critical services; timers still fire them but they fail immediately.
- **[INFO]** (1x): `prices_hermes.db` is 0 bytes — empty. Prices now served via JSON/API, not local SQLite. Not an issue.
- **[INFO]** (1x): `brain.db` is 0 bytes at both `/root/.hermes/brain.db` and `/root/.hermes/data/brain.db`. Trade data lives in `signals_hermes_runtime.db` now. Not an issue.
- **[INFO]** (1x): `hermes-hl-volume.timer` — LAST passed 27min ago (should fire more often). Service is failed so timer is stuck.
- **[INFO]**: Pipeline at 6/6 max positions — 2 signals approved but skipped (MERL SHORT conf=99, etc). Positions need to close before new entries.

---

## Error Alerts — 2026-08-09 18:40 UTC
- **[WARN]** (1x): `[PHANTOM-DBG] ASTER LONG: TIGHT SL DETECTED sl=0.602210 entry=0.602220 dist=0.002%` — SL distance too tight, phantom trade risk. Needs param review.
- **[WARN]** (1x): `hermes-hl-volume: 429 rate limit` — Hyperliquid API rate limited, transient. Will recover.
- **[WARN]** (1x): `hermes-git-release: status=1/FAILURE` — Backup failing for 2+ hours. Needs investigation.

## Error Alerts — 2026-08-09 20:40 UTC
- **[CRITICAL]** (60x in last 3h, 1x/min): `signal_compactor NameError: RANGE_BREAKOUT_PLUS_ENABLED is not defined` — Root cause: `signal_schema.py:is_component_disabled()` import block missing 3 range_breakout constants. FIXED by adding `RANGE_BREAKOUT_ENABLED, RANGE_BREAKOUT_PLUS_ENABLED, RANGE_BREAKOUT_MINUS_ENABLED` to import at line 1888. Verified with direct run — compactor now completes cleanly (cycle=16305, 0 hotset).

## Error Alerts — 2026-08-10 02:40 UTC
- **WARN** (Nx2): `ERR decider_run: Traceback at decider_run.py:2881` — non-fatal, pipeline continues after error
- **AUTO-FIX**: None needed — pipeline self-recovered. Consider removing defunct decider_run call from run_pipeline.py.

## Error Alerts — 2026-08-10 04:08 UTC
- **REPEATED** (7x): `Aug N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`

## Error Alerts — 2026-08-10 06:41 UTC
- **[INFO]** (6x): `hermes-bug-hunter.service` — failed: imports defunct `ai_decider`/`signal_gen`. Non-critical, needs code cleanup.
- **[INFO]** (3x): `hermes-hl-volume.service` — failed: exit-code. Non-critical utility.
- **[INFO]** (1x): `hermes-mtf-macd-tuner.service` — failed: exit-code. Non-critical.
- **[INFO]** (1x): `hermes-signal-reporter.service` — failed: timeout. Non-critical.
- **[INFO]** (1x): `hermes-trading-checklist.service` — failed: exit-code. Non-critical.
- **[INFO]** (1x): `hermes-upgrade-implementer.service` — failed: exit-code. Non-critical.
- **[INFO]** (repeated): `[PHANTOM-DBG] ETH LONG` — SL stable at0.102% distance, no action needed. Debug output only.
- **AUTO-FIX**: None needed — all issues are non-critical utilities. Core pipeline healthy.

## Error Alerts — 2026-08-10 14:40 UTC
- **[WARN]** (1x): `Disk 82% used` — approaching 85% threshold. `self_close_watcher.err.log` is 35MB — should be rotated/compressed.
- **[INFO]** (1x): `Pipeline OK` — running clean at 14:38, no errors in last 30min.
- **[INFO]** (1x): `100 signals generated (1h)` — 0 approved (all filtered by confidence threshold at compaction).
- **[INFO]** (1x): `Only 1/6 positions open` — capital under-utilized. No signals above 50% confidence.
- **[AUTO-FIX]**: None needed — all systems nominal.

## Error Alerts — 2026-08-10 18:41 UTC
- **[INFO]**: Pipeline healthy — timer active, last run completed at 18:39, no errors in 30min.
- **[WARN]** (1x): `Disk 84% used` — up from 82% at 14:40. 19GB free. Approaching 85% threshold.
- **[INFO]**: 108 signals generated (1h), 0 approved — market overwhelmingly NEUTRAL (105/106 tokens). Only CRV shows LONG_BIAS (95% conf).
- **[INFO]**: 0 open positions, 60 closed today (-0.06 USDT PnL). Hotset empty — no signals survived compaction.
- **[INFO]**: 218/549 tokens stale (40%). 1m candles fresh (1min), 15m at 11min, 1h at 41min.
- **[AUTO-FIX]**: None needed — no actionable issues. Neutral market = expected low activity.

## Error Alerts — 2026-08-10 20:40 UTC
- **[INFO]**: Pipeline OK — running clean, last cycle #149574 at 20:39, no errors in 30min.
- **[WARN]** (1x): `Disk 80% used` — down from 84% at 18:41 after log compression. 23GB free.
- **[WARN]** (1x): `5m candle freshness 21%` — only 36/172 tokens have fresh 5m candles (10min window). 136 tokens missing recent candles.
- **[INFO]**: 61 signals generated (1h), 0 approved, 1 executed. Market NEUTRAL (105/106 tokens). Macro gate: REDUCE (regime=NEUTRAL, wr=30%).
- **[INFO]**: 2 open positions (BSV SHORT, ASTER LONG). 70 closed today (-0.62% PnL). Win rate 47.1% (33/70) in 24h.
- **[INFO]**: 237/549 tokens >= 50% speed (43%). 326/549 speeds fresh (59%).
- **[INFO]**: 3 zero-byte DBs: prices.db, speed_hermes.db, hermes_trades_runtime.db — likely legacy/unused.
- **[AUTO-FIX]**: Compressed 64 old log files. Disk recovered from 84% to 80%.

## Error Alerts — 2026-08-10 22:40 UTC
- **[WARN]** (14x): `ERR decider_run: Traceback ... decider_run.py line 2888` (22:27-22:35 UTC)
- **AUTO-FIX**: None needed — self-resolved at 22:38. Traceback truncated in journalctl; manual dry-run confirmed decider_run.py runs clean now.
- **NOTE**: Likely transient DB lock or race condition during BSV signal processing. Pipeline continued operating (position_manager, trades-api, signals_runner all unaffected).

## Error Alerts — 2026-08-10 23:08 UTC
- **REPEATED** (7x): `Aug N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`

## Error Alerts — 2026-08-11 02:41 UTC
- **[WARN]** (12x in 30min): `ERR decider_run: Traceback at decider_run.py:2888` — crashes every pipeline cycle. Traceback truncated to 2 lines by run_pipeline.py:96 (`[:2]`). Pipeline continues and completes (exit 0). Runs clean when called directly — context-dependent, likely race condition.
- **[INFO]**: Pipeline OK — 30 cycles/30min, 2 open trades (HTTST4 paper + ASTER live), 7 closed today (-0.10 USDT).
- **[INFO]**: Regime NEUTRAL, macro gate REDUCE. Hotset empty (no signals above threshold). 84 signals generated (18 tokens).
- **[INFO]**: Disk 81% (90G/118G). All 40+ hermes timers firing on schedule.
- **AUTO-FIX**: None needed — pipeline self-recovered. Root cause of decider_run errors remains hidden due to stderr truncation.

## Error Alerts — 2026-08-11 03:41 UTC
- **[INFO]**: Pipeline OK — all cycles on schedule, no errors in last 30min. Cycle #149999.
- **[INFO]**: 106 signals generated (1h), 28004 active. Hotset empty (no signals survived compaction).
- **[INFO]**: 1 open (ASTER LONG), 57 closed today. PnL: -0.16 USDT (24h). Win rate 40% (23/57).
- **[INFO]**: Regime NEUTRAL (105/106 tokens). Speed: 43% >=50th percentile (below 50% target).
- **[WARN]**: Disk 81% (90G/118G) — approaching 85% threshold.
- **AUTO-FIX**: None needed.

## Error Alerts — 2026-08-11 06:41 UTC
- **[OK]**: Pipeline healthy — last cycle completed at 06:40:11 (exit 0, 14.9s CPU). Next fire 06:41:00.
- **[OK]**: 172 signals generated (1h). 1 executed, 5 pending. 0 errors.
- **[OK]**: 1 open (ASTER LONG +0.08%), 56 closed today. PnL: -3.14%.
- **[OK]**: Regime NEUTRAL (103/106). 2 volatility-gated (JUP, BCH) — normal.
- **[WARN]**: Disk 81% (90G/118G) — persistent, approaching 85% threshold.
- **AUTO-FIX**: None needed.

## Error Alerts — 2026-08-11 10:08 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   [_get_meta] fetch failed: <urlopen TOK [Errno -N] Temporary failure in name resolution>`

## Error Alerts — 2026-08-11 15:42 UTC
- **[WARN]** (Nx per run): `ERR decider_run: Traceback ... line 2908` — decider_run.py crashes every pipeline cycle. Pipeline continues (try/except wraps it). Error: truncated traceback, likely import or runtime error inside `run()`.
- **[WARN]** (5x): `[PHANTOM-DBG] HBAR LONG` — SL not moving (0.086% distance unchanged across multiple runs). Position may be stuck.
- **AUTO-FIX**: None applied — decider_run error is non-blocking, pipeline runs successfully despite it.

## Error Alerts — 2026-08-11 16:08 UTC
- **REPEATED** (7x): `Aug N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`

## Error Alerts — 2026-08-11 17:40 UTC
- **[WARN]** (2x): `decider_run crash at line 2908` — intermittent, non-fatal. Pipeline continues through position_manager. Only 2 occurrences in last hour; most cycles clean.
- **[WARN]** (5 tokens): `Stale 1m candles` — LIT (69h), SUSHI (67h), AAVE (50h), PNUT (50h), SKY (50h). Likely delisted/low-volume tokens not worth tracking.
- **[INFO]** Disk at 83% (93G/118G) — approaching 85% WARN threshold. pipeline.log is 45M.
- **AUTO-FIX**: None required. Pipeline operational. decider_run errors are non-blocking.

## Error Alerts — 2026-08-11 19:08 UTC
- **REPEATED** (18x): `Aug N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TOK hermes-trades-api: TOK (most recent call last):`
- **REPEATED** (14x): `Aug N N:N:N python3[TOK]: TOK (most recent call last):`
- **REPEATED** (14x): `Aug N N:N:N python3[TOK]: SyntaxError: ':' expected after dictionary key`
- **REPEATED** (14x): `Aug N N:N:N systemd[N]: hermes-pipeline.service: Main process exited, code=exited, status=N/FAILURE`
- **REPEATED** (14x): `Aug N N:N:N systemd[N]: hermes-pipeline.service: Failed with result 'exit-code'.`
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   TS signals_runner: ImportError — signals module not available: cannot import name 'VORTEX_BREAK_ENABLED' from 'hermes_constants' (/root/.hermes/scripts/hermes_constants.`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS signals_runner: ImportError — signals module not available: cannot import name 'RETURN_EXHAUSTION_ENABLED' from 'hermes_constants' (/root/.hermes/scripts/hermes_const`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS signals_runner: ImportError — signals module not available: cannot import name 'ENGULFING_ENABLED' from 'hermes_constants' (/root/.hermes/scripts/hermes_constants.py)`

## Health Report — 2026-08-11 19:40 UTC

```
=== Health Report ===
Time: 2026-08-11 19:40 UTC

PIPELINE: OK
- Status: running (cycle #150960+)
- Signals (1h): 0 generated, 0 executed
- Trades: 5 open, 25 closed today
- PnL: -3.34%
- Errors: 0 (last 10 min); decider_run crash streak 19:09-19:27 resolved

MARKET:
- Regime: 104 LONG / 0 SHORT / 104 NEUTRAL (overall NEUTRAL)
- Speed: 55% tokens fresh (299/549)
- Macro gate: REDUCE (regime=NEUTRAL, wr=40%)
- Hotset: empty (0 tokens survived compaction)

SYSTEM:
- Timers: 15+ active (pipeline, price-collector, cut-loser, profit-monster, etc.)
- Disk: 84% (99G/118G) — approaching WARN threshold
- Prices: 299 fresh, 250 stale
- Pipeline: running normally
- hl-sync-guardian: active

AUTO-FIXES APPLIED:
- None needed. Pipeline self-recovered from decider_run errors.

ALERTS:
- [WARN] Disk at84% — pipeline.log=47M, pipeline.log.gz=90M. Compress/rotate when >85%.
- [WARN] Hotset empty — 0 signals survived compaction. Macro gate REDUCE active.
- [INFO] decider_run crash streak (19:09-19:27) resolved by ~19:30. Non-blocking.
```

## Error Alerts — 2026-08-11 19:40 UTC
- **[INFO]** Pipeline recovered from decider_run crash streak (19:09-19:27). Last error at 19:27, clean since 19:30+.
- **[WARN]** Disk at 84% (99G/118G) — 1% from threshold. pipeline.log (47M) + .gz (90M) are largest.
- **[WARN]** Hotset empty — 0 tokens survived compaction. Market is NEUTRAL, macro gate REDUCE (wr=40%).
- **AUTO-FIX**: None required. Pipeline operational.

## Health Report — 2026-08-12 01:42 UTC
- **WARN** (Nx): Disk at 85% — **AUTO-FIX**: Removed 3.1GB pre-update snapshot, cleaned 2GB old sessions, freed 12GB total (now 76%)
- **WARN** (2x): `decider_run.py` crashes at line 2911 (file is 2896 lines) — non-fatal, pipeline continues
- **WARN**: PHANTOM-WRITE ATOM LONG SL very tight (0.1% from entry)
- **INFO**: trades_hermes.db and speed_hermes.db are empty (0 bytes) — not used by current pipeline

## Health Report — 2026-08-12 02:42 UTC
- **[WARN]** (5x): `PHANTOM-WRITE` APT LONG trade_id=13649 — SL=0.574200 dist=0.122% from entry=0.573500 (tight, re-written every cycle). Token not in token_intel. Needs param review.
- **[WARN]** (1x): `HYPE mirror_close FAILED` PEOPLE — DB committed but HL still open (02:36:33). Transient API error, HL position may remain open.
- **[WARN]**: 230/549 tokens (42%) marked stale in token_speeds — expected for inactive tokens but worth monitoring
- **[INFO]**: Price collector running normally (104 prices/30s)
- **[INFO]**: Pipeline cycle #151381 — 6 open, 0 closed, 0.40% PnL, 43 closed today
- **[INFO]**: 254 signals generated in last hour, 22W/21L (52% winrate) in 24h
- **[INFO]**: Regime — 1 LONG (IOTA bias), 0 SHORT, 104 NEUTRAL — market mostly flat
- **[INFO]**: All 50+ timers active, disk at 76%

## Error Alerts — 2026-08-12 04:09 UTC
- **NEW** (1x): `Aug N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-08-12 04:42 UTC
- **[WARN]** (1x): `Signal accel_300: ERROR → ERROR: name '_get_1h_trend' is not defined`
- **AUTO-FIX**: Added missing `_get_1h_trend()` function to `scripts/signals/accel_300.py` (copied from `range_breakout.py`). Syntax verified.

## Error Alerts — 2026-08-12 05:09 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   Signal accel_300: TOK → TOK: name '_get_1h_trend' is not defined`

## Health Report — 2026-08-12 10:40 UTC

```
=== Health Report ===
Time: 2026-08-12 10:40 UTC

PIPELINE: OK
- Status: running (cycle #151860, last at 10:39:05)
- Signals (1h): 198 generated, 0 approved (all blocked by signal_analyst)
- Trades: 0 open, 0 closed today, PnL: 0.00 USDT
- Errors: 0 (no tracebacks in last 10min)

MARKET:
- Regime: 2 LONG_BIAS / 1 SHORT_BIAS / 101 NEUTRAL (overall NEUTRAL)
- Speed: 231/549 tokens >= 50% percentile (42%)
- Hotset: 2 tokens (INJ SHORT conf=78 score=105.4, MERL SHORT conf=88 score=0)
- 192/549 speeds stale (35%)

SYSTEM:
- Timers: 61 loaded, all active
- Disk: 77% used (26G free)
- Failed services: 5 (bug-hunter, hl-volume, mtf-macd-tuner, trading-checklist, upgrade-implementer)
- hl-sync-guardian: active
- Pipeline timer: running (1min)

AUTO-FIXES APPLIED:
- None needed. Pipeline operational. hl-volume 429 is transient.

ALERTS:
- [WARN] 5 failed services (non-critical): bug-hunter, hl-volume (429 rate limit), mtf-macd-tuner, trading-checklist, upgrade-implementer
- [WARN] 192/549 speeds stale (35%) — expected for inactive tokens
- [WARN] MERL SHORT in hotset has score=0, rounds=1 — likely to be filtered
- [INFO] Market overwhelmingly NEUTRAL — expected low trading activity
```

## Error Alerts — 2026-08-12 10:40 UTC
- **[WARN]** (5x): Non-critical services failed — `hermes-bug-hunter` (3h ago, imports defunct ai_decider), `hermes-hl-volume` (27min ago, Hyperliquid 429 rate limit), `hermes-mtf-macd-tuner` (3h53m ago), `hermes-trading-checklist` (45min ago, CRIT=1), `hermes-upgrade-implementer` (8h ago)
- **[WARN]** (1x): `hermes-hl-volume` 429 rate limit — transient, self-correcting on next timer fire
- **[INFO]**: Pipeline healthy — cycle #151860, 0 errors in last 30min. 198 signals generated but all blocked by signal_analyst (scores too low). 0 open positions, 0 closed today.
- **AUTO-FIX**: None needed — all issues are non-critical utilities or transient API limits.

## Error Alerts — 2026-08-12 17:09 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   [coin_tracker] TOK: no such table: _coin_registry`
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: [coin_tracker] Done: N coins processed, N skipped, N errors`

## Error Alerts — 2026-08-12 18:09 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   [coin_tracker] TOK: 'NoneType' object has no attribute 'get'`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   [coin_tracker] TOK: name '_read_candles' is not defined`
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   [coin_tracker] TOK: no such table: agg_scores`

## Error Alerts — 2026-08-12 19:09 UTC
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   [coin_tracker] TOK: expected an indented block after 'for' statement on line N (coin_tracker.py, line N)`

## Error Alerts — 2026-08-12 19:40 UTC
- **[WARN]** (6/cycle): `[coin_tracker] Error processing kBONK/kFLOKI/kLUNC/kNEIRO/kPEPE: table already exists`
- **AUTO-FIX**: Added `IF NOT EXISTS` to `CREATE TABLE` and `CREATE INDEX` in `coin_tracker_schema.py` (lines 127, 153-155, 167, 193-195). Root cause: module-level `_TABLE_EXISTS_CACHE` is empty after pipeline restart; the sqlite_master check races with concurrent CREATE TABLE.
- **[WARN]**: `hermes-hl-volume` — 429 rate limit from Hyperliquid API (transient, will self-heal)
- **[WARN]**: `hermes-trading-checklist` — pipeline output parsing + 53195 signals needing archival
- **[INFO]**: `hermes-bug-hunter` — 83 bare except clauses, 111 connection leaks, 72 atomic JSON writes, 5 hardcoded passwords (known tech debt, not blocking)

## Error Alerts — 2026-08-12 20:09 UTC
- **REPEATED** (13x): `Aug N N:N:N python3[TOK]: TS   [coin_tracker] TOK: expected an indented block after 'for' statement on line N (coin_tracker.py, line N)`
- **REPEATED** (14x): `Aug N N:N:N python3[TOK]: [coin_tracker] TOK processing kBONK: table coin_kBONK already exists`
- **REPEATED** (14x): `Aug N N:N:N python3[TOK]: [coin_tracker] TOK processing kFLOKI: table coin_kFLOKI already exists`
- **REPEATED** (14x): `Aug N N:N:N python3[TOK]: [coin_tracker] TOK processing kLUNC: table coin_kLUNC already exists`
- **REPEATED** (14x): `Aug N N:N:N python3[TOK]: [coin_tracker] TOK processing kNEIRO: table coin_kNEIRO already exists`
- **REPEATED** (14x): `Aug N N:N:N python3[TOK]: [coin_tracker] TOK processing kPEPE: table coin_kPEPE already exists`

## Error Alerts — 2026-08-13 01:09 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TOK ab_optimizer: TOK (most recent call last):`

## Error Alerts — 2026-08-13 01:41 UTC
- **WARN** (6x): `ab_optimizer` crash on missing `/root/.hermes/config/ab_tests.json`
- **AUTO-FIX**: Created config directory + empty `ab_tests.json` — ab_optimizer now runs clean
- **INFO**: `hermes-hl-sync-guardian.timer` and `hermes-atr-sl-updater.timer` disabled (not running)

## Error Alerts — 2026-08-13 02:09 UTC
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TOK ab_optimizer: TOK (most recent call last):`

## Error Alerts — 2026-08-13 03:09 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   [TOK] trail load TOK: name 'Path' is not defined`

## Error Alerts — 2026-08-13 10:40 UTC
- **WARN** (1x): `hotset empty` — 0 signals survived compaction, expected in flat market (104/104 NEUTRAL)
- **WARN** (1x): `disk 81%` — 90G/118G used, 22G free. Compress if >85%.
- **INFO** (7x): `service failures` — better-coder, bug-hunter, hl-volume, mtf-macd-tuner, signal-reporter, study-winning-combos, trading-checklist all FAILED (non-critical). mtf-macd-tuner had multiprocessing pool crash.

## Health Monitor — 2026-08-13 19:41 UTC
- **INFO**: Pipeline healthy — last run 19:39, 0 errors, timer active
- **WARN**: Disk at 81% (22GB free of 118GB) — approaching 85% threshold
- **INFO**: 81 signals generated in last hour, 0 open trades, 68 closed today
- **INFO**: Today PnL: -0.85 USDT
- **INFO**: Regime: 103 NEUTRAL / 1 SHORT / 0 LONG
- **INFO**: Hotset empty (normal for neutral regime)
- **INFO**: Prices fresh (<1 min stale)
- **AUTO-FIX**: None required

## Error Alerts — 2026-08-13 20:40 UTC
- **CRITICAL** (Nx/min): `signals_runner: ERROR — name 'R2_TREND_LONG_ENABLED' is not defined` — broke entire signal generation
- **AUTO-FIX**: Added missing import `R2_TREND_LONG_ENABLED` to `scripts/signals/__init__.py:31`

## Error Alerts — 2026-08-13 21:09 UTC
- **REPEATED** (23x): `Aug N N:N:N python3[TOK]: TS   TS signals_runner: TOK — name 'R2_TREND_LONG_ENABLED' is not defined`

## Health Check — 2026-08-13 22:40 UTC
- **Status**: ALL CLEAR — no issues detected
- **Pipeline**: active, last run completed 22:39:19 (18.7s CPU)
- **Guardian**: active
- **Signals (1h)**: 155 generated, 64 in last 30min
- **Open positions**: 5/6 (logs show 5 active)
- **Prices**: 1m candles 1.3min old, 123 coins — fresh
- **Candles**: 212 coins on 15m — healthy
- **Disk**: 81% (118G total, 22G free)
- **Timers**: hermes-pipeline.timer firing on schedule (next: 22:41)
- **Errors**: 0 in last 30min
- **Regime**: 1 long bias, 1 short bias, 102 neutral

## Error Alerts — 2026-08-14 03:40 UTC

- **WARN** (1x): `runtime.db tables=[]` — all runtime/trades DBs are empty (0KB). Positions tracked in-memory by pipeline process, not persisted to disk.
- **WARN** (1x): `hotset.json empty` — no signals survived compaction. Market is 102/104 NEUTRAL, 2 SHORT_BIAS, 0 LONG. Dead market = no trades.
- **WARN** (1x): `0 signals above 50% confidence` — decider skipped execution. Expected given flat market.
- **INFO**: Pipeline healthy, no crashes/errors. 5 open positions, 55 closed today (-7.66% PnL). All timers firing.
- **NO AUTO-FIXES NEEDED** — all issues are market-state driven, not system failures.
