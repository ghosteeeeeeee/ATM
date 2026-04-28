---
name: sync-open-trades
description: Reconcile open paper positions (trades.json) against live Hyperliquid positions and close orphaned entries in either direction.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, reconciliation, paper-trading, hyperliquid]
    input_files: [/var/www/hermes/data/trades.json]
  canonical_script: /root/.hermes/scripts/hype-paper-sync.py
---

# Sync Open Trades

Reconcile paper open positions (trades.json) against live Hyperliquid positions and close orphaned entries in either direction.

## Architecture

**Source of truth:** `/var/www/hermes/data/trades.json` (written by pipeline/hermes-trades-api)

**Legacy (DEPRECATED):** `brain.db` (PostgreSQL at 10.60.212.238) — no longer used for trades, DO NOT reference it

**Actual sync script:** `hype-paper-sync.py` — the working reconciliation tool that reads `trades.json` and compares against live HL positions

## Problem

`trades.json` can get out of sync with live HL positions:
- Positions marked open in trades.json but closed on HL (phantom paper entries)
- Positions open on HL but not in trades.json (orphan HL positions — rare, safety net closes them)

## Solution (via hype-paper-sync.py)

1. Load open positions from `trades.json` (key: `$.open`)
2. Load open positions from HL via `get_open_hype_positions_curl()`
3. Find tokens in paper but NOT on HL → orphaned paper entries (close them)
4. Find tokens on HL but NOT in paper → orphaned HL positions (close them on HL)
5. Matched tokens → confirmed in sync

## Usage

```bash
# Dry run (default — reads only, no changes)
cd /root/.hermes/scripts && python3 hype-paper-sync.py

# Live — actually close orphaned positions
cd /root/.hermes/scripts && python3 hype-paper-sync.py --apply
```

## What gets closed

- **Paper-only (no HL):** Marked as `ORPHAN_PAPER` in trades.json — no real HL trade
- **HL-only (no paper):** Closed on HL via `market_close` — real trade, then paper entry created with same ID and closed

## CRITICAL: The Guardian Reverts Manual trades.json Edits

**`hl-sync-guardian.py` runs as a separate process (PID tracked in logs) and rewrites `trades.json` from the postgres DB every 5 minutes.** If you manually edit trades.json to close a position, the guardian's next cycle will RE-INSERT that position back into trades.json (because it still exists in postgres as open).

**To properly close a position, you MUST close it in BOTH places:**

1. **Close on Hyperliquid** (if it exists there):
   ```bash
   cd /root/.hermes/scripts
   # Kill guardian first so it doesn't interfere
   kill $(pgrep -f hl-sync-guardian)
   sleep 2

   # Close on HL via API
   python3 -c "
   from hyperliquid_exchange import close_position
   close_position('MEW')
   "
   ```

2. **Close in postgres DB** (the source the guardian reads from):
   ```bash
   # Find the trade ID
   psql -U postgres -d brain -t -c \
     "SELECT id, token, status FROM trades WHERE token='MEW' AND status='open'"

   # Close it
   psql -U postgres -d brain -t -c \
     \"UPDATE trades SET status='closed', exit_price=0.000592, close_time=NOW(), close_reason='manual_close' WHERE id=<ID>\"
   ```

3. **Fix trades.json** (now it won't revert since postgres matches):
   ```python
   # Remove from open, add to closed in /var/www/hermes/data/trades.json
   ```

4. **Restart guardian**:
   ```bash
   cd /root/.hermes/scripts && nohup python3 hl-sync-guardian.py > /root/.hermes/logs/sync-guardian.log 2>&1 &
   ```

**The order matters:** Kill guardian → close in postgres → verify HL → fix trades.json → restart guardian.

**Why:** The guardian's `_update_trades_json_atr()` at line 2799 writes back to trades.json every cycle. It reads from postgres via `get_db_open_trades()` (psql query at line 518). As long as the trade exists in postgres as `status='open'`, the guardian will keep re-inserting it into trades.json.

**Simpler alternative:** Just close the position on HL. The guardian's orphan detection (Step 3) will automatically close the paper entry on its next cycle — no manual postgres edit needed.

## What This Skill Does NOT Check

This skill only reconciles **whether positions exist**, not **whether they should exist or have correct SL/TP settings**. It will report "synced" even when all positions are losing money due to:
- Wrong k multiplier for phase (e.g., k=1.0 for `phase=quiet` = too-tight SL)
- Market regime mismatch (opening LONGs during SHORT_BIAS regime)
- Stale ATR cache causing wrong SL computation

If trades are consistently hitting SL immediately, run `atr-sl-k-debug` to diagnose k multiplier issues.

## Safety rules

- Default is **dry-run** — pass `--apply` to execute closes
- Every action is logged before it runs
- In-memory dedup set prevents double-closing in one run
- Idempotent — already-closed trades are skipped
- **Never manually edit trades.json while the guardian is running** — your changes will be reverted
