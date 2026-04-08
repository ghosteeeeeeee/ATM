# Plan: ATR-Adaptive TP/SL — Single Source of Truth (No Trailing)

## Goal

Replace the deprecated trailing stop system with a single, clean ATR-based TP/SL mechanism that:
1. Computes SL and TP from current ATR every cycle
2. Batch-updates HL orders for ALL positions in exactly 2 API calls per cycle
3. Gives 2:1 risk:reward ratio (TP = 2 × ATR, SL = 1 × ATR, both × volatility k)
4. Cascade-flip positions are excluded (they have their own tighter logic)

---

## Current State (what we're replacing)

### The deprecated trailing system (~270 lines of code):
| Component | Location | What it does |
|-----------|----------|--------------|
| `get_trailing_stop()` | line ~1278 | Computes trailing SL buffer (engages at +1% profit, tightens with ATR) |
| `check_trailing_stop()` | line ~1410 | Checks if trailing SL is hit |
| `activate_trailing_stop()` | line ~1451 | Activates trailing state in `trailing_stops.json` |
| Trailing activation block | line ~1658-1678 | Activates trailing when profit > ATR-based threshold |
| Trailing SL exit block | line ~1680-1690 | Exits via trailing SL when hit |
| `trailing_stops.json` | `/var/www/hermes/data/trailing_stops.json` | Persists trailing state (102 entries, many orphaned) |
| A/B columns | DB: `trailing_activation`, `trailing_distance`, `trailing_phase2_dist` | A/B test for trailing params |

### Why it's being removed
- Complex multi-phase logic (phase1/phase2, ATR-aware buffer, volume confirmation, tighten rate)
- 102 orphaned entries in `trailing_stops.json`
- Cascade-flip already has its own tighter SL (`CASCADE_FLIP_POST_TRAIL_PCT = 0.5%`)
- ATR-adaptive SL/TP is simpler and more correct — always current ATR, no waiting for activation

### Current ATR-based SL at entry (from `get_trade_params()`)
```
SL = entry_price ± (k × ATR)
k = 1.5 (low vol), 2.0 (normal), 2.5 (high vol)
TP = fixed 8% (NOT ATR-based — this is what we're fixing)
```

---

## Proposed Design

### Formula
```
SL_distance  = k × ATR           (same as current entry SL)
TP_distance  = 2 × k × ATR       (2× the SL distance → 2:1 R:R)
k            = 1.5 / 2.0 / 2.5  (by volatility bands, same as SL)
```

| Volatility | ATR% | k | SL distance | TP distance | Example (BTC $100k, ATR 1%) |
|-----------|------|---|------------|------------|------------------------------|
| Low | <1% | 1.5 | 1.5% | 3.0% | SL=$98,500, TP=$103,000 |
| Normal | 1-3% | 2.0 | 2.0% | 4.0% | SL=$98,000, TP=$104,000 |
| High | >3% | 2.5 | 2.5% | 5.0% | SL=$97,500, TP=$105,000 |

### What gets updated per cycle
Every position gets its SL and TP recomputed from current ATR, subject to:
- **Delta threshold**: Only push to HL if either SL or TP has moved > 0.3%
- **Cascade-flip exclusion**: Positions with `source.startswith('cascade-reverse-')` are skipped
- **Batch execution**: One `cancel_bulk` + one `place_bulk` for all affected positions (2 API calls total)

### Constants (add to `position_manager.py` top)
```python
ATR_UPDATE_THRESHOLD_PCT = 0.003   # 0.3% minimum delta to push update to HL
```

Remove/deprecate:
```python
# REMOVE these trailing constants:
TRAILING_START_PCT_DEFAULT
TRAILING_BUFFER_PCT_DEFAULT
TRAILING_ATR_MULT_START
TRAILING_ATR_MULT_BUFFER
TRAILING_BUFFER_MIN_ABS
TRAILING_VOL_CONF_BUFFER
TRAILING_VOL_NO_CONF_BUFFER
TRAILING_TIGHTEN
CASCADE_FLIP_POST_TRAIL_PCT
TRAILING_DATA_FILE
```

---

## Step-by-Step Plan

### Step 1: Audit — snapshot current state
Before touching anything:
```python
# Log to trading.md:
- Count of open positions
- Count of entries in trailing_stops.json (102 is the current number)
- Which tokens have cascade-reverse- positions
- Current ATR values for all open tokens
```

### Step 2: Add constants
```python
ATR_UPDATE_THRESHOLD_PCT = 0.003   # only push if delta > 0.3%
```

### Step 3: Delete the trailing system

**File**: `/root/.hermes/scripts/position_manager.py`

Delete entirely:
- [ ] `_load_trailing_data()` function (~line 1128)
- [ ] `_save_trailing_data()` function (~line 1135)
- [ ] `is_trailing_active()` function (~line 1150)
- [ ] `activate_trailing_stop()` function (~line 1451)
- [ ] `get_trailing_stop()` function (~line 1278)
- [ ] `check_trailing_stop()` function (~line 1410)
- [ ] Trailing activation block in main cycle (~line 1658-1678)
- [ ] Trailing SL exit block in main cycle (~line 1680-1690)
- [ ] Cascade-flip post-trail constant `CASCADE_FLIP_POST_TRAIL_PCT` (line ~103)
- [ ] All trailing constants (`TRAILING_*`) from top of file
- [ ] Remove `trailing_stops.json` state file after migration

**DB**: Drop A/B test columns (or leave them, they won't be used):
```sql
ALTER TABLE trades DROP COLUMN IF EXISTS trailing_activation;
ALTER TABLE trades DROP COLUMN IF EXISTS trailing_distance;
ALTER TABLE trades DROP COLUMN IF EXISTS trailing_phase2_dist;
```

### Step 4: Add ATR-based TP to `get_trade_params()`

**File**: `/root/.hermes/scripts/position_manager.py` — `get_trade_params()` (~line 1073)

Update to compute TP using ATR, not fixed `TP_PCT`:
```python
# OLD:
target = round(price * (1 + TP_PCT), 8)

# NEW:
# TP = 2 × k × ATR (2:1 R:R)
if token:
    atr = _pm_get_atr(token)
    if atr is not None:
        atr_pct = atr / price
        k = _pm_atr_multiplier(atr_pct)
        tp_pct = 2 * k * atr_pct          # 2× SL distance
        tp_pct = max(tp_pct, TP_PCT)      # floor at original 8%
    else:
        tp_pct = TP_PCT
else:
    tp_pct = TP_PCT

if direction == "LONG":
    target = round(price * (1 + tp_pct), 8)
elif direction == "SHORT":
    target = round(price * (1 - tp_pct), 8)
```

### Step 5: Add `_force_fresh_atr()` helper

```python
def _force_fresh_atr(token: str, period: int = 14, interval: str = '1h') -> float | None:
    """
    Force-fetch ATR bypassing cache. Used for ATR-adaptive order updates.
    Inlines _pm_get_atr() logic without the TTL check so we always
    get the current ATR value for decision-making.
    """
    import time as _time
    try:
        from hyperliquid.info import Info
        info = Info('https://api.hyperliquid.xyz', skip_ws=True)
        now = _time.time()
        end_t = int(now * 1000)
        start_t = end_t - (60 * 60 * 1000 * (period + 5))
        candles = info.candles_snapshot(token.upper(), interval, start_t, end_t)
        if not candles or len(candles) < period + 1:
            return None
        trs = []
        for i in range(1, min(period + 1, len(candles))):
            high = float(candles[i]['h'])
            low  = float(candles[i]['l'])
            prev_close = float(candles[i - 1]['c'])
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        return sum(trs) / len(trs) if trs else None
    except Exception:
        return None
```

### Step 6: Add `_atr_multiplier()` helper

Same formula as `decider_run._atr_multiplier()` but without the A/B override (A/B is only for entry SL, not for ongoing ATR updates):

```python
def _atr_multiplier(atr_pct: float) -> float:
    """Return k multiplier for ATR-based SL/TP. Self-calibrating by volatility."""
    if atr_pct < 0.01:
        return 1.5    # LOW_VOLATILITY
    elif atr_pct > 0.03:
        return 2.5    # HIGH_VOLATILITY
    else:
        return 2.0    # NORMAL_VOLATILITY
```

### Step 7: Add `_collect_atr_updates()` function

```python
def _collect_atr_updates(open_positions: List[Dict]) -> List[Dict]:
    """
    Collect all open positions (excluding cascade-flip) whose SL or TP has drifted
    > ATR_UPDATE_THRESHOLD_PCT from current ATR.

    Called once per cycle, after the main position loop.
    Returns list of update dicts:
      {trade_id, token, direction, sz, entry_price,
       old_sl, new_sl, old_tp, new_tp, needs_sl, needs_tp}
    """
    if not open_positions:
        return []

    # Deduplicate tokens — one ATR fetch per unique token
    tokens_seen = {}
    for pos in open_positions:
        token = str(pos.get('token', '')).upper()
        if token and token not in tokens_seen:
            atr = _force_fresh_atr(token)
            tokens_seen[token] = atr

    updates = []
    for pos in open_positions:
        token = str(pos.get('token', '')).upper()
        direction = str(pos.get('direction', '')).upper()
        entry_price = float(pos.get('entry_price') or 0)
        trade_id = pos.get('id')
        current_sl = float(pos.get('stop_loss') or 0)
        current_tp = float(pos.get('target') or 0)
        source = str(pos.get('source') or '')

        # Skip cascade-flip positions — they have their own tighter SL
        if source.startswith('cascade-reverse-'):
            continue

        if not token or not entry_price or not trade_id:
            continue

        atr = tokens_seen.get(token)
        if atr is None:
            continue

        atr_pct = atr / entry_price
        k = _atr_multiplier(atr_pct)
        sl_pct = k * atr_pct
        tp_pct = 2 * k * atr_pct

        if direction == "LONG":
            new_sl = round(entry_price * (1 - sl_pct), 8)
            new_tp = round(entry_price * (1 + tp_pct), 8)
        elif direction == "SHORT":
            new_sl = round(entry_price * (1 + sl_pct), 8)
            new_tp = round(entry_price * (1 - tp_pct), 8)
        else:
            continue

        # Check deltas
        sl_delta = abs(new_sl - current_sl) / current_sl if current_sl > 0 else 1.0
        tp_delta = abs(new_tp - current_tp) / current_tp if current_tp > 0 else 1.0

        needs_sl = sl_delta > ATR_UPDATE_THRESHOLD_PCT
        needs_tp = tp_delta > ATR_UPDATE_THRESHOLD_PCT

        if needs_sl or needs_tp:
            updates.append({
                'trade_id': trade_id,
                'token': token,
                'direction': direction,
                'entry_price': entry_price,
                'old_sl': current_sl,
                'new_sl': new_sl,
                'old_tp': current_tp,
                'new_tp': new_tp,
                'needs_sl': needs_sl,
                'needs_tp': needs_tp,
                'atr': atr,
                'atr_pct': atr_pct,
                'k': k,
            })

    return updates
```

### Step 8: Add `_execute_atr_bulk_updates()` function

```python
def _execute_atr_bulk_updates(updates: List[Dict]) -> dict:
    """
    Execute SL/TP updates for all affected positions in exactly 2 HL API calls:
      1. cancel_bulk_orders — cancel all stale SL+TP orders for affected tokens
      2. place_bulk_orders  — place all new SL+TP orders

    Position sizes fetched once from HL, reused across all updates.
    """
    if not updates:
        return {'cancelled': 0, 'placed': 0, 'errors': []}

    from hyperliquid_exchange import get_exchange, get_open_hype_positions, _HL_TICK_DECIMALS, _hl_tick_round

    exchange = get_exchange()

    # ── 1. Get position sizes from HL (one call, reused) ──────────────────────
    positions, err = get_open_hype_positions()
    if err or not positions:
        return {'cancelled': 0, 'placed': 0, 'errors': [str(err or 'no positions')]}

    sz_map = {}
    for coin_name, p in positions.items():
        sz_map[coin_name.upper()] = abs(float(p.get('szi', 0) or 0))

    # ── 2. Find stale order IDs to cancel (one all_open_orders call) ───────────
    all_open = exchange.info.all_open_orders()  # one API call
    affected_tokens = {u['token'].upper() for u in updates}
    stale_order_ids = []
    for order in all_open:
        if order.get('coin', '').upper() in affected_tokens:
            if order.get('tif', '').startswith('GTD'):  # SL/TP orders use GTD TIF
                stale_order_ids.append({'oid': order['oid'], 'coin': order['coin']})

    # ── 3. Cancel all stale orders (one bulk call) ─────────────────────────────
    if stale_order_ids:
        exchange.cancel_bulk_orders(stale_order_ids)

    # ── 4. Build and place all new SL+TP orders (one bulk call) ───────────────
    new_orders = []
    for u in updates:
        token = u['token']
        direction = u['direction']
        sz = sz_map.get(token.upper(), 0)
        if sz <= 0:
            continue

        decimals = _HL_TICK_DECIMALS.get(token.upper(), 6)
        is_short = direction == 'SHORT'

        if u['needs_sl']:
            sl_px = _hl_tick_round(u['new_sl'], decimals)
            sl_type = {"trigger": {"triggerPx": sl_px, "isMarket": True, "tpsl": "sl"}}
            # SL is reduce-only, opposite direction
            new_orders.append(exchange.build_order(
                token, not is_short, sz, sl_px, sl_type, reduce_only=True
            ))

        if u['needs_tp']:
            tp_px = _hl_tick_round(u['new_tp'], decimals)
            tp_type = {"trigger": {"triggerPx": tp_px, "isMarket": True, "tpsl": "tp"}}
            new_orders.append(exchange.build_order(
                token, is_short, sz, tp_px, tp_type, reduce_only=True
            ))

    placed = 0
    errors = []
    if new_orders:
        result = exchange.place_bulk_orders(new_orders)  # one API call
        if result.get('errors'):
            errors.extend(result['errors'])
        else:
            placed = len(new_orders)

    return {
        'cancelled': len(stale_order_ids),
        'placed': placed,
        'errors': errors,
    }
```

### Step 9: Update main position manager cycle

**In the main loop (around line 1800-1947)**:

REMOVE:
- [ ] Trailing activation block (lines ~1658-1678)
- [ ] Trailing SL exit block (lines ~1680-1690)
- [ ] `trailing_active = is_trailing_active(trade_id)` check
- [ ] `activate_trailing_stop()` call
- [ ] `get_trailing_stop()` / `check_trailing_stop()` calls
- [ ] Cascade flip post-trail k override (`source.startswith('cascade-reverse-')` → tighter trailing)
- [ ] `trailing_stops.json` writes
- [ ] The MACD-cascade flip check that depended on `not trailing_active`

AFTER the main loop closes (before the final print `Position Manager: N open...`):
```python
# ── 7. ATR-adaptive TP/SL batch update ─────────────────────────────────────
# Skip cascade-reverse- positions — they have their own tighter SL
open_positions = [pos for pos in [filled loop data] if not str(pos.get('source', '')).startswith('cascade-reverse-')]
updates = _collect_atr_updates(open_positions)
if updates:
    result = _execute_atr_bulk_updates(updates)
    if result['placed'] > 0 or result['cancelled'] > 0:
        # Batch update DB
        trade_ids_and_values = [(u['trade_id'], u['new_sl'], u['new_tp']) for u in updates]
        try:
            cur.executemany(
                "UPDATE trades SET stop_loss = %s, target = %s WHERE id = %s",
                trade_ids_and_values
            )
            conn.commit()
        except Exception as e:
            print(f"  [ATR] DB update failed: {e}")
        print(f"  [ATR] ✅ Batch: {len(updates)} positions | "
              f"{result['cancelled']} cancelled | {result['placed']} placed")
```

### Step 10: Verify HL bulk API availability

**File**: `/root/.hermes/scripts/hyperliquid_exchange.py`

Check for:
- `cancel_bulk_orders()` — HL API: `POST /api/v1/batchCancels`
- `place_bulk_orders()` — HL API: `POST /api/v1/batchOrders`
- `build_order()` — helper to construct order payload

If not present, add thin wrappers.

### Step 11: Clean up trailing state file

```python
# After deployment, safe to clear:
os.remove('/var/www/hermes/data/trailing_stops.json')
```

(Or clear it on first run of the new cycle)

---

## Files to Change

| File | Change |
|------|--------|
| `/root/.hermes/scripts/position_manager.py` | Delete trailing funcs + blocks, add `_force_fresh_atr`, `_atr_multiplier`, `_collect_atr_updates`, `_execute_atr_bulk_updates`, update `get_trade_params` TP formula, add cycle hook |
| `/root/.hermes/scripts/hyperliquid_exchange.py` | Add `cancel_bulk_orders()` + `place_bulk_orders()` + `build_order()` if not present |
| DB | `ALTER TABLE trades DROP COLUMN IF EXISTS trailing_*` |
| `/root/.hermes/data/trailing_stops.json` | Clear on first deploy |

---

## Tests / Validation

- [ ] **Before**: log all open positions, their current SL/TP, and current ATR values
- [ ] **After**: verify all cascade-reverse- positions are excluded from ATR updates
- [ ] **After**: run 1 cycle, verify exactly 2 HL API calls (`all_open_orders` + `cancel_bulk` OR `place_bulk`)
- [ ] **After**: check DB `stop_loss` and `target` columns match what ATR would produce
- [ ] **DB**: confirm `trailing_*` columns are gone or NULL
- [ ] **`trailing_stops.json`**: confirm file is empty/absent
- [ ] **No regressions**: run for 24h, verify positions still close correctly when SL/TP hits

---

## Summary of Changes from Original Plan

| Decision | Answer |
|----------|--------|
| TP formula | TP = 2 × k × ATR (2:1 R:R, not 1:1) |
| Cascade-flip exclusion | Yes — `cascade-reverse-*` positions skipped |
| Trailing code | DELETE entirely |
| Bulk HL calls | Exactly 2 per cycle: `cancel_bulk_orders` + `place_bulk_orders` |
