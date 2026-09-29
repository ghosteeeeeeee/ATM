## Error Alerts — 2026-09-29 08:46 UTC

### CRITICAL (0)
- None

### WARN (1)
- **WARN** (continuous): `position_manager: FAILED` every cycle — **NOT A BUG**. Lock conflict with hermes-hl-sync-guardian.service. Guardian handles SL/TP and positions. Loss cooldowns + ATR updates complete before exit. Fix: remove position_manager from pipeline steps since guardian covers all functionality.

### INFO
- **AUTO-FIX** (08:46): Compressed logs older than 7 days
- Disk at 84% (93GB/118GB) — monitor
- Market regime: NEUTRAL (117 tokens, no directional bias)
- Today: 6 trades, 83% WR (5W/1L)
- Loss cooldowns: CC:LONG streak=50, BABY:SHORT streak=100

### AUTO-FIXES APPLIED
- Cleaned /tmp/*.so (2.5GB node-compile-cache files >3 days old)
- Trimmed pipeline.log from 77MB to ~15MB (last 5000 lines)
- Compressed old log files (>3 days)
- Disk: 86% → 83% (3GB reclaimed)

## Error Alerts — 2026-09-29 05:58 UTC
- **REPEATED** (10x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.2s (rc=N)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: +N.N% from high, +N.N% from low — blocking TOK entries`

## Error Alerts — 2026-09-29 07:58 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.3s (rc=N)`

## Error Alerts — 2026-09-29 08:58 UTC
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.0s (rc=N)`

## Error Alerts — 2026-09-29 10:58 UTC
- **REPEATED** (13x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BULL+TOK, allowing despite TOK filter`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+LEAN_BULL+AT, allowing despite TOK filter`
