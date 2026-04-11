# CONTEXT.md — Hermes ATM
## Quick Status
```
PIPELINE: ERROR (last run 72+00:0) | WASP: unknown
LIVE TRADING: ON ✅ | POSITIONS: 9 open, 53 closed (brain)
REGIME: UNKNOWN
Updated: 2026-04-11 05:54 UTC
```

## Critical Flags
- CASCADE_FLIP_ENABLED = False (position_manager.py line 78)
- hype_live_trading.json: ON — kill switch for live trading
- Guardian: running (hl-sync-guardian.service)

## Active
- hype_live_trading.json: ON (2026-04-05 05:45 UTC)
- Regime: SHORT bias
- CASCADE_FLIP_ENABLED = False (kill switch active)

## Pipeline Health
- Pipeline: RUNNING (hermes-pipeline.timer systemd)
- WASP: check via hermes-wasp.timer
- HL cache: FRESH

## Signal DBs
- Hermes: /root/.hermes/data/signals_hermes_runtime.db (local SQLite)

## HL Wallet
- 0x324a9713603863FE3A678E83d7a81E20186126E7
- Fills: /root/.hermes/data/hl_fills_*_raw.csv (2000 fills, Mar 10-25 2026)

## This Session (2026-04-10 15:38 UTC)
- T: cascade-flip disabled? CASCADE_FLIP_ENABLED=False confirmed
- Git repo packaged: ATM-Hermes-20260410-1536-full-5622130.zip → /var/www/git/
- index.html updated with latest zip
- context-compactor migrated: cron → hermes-context-compactor.timer (systemd)
- SESSION START hash enforcement wired: /root/.hermes/data/CONTEXT_MD_HASH.txt

## In Flight / Known Issues
- Cascade-flip: DISABLED pending revisit

---
*Updated: 2026-04-11 05:54 UTC*
