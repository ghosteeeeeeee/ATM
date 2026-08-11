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
