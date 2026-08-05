# Hot-Set Entry Price vs Actual HL Fill Price Discrepancy

## The Problem

Trades opened through the hot-set pipeline (signal_compactor → hotset.json → decider_run → brain.py → HL) record `entry_price` from the signal price — which is derived from `hype_cache` mid prices — NOT from the actual HL fill price.

**Example (June 11 2026):**
- PEOPLE LONG opened 17:34:07: DB entry_price=0.005406, actual HL fill=0.005427, delta=+0.39%
- UNI SHORT opened 17:38:07: DB entry_price=2.5356, actual HL fill=2.5000, delta=-1.43%

This is NOT the guardian's fault — the hot-set pipeline opened these trades at the wrong price. The guardian later synced `hl_entry_price` but the wrong `entry_price` is what gets used for PnL calculations until corrected.

## Why It Happens

1. `signal_compactor` builds hotset.json with signal prices (from `hype_cache` mids)
2. `decider_run` reads hotset.json, executes trades via `brain.py add_trade()`
3. `brain.py mirror_open()` uses `entry_price` parameter for size calculation
4. `mirror_open()` returns the actual HL fill price in `result['entry_price']`
5. `brain.py add_trade()` stores BOTH `entry_price` (signal price) AND `hl_entry_price` (HL fill price) — but only if `mirror_open()` returns it
6. If `mirror_open()` doesn't return the fill price (e.g. no HL fill data), `hl_entry_price` stays 0

## Key Insight — Two Entry Prices Stored

```sql
entry_price     -- signal price / hype_cache mid (WRONG, from signal time)
hl_entry_price  -- actual HL fill price (CORRECT, from HL fills)
```

PnL calculations should use `hl_entry_price`. Most code uses `entry_price` — hence wrong PnL.

## Diagnostic

```sql
-- Find trades where entry_price and hl_entry_price differ significantly
SELECT id, token, direction, entry_price, hl_entry_price,
       ROUND((entry_price - hl_entry_price) / NULLIF(hl_entry_price, 0) * 100, 4) AS entry_delta_pct,
       pnl_pct, pnl_usdt, open_time
FROM trades
WHERE hl_entry_price > 0
  AND abs(entry_price - hl_entry_price) / NULLIF(hl_entry_price, 0) > 0.001
ORDER BY open_time DESC LIMIT 20;
```

## The Fix Path

The hot-set pipeline needs to:
1. Fetch actual HL open fill price after `mirror_open()` confirms the position
2. Update `hl_entry_price` in the DB record immediately after confirmation
3. Signal quality / PnL calculations should prefer `hl_entry_price` over `entry_price`

This is a `brain.py` fix — after `mirror_open()` succeeds, poll HL fills for the actual open price and update the trade record.
