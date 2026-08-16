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
