# ZK Trade TP/SL Inconsistency — 2026-05-15 (LIVE BUG)

## Summary

ZK SHORT trade #9884 has SL=0.70% and TP=2.99% — TP/SL ratio = 4.27x instead of the expected 1.25x (ATR_TP_K_MULT). Two different implied ATRs from the same trade (0.70% vs 2.39%).

## Live Trade State (from PostgreSQL, 2026-05-15 12:46 UTC)

```
id: 9884 | token: ZK | direction: SHORT
entry_price: 0.01752600
stop_loss:   0.01764868  (0.70% above entry)
target:      0.01700226  (2.99% below entry)
highest_price: 0.01763800  ← went underwater (price moved against SHORT)
lowest_price:  0
open_time:  2026-05-15 05:25:07
updated_at: 2026-05-15 12:46:04
atr_managed: True
hl_sl_order_id: null | hl_tp_order_id: null
```

## The Math

- SL = 0.70% → `atr_pct = SL / k = 0.70%` (k=1.0, LOW_VOL)
- TP = 2.99% → implied ATR = 2.99% / 1.25 = 2.39%
- Same trade, same ATR fetch, different results
- Expected: TP = 1.25 × SL distance = 0.875% → TP price = entry × (1 - 0.00875) = 0.017373
- Actual: TP = 2.99% → TP price = 0.01700226

## TP Changed, SL Didn't

DB timestamps show:
- SL last updated: 12:28:04 (0.01764868)
- TP last updated: 12:46:04 (0.01700226, was 0.01704681 at 05:25)

## Root Cause (CONFIRMED — session 2026-05-15)

**Confirmed architecture**: `position_manager._collect_atr_updates()` is the sole ATR engine. `_persist_atr_levels()` writes both SL and TP in one DB UPDATE, but `needs_sl` and `needs_tp` are computed independently per-cycle. Each can be True while the other is False — meaning SL and TP can be updated at different times with different ATR values.

**The SHORT TP bug in code** (lines 1729-1741):
```python
if current_tp > 0:
    tp_at_ref = round(ref_price * (1 - effective_tp_pct), 8)
    if tp_at_ref >= current_tp:
        new_tp = current_tp    # would loosen — KEEP locked TP
    else:
        new_tp = tp_at_ref     # would tighten — update
else:
    # First time setting TP — ref_price is used (lowest_price for SHORT)
    new_tp = round(ref_price * (1 - effective_tp_pct), 8)
```

The `is_new_trade` / `_in_profit` fix at line 1650-1651 anchors SL to `_entry` for new/in-profit SHORTs (correct). But TP at line 1655 always uses `ref_price` (lowest_price). When `lowest_price = 0` in DB, the fallback at line 1598 uses `current_price` — a different reference than the `_entry` anchor used for SL.

**Evidence from live ZK trade**:
- DB: `lowest_price = 0` (never tracked)
- SL update (12:28): used `_entry = 0.017526` → SL = 0.70% ✓
- TP update (12:46): used `current_price` (fallback) as ref_price → TP = 3.75% ✗
- Result: TP/SL ratio = 5.4x instead of 1.25x

**The fix**: When `lowest_price = 0` (uninitialized) for a SHORT, TP must also use `_entry` as the reference price, not `current_price`. The `_entry` anchor for in-profit SHORTs must apply to BOTH SL and TP computation.

**DB timestamps prove independence**:
- SL written: 12:28:04 (0.01764868 = 0.70%)
- TP written: 12:46:04 (0.01700226 = 3.75%, was 0.01704681 at 05:25)
- TP changed -0.44% while SL stayed fixed — two separate update cycles with different ref_prices

## Key Files

- `position_manager.py:_collect_atr_updates()` (lines ~1630-1741) — active ATR computation
- `position_manager.py:_persist_atr_levels()` (line ~1818) — single UPDATE for both SL+TP
- `position_manager.py:_compute_dynamic_sl()` / `_compute_dynamic_tp()` (lines ~1396-1445) — DEAD CODE, never called
- `hermes_constants.py` — ATR_TP_K_MULT=1.25 (TP should be 1.25×SL distance)

## References

- `references/zk-trade-atr-flow-2026-05-15.md` — original trade flow
- `references/atr-sl-direction-bug.md` — related SHORT SL direction fix (SL anchored to _entry for new/in-profit SHORTs)
- `references/atr-trailing-sl-in-profit.md` — SHORT TP bug (TP never trails, uses entry_price)

## Key Files

- `position_manager.py:_collect_atr_updates()` (lines ~1630-1700) — active ATR computation
- `position_manager.py:_compute_dynamic_sl()` / `_compute_dynamic_tp()` (lines ~1396-1445) — DEAD CODE, never called
- `hermes_constants.py` — ATR_TP_K_MULT=1.25 (TP should be 1.25×SL distance)

## References

- `references/zk-trade-atr-flow-2026-05-15.md` — original trade flow
- `references/atr-sl-direction-bug.md` — related SHORT SL direction fix
- `references/atr-trailing-sl-in-profit.md` — SHORT TP bug (TP never trails, uses entry_price)