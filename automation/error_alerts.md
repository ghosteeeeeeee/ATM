## Error Alerts — 2026-09-29 14:48 UTC

### CRITICAL (0)
- None

### WARN (1)
- **WARN** (continuous): `position_manager: FAILED` every cycle (120x/2h) — Lock conflict with hermes-hl-sync-guardian.service. Guardian handles SL/TP and positions. Pipeline step reports rc=1 but rest of pipeline completes fine. Portfolio tracking works (5 open, 37 closed, +9.5% PnL). Fix: remove position_manager from pipeline steps since guardian covers all functionality.
- **WARN**: Disk at 84% (94GB/118GB) — 1% from 85% threshold. Monitor.

### INFO
- Market regime: NEUTRAL (88 coins, 0% hot, 8% cold)
- Live trading: ENABLED (CEO re-enabled)
- 10 active signals (WLFI, GMX, BIGTIME, ADA, SEI, MNT, TURBO, ME, ETC)
- Phantom write blocked: BTC LONG trade 15705 — SL 0.052% from entry (safety working)

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

## Error Alerts — 2026-09-29 11:46 UTC
- **[WARN]** (120x/2h): `position_manager: FAILED (rc=1)` — Guardian lock contention. hermes-hl-sync-guardian.service holds lock, position_manager correctly defers. ATR/SL/TP work completes before exit. Cosmetic, no trading impact.
- **[WARN]** (1x): `Disk at 84%` — 19G free of 118G. 1% from 85% warn threshold. Consider compressing old logs (>7 days).
- **[WARN]** (1x): `ALGO SHORT loss streak=21` — Consecutive SHORT losses for ALGO. Cooldown active (1.5h). Will auto-resume.

## Error Alerts — 2026-09-29 11:58 UTC
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+NEUTRAL+AT, allowing despite TOK filter`
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.3s (rc=N)`

## Error Alerts — 2026-09-29 12:46 UTC
- **[WARN]** (continuous): `position_manager: FAILED (rc=1)` — Guardian lock contention (unchanged). Cosmetic only.
- **[WARN]** (1x): `ALGO SHORT loss streak=79` — Up from 21 at 11:46. Strategy effectively paused. Cooldown 1.5h per cycle.
- **[WARN]** (1x): `CHIP SHORT loss streak=34` — Cooldown expiring soon (~18min).
- **INFO**: Disk at 84% (19G free). No cleanup needed yet.
- **INFO**: Market regime LONG_BIAS. 5 tokens long, 0 short, 112 neutral.
- **INFO**: 11 trades today, 63.6% WR, +$0.33 USDT. 0 open positions.
- **INFO**: 5 tokens on 900h PUMP_RIDER block (LTC, BTC, ME, ACE, ALT) — intentional.

## Error Alerts — 2026-09-29 12:58 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.0s (rc=N)`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.2s (rc=N)`

## Error Alerts — 2026-09-29 15:58 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] TOK TOK — continuum says RECOVERY+TOK+TOK, allowing despite TOK filter`

## Error Alerts — 2026-09-29 16:58 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.0s (rc=N)`

## Error Alerts — 2026-09-29 17:48 UTC
- **WARN** (4x): `position_manager: FAILED in N.Ns (rc=1)` — Guardian lock contention, not a crash
- **WARN**: `BTC LONG loss streak = 97` — system keeps trying and losing
- **WARN**: Disk at 85% (18G free)
- **INFO**: 6 phantom trades with near-zero PnL

## Error Alerts — 2026-09-29 17:58 UTC
- **REPEATED** (11x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
- **REPEATED** (11x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.3s (rc=N)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   ✅ [TOK-TOK-OVERRIDE] CASHCAT TOK — continuum says DECLINING+LEAN_BEAR+TOK, allowing despite TOK filter`
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.7s (rc=N)`
