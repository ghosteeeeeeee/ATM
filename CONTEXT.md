# CONTEXT.md — Hermes ATM
## Quick Status
```
WIN RATE:  46% (7d) | PNL: -$23.50 (7d) | POSITIONS: 8 open (all SHORT, all real HL)
BIAS: SHORT | LIVE TRADING: ON
```
**8 real HL positions (all SHORT):** MORPHO, ZORA, TRX, UNI, ASTER, ZEC, SKY, TST

## Active
- 8 open positions (real HL), all SHORT — Guardian actively mirroring
- hype_live_trading.json: ON (2026-04-05 05:45 UTC)
- Regime: SHORT bias
- DB: vacuum'd (signals compacted, 99 closed trades archived)

## Pipeline Health
- Pipeline: RUNNING ✅
- WASP: 0 ERRORS, 5 warnings (non-blocking) ✅
- WASP cron: INSTALLED ✅
- hermes-pipeline cron: restart needed (was stale since Apr 2)
- HL cache: FRESH ✅
- 222 stale momentum_cache entries: CLEARED ✅

## This Session (2026-04-05 ~05:40 UTC)
- **Emergency resolved:** live trading was OFF, pipeline verified healthy, re-enabled
- **Fix:** decider-run.py approved-signals loop now has regime check (was HOT-SET only)
- **Fix:** 222 stale momentum_cache entries cleared
- **Fix:** WASP cron installed (every 5min)
- **Fresh-run:** 99 closed trades archived, 11662 signals purged, DB vacuum'd
- **Git:** committed + pushed v3bcee80-20260405-0546

## Critical Bugs Fixed
- AAVE/STX contrarian trades: regime filter now applies to APPROVED signals path
- Guardian mirror_open: missing `import sys` (hyperliquid_exchange.py)

## Signal DBs
- Hermes: /root/.hermes/data/signals_hermes_runtime.db (local SQLite)
- OpenClaw: /root/.openclaw/workspace/data/signals.db (empty)
- Tokyo PG: not reachable (sleep mode)

## HL Wallet
- 0x324a9713603863FE3A678E83d7a81E20186126E7
- Fills: /root/.hermes/data/hl_fills_*_raw.csv (2000 fills, Mar 10-25 2026)

## In Flight / Known Issues
- 5 WAIT signals never re-reviewed: BIGTIME, SNX, ORDI, DYDX, ZETA
- 3 AB test variants with < 5 trades: entry-timing, trailing-stop (2 variants)
- 282 signals below 55% confidence in last hour (signal gen flooding)
- hype_live_trading.json is the KILL SWITCH — must be false to prevent real orders

---
*Updated: 2026-04-05 05:48 UTC*
