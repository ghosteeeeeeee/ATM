# SUI Ghost Trade Fix — 2026-05-16

## Trade: SUI LONG #10051

| Field | Value |
|-------|-------|
| Token | SUI |
| Direction | LONG |
| Entry | 1.064 |
| SL (wrong) | 1.0923 |
| SL distance | 0 |
| Close reason | `atr_sl_hit` |
| Opened | 2026-05-16 17:30:11 |
| Closed | 2026-05-16 17:30:14 (3 seconds) |
| PnL | +0.0235% |
| Signal | `rs-s57,zscore-pump+` |
| is_guardian_close | f |
| Leverage | 5 |

**SL was placed ABOVE entry — immediately triggered on the first price uptick.**

---

## Root Cause

In `compute_atr_sl_tp()` (tpsl_utils.py), the `is_new_trade` gate:

```python
is_new_trade = (highest_price == entry_price and pnl_pct >= 0)
```

For a NEW trade:
- `brain.py` DB INSERT sets `highest_price = entry` for LONG (line ~500)
- On first ATR cycle, `highest_price == entry_price` → True
- BUT if `pnl_pct < 0` (price moved against the trade before first cycle ran), the gate evaluates `False`
- `is_new_trade = False` → INIT k floor bypassed → phase k applied directly
- Phase k for a newly opened trade with positive momentum = 1.0 (neutral) or 0.75 (NORMAL_VOL)
- Using `highest_price` (which equals `entry`) as ref_price: `entry × (1 + k × atr_pct)` → SL above entry for LONG

**The correct behavior for a new trade's initial SL:** it must use `entry_price` as anchor with INIT k=0.5, producing SL **below** entry for LONG.

---

## The Fix

**Location:** `tpsl_utils.py` — `compute_atr_sl_tp()` function, inside the `is_new_trade` gate block (around lines 310-360).

**When `is_new_trade` is False BUT `current_sl <= 0` (no SL written yet) AND `highest_price ≈ entry`:** force entry_price as the reference anchor with INIT floors.

**Conceptual fix** (pseudo-code):

```python
# Existing gate:
is_new_trade = (highest_price == entry_price and pnl_pct >= 0)

# NEW additional condition: even if is_new_trade=False, if no SL has been
# written yet (current_sl <= 0) AND highest_price ≈ entry, use INIT treatment.
# This covers the case where price moved against the trade before the first
# ATR cycle ran, causing pnl_pct < 0 → is_new_trade=False prematurely.

force_init = (
    not is_new_trade
    and current_sl <= 0
    and abs(highest_price - entry_price) / entry_price < 0.001  # peak ≈ entry
)

if is_new_trade or force_init:
    # Use INIT k and INIT floors
    eff_sl_pct = max(INIT_K * sl_pct, INIT_SL_MIN)
    ref_price = entry_price  # Always use entry for initial SL
    ...
```

**Key insight:** `current_sl <= 0` is the signal that no SL has been computed yet. If `is_new_trade` is False but `current_sl` is still 0 (not yet written to DB), the trade is still in its initial state — just with a negative PnL from early price movement. The fix ensures INIT treatment persists until the first non-zero SL is written.

**For SHORT:** The same logic must be verified — entry_price as anchor with INIT k should place SL ABOVE entry for SHORT. Confirm `compute_atr_sl_tp` SHORT path uses `entry_price` for initial SL when `force_init` applies.

---

## ATR values at time of trade

- SUI ATR(14) = 0.005157 (~0.52% per bar)
- Entry = 1.064

**Correct initial SL for SUI LONG:**
```
INIT_SL_PCT = 0.03  (3% from hermes_constants — sl_distance for A/B test, control=0.03)
INIT_K = 0.5
eff_sl_pct = max(0.5 * 0.0052, 0.005) = max(0.0026, 0.005) = 0.005  (0.50% floor wins)
SL = entry × (1 - 0.005) = 1.064 × 0.995 = 1.05868
```

This would place SL at ~1.059 (below entry), correct for a LONG. Instead, the bug produced SL=1.0923 (above entry).

---

## Why `sl_distance=0` in the trade record

brain.py INSERT writes `sl_distance` from A/B test (control=0.03). But `compute_atr_sl_tp` computes the actual SL value. The DB column `stop_loss` stores the computed price, not the distance. `sl_distance=0` in the trade record means the distance column wasn't updated after initial insert — but the `stop_loss` column (1.0923) was written by position_manager's `_persist_atr_levels`.