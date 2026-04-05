---
name: sync-open-trades
description: Reconcile open paper positions (trades.json) against live Hyperliquid positions and close orphaned paper-only entries. Gracefully removes phantom positions that were never executed on HL.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, reconciliation, paper-trading, hyperliquid]
    input_files: [/var/www/hermes/data/trades.json]
---

# Sync Open Trades

Reconcile paper open positions against live HL positions and close orphaned paper-only entries.

## Problem

Paper trades.json can contain positions marked as "executed" that were never actually opened on Hyperliquid. This creates a sync gap between local (paper) and remote (HL) state.

## Solution

1. Load open positions from `/var/www/hermes/data/trades.json`
2. Load open positions from HL via `get_open_hype_positions_curl()`
3. Find tokens in paper but NOT on HL → these are orphaned paper entries
4. Gracefully close them from paper DB (mark as closed, no real HL trade)
5. Report mismatches

## Safety rules

- **NO real trades placed** — only closes paper entries that have no HL counterpart
- Uses hype-paper-sync.py dry-run logic but targets ONLY orphaned paper entries
- Logs every action before taking it
- Default is dry-run; must pass confirmation to apply
