## Error Alerts — 2026-09-19 08:45 UTC
- **[WARN]** (1x): `breakout_engine timed out (killed after 60s)` at 08:35 — recovered on next cycle
- **[WARN]** (1x): `signal_compactor timed out (killed after 60s)` at 08:42 — recovered on next cycle
- **[INFO]**: 8 support services in failed state (5m-candle, better-coder, away-detector, etc.) — none blocking pipeline
- **[WARN]**: Disk at 83% — approaching 85% threshold
- **[NOTE]**: hermes-5m-candle dead since Sep 11 (8 days) — no candles_5m table in runtime DB

## Error Alerts — 2026-09-19 08:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS TOK breakout_engine: timed out (killed after N.0s)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: breakout_engine`

## Error Alerts — 2026-09-19 09:56 UTC
- **REPEATED** (7x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — CONTAGION+MOMENTUM`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: CONTAGION,MOMENTUM | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.0x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.6x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-19 10:44 UTC
- **OK**: Pipeline running normally, 0 errors in last 30min
- **OK**: 6 open trades, 47 closed today, +21.87% PnL
- **OK**: All timers firing on schedule
- **INFO**: Disk at 84% — 1% below WARN threshold
- **INFO**: Regime LONG_BIAS (4 long, 1 short, 113 neutral across 118 tokens)

## Error Alerts — 2026-09-19 10:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: CONTAGION,MOMENTUM | vol=N.2x eth_div=+N.N% | MOMENTUM: -N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: TOK,CONTAGION | vol=N.3x eth_div=+N.N%`

## Error Alerts — 2026-09-19 11:56 UTC
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Error Alerts — 2026-09-19 12:45 UTC
- **OK**: Pipeline running normally, 0 errors in last 30min
- **OK**: 4 open trades, 47 closed today, +28.81% PnL
- **WARN**: Hotset empty — 0 signals survived compaction this cycle
- **INFO**: Disk at 84% — 1% below WARN threshold
- **INFO**: 32 phantom trades (|pnl_pct|<0.01%) — 201 near-zero PnL fills total
- **INFO**: Regime LONG_BIAS (4 long, 1 short, 113 neutral across 118 tokens)

## Error Alerts — 2026-09-19 13:45 UTC
- **OK**: Pipeline last run 13:43 — completed in 26s, no errors
- **OK**: 3 open trades (CAKE SHORT, DOGE LONG, BABY LONG), 36 closed today
- **OK**: PnL +37.18% (pipeline), -0.77 USDT (DB absolute)
- **WARN**: signal_compactor timed out (60s) at 13:37 — auto-recovered, next runs 0.8-3.7s
- **WARN**: Hotset empty — 0 signals survived compaction (continuing from 12:45)
- **INFO**: Regime NEUTRAL (3 long, 3 short, 113 neutral across 119 tokens) — quiet market
- **INFO**: Disk 84% — 1% below WARN threshold (unchanged)
- **INFO**: HL sync guardian active, pipeline service idle (normal after completion)
- **INFO**: No hermes timers listed — pipeline triggered by external mechanism

## Error Alerts — 2026-09-19 14:56 UTC
- **REPEATED** (4x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum +N.N% — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.0s)`

## Error Alerts — 2026-09-19 15:56 UTC
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS TOK signal_compactor: timed out (killed after N.1s)`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor`

## Error Alerts — 2026-09-19 16:56 UTC
- **REPEATED** (15x): `Sep N N:N:N python3[TOK]: TS   TS   ← mark_signal_executed returned: N (N=failed/already-claimed, N=success)`

## Error Alerts — 2026-09-19 17:56 UTC
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM`
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`
