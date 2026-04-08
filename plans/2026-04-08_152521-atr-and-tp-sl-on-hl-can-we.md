# Plan: ATR-Trailing TP/SL on Hyperliquid

## Goal
Ensure ATR-based SL/TP orders on Hyperliquid trail with price — every time local DB computes a new ATR value, HL orders are updated to reflect the new price anchors.

---

## Current State (What Already Works)

The ATR-adaptive TP/SL pipeline already exists:

1. `sync_open_trades` (position_manager.py, step 7) calls `_collect_atr_updates(positions)`
2. `_collect_atr_updates` force-fetches ATR for each token, recomputes SL/TP anchored to `current_price` (live mids), and flags updates where delta > `ATR_UPDATE_THRESHOLD_PCT` (0.3%)
3. `_execute_atr_bulk_updates` cancels stale reduce-only orders and places new SL+TP in 2 bulk HL calls

The SL is already anchored to `current_price` (line 1152: `ref_price = current_price if current_price > 0 else entry_price`), so it moves with price each cycle.

---

## Problems Found

### BUG 1 (Critical): Cancel-All vs. Selective Cancel
`_execute_atr_bulk_updates` (line 1225–1231) cancels **ALL** reduce-only orders for a token whenever **any** SL or TP on that token needs updating. This means:
- If Token A has SL drift but TP unchanged → TP order is still cancelled and not re-placed
- If Token B has no changes but shares a cancel batch with Token A → Token B's orders are nuked

**Fix**: Track per-order OIDs. Only cancel the specific SL+TP orders that need to move.

### BUG 2: Position size truncation for DYDX
HL returns `sz=99.9` for DYDX but actual size is `100.0`. `get_open_hype_positions` may be rounding/truncating:
```python
sz_map[coin_name.upper()] = abs(float(p.get('size', 0) or 0))
```
HL uses integer-based sizing internally. For DYDX (szDecimals=1), `99.9` rounds to `99` or `100` depending on rounding direction.

**Fix**: Check if HL returns fractional sizes; if so, look at `npos` (net position) or use the raw integer.

### Missing: HL tokens LINK, SAND, ETHFI
`_HL_TICK_DECIMALS` has entries for these (line 1068–1077) but the decider/guardian may not include them in the active token list. Confirmed missing from HL orders as of 2026-04-08.

---

## Proposed Changes

### 1. Fix `_execute_atr_bulk_updates` — selective cancel by OID tracking

**File**: `position_manager.py`

**Approach**: Instead of cancelling all reduce-only orders for affected tokens, track which specific SL+TP OIDs are currently on HL for each trade, then only cancel those OIDs.

Implementation options:
- **Option A (recommended)**: Have `_collect_atr_updates` also fetch the current open orders for affected tokens and map trade_id → {sl_oid, tp_oid}. Pass this to `_execute_atr_bulk_updates` so only those OIDs are cancelled.
- **Option B**: Use HL's `cancelByCloid` with client order IDs (cloids) — each SL/TP gets a stable cloid, cancel by cloid instead of OID.

### 2. Add trailing logic — SL only moves in profit direction

**Current**: SL = `ref_price * (1 - k*atr_pct)` — moves both ways as price fluctuates.

**Desired**: For LONG, if `new_sl <= old_sl` (SL would move down into a loss), skip. Only move SL up. Same for SHORT in reverse.

```python
# In _collect_atr_updates, after computing new_sl:
if direction == "LONG":
    if new_sl <= current_sl:  # only tighten, never loosen
        new_sl = current_sl
        needs_sl = False
elif direction == "SHORT":
    if new_sl >= current_sl:  # only tighten, never loosen
        new_sl = current_sl
        needs_sl = False
```

Same trailing logic for TP (TP only moves in profit direction, TP typically moves away from price for LONG).

### 3. Fix DYDX size — verify integer-based sizing

**File**: `hyperliquid_exchange.py`

In `get_open_hype_positions`, investigate how HL returns sizes. Add logging to capture raw size values. If HL returns fractional for DYDX, use `ceil` or `round` appropriately.

### 4. Reduce HL API calls — single open_orders per cycle

**Current**: `_execute_atr_bulk_updates` calls `exchange.info.open_orders()` once (good). But `get_open_hype_positions()` also calls the exchange separately.

**Optimization**: Cache the open orders result and reuse across both calls within the same cycle. This saves 1 API call/cycle.

### 5. (Optional) Use `grouping="positionTpsl"` for native HL TP/SL linking

HL's `grouping: "positionTpsl"` option links TP+SL to the same position. This is already available in `place_bulk_orders(grouping="positionTpsl")`. Consider using it to prevent orphaned orders.

---

## Step-by-Step Implementation Plan

### Step 1: Fix selective cancel (BUG 1)
- [ ] Modify `_collect_atr_updates` to also fetch open orders for affected tokens
- [ ] Build a `trade_id → {sl_oid, tp_oid}` mapping from open orders
- [ ] Pass this map to `_execute_atr_bulk_updates`
- [ ] Cancel only those specific OIDs instead of all reduce-only for the token
- [ ] Verify: add logging showing which OIDs were cancelled/placed

### Step 2: Add trailing SL logic (New Feature)
- [ ] Modify `_collect_atr_updates` to only move SL in profit direction
- [ ] Apply same logic to TP (only moves in profit direction)
- [ ] Test with simulated price movements

### Step 3: DYDX size investigation (BUG 2)
- [ ] Add debug logging in `get_open_hype_positions` for DYDX
- [ ] Verify raw HL size response vs. displayed size
- [ ] Fix size handling if needed

### Step 4: Open orders caching (Optimization)
- [ ] In `_execute_atr_bulk_updates`, pass already-fetched open orders
- [ ] Avoid duplicate `open_orders()` call per cycle

### Step 5: Verify end-to-end
- [ ] Run `sync_open_trades` with debug output
- [ ] Confirm SL moves correctly on BTC, DYDX
- [ ] Check no spurious order cancellations

---

## Files to Change

| File | Change |
|------|--------|
| `position_manager.py` | `_collect_atr_updates`: add trailing logic + fetch open orders for OID mapping. `_execute_atr_bulk_updates`: selective cancel by tracked OIDs |
| `hyperliquid_exchange.py` | `get_open_hype_positions`: DYDX size investigation |

---

## Validation

1. Run `python3 -c "from position_manager import sync_open_trades; sync_open_trades()"` with debug logging
2. Confirm BTC/DYDX SL orders reflect current ATR-based prices
3. Confirm only the intended OIDs are cancelled (check HL open orders before/after)
4. Confirm no regression: existing positions still have correct SL/TP

---

## Risks & Tradeoffs

- **Risk**: Changing cancel logic could leave orphaned orders if OID tracking is wrong. Mitigate: always verify open orders count after update.
- **Tradeoff**: Trailing SL (only moving in profit direction) may result in larger drawdowns before exit, but prevents getting stopped out by normal volatility.
- **Open question**: Should TP also be trailing (moves away from price as profit increases), or stay fixed at a target? T to clarify — current code uses `tp_pct = 2 * k * atr_pct` as a fixed multiplier, not trailing.
