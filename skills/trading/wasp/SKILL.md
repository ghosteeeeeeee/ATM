---
name: wasp
description: Hermes WASP — System Health & Anomaly Detector. Runs via systemd timer every 30min, checks signals DB, positions, HL mirror sync, trailing stops, cooldowns, regime, web API, and AI decider health. Logs to /root/.hermes/logs/wasp.log.
category: trading
---

# WASP — Hermes System Health & Anomaly Detector

## Quick Run
```bash
cd /root/.hermes/scripts && python3 wasp.py
# Full log: tail -50 /root/.hermes/logs/wasp.log
```

## What it checks

| Check | File | Key Issues to Watch |
|---|---|---|
| `check_signals()` | signals DB | stuck APPROVED signals, stale PENDING, duplicates |
| `check_ai_decider()` | signals DB | empty pending queue, 0 confidence signals |
| `check_positions()` | signals DB | NULL close_reason, per-token limits, stale mirror positions |
| `check_trailing_stops()` | signals DB | trailing not activated, TS activation ratio |
| `check_ab_testing()` | signals DB | cell_A vs cell_B win rate divergence |
| `check_regime()` | hype_live_trading.json | regime mismatch |
| `check_pipeline()` | systemd journal + logs | pipeline failures, double-runs |
| `check_mirror()` | hyperliquid_exchange.py | HL position count vs DB count |
| `check_web_api()` | /var/www/hermes/ | stale data files |
| `check_cooldowns()` | cooldowns.json | cooldowns file missing |
| `check_db_integrity()` | both DBs | DB file missing or empty |

## Common Issues & Fixes

### 34 APPROVED signals stuck >1h
- **Cause**: Position limit hit (10/10) — no room to execute
- **Fix**: Close some positions or raise limit in decider-run.py

### 14 trades NULL close_reason
- **Cause**: close_reason not recorded at close time
- **Fix**: Backfill from HL trade history (see brain skill: backfill historical trades)

### WASP cron not installed
- **Cause**: Old cron-based wasp was dead
- **Fix**: Already migrated to systemd (see systemd timer setup)

### 1 WAIT signal never re-reviewed (old label)
- **Cause**: Signals generated before threshold change have `[WAIT]` label in DB but aren't being picked up
- **Fix**: Either delete stale signals or re-run signal_gen

### Positions at limit (10/10)
- Normal when market is ranging and signals are firing
- Stops and trailing stops will free up slots

## Systemd Setup
```bash
# Install
cp hermes-wasp.service /etc/systemd/system/
cp hermes-wasp.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now hermes-wasp.timer

# Verify
systemctl list-timers --no-pager | grep wasp
journalctl -u hermes-wasp.service -n 10 --no-pager
```

## Log Location
- `/root/.hermes/logs/wasp.log` — full output
- `/root/.hermes/logs/wasp.err.log` — errors only
