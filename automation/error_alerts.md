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
