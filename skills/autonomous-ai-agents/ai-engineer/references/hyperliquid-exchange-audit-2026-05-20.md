# hyperliquid_exchange.py Bugs — 2026-05-20 Audit

## Bugs Found + Fixed

### BUG-1 (CRITICAL): mirror_open notional_usdt = signal-level ~$10, not actual HL fill
**File:** hyperliquid_exchange.py:984
**Before:** `"notional_usdt": size_usdt` — size_usdt is ~$10.10 (pre-order), not actual fill notional
**After:** `"notional_usdt": entry_info.get("total_sz", sz) * fill_price` — actual HL coin units × fill price

Why this matters: hl-sync-guardian.py and brain.py use `hl_notional_usdt` as the notional base for PnL calculations. If it stores ~$10 instead of ~$7 (actual), profits are systematically inflated and losses deflated by ~30-40%.

### BUG-2 (HIGH): mirror_open result missing hl_realized_pnl
**File:** hyperliquid_exchange.py:979-988
**Fix:** Added `"hl_realized_pnl": entry_info.get("realized_pnl", 0)` to result dict

### BUG-3 (HIGH): mirror_open_batch result missing critical fields
**File:** hyperliquid_exchange.py:1123-1129
**Fix:** Added `notional_usdt`, `total_sz`, `hl_entry_price` to batch result dict

## Bugs NOT Reproduced (Already Fixed)

### BUG-4: side=='B' filter misses LONG closes
**Status:** NOT REPRODUCED — code already uses `'Close' in f.get('dir', '')` since lines 864-868 (hyperliquid_exchange.py). My audit had a stale read.

### BUG-5: mirror_close no fill polling retry
**Status:** ALREADY FIXED — lines 1161-1166 have 3-attempt retry with 2s delay (same pattern as guardian's `_poll_hl_fills_for_close`)

## Key Lesson

`mirror_get_entry_fill()` returns both `total_sz` (actual HL coin units from fills) AND `entry_price` (actual HL fill price). These should be used to compute actual notional:
```python
actual_notional = entry_info.get("total_sz", sz) * fill_price
```

Never use `size_usdt` (the pre-order input parameter) as the notional — it includes the MIN_ORDER_BUFFER and is signal-level intent, not HL-ground-truth.