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
