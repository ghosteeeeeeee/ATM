# Guardian Self-Close Dual-SL/SL Bug (2026-05-18)

## The Problem

`hl-sync-guardian.py` has a `self_close_watcher` block that monitors open positions for TP/SL breaches. When a new position is detected, it computes SL/TP **independently** using `compute_atr_sl_price()` and `compute_atr_tp_price()` from `tpsl_utils.py`, storing results in the **`tpsl_self_close`** table.

**This table is completely separate from `brain.trades.stop_loss` and `brain.trades.target`.**

Guardian breach detection (lines 3064-3077) checks against **`tpsl_self_close` values**, NOT position_manager's computed values. Two independent systems can have DIFFERENT SL/TP for the same position.

## How Guardian Computes SL/TP (when no tpsl_self_close record exists)

```python
# hl-sync-guardian.py lines 3056-3058
sl_price = compute_atr_sl_price(coin, direction, entry_px, curr)
tp_price = compute_atr_tp_price(coin, direction, entry_px, curr)
_upsert_self_close(coin, direction, sz, entry_px, sl_price, tp_price)
```

For a **SHORT** trade:
- `compute_atr_tp_price()`: `TP = anchor * (1 - min(max(k*atr_pct, ATR_TP_MIN=1.5%), ATR_TP_MAX))`
- `compute_atr_sl_price()`: `SL = anchor * (1 + min(max(k*atr_pct, ATR_SL_MIN=0.5%), ATR_SL_MAX))`
- Anchor = `lowest_price` if available, else `entry_px`

This means **guardian's initial SL/TP** is computed at open time with no trailing logic yet. It can differ from position_manager's values if:
1. ATR was stale/unavailable at guardian open time → falls back to fixed percentages
2. Guardian anchor (lowest_price) differs from position_manager's anchor
3. Guardian uses `ATR_TP_MIN=1.5%` floor vs position_manager's phase-k system

## Real Example: 0G SHORT

From the trade display:
```
0G  SHORT  Entry $0.4961  Current $0.4956  SL $0.503663
```

Guardian computed: SL = 0.503663 (= entry * (1 + 0.7% fallback))
Position_manager intended: likely much tighter based on ATR

SL is **above entry** for a SHORT — price would have to RISE for this SL to hit, meaning the trade is in profit and the SL is not protecting it.

## Why This Causes Premature Closes

Guardian closes when:
- SHORT TP breach: `curr <= tp_price` (price dropped to TP)
- SHORT SL breach: `curr >= sl_price` (price rose to SL)

For a SHORT in profit:
- TP breach = price dropped enough (correct close)
- SL breach = price rose back through SL (correct close... if SL is below entry)

If guardian's SL is **above entry** (like 0G at 0.5036 vs entry 0.4961), the trade must first drop to SL (a gain) then rise back through SL (a loss from the gain). This is backwards — the trade is protected by a SL ABOVE entry, meaning it can never close at a loss.

## The Fix Options

1. **Guardian reads from `trades.stop_loss/target`** instead of computing its own — position_manager is the authority, guardian just monitors and executes
2. **Guardian writes its computed values to `trades` table** so they're visible to position_manager — synchronize the two systems
3. **Disable guardian's self-close entirely** and rely on position_manager — simpler but loses guardian's fail-safe

## Diagnostic Query

```sql
-- Compare guardian (tpsl_self_close) vs position_manager (brain.trades) SL/TP
SELECT 
    t.token, t.direction, t.entry_price,
    t.stop_loss AS pm_sl, t.target AS pm_tp,
    s.sl_price AS guardian_sl, s.tp_price AS guardian_tp,
    t.atr_managed
FROM trades t
LEFT JOIN tpsl_self_close s ON t.token = s.coin AND t.direction = s.direction
WHERE t.status = 'open';
```

## Pipeline Log Evidence

When `zscore-pump` or `rs` signals show "stale price_history, skipping", position_manager's `_force_fresh_atr()` may return `None` → `atr_pct = 0` → `_collect_atr_updates()` skips the token (line 1628: `if atr is None: continue`) → guardian's initial computed values persist unchallenged.

Pipeline log timestamps for 00:34-00:39 show repeated "stale price_history" for MORPHO, SNX, UMA — meaning position_manager never overwrote guardian's initial SL/TP.

## Key Files

- `hl-sync-guardian.py` lines 3056-3058: guardian TP/SL computation
- `hl-sync-guardian.py` lines 3064-3077: breach detection against tpsl_self_close
- `tpsl_utils.py` lines 170-236: standalone `compute_atr_sl_price()` / `compute_atr_tp_price()`
- `position_manager.py` line 1628: `if atr is None: continue` — skips tokens with no fresh ATR