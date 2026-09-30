# Error Alerts

## Error Alerts — 2026-09-30 00:48 UTC
- **WARN** (1): `Disk at 85% (95G/118G)` — coin_tracker.db=3.3G, candles.db=2.2G, /var/log=3.4G
  - **AUTO-FIX (01:48)**: Vacuumed journal logs, freed 1.0G. Now 84% (94G/118G).
- **WARN** (Nx): `Phantom trade_id=15705 (BTC LONG)` — closed every cycle by UNIVERSAL_MAX_HOLD but persists. SL distance only 0.052% from entry.
  - **AUTO-FIX**: None. Known zombie trade. Requires manual DB cleanup or guardian code fix.

## Error Alerts — 2026-09-30 01:48 UTC
- **WARN** (1): `position_manager: FAILED in 0.8-3.5s (rc=1)` — every pipeline cycle for 30+ minutes. ATR SL/TP updates and position closes ARE completing successfully. rc=1 appears to be benign exit code from guardian lock contention, not a real failure.
  - **AUTO-FIX**: None. Work completes despite rc=1. Monitor for actual missed position management.
- **WARN** (1): `Loss cooldowns extreme` — COMP:LONG streak=83 (1.5h cooldown), ALGO:SHORT streak=43 (1.5h cooldown). These pairs are generating persistent losses.
  - **AUTO-FIX**: None. Loss cooldowns are working as designed. These pairs need signal quality review.
- **INFO**: `Market regime` — 10 LONG_BIAS, 0 SHORT, 106 NEUTRAL. Hotset empty — no signals survived compaction above 50% confidence. 5 active signals (SAGA, KLUNC, JUP, ETC, KPEPE). 19 trades in last 24h, 57.9% win rate, $0.30 PnL.

## Error Alerts — 2026-09-30 02:46 UTC
- **WARN** (Nx): `hermes-coding-mcp` in restart loop — 670,138 restarts, script missing (`run_mcp_server.py`)
- **AUTO-FIX**: Stopped + disabled `hermes-coding-mcp.service`
- **WARN**: Disk 84% used (19G free of 118G)
- **WARN**: BTC LONG loss streak=13 (1.5h cooldown active)
- **INFO**: Position manager "FAILED" = Guardian lock (hl-sync-guardian running). NOT a crash — working as designed.

## Error Alerts — 2026-09-30 04:58 UTC
- **REPEATED** (8x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.1s (rc=N)`

## Error Alerts — 2026-09-30 06:46 UTC
- **WARN** (1x): `disk 84%` — 18G free of 118G, approaching 85% threshold. Monitor.
- **INFO**: Market entirely neutral (116/116 tokens). 0 open trades. No signals above 50% confidence. Pipeline healthy, just quiet.
