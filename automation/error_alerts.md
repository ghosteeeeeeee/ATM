# Error Alerts

## 2026-08-15 15:18 UTC — Health Monitor
- **INFO**: No CRITICAL or WARN issues detected
- **AUTO-FIX**: Disabled deprecated `hermes-self-close-watcher.timer` (logic migrated to `hermes-hl-sync-guardian`)
- **NOTE**: GRASS phantom-write guard active — blocking SL tighten within 0.08% of entry (trade_id=13905)

## 2026-08-15 20:19 UTC — Health Monitor
- **WARN** (1x): `hermes-brain.db` is EMPTY (0 bytes, 0 tables) — trades tracked via trades.json, brain DB appears defunct
- **WARN** (1x): BLUR mirror_close FAILED at 20:04 — "HL API failed: Non-dict response from exchange: None"
- **WARN** (1x): ROLLBACK FAILED at 20:13 — sig#1551419 already claimed by another process (race condition)
- **WARN** (1x): hl_cache.json has only 6 tokens vs 108 in price collector (may be expected if HL-only)
- **INFO**: Pipeline running, 5 open positions, 53 closed today, -0.58% PnL
- **AUTO-FIX**: None needed — no CRITICAL issues

## Error Alerts — 2026-08-15 21:02 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS [Position Manager] TOK mirror_close TOK (DB committed, HL still open): mirror_close(TOK): HL TOK failed — Non-dict response from exchange: None`

## Error Alerts — 2026-08-15 22:02 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   [TOK CLEANUP] Failed to cancel stale orders for TOK: TOK TOK N: Too Many Requests`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS [Position Manager] TOK mirror_close TOK (DB committed, HL still open): HL TOK TOK: N null`
- **REPEATED** (3x): `Aug N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   ⚠️ ROLLBACK TOK: sig#N already claimed by another process`
- **REPEATED** (4x): `Aug N N:N:N python3[TOK]: TS   TS   → TOK: Command '['/usr/bin/python3', '/root/.hermes/scripts/brain.py', 'trade', 'add',`

## Error Alerts — 2026-08-16 00:18 UTC
- **CRITICAL** (1x): `hermes-pipeline.service` was INACTIVE — restarted successfully
- **WARN** (1x): ROLLBACK FAILED: sig#1551768 already claimed by another process (race condition)
- **WARN** (6x): 6 services in failed state: better-coder (missing module), hl-volume (API error), mtf-macd-tuner, bug-hunter, trading-checklist, wasp
- **INFO**: Pipeline OK after restart. 5 open positions, 0 closed today, -1.57% PnL
- **INFO**: Regime NEUTRAL (102 neutral, 1 long, 1 short). 56 signals/hr. 412 in queue
- **INFO**: Disk 72% used, all critical timers firing
- **AUTO-FIX**: Restarted `hermes-pipeline.service` (was inactive)
- **NOTE**: better-coder/hl-volume/mtf-macd-tuner failures are non-critical code/API issues, not trading-impacting

## Error Alerts — 2026-08-16 02:02 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   [brain.py] ❌ TOK: stderr=[_http_post] N rate-limited, attempt N/N, waiting 1s...`
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS   → TOK: [_http_post] N rate-limited, attempt N/N, waiting 1s...`

## Error Alerts — 2026-08-16 04:02 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS   TS [Position Manager] TOK mirror_close TOK (DB committed, HL still open): mirror_close(W): HL TOK failed — Non-dict response from exchange: None`

## Error Alerts — 2026-08-16 08:02 UTC
- **NEW** (1x): `Aug N N:N:N python3[TOK]: TS TOK position_manager: timed out`

## Error Alerts — 2026-08-16 22:18 UTC
- **WARN** (6x): `hermes-better-coder.service, hermes-wasp.service, hermes-bug-hunter.service, hermes-hl-volume.service, hermes-mtf-macd-tuner.service, hermes-trading-checklist.service — FAILED`
- **DETAILS**: better-coder: missing dispatcher module; hl-volume: 429 rate limit; mtf-macd: missing warmup attr; bug-hunter: found 3 issues (non-atomic JSON, hardcoded passwords, dead imports); trading-checklist: 64637 signals in DB; wasp: unknown
- **AUTO-FIX**: None applied — all non-critical utility services, pipeline core is healthy

## Error Alerts — 2026-08-17 01:20 UTC
- **WARN** (1x): Hotset empty — 0 signals survived compaction, no new entries considered
- **WARN** (1x): HYPE LONG phantom-write guard active — blocking SL tighten to 0.105% from entry (trade_id=13971)
- **INFO**: Pipeline running, 2 open positions, 1 closed today (+$0.07), -1.51% portfolio PnL
- **INFO**: 42% of tracked tokens stale (low velocity) — expected in quiet NEUTRAL market
- **AUTO-FIX**: None needed — no CRITICAL issues

## Error Alerts — 2026-08-17 02:02 UTC
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   TS   ⚠️ ROLLBACK TOK: sig#N already claimed by another process`
- **REPEATED** (5x): `Aug N N:N:N python3[TOK]: TS   TS   → TOK: TOK (most recent call last):`

## Health Report — 2026-08-17 09:19 UTC
- **OK** Pipeline: running, cycle #158920, 50 signals generated (1h), 0 errors
- **WARN** Phantom trades (6): SYRUP, CFX, HYPE, NOT with 0% PnL in closed_today
- **INFO** Market: 102 NEUTRAL / 1 LONG (ACE) / 1 SHORT (CHIP) — very quiet
- **INFO** Positions: 2 open (MERL -0.25%, APT -0.19%), SLs healthy

## Error Alerts — 2026-08-17 11:19 UTC
- **WARN** (1x): `APT mirror_close FAILED` — HL API returned non-dict response at 10:34. DB committed, HL position still open (degraded gracefully).
- **WARN** (5x): Auxiliary services in failed state: hermes-better-coder, hermes-bug-hunter, hermes-mtf-macd-tuner, hermes-trading-checklist, hermes-wasp. All non-critical monitoring/tuning services, not auto-restarted to avoid masking root cause.
- **INFO**: No auto-fixes applied — pipeline core is healthy.

## Health Report — 2026-08-17 15:19 UTC
- **OK** Pipeline: running, 3 open trades, 3,706 closed all-time, +3.20% PnL today, 0 errors
- **INFO** Market: 3 LONG_BIAS (HEMI +6.6%, KAITO +6.2%, ACE +2.6%) / 0 SHORT / 102 NEUTRAL — mostly flat
- **INFO** Signals: 0 HOT/WARM in last hour — expected given neutral-dominated market
- **OK** Timers: hermes-pipeline ✓ | hermes-price-collector ✓ | hl-sync-guardian ✓
- **OK** Disk: 74% (30GB free), no stale logs bloating
- **NO AUTO-FIX NEEDED**

## Health Report — 2026-08-17 20:20 UTC

=== Health Report ===
Time: 2026-08-17 20:20 UTC

PIPELINE: OK
- Status: running (cycle #159582+)
- Signals (1h): 65,856 generated (LONG: 31,860 / SHORT: 33,976)
- Decisions (1h): 2 EXECUTED, 3 PENDING, 5,742 SKIPPED, 60,109 EXPIRED
- Trades: 2 open, 39 closed today, +3.97% PnL
- Errors: 0

MARKET:
- Regime: NEUTRAL (102 tokens) / 2 SHORT_BIAS (HEMI, POL) / 0 LONG
- BTC: 4,309 (-0.21% 16c)
- ETH: ,907 (-0.19% 16c)
- SOL: 5.71 (-0.26% 16c)

SYSTEM:
- Timers: 48 active (all hermes timers running)
- Disk: 75% used (83G/118G)
- Pipeline: active, cycling every minute
- hl-sync-guardian: active
- cut-loser: active, no errors
- Position manager: 2 open, 0 closed this cycle

AUTO-FIXES APPLIED:
- None needed

ALERTS:
- alerts.json has stale WARNING from ~18:40 UTC about low signal count (since resolved — 65K signals/hour now)

## Error Alerts — 2026-08-18 08:19 UTC
- **[WARN]** (Nx): `43% tokens stale (102/239)` — price data may be lagging for many tokens
- **[WARN]** (Nx): `6 services FAILED` — hermes-better-coder, hermes-bug-hunter, hermes-hl-volume, hermes-mtf-macd-tuner, hermes-trading-checklist, hermes-wasp (all non-critical, Restart=no)
- **[INFO]**: Pipeline running, 2/4 positions open, -1.48% PnL today, CHIP hotset signal at 75% confidence
