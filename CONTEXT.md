# CONTEXT.md — Hermes ATM
## Quick Status
```
PIPELINE: RUNNING ✅ | HOTSET: 3 tokens (SCR/BTC/ETH SHORT) | LIVE TRADING: ON
REGIME: SHORT_BIAS | POSITIONS: 9 open | UPTIME: +21.29% today
Updated: 2026-04-08 18:13 UTC
```
**10 open positions (brain DB):** 2 SHORT (DYDX, SKY), 8 LONG (UMA, SCR, ICP, AVAX, AXS, ETHFI, SAND, XRP)

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

## This Session (2026-04-08 ~07:20 UTC)
- **Building:** CONTEXT.md Per-Call System — auto-refresh cron, SOUL.md Context Anchor, brain.md File Anchors
- **Building:** hermes_write_with_lock.py — flock-based write lock to prevent concurrent write collisions
- **Building:** sync_kanban_tasks.py — bidirectional TASKS.md ↔ kanban.json sync
- **Building:** hermes-brain-sync.timer — daily 6am EST deep PM audit via project-manager-senior subagent
- **Live trading:** ON — DO NOT change hype_live_trading.json

## Critical Bugs Fixed
- AAVE/STX contrarian trades: regime filter now applies to APPROVED signals path
- Guardian mirror_open: missing `import sys` (hyperliquid_exchange.py)

## Signal DBs
- Hermes: /root/.hermes/data/signals_hermes_runtime.db (local SQLite)

## HL Wallet
- 0x324a9713603863FE3A678E83d7a81E20186126E7
- Fills: /root/.hermes/data/hl_fills_*_raw.csv (2000 fills, Mar 10-25 2026)

## In Flight / Known Issues
- 5 WAIT signals never re-reviewed: BIGTIME, SNX, ORDI, DYDX, ZETA
- 3 AB test variants with < 5 trades: entry-timing, trailing-stop (2 variants)
- 282 signals below 55% confidence in last hour (signal gen flooding)
- hype_live_trading.json is the KILL SWITCH — must be false to prevent real orders

## PENDLE/MET TP/SL Issue (Fixed 2026-04-08)
- PENDLE/MET TP/SL on HL were failing: "Invalid TP/SL price" — missing from _HL_TICK_DECIMALS
- Fix: Added PENDLE→4 decimals, MET→5 decimals to hyperliquid_exchange.py
- PENDLE/MET still underwater (PENDLE entry=1.033, curr≈1.027; MET entry=0.1357, curr≈0.134)
- Plan A: HL TP/SL (fix deployed in guardian, needs 1 cycle to apply)
- Plan B: Internal breach detector added to guardian (Step 11) — fires market close if SL/TP breached
- ETH has 6 stale limit orders (not trigger orders) — from old code path, not harmful but messy
- Guardian restarted with new code (PID 2988175)

---
*Updated: 2026-04-08 07:30 UTC*
