# Health Report — 2026-08-24 14:21 UTC

## PIPELINE: OK (with fixes applied)
- **Status**: running (active)
- **Cycles (1h)**: 58 completed
- **Signals (1h)**: 168 generated (11 types: support_resistance, macd_divergence_short, signal_confluence lead)
- **Trades**: 5 open, 82 closed today
- **PnL**: -6.99% (was +15.30% at 13:56, dropped during cascade flip window)
- **Errors**: 6 position_manager FATAL (fixed), 1 signal_compactor traceback (non-fatal)

## MARKET
- **Regime**: SHORT_BIAS (7 short, 0 long, 98 neutral across 105 tokens)
- **Speed**: 239 tokens tracked
- **Hotset**: 9 tokens (STX active as #1 candidate)

## SYSTEM
- **Services**: hermes-pipeline=active, hermes-hl-sync-guardian=active
- **Timers**: 0 hermes-* timers listed (pipeline runs via systemd service, not timer)
- **Disk**: 84% used (93G/118G) — 1% from WARN threshold
- **Prices**: Fresh (updated 14:21 UTC)

## AUTO-FIXES APPLIED
1. **cascade_flip.py:31** — Added `compute_pnl_usdt` to import from pnl_utils. Root cause of 6 position_manager crashes. Verified import works.

## ALERTS
- **CRITICAL (fixed)**: position_manager crashing on cascade flip — missing import in cascade_flip.py
- **WARN**: Disk at 84% — compress old logs if >85%
- **WARN**: PURRUSDT Binance 400 errors — symbol may be delisted
- **WARN**: signal_compactor truncated traceback (1x, non-fatal)
