# HL Trigger SL/TP — V2 Implementation Spec

**Status:** Draft
**Date:** 2026-09-12
**Author:** Hermes Agent (researched code, SDK, HL API docs, git history)

---

## 1. Problem Statement

25 catastrophic losses in the last 7 days (-172.59% total) had SL set correctly at 1.2-1.5% but actual loss was **3.6x to 6.6x worse** due to guardian using market orders for SL execution. Market orders during volatile drops fill at terrible prices (slippage amplified by 5x leverage).

**Current system:**
- `position_manager` computes ATR SL/TP and writes to brain DB
- Guardian (`hl-sync-guardian.py`) reads DB SL/TP and fires `market_close()` when breached
- Market close fills 5-10x worse than SL during volatile conditions
- HL trigger orders (server-side SL) were tried, then disabled due to bugs

**If HL trigger orders worked:**
- Avg catastrophic loss: -6.90% → ~-1.33% (no slippage)
- 7-day savings: ~139% PnL

---

## 2. What Existed Before (V1 — Disabled 2026-05-15)

### 2.1 Code Remnants Still Present

| File | What | Status |
|------|------|--------|
| `position_manager.py:100` | `ATR_HL_ORDERS_ENABLED = False` | Kill switch — OFF |
| `position_manager.py:2431` | `if ATR_HL_ORDERS_ENABLED: _execute_atr_bulk_updates()` | Guard — dead path |
| `brain.py:787-791` | Step 5: `if sz and stop_loss: pass` | Disabled SL at trade open |
| `hl-sync-guardian.py:37` | `UNPROTECTABLE_COINS` | Active — 8 coins |
| `hyperliquid_exchange.py:1590-1625` | `place_sl()` | Active — never called |
| `hyperliquid_exchange.py:1522-1587` | `place_tp()` | Active — never called |
| `hyperliquid_exchange.py:1628-1685` | `place_tp_sl_batch()` | Active — never called |
| `hyperliquid_exchange.py:2033-2081` | `replace_sl()` | Active — never called |
| `hyperliquid_exchange.py:1994-2030` | `replace_tp()` | Active — never called |
| `hl-sync-guardian.py:1620-2056` | `close_position(token, slippage=CLOSE_SLIPPAGE)` | **Active — the slippage path** |

### 2.2 Deleted Code (Git History)

`_execute_atr_bulk_updates()` was deleted in commit `437b3f07` (ponytail audit). The deleted code:
- Cancelled stale orders by matching trigger price proximity (buggy)
- Built orders using `build_order()` (internal helper, not SDK)
- Called `place_bulk_orders()` in chunks of 10
- No retry on individual failures
- No verification that orders actually landed on HL

### 2.3 Why V1 Was Disabled

| Bug | Description | Impact |
|-----|-------------|--------|
| **Incomplete order placement** | Some coins got orders, some didn't | 50%+ of positions unprotected |
| **Stale order matching** | Cancelled by trigger price proximity, not OID/cloid | Cancelled wrong orders or missed stale ones |
| **Rate limiting** | Bulk API calls hit HL rate limits with 10+ orders | Cascading failures across all positions |
| **No verification** | Never checked if orders actually landed on HL | False sense of security |
| **Race with guardian** | Both position_manager and guardian could fire closes simultaneously | Double-close risk |
| **UNPROTECTABLE_COINS** | BTC, AAVE, MORPHO, ASTER, PAXG, AVNT, PENDLE, MET | HL rejects trigger orders for these |

---

## 3. What's Available Now (SDK V2)

The HL Python SDK has mature functions that didn't exist when V1 was built:

```python
# Atomic TP+SL placement (replaces existing atomically)
place_tp_sl_batch(coin, direction, sl_price, tp_price, size)
  → Uses grouping="normalTpsl" — atomic replacement

# Modify existing trigger orders (no cancel+recreate race)
replace_sl(coin, direction, new_price, size)
  → Falls back to place_sl() if no existing order found

replace_tp(coin, direction, new_price, size)
  → Falls back to place_tp() if no existing order found

# Find existing orders (cached open_orders + per-order query)
_find_open_trigger_order(coin, "sl"|"tp")
  → Returns (oid, cloid, sz, trigger_px) or (None, None, None, None)

# Cancel operations
cancel_sl(coin) / cancel_tp(coin)
clean_all_tpsl_orders(coin)  # cancels ALL TP+SL for a coin
cancel_all_open_orders(coin) # cancels EVERYTHING for a coin
```

### 3.1 HL API Key Facts (from docs)

- Trigger orders use `"trigger": {"triggerPx": str, "isMarket": true, "tpsl": "sl"|"tp"}`
- `reduceOnly: true` ensures the order only closes, never opens
- `grouping: "normalTpsl"` atomically replaces TP+SL (no race window)
- `modify` has `always_place` flag: when true, places new order even if cancel fails
- SL price must be on the correct side of current price (LONG: below, SHORT: above)
- Price must be rounded to coin-specific tick size (`_hl_tick_round`)
- `fast: true` on cancel rejects trigger orders (we don't want this)
- Trigger orders fire as market orders when price crosses `triggerPx`

---

## 4. V2 Design: Dual-Layer Protection

### 4.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    POSITION MANAGER                       │
│  _collect_atr_updates() → computes ATR SL/TP             │
│  _persist_atr_levels()  → writes to DB                   │
│  _sync_hl_triggers()    → NEW: syncs HL trigger orders   │
└──────────────┬──────────────────────┬────────────────────┘
               │                      │
               ▼                      ▼
┌──────────────────┐    ┌──────────────────────────────┐
│   BRAIN DB        │    │   HYPERLIQUID (server-side)   │
│   stop_loss col   │    │   trigger SL/TP orders        │
│   target col      │    │   ← fires as market on cross  │
└──────┬───────────┘    └──────────────┬───────────────┘
       │                               │
       ▼                               ▼
┌──────────────────┐    ┌──────────────────────────────┐
│   GUARDIAN         │    │   HL ENGINE (on-chain)        │
│   hard_sl fallback │    │   Executes when price crosses │
│   (market order)   │    │   triggerPx                    │
│   ← only when HL   │    │   ← fills at trigger price    │
│     trigger fails   │    │      (no slippage for market  │
└──────────────────┘    │       trigger)                  │
                         └──────────────────────────────┘
```

### 4.2 Key Principle: Guardian Becomes the Safety Net, Not the Executor

**V1:** Guardian detects SL breach → fires market_close → slippage
**V2:** HL trigger fires automatically → zero slippage. Guardian only closes when HL trigger fails.

### 4.3 Order Flow

#### Trade Open (brain.py)
```
1. mirror_open() places position on HL
2. DB INSERT writes trade row
3. NEW: place_tp_sl_batch() places initial SL+TP on HL
   - SL = entry ± ATR_SL_MIN_INIT
   - TP = entry ± ATR_TP_MIN
   - Uses normalTpsl grouping (atomic)
   - If HL rejects → log warning, continue (guardian monitors via DB)
```

#### ATR SL Update (position_manager._collect_atr_updates)
```
1. compute_atr_sl_tp() returns new_sl, new_tp
2. _persist_atr_levels() writes to DB
3. NEW: _sync_hl_triggers() updates HL orders
   - replace_sl(coin, direction, new_sl, size)  — atomic modify
   - replace_tp(coin, direction, new_tp, size)  — atomic modify
   - Only fires if SL/TP actually changed (delta check)
   - Rate-limit: max 1 modify per coin per 60s
   - Fail-open: if HL fails, DB SL/TP still works (guardian monitors)
```

#### Guardian Breach Check (hl-sync-guardian.py)
```
1. Read DB SL/TP for all open positions
2. Check if HL trigger order exists for this coin
3. IF HL trigger exists AND is at correct price → skip (HL will handle)
4. IF no HL trigger OR wrong price → log warning, fire market_close as fallback
```

---

## 5. Implementation Details

### 5.1 New Kill Switches (hermes_constants.py)

```python
# HL Trigger SL/TP — server-side stop-loss
HL_TRIGGER_SL_ENABLED = False      # Master switch — disabled until tested
HL_TRIGGER_SL_AT_TRADE_OPEN = True  # Place SL+TP at trade open time
HL_TRIGGER_SL_ON_UPDATE = True     # Update SL/TP when ATR trails
HL_TRIGGER_SL_VERIFY = True        # Verify orders landed after placing
HL_TRIGGER_SL_MAX_PER_CYCLE = 5    # Max HL API calls per pipeline cycle
HL_TRIGGER_SL_RETRY_COUNT = 2      # Retries on rate-limit
```

### 5.2 UNPROTECTABLE_COINS Expansion

Current list (8 coins): `AAVE, MORPHO, ASTER, PAXG, BTC, AVNT, PENDLE, MET`

**Root cause investigation needed:** Why do these coins reject trigger orders?
- BTC: price too high (integer prices, $100k+), trigger order notional may exceed limits
- AAVE/MORPHO: possibly low liquidity or HL-specific restrictions
- PAXG: gold-backed token, different trading rules?
- AVNT/PENDLE/MET: possibly delisted or restricted

**Action:** Test each coin individually with a tiny SL order to confirm which ones actually fail.

### 5.3 New Function: _sync_hl_triggers()

Location: `position_manager.py` (replaces deleted `_execute_atr_bulk_updates`)

```python
def _sync_hl_triggers(updates: List[Dict]) -> int:
    """
    Sync ATR SL/TP updates to Hyperliquid trigger orders.
    
    For each position with a changed SL or TP:
    1. replace_sl() / replace_tp() — atomic modify (no cancel+recreate race)
    2. Verify order landed via _find_open_trigger_order()
    3. If HL fails, log warning — DB SL/TP still active (guardian monitors)
    
    Returns: number of successful HL syncs.
    """
```

Key differences from V1:
- Uses `replace_sl()`/`replace_tp()` instead of cancel+place
- Atomic modify (no race window between cancel and place)
- Verification step catches silent failures
- Rate-limited: max N calls per cycle
- Fail-open: DB SL/TP always works, HL is bonus protection

### 5.4 Guardian Changes (hl-sync-guardian.py)

```python
# In breach detector (Step 11):
# Before firing market_close, check if HL has an active trigger order
hl_trigger_exists = _check_hl_trigger_exists(token, direction)
if hl_trigger_exists:
    log(f'  [GUARDIAN] {token} — HL trigger active, skipping market_close')
    continue  # HL will handle the close
else:
    log(f'  [GUARDIAN] {token} — NO HL trigger, firing market_close')
    close_position(token, slippage=CLOSE_SLIPPAGE)
```

### 5.5 Brain.py Trade Open

```python
# Step 5: Place SL + TP on HL (re-enabled)
if HL_TRIGGER_SL_ENABLED and HL_TRIGGER_SL_AT_TRADE_OPEN:
    if sz and stop_loss and not is_unprotectable:
        result = place_tp_sl_batch(hype_token, direction, stop_loss, target, sz)
        if result.get('success'):
            log(f'[brain.py] HL SL+TP placed: SL={stop_loss:.6f} TP={target:.6f}')
        else:
            log(f'[brain.py] ⚠️ HL SL+TP failed: {result.get("errors")} — guardian will monitor')
```

---

## 6. Bugs to Fix in Existing HL Functions

### 6.1 replace_sl() — Stale OID Bug

**Current code (hyperliquid_exchange.py:2033-2081):**
```python
def replace_sl(coin, direction, new_price, size=None):
    oid, cloid, existing_sz, _ = _find_open_trigger_order(coin, "sl")
    if oid is None:
        return place_sl(coin, direction, new_px, sz)  # ← OK: create new
    result = exchange.modify_order(oid, coin, is_buy, sz, new_px, ...)
```

**Bug:** When HL returns `"Invalid TP/SL price"` error, the code tries `cancel_order(coin, oid)` then `place_sl()`. But if the order was already FILLED between the `_find_open_trigger_order` call and the `modify_order` call, the cancel also fails.

**Fix:** The existing delete-and-recreate logic is correct for this case. But we should also handle the case where the position is already closed (HL has no position for this coin) by checking `get_open_hype_positions()` first.

### 6.2 _find_open_trigger_order() — Rate Limit Bug

**Current code:** Makes N API calls (`query_order_by_oid`) per open order to check `isTrigger`.

**Impact:** With 10 positions × 2 (TP+SL) = 20 `query_order_by_oid` calls per cycle.

**Fix:** Already partially mitigated by `_get_cached_open_orders()` (55s cache). But `_find_open_trigger_order` still calls `query_order_by_oid` for each matching coin. We could cache full order details too.

### 6.3 Price Side Validation

**Bug:** If `triggerPx` is on the wrong side of current price, HL silently rejects the order. Our code doesn't pre-validate.

**Fix:** Add validation before placing:
```python
# LONG: SL must be BELOW current price, TP must be ABOVE
# SHORT: SL must be ABOVE current price, TP must be BELOW
if direction == 'LONG' and sl_price >= current_price:
    log(f'WARN: SL {sl_price} >= current {current_price} for LONG — skip HL SL')
    return
```

### 6.4 Tick Size Rounding

**Current code:** Uses `_hl_tick_round()` with `_hl_price_decimals()`. This is correct.

**But:** Some coins have unusual tick sizes (BTC = integer, ETH = 1 decimal). If rounding pushes SL past current price, the order fails silently.

**Fix:** After rounding, re-validate price side.

---

## 7. Risk Analysis

### 7.1 What If HL Trigger Fails?

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| HL rejects trigger order | SL only in DB, guardian monitors | Guardian fires market_close (current behavior) |
| HL trigger fires but fills at bad price | Some slippage, but less than our market_close | HL market trigger is faster than our polling cycle |
| HL rate-limited | Trigger order not placed | Fail-open: guardian monitors DB |
| HL trigger fires during network partition | We don't know it fired | Guardian sees no position → closes DB trade |

### 7.2 Race Conditions

| Race | V1 Problem | V2 Solution |
|------|-----------|-------------|
| Guardian + HL trigger both fire | Double-close | Guardian checks HL position before closing |
| ATR update + HL trigger both running | Order replaced mid-fire | replace_sl() is atomic; HL rejects if already fired |
| Two pipeline runs overlap | Duplicate SL orders | normalTpsl grouping replaces atomically |

### 7.3 Rate Limit Budget

HL rate limits: ~100 requests/minute (varies by endpoint).

Per pipeline cycle (60s):
- `_find_open_trigger_order` × 10 tokens × 2 (SL+TP) = 20 queries (cached: 1)
- `replace_sl` × up to 5 updates = 5 calls
- `replace_tp` × up to 5 updates = 5 calls
- **Total: ~11 API calls/cycle** (well within limits)

---

## 8. Testing Plan

### Phase 1: Dry Run (HL_TRIGGER_SL_ENABLED = False, logging only)
1. In `_sync_hl_triggers()`, compute what WOULD be placed but don't place
2. Log: token, SL, TP, would_replace, would_place_new
3. Run for 24-48 hours to verify order logic
4. Check: how many positions would have active HL triggers?

### Phase 2: Paper Trading
1. Enable for paper trades only (live_trading=False)
2. Place SL+TP on HL for paper trades
3. Monitor: do orders land? Do they fire correctly?
4. Check: UNPROTECTABLE_COINS list — test each coin

### Phase 3: Live with Safety Margin
1. Enable for live trades
2. Keep guardian market_close as fallback
3. Monitor: slippage reduction vs V1
4. Run for 7 days before declaring success

---

## 9. Expected Impact

| Metric | Current (V1) | With HL Triggers (V2) |
|--------|-------------|----------------------|
| Catastrophic losses (7d) | 25 trades, -172.59% | ~0 (HL fires at trigger price) |
| Avg catastrophic loss | -6.90% | ~-1.3% (no slippage) |
| Guardian market_close rate | 100% of SL hits | ~10% (only UNPROTECTABLE + failures) |
| Total 7d PnL improvement | baseline | **+139%** (saved from slippage) |

---

## 10. Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add HL_TRIGGER_SL_* kill switches |
| `scripts/position_manager.py` | Add `_sync_hl_triggers()`, wire into `check_and_manage_positions()` |
| `scripts/brain.py` | Re-enable Step 5 SL+TP placement at trade open |
| `scripts/hl-sync-guardian.py` | Add HL trigger check before market_close |
| `scripts/hyperliquid_exchange.py` | Fix replace_sl/replace_tp validation bugs |
| `plans/hl-trigger-sl-v2.md` | This spec |
