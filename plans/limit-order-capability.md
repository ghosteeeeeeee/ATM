# Plan: Limit Order Capability for Manual Trades

**Status:** PHASE 1 SHIPPED 2026-10-17 — `scripts/limit_order.py` (place/list/cancel subcommands, dry-run + confirm guards, HL min-notional check). Tested: dry-run sizing (SELL 0.00068 BTC @ 82100, 5x), live list API, min-notional rejection. Phases 2–4 (brain.py --limit, --tif on trade add, guardian fill-integration) DEFERRED until standalone is proven in use.

## Context
Manual trades currently use market orders via `brain.py trade add`. When the CEO identifies a setup at a specific price level (e.g., "SHORT at EMA180 rejection"), there's no way to place a limit order that fills at that price. The trade would need to be entered manually when price reaches the level.

## Current State
- `hyperliquid_exchange.place_order()` supports `order_type="Limit"` with `tif="Gtc"` (Good Till Cancelled)
- `brain.py trade add` uses market orders via `mirror_open()`
- No CLI/script to place a standalone limit order

## Goal
Add the ability to place limit orders for manual trades, so the CEO can set entry prices and let the market come to them.

## Implementation

### 1. Add `--limit` flag to `brain.py trade add`
```bash
python3 brain.py trade add BTC short 11.10 82100 --real --signal ai-trader-manual \
    --strategy ai-trader --confidence 70 --leverage 5 --sl 82300 --target 81500 \
    --limit  # places limit order instead of market
```

When `--limit` is passed:
- Use `place_order(coin, side, sz, price=entry, order_type="Limit", tif="Gtc")`
- Record trade with `status='pending'` in PostgreSQL
- Guardian/position manager picks up when filled

### 2. Add `--tif` flag for time-in-force
```bash
--tif Gtc    # Good Till Cancelled (default)
--tif Ioc    # Immediate or Cancel (partial fill ok)
--tif Alo    # Add Liquidity Only
```

### 3. Create standalone limit order script
```bash
python3 scripts/limit_order.py BTC short 82100 11.10 --sl 82300 --target 81500 --lev 5
```

Simpler interface for quick limit orders without full trade metadata.

### 4. Guardian integration
- Guardian already monitors open positions
- Need to add: check for pending limit orders
- When limit order fills, create trade entry automatically

## Example Use Case: BTC SHORT at EMA180
```bash
# Place limit SHORT at EMA180 rejection
python3 brain.py trade add BTC short 11.10 82100 --real --signal ai-trader-manual \
    --strategy ai-trader --confidence 70 --leverage 5 --sl 82300 --target 81500 --limit

# If BTC rises to 82100, order fills automatically
# If BTC drops without hitting 82100, order stays open (Gtc)
# If CEO changes mind, cancel: python3 scripts/cancel_order.py BTC
```

## Files to Modify
1. `brain.py` — add `--limit` and `--tif` flags
2. `scripts/limit_order.py` — new standalone script
3. `hl-sync-guardian.py` — monitor pending limit orders
4. `hyperliquid_exchange.py` — add `cancel_order()` helper

## Priority
**Medium** — useful for precise entries but not blocking current trading. The watchdog picks at market price which works for most setups.

## Date
2026-10-13 — Created while analyzing BTC MACD divergence setup at EMA180.
