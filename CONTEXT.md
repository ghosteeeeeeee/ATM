# CONTEXT.md — Hermes ATM
## Quick Status
```
WIN RATE:  43% (7d) | PNL: -$26.56 (7d) | POSITIONS: 5 open / 10 max
BIAS: SHORT | LIVE TRADING: OFF (emergency-off)
```
**5 real HL positions:** TRX, UNI, MORPHO, ZORA, ASTER — all SHORT

## Active
- 5 open positions (real HL), all SHORT
- Regime: SHORT bias
- DB: 172MB (signal_archiver + vacuum needed)
- 5 stale momentum_cache entries > 2h old

## This Session (2026-04-05 ~05:30 UTC)
- **EMERGENCY:** hype_live_trading.json was LIVE — 10 paper trades executed as real HL orders
  - Guardian's mirror_open() was the execution path (decider-run hardcodes paper=True)
  - Guardian closed 10 phantom trades when HL didn't confirm positions (APE, STX, AAVE, etc.)
  - 5 real HL positions remain (TRX, UNI, MORPHO, ZORA, ASTER — all SHORT)
  - hype_live_trading.json → `{"live_trading": false, "reason": "emergency-off"}`
- **Fix applied:** decider-run.py approved-signals loop now has regime check (was HOT-SET only)

## In Flight
- WASP service: broken since 03:06
- 5 stale momentum_cache entries > 2h old
- 297 signals below 55% confidence in last hour (signal gen flooding)

## Decisions Made
- Live trading KILL SWITCH: /var/www/hermes/data/hype_live_trading.json — must be false to prevent real orders
- Signal DB: /root/.hermes/data/signals_hermes_runtime.db (local SQLite) — Tokyo PG not reachable
- PnL dashboard: accurate — computed live from prices, DB only writes on close

---
*Updated: 2026-04-05 05:38 UTC*
