# SHORT `is_new_trade` Detection Fails — INIT Floor Never Applied

**Date:** 2026-05-21  
**Finding:** BSV SHORT (entry=14.937, SL=14.97409) was using ACCEL floor (0.70%) instead of INIT floor (0.30%) from first trailing update cycle.

## Root Cause

In `tpsl_utils.py` `compute_atr_sl_tp()`, the `is_new_trade` check for SHORT direction is:

```python
elif direction == 'SHORT' and lowest_price > 0:
    if abs(lowest_price - entry_f) / entry_f < 0.001:
        is_new_trade = True
```

**Problem:** `lowest_price` (the nadir tracker) starts tracking from the first candle after the trade opens. Within that first candle, `lowest_price` may already be different from `entry_f` by >0.10%, causing `is_new_trade=False` immediately.

**For LONG:** `highest_price > 0` check fires, but the `abs(...) < 0.001` deviation threshold may keep it as `is_new_trade=True` longer since peak doesn't deviate as fast on the first candle.

**Result:** Every SHORT trade is treated as "established" (ACCEL) from the first trailing update cycle. INIT floor (`ATR_SL_MIN_INIT`) is **never applied to SHORT trades**.

## Secondary Effect — Nadir Anchoring

When ACCEL floor IS applied, it uses `lowest_price` (nadir) as the reference, not `entry_f`:

```python
# INIT path: sl_price = entry_f × (1 + MIN_SL_PCT)
# ACCEL path: sl_price = lowest_price × (1 + MIN_SL_PCT)
```

If the nadir was ~0.45% below entry when the trade was opened (e.g., BSV nadir at 14.869 vs entry 14.937):
- `SL = 14.869 × 1.007 = 14.974` (actual: 14.97409)
- SL is only **0.131% above current price** (14.9545)

## Why All 5 Open Positions Have Tight SLs

| Token | ATR(14) | k_eff | k×ATR | Floor |
|-------|---------|-------|-------|-------|
| BSV   | 0.036%  | 0.50  | 0.018%| 0.70% |
| LINEA | 0.041%  | 0.04  | 0.002%| 0.70% |
| IP    | 0.078%  | 0.50  | 0.039%| 0.70% |
| TAO   | 0.028%  | 0.50  | 0.014%| 0.70% |
| FET   | 0.047%  | 0.04  | 0.002%| 0.70% |

k×ATR for all positions is 0.01-0.04%. The 0.70% floor is **17-70× larger** than k×ATR. Phase multipliers (BUILDING=1.0, EXTREME=0.08) are completely neutralized.

## Guardian Orphan Path Also Bypasses INIT

`hl-sync-guardian.py` `add_orphan_trade()` (lines 711-770) uses hardcoded:
```python
sl_pct = ATR_SL_MIN_ACCEL   # 0.70%, not ATR_SL_MIN_INIT
tp_pct = ATR_TP_MIN_ACCEL   # 1.10%, not ATR_TP_MIN
```

This bypasses `position_manager.get_trade_params()` which is the only function that applies `ATR_K_INITIAL=1.0` and `ATR_SL_MAX_INIT=0.90%` cap.

## Fix Direction (No Changes Made — Report Only)

1. **For SHORT `is_new_trade` detection:** Add a pure time-based or candle-count gate before ACCEL floor applies (e.g., first 3 trailing update cycles use INIT floor regardless of nadir/peak movement)

2. **For nadir anchoring:** When `is_new_trade=True`, SL reference should be `entry_f`, not `lowest_price`

3. **For orphan path:** Call `position_manager.get_trade_params()` instead of hardcoding SL computation

4. **For floor dominance on low-ATR tokens:** Consider a minimum SL distance (in $) that is not a percentage of entry — e.g., "SL must be at least $X away from entry regardless of ATR" — so that 0.03% ATR tokens still get meaningful breathing room