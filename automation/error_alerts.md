# Error Alerts

## Error Alerts — 2026-09-17 23:44 UTC
- **WARN** (1x): `disk_usage` — disk at 84% (19G free), approaching 85% threshold. Monitor and compress old logs if it rises.
- **INFO**: `macro_gate_reduce` — macro gate REDUCE active (wr=20% < 30), system correctly throttling entries.

## Error Alerts — 2026-09-17 13:43 UTC
- **OK**: Pipeline health check passed. No WARN or CRITICAL issues detected.
- Pipeline running (cycle #203864), 10 active signals, 0 open trades, 83% disk.
- Auto-fixes applied: none needed.

## Error Alerts — 2026-09-17 13:56 UTC
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.2s (rc=N)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TOK decider_run: TOK (most recent call last):`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.1s (rc=N)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TOK position_manager: TOK (most recent call last):`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   hermes-trades-api: TOK in N.1s (rc=N)`
- **NEW** (2x): `Sep N N:N:N python3[TOK]: TS   TOK hermes-trades-api: TOK (most recent call last):`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: decider_run, position_manager, hermes-trades-api`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   signal_compactor: TOK in N.2s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   Signal bb_bounce_v2_short: TOK → TOK: cannot import name 'get_all_latest_prices' from 'signal_schema' (/root/.hermes/scripts/signal_schema.py)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   Signal bb_bounce_v3_long: TOK → TOK: unexpected indent (signal_schema.py, line N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   Signal return_exhaustion_short: TOK → TOK: cannot import name 'get_all_latest_prices' from 'signal_schema' (/root/.hermes/scripts/signal_schema.py)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   decider_run: TOK in N.1s (rc=N)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS WARNING: N steps failed: signal_compactor, decider_run, position_manager, hermes-trades-api`

## Error Alerts — 2026-09-17 14:56 UTC
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — MOMENTUM+BTC_LEVEL`
- **REPEATED** (3x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.1x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: -N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.0x eth_div=-N.N% | MOMENTUM: +N.N% (TOK blocked)`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK WARNING: +N.N% | layers: MOMENTUM,BTC_LEVEL | vol=N.3x eth_div=-N.N% | MOMENTUM: -N.N% (TOK blocked)`

## Error Alerts — 2026-09-17 16:56 UTC
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK 30m momentum -N.N% — blocking TOK entries`

## Error Alerts — 2026-09-17 18:45 UTC
- **[WARN]** Disk at 83% (93G/118G) — approaching 85% threshold
- **[INFO]** Winrate 18.75% (1h window) — signal_analyst REDUCE gate active
- **[INFO]** 16 trades closed today, -1.76 USDT PnL

## Error Alerts — 2026-09-17 19:56 UTC
- **REPEATED** (6x): `Sep N N:N:N systemd[N]: hermes-pipeline.service: Failed to kill control group /system.slice/hermes-pipeline.service, ignoring: Invalid argument`

## Error Alerts — 2026-09-17 20:44 UTC
- **WARN** (32x): `phantom_trades` — trades with <0.01% PnL in signal_outcomes
- **WARN** (1x): `macro_gate_reduce` — signal analyst macro gate: REDUCE (wr=20% < 30)
- **INFO** (4x): `systemd_kill_group` — "Failed to kill control group" — cosmetic, no impact
