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
