# Plan: Self-Close Fallback + Direction Mismatch Detection

**Date:** 2026-04-09 09:35 UTC (updated 10:07 UTC)
**Context:** TNSR position was SHORT but HL had LONG-close orders (side=A, sell, would close long not short). Detected via TNSR's open orders showing sz=209.7 (same as position size) but position being SHORT. Root cause: `get_open_hype_positions_curl()` from hype_cache was returning stale data — CACHED positions didn't match actual HL state. Fixed by adding direction mismatch detection to batch and adding explicit fresh HL position fetch alongside cached positions.

---

## 1. Known Unprotectable Coins

| Coin | HL Asset ID | Failure Mode |
|------|-------------|--------------|
| AAVE | 28 | All TP/SL attempts → "Invalid TP/SL price. asset=28" |
| MORPHO | 173 | Same |
| ASTER | 207 | Same |
| PAXG | 187 | Same |
| BTC | 0 | Intermittent — works above ~4% above mid, fails below. Rate-limit artifact. |

**SAND, AVNT:** szDecimals=0, coin <$1 — integer TP/SL prices meaningless, skip.

---

## 2. Design: Guarded Close Function

**File:** `batch_tpsl_rewrite.py` (or new shared module)

The guarded close function:
1. Takes `(coin, direction, size)` — the position to close
2. Looks up current price from `hype_cache.get_allMids()`
3. Places a **market order** to close the full position — no TP/SL, just a plain market close
4. Logs the attempt and outcome to the brain DB
5. On any exception → log + continue (never raise)

```python
def guarded_close_position(coin: str, direction: str, size: float) -> dict:
    """
    Attempt to close a position for a coin that cannot have TP/SL on HL.
    Falls back to manual market close if TP/SL trigger is detected.
    Returns dict with outcome.
    """
    import hype_cache as hc
    from hyperliquid_exchange import get_exchange, _exchange_rate_limit

    coin = coin.upper()
    size = abs(float(size))

    try:
        mids = hc.get_allMids()
        price = float(mids.get(coin, 0))
        if price == 0:
            return {"ok": False, "error": f"No price for {coin}"}

        _exchange_rate_limit()
        exchange = get_exchange()

        # For a close: is_buy is OPPOSITE of direction (close LONG → sell)
        is_buy = direction.upper() == "SHORT"

        result = exchange.order(coin, is_buy, size, price, None, reduce_only=True)
        statuses = result.get("response", {}).get("data", {}).get("statuses", [])
        error = statuses[0].get("error") if statuses else None

        if error:
            return {"ok": False, "error": error}

        return {"ok": True, "coin": coin, "size": size, "close_price": price}
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

---

## 3. Integration Into Batch Rewriter

**In `batch_tpsl_rewrite.py` — `rewrite_coin()` function:**

After computing SL/TP from current mid, but BEFORE attempting HL TP/SL placement:

```python
UNPROTECTABLE_COINS = {'AAVE', 'MORPHO', 'ASTER', 'PAXG', 'BTC'}

def rewrite_coin(coin, pos_data, prices, hl_orders):
    token = coin.upper()
    ...

    # Step 2: Compute SL/TP from current mid
    sl_raw, tp_raw = compute_sl_tp(direction, entry_px, current_px, atr)
    sl = round_price(sl_raw, token)
    tp = round_price(tp_raw, token)

    # NEW: If coin is unprotectable, install self-close fallback
    if token in UNPROTECTABLE_COINS:
        log.info(f"  {token}: no HL TP/SL — installing self-close fallback")
        # Store SL/TP in brain DB so self-close watcher can use them
        db_store_tpsl_fallback(token, direction, size, sl, tp, entry_px)
        return {"skipped": "unprotectable", "sl": sl, "tp": tp}

    # Normal path: place TP/SL on HL...
```

---

## 4. Standalone Self-Close Watcher

**File:** `self_close_watcher.py` (new, run via cron every 1 min alongside batch)

**Logic:**
1. Load UNPROTECTABLE_COINS from `batch_tpsl_rewrite.py` (import shared constant)
2. Get open positions from `get_open_hype_positions_curl()`
3. For each position where coin is in UNPROTECTABLE_COINS:
   a. Fetch stored SL/TP from brain DB (or compute from current mid)
   b. Get current price from `get_allMids()`
   c. **Trigger check:**
      - LONG: if `current_px <= sl` OR `current_px >= tp` → close
      - SHORT: if `current_px >= sl` OR `current_px <= tp` → close
   d. Call `guarded_close_position()`
   e. Log result
4. **Never fail silently** — always log outcome

```python
# Trigger condition (LONG):
if (current_px <= sl) or (current_px >= tp):
    result = guarded_close_position(coin, direction, size)
    log.info(f"SELF-CLOSE: {coin} {direction} {size} — {'OK' if result['ok'] else result['error']}")
```

**Note:** BTC is in UNPROTECTABLE_COINS only when rate-limited. Once the batch succeeds for BTC, it should be **dynamically removed** if HL TP/SL placement succeeds. Re-add if it fails again.

---

## 5. Dynamic BTC Handling

BTC fails at 73300-73400 (batch's computed range) but works at 73500+. 
**Fix:** After computing TP from mid, cap the minimum distance at **4% above mid** for BTC, not 3%. This ensures we hit the working range (73500+ vs 73323):

```python
# In compute_sl_tp or round_price:
if token == 'BTC':
    tp = max(tp, round(current_px * 1.04, 1))  # at least 4% above current
    sl = min(sl, round(current_px * 0.96, 1))  # at most 2% below current
```

Also: if TP/SL placement succeeds for BTC 3 consecutive times → remove from UNPROTECTABLE_COINS (temporary unprotectability, rate-limit artifact). Re-add if it fails again.

---

## 6. Files To Change

| File | Change |
|------|--------|
| `batch_tpsl_rewrite.py` | Add `UNPROTECTABLE_COINS`, guarded TP/SL skip, `db_store_tpsl_fallback()` |
| `self_close_watcher.py` | **New file** — self-close cron job |
| `hl-sync-guardian.py` | Restart; also add UNPROTECTABLE_COINS check in reconcile loop |
| `brain/trading.md` | Document the fallback system |
| `brain/TASKS.md` | Add "Self-close fallback for unprotectable coins" |

---

## 7. systemd Timer

```
hermes-self-close-watcher.service  → Runs self_close_watcher.py
hermes-self-close-watcher.timer    → Every 1 min, aligned with batch
```

---

## 8. Verification

1. After deploy: open HL UI, confirm AAVE/MORPHO/ASTER/PAXG have NO TP/SL orders
2. Run `self_close_watcher.py` manually — confirm it logs correctly
3. Temporarily set a test SL close to current price ±0.1% — verify it triggers and closes
4. After 3 consecutive BTC TP/SL placements succeed → confirm BTC auto-removes from fallback list

---

## 10. Direction Mismatch Detection (Implemented)

**Problem:** TNSR was SHORT but HL orders were side=A (sell, would close LONG). No error thrown — orders just sat there uselessly.

**Detection logic** (added to `batch_tpsl_rewrite.py` Step 1.5):
```
For each coin with existing HL orders:
  If position is LONG and any order is side=B (buy) → MISMATCH
  If position is SHORT and any order is side=A (sell) → MISMATCH
  → Cancel mismatched orders immediately, log ERROR
```

**Why it happened:** `get_open_hype_positions_curl()` from hype_cache returned stale positions. HL orders were from a prior state where TNSR was LONG. Cache refreshed between order placement and next batch run.

**Fix:** Batch now cross-checks direction from cache against actual HL order sides. Mismatched orders are cancelled on the spot.

---

## 11. Verification Checklist

- [x] Batch direction mismatch detection active
- [x] Self-close watcher running (background process PID 3250580)
- [x] tpsl_self_close DB table created
- [x] SKIP coins (AAVE, MORPHO, ASTER, PAXG) now storing to self-close DB
- [x] Guardian restarted
- [x] Hotset confirmed populated (3 tokens, live, correct path `/var/www/hermes/data/hotset.json`)
- [ ] BTC TP/SL still failing — investigate further (rate limit vs genuine issue)
- [ ] Need sudo access for systemd/timer setup (blocked) — fallback cron not possible without sudo
- [ ] Manual cron setup for self_close_watcher every 1 min (needed)