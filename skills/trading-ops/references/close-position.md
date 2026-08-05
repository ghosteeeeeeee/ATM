---
name: close-position
description: Close a specific Hyperliquid position by coin symbol AND sync to paper trades.json + brain PostgreSQL. After HL close fills, fetches the exit price, updates paper with reason=manual_close, and closes the brain trade. Records loss cooldown (wins do NOT trigger cooldown).
version: 1.3.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, hyperliquid, close, sync]
notes:
  - get_trade_history() returns 422 for many coins — always fall back to avgPx from close result
  - Must close in BOTH postgres (brain) AND trades.json — guardian reads from postgres and will re-insert if only trades.json is updated
  - Only LOSSES trigger cooldown — wins do NOT block re-entry
  - Win cooldowns were removed from position_manager.py entirely
---

# Close Position

Close a specific Hyperliquid position by coin symbol. **Full stop-the-line sync** — updates HL, paper trades.json, and brain PostgreSQL in one shot.

## ⚠️ Critical: Postgres-First Reconciliation

**The guardian reads from postgres, NOT trades.json.** If you manually edit trades.json without closing the trade in postgres, the guardian will re-insert the position on its next cycle (every 5 min) — clobbering your edit.

To close a position cleanly, you MUST close in BOTH:
1. HL (via this skill)
2. Postgres (`UPDATE trades SET status='closed' WHERE token='XMR' AND status='open'`)

This skill does both. If you only edit trades.json, the guardian will undo your changes.

## Usage

```
/close-position STRK
/close-position BTC
/close-position ETH
```

## How it works

1. Calls `close_position(coin)` on Hyperliquid (real market order)
2. Verifies the position is gone from HL
3. Fetches exit price from `get_trade_history()` (last fill = exit price)
   - NOTE: `get_trade_history()` does **NOT** accept a `limit` kwarg
4. Removes coin from paper `trades.json` open, appends to closed with `reason: manual_close`
5. Closes the corresponding brain PostgreSQL trade with `exit_reason: manual_close`
6. Reports final state across all 3 stores (HL / Paper / Brain)

## Exit Price — Primary + Fallback

Exit price is fetched from `get_trade_history()` (last fill = exit price).

**If `get_trade_history()` fails (422 or network error):** do NOT default to 0.0 — extract `avgPx` from the `close_position()` result's filled status instead:
```python
statuses = result.get('result', {}).get('response', {}).get('data', {}).get('statuses', [])
if statuses and 'filled' in statuses[0]:
    exit_price = float(statuses[0]['filled'].get('avgPx', 0))
```
This has proven reliable across XMR, INIT, LAYER and other coins where `get_trade_history()` returns 422 after a fill.

## Notes

- Uses `hyperliquid_exchange.close_position()` — same function guardian uses
- Works on **live HL positions only**
- `reason=manual_close` distinguishes operator closes from guardian/ATR stops
- After using this skill, **do not** run `sync-open-trades` separately — the close is already synced

## ⚠️ Critical: Do NOT Run Multiple Closes in Parallel Against Same File

`trades.json` is a plain JSON file with no locking. Running multiple `close_position.py` instances simultaneously causes concurrent read/write races that corrupt the file mid-operation (JSONDecodeError on partial writes). HL closes will succeed, but paper sync will fail on some coins.

**Rule: close positions sequentially, never in parallel, unless you have a distributed lock on trades.json**
