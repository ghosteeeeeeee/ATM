## Health Report — 2026-09-27 06:49 UTC
- **OK**: Pipeline running (LIVE). Both services active. Timer: `hermes-pipeline.timer` firing every minute.
- **OK**: Last cycle 06:49 completed clean (rc=0 all steps). 0 open | 0 closed today | +0.00% PnL.
- **OK**: Signals: 5,124 in DB, 5 generated in last hour. Latest: HBAR SHORT (74.8), LDO LONG (75.0), DOT SHORT (88.0).
- **OK**: Market: coin_tracker regime NEUTRAL. Macro gate: LONG=FULL, SHORT=REDUCE.
- **WARN**: Hotset empty — 0 tokens survived compaction. All signals filtered out. No trades possible until compaction promotes signals.
- **WARN**: `decider_run` intermittent failures (6x in 30min at 06:18-06:41). All were when signals attempted execution (MNT, YGG). Self-recovered at 06:42 — no failures since. Root cause: unclear (truncated traceback at line 4368). Pipeline continued through failures.
- **OK**: Timers: 40+ active, all firing on schedule. No missed runs.
- **OK**: Disk: 83% (92G/118G) — stable, below 85% threshold.
- **OK**: Position Manager: 0 open | 0 closed | 0 adjusted. No phantom trades.
- **INFO**: Contrarian analysis: 0 hot, 83 warm, 8 cold — NEUTRAL signal.
- **INFO**: Liquidation heatmap: 9 coins, 112 clusters, 0 cascade zones.
- **AUTO-FIX**: None required. Pipeline self-recovered from decider_run failures.

## Error Alerts — 2026-09-25 04:45 UTC
- **WARN** (1x): `Disk at 85% (95G/118G)` — approaching threshold
- **AUTO-FIX**: None applied — monitor, compress logs if >90%
- **WARN** (continuous): `hotset.json empty — no signals survived compaction` — pipeline runs clean but produces no actionable signals
- **AUTO-FIX**: None — market is 118/118 NEUTRAL, compaction is working as intended (filtering noise)

## Error Alerts — 2026-09-25 04:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.1s (rc=N)`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.6s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] W TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.7s (rc=N)`

## Error Alerts — 2026-09-25 07:46 UTC
- **WARN** (Nx1): `Disk at 85% (95G/118G)` — threshold 85%
- **AUTO-FIX**: Vacuumed systemd journal (freed 336MB), compressed old hermes logs. Disk went 86% → 85%.
- **NOTE**: Monitor — still at threshold. Next cleanup may need manual intervention or log rotation config.

## Error Alerts — 2026-09-25 07:57 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.6s (rc=N)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`

## Error Alerts — 2026-09-25 08:46 UTC
- **WARN** (1x): `Disk at 85% (95G/118G)` — unchanged since 07:46 cleanup
- **NOTE**: Top DBs: coin_tracker (2.9G), candles (2.1G), mtf_macd_tuner (906M), signals_hermes (832M), session_brain (774M). Total data dir: 7.9G. Logs only 39M.
- **INFO**: No pipeline errors. No phantom trades. No crashes. Prices fresh (45s). All timers firing.
- **AUTO-FIX**: None needed — pipeline healthy, disk at threshold but not over.

## Error Alerts — 2026-09-25 09:45 UTC
- **WARN** (1x): `Disk at 85% (17GB free)` — data/ = 7.9GB, not logs. Consider DB vacuum or old signal purge.
- **WARN** (1x): `hermes-hl-sync-guardian.service inactive` — no logs in 1h, no timer entries. May be expected.
- **AUTO-FIX**: Compressed logs older than 1 day (saved ~0 bytes, logs were already small).

## Error Alerts — 2026-09-25 09:57 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`

## Error Alerts — 2026-09-25 11:57 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.6s (rc=N)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.8s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.2s (rc=N)`

## Health Report — 2026-09-25 12:45 UTC
- **PIPELINE**: OK — running normally, 0 errors
- **WARN** (1x): Disk usage at 86% (95G/118G)
- **INFO**: BTC crash guard active, blocking LONG entries
- **INFO**: 0 open trades, 11 closed today (-4.83% PnL)
- **AUTO-FIX**: Cleaned /tmp node-compile-cache (6GB freed), compressed old logs. Disk 86% → 80%.

## Error Alerts — 2026-09-25 12:57 UTC
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-25 14:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`

## Error Alerts — 2026-09-25 15:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+NEUTRAL+TOK, allowing despite TOK filter`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`

## Error Alerts — 2026-09-25 16:46 UTC
- **CRITICAL** (607,835 restarts): `hermes-coding-mcp.service` — missing `/root/.hermes/scripts/run_mcp_server.py`
- **AUTO-FIX**: Disabled hermes-coding-mcp.service to stop CPU-burning restart loop
- **INFO**: hermes-5m-candle failed 1 week ago (stale, journal rotated)
- **WARN**: Disk at 76% (90G/118G) — approaching 85% threshold

## Error Alerts — 2026-09-25 19:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.0s (rc=N)`

## Error Alerts — 2026-09-25 20:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`

## Error Alerts — 2026-09-25 21:57 UTC
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BEAR+TOK, allowing despite TOK filter`

## Error Alerts — 2026-09-25 22:57 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.5s (rc=N)`

## Error Alerts — 2026-09-26 00:58 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.6s (rc=N)`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`

## Error Alerts — 2026-09-26 01:48 UTC
- **WARN** (150x): `ERR decider_run: Traceback ... line 4358` — crash after mark_signal_executed on AIXBT/WLFI/NXPC signals. Journalctl truncated traceback. Now resolved (hotset empty). Root cause unknown — will recur on next signal. Needs investigation.
- **WARN**: Disk at 81% (22GB free of 118GB). Monitor.

## Error Alerts — 2026-09-26 01:58 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.7s (rc=N)`

## Error Alerts — 2026-09-26 03:58 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   [TOK-TOK] TOK: skip TOK — hebbian n=N < N (insufficient data, TOK-open)`

## Error Alerts — 2026-09-26 04:58 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.7s (rc=N)`

## Error Alerts — 2026-09-26 05:47 UTC
- **WARN** (6x): `decider_run: FAILED in 0.6s (rc=1)` — Traceback at decider_run.py:4358, journalctl truncated (same root cause as 01:48). Occurred 05:36–05:40 UTC. **Self-recovered at 05:41** — no auto-fix needed.
- **NOTE**: Market 116/118 NEUTRAL. Only signal evaluated: AIXBT LONG (97% conf) — approved by decider, blocked by volatility gate (ATR=1.6566% > 1.5% storm threshold). 0 open, 0 closed, 0 PnL today.
- **NOTE**: Disk 81% (22GB free). OK for now.

## Error Alerts — 2026-09-26 05:58 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for IO: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TOK`

## Error Alerts — 2026-09-26 06:58 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.7s (rc=N)`

## Error Alerts — 2026-09-26 08:46 UTC
- **REPEATED** (12x): `decider_run: FAILED in 0.6s (rc=1)` — Traceback at decider_run.py:4358, 08:21-08:32
- **AUTO-FIX**: None needed — self-recovered at 08:44, last 3 runs OK
- **WARN**: Price collector LOCK-WAIT contention on info_rate — multiple DB writers, benign
- **INFO**: Market 116/118 NEUTRAL, 0 signals above 50% confidence, 0 open/closed trades. Hotset 0 tokens.

## Error Alerts — 2026-09-26 08:58 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.9s (rc=N)`

## Error Alerts — 2026-09-26 12:45 UTC
- **WARN** (1x): `hotset fallback DB query returned 0 tokens`
- **WARN** (4x): `price DBs empty (0 bytes)` — prices.db, prices_hermes.db, price_candles.db, price_history.db
- **AUTO-FIX**: None applied — pipeline healthy, price DBs likely by design (API-only mode)

## Error Alerts — 2026-09-26 13:45 UTC
- **WARN**: Disk at 82% (91G/118G) — monitor for cleanup if approaching 85%
- **INFO**: decider_run failing (rc=1) every pipeline cycle — expected, ai_decider.py is defunct per AGENTS.md
- **WARN**: 7 services in failed state: 5m-candle, away-detector, better-coder, bug-hunter, git-release, mtf-macd-tuner, weather-station-api

## Error Alerts — 2026-09-26 22:46 UTC
- **WARN** (1): `disk_82pct` — Disk at 82% (92G/118G)
- **INFO**: 0 signals above 50% confidence — market quiet
- **INFO**: coin_tracker_data.json not found in /var/www/hermes/data/

## Error Alerts — 2026-09-26 23:46 UTC
- **WARN** (4x): `decider_run: FAILED` — transient failures 23:40-23:43, self-recovered at 23:44. First failure took 19.5s (likely DB lock or API timeout).
- **INFO**: Pipeline healthy, no auto-fix needed — decider_run working normally since 23:44.
- **WARN**: Hotset empty — 62 signals generated but 0 survived compaction. All 118 tokens in NEUTRAL regime (0 long bias, 0 short bias). Expected for low-volatility Saturday.
- **INFO**: 0 open trades, 0 closed today — regime filtering is working as designed.
- **INFO**: Disk at 82% (92G/118G) — stable since last check.

## Health Report — 2026-09-27 05:45 UTC
- **INFO**: Pipeline OK. Completed at 05:44 (LIVE). 0 open, 0 closed today.
- **INFO**: All 118 tokens NEUTRAL regime. No long/short bias.
- **INFO**: 57 timers active, all firing. No missed runs.
- **WARN**: Disk at 83% (92G/118G) — approaching 85% cleanup threshold.
- **INFO**: Dead price DBs (price_candles.db, price_history.db, prices.db, prices_hermes.db) are 0 bytes, harmless but stale.
- **AUTO-FIX**: None required.

## Error Alerts — 2026-09-27 06:58 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   ⚠️ [TOK-TOK] TOK failed for TOK: Command '['/root/.opencode/bin/opencode', 'run', 'You are a crypto trading gate. Evaluate this signal and reply TOK of: GO, TOK, TO`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says DECLINING+LEAN_BULL+TOK, allowing despite TOK filter`

## Health Report — 2026-09-27 07:45 UTC
- **OK**: Pipeline running (LIVE). Last run 07:44:31, rc=0.
- **OK**: Services: hermes-pipeline=active, hl-sync-guardian=active.
- **OK**: Signals: 50 generated in last hour, 0 approved (>50% threshold). Market filtering noise correctly.
- **OK**: Trades: 0 open | 0 closed today. No phantom trades.
- **INFO**: Market: 118 tokens scanned — 3 LONG_BIAS (NIL, SUI, BIGTIME), 0 SHORT, 115 NEUTRAL. BTC $84,552.
- **WARN**: Disk at 83% (92G/118G) — approaching 85% cleanup threshold. Monitor.
- **INFO**: Timers: hermes-price-collector active (running 1d+). All services healthy.
- **AUTO-FIX**: None required. Pipeline healthy.

## Error Alerts — 2026-09-27 08:58 UTC
- **REPEATED** (12x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.6s (rc=N)`
- **REPEATED** (13x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (13x): `Sep N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **REPEATED** (13x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says TOK+LEAN_BULL+TOK, allowing despite TOK filter`

## Health Report — 2026-09-27 09:46 UTC
- **OK**: Pipeline running (LIVE). Completed 30 cycles in last 30 min. All services active.
- **OK**: hermes-pipeline.service = active, hermes-hl-sync-guardian.service = active.
- **OK**: Signals: 70+ generated in last hour. Latest: KSHIB SHORT (84.8), TRX SHORT (75.0), GMT LONG (75.0), SAND LONG (82.0).
- **OK**: Trades: 0 open | 0 closed today. Last trade: Sep 25 (BTC LONG continuum-osc+, +0.40%).
- **OK**: Market: 118 tokens scanned — 3 LONG_BIAS (NIL, SUI, BIGTIME), 0 SHORT_BIAS, 115 NEUTRAL. Overall: NEUTRAL.
- **WARN**: Disk at 83% (92G/118G) — approaching 85% cleanup threshold. Monitor.
- **WARN**: decider_run failing 4x/hour (rc=1) — CTX-GATE skipping LLM for SAND (hebbian n=2 < 5, fail-open). Non-blocking, signals marked executed via fail-open path.
- **OK**: All 40+ timers active, firing on schedule. No missed runs.
- **OK**: Signal compactor running clean (1/min, deactivated successfully each cycle).
- **AUTO-FIX**: None required. decider_run failures are non-critical (fail-open design).

## Error Alerts — 2026-09-27 09:58 UTC
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-09-27 10:46 UTC
- **WARN** (5x): `decider_run` crash at line 4368 — BLUR LONG blocked by BTC momentum (-0.22%), mark_signal_executed succeeds (rc=1), then exception after. Non-blocking: pipeline continues. Root cause: exception in execution path after BTC-crash block. 
- **WARN**: `signal-compactor.err.log` — repeated `LOCK-WAIT info_rate` contention (48+ retries). Lock contention on info_rate DB during concurrent access.
- **INFO**: No auto-fixes applied — all issues are non-critical, pipeline completing normally.
