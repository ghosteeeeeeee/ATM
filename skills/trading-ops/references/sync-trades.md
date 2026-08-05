---
name: sync-trades
description: Reconcile Hyperliquid real trades with Hermes paper DB — populate signal_outcomes from HL fills CSV without placing any trades. Filters out HFT micro-fills (<$0.10 |pnl|).
version: 1.0.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, hyperliquid, reconciliation, signals]
    input_files: [data/hl_fills_<addr>.csv]
    output_db: [data/signals_hermes_runtime.db]
---

# Sync Trades — HL → Hermes Reconciliation

Reconstructs closed trades from the HL fills CSV and populates `signal_outcomes`
in `signals_hermes_runtime.db`. Safe, read-only on HL side — no orders placed.

## Key decisions

- **Each CSV row = one fill** (not one trade). Group by coin, pair open→close.
- **Filter HFT noise**: skip fills with |closedPnl| < $0.10 (removes ~500 micro-fills).
- **Skip bad coins**: STG, STRAX (known pump signal garbage).
- **Dedup key**: (token, ROUND(pnl_usdt,4), closed_at) — upserts by this key.
- **No existing overlap**: HL fills are March 10-25; DB has April 1+ outcomes.

## Run

```bash
# Dry run first (default)
python3 skills/trading/sync-trades/scripts/sync_trades.py

# Write to DB
python3 skills/trading/sync-trades/scripts/sync_trades.py --no-dry-run
```

## Recent results (2026-04-03)

- 51 trades synced from HL fills (|pnl| >= $0.10)
- 26W/25L, net_pnl = -$2.06
- DB now has 261 total outcomes

## Safety rules

- **NO trades placed** — read CSV only
- Upsert by dedup key — never duplicate outcomes
- Skip still-open positions (1 fill = no close found)
