# HH_HL Breakout Threshold Unit Mismatch — 2026-05-09
**File:** `signals/hh_hl.py`, `_detect_breakout()` lines 236-245

## Bug
`_classify_structure()` returns `breakout_strength` in **percent units** (e.g., `0.014 = 0.014%`), but `HH_HL_BREAKOUT_THRESHOLD = 0.0005` in `hermes_constants.py` is in **decimal fraction** (`= 0.05%`). The comparison `0.014 >= 0.0005` was always True.

## Result
AAVE fired on a 0.014% "breakout" when the threshold was 0.05%. Same for SNX. Both should have been filtered out.

## Fix Applied
```python
# Before (broken):
if structure == 'HH_HL' and breakout_strength >= HH_HL_BREAKOUT_THRESHOLD:

# After (fixed):
if structure == 'HH_HL' and (breakout_strength / 100) >= HH_HL_BREAKOUT_THRESHOLD:
```

## After Fix
Only genuine 0.05%+ breakouts pass:
- AVAX: 0.050% ✅
- POPCAT: 0.053% ✅
- SAGA: 0.050% ✅
- AAVE: filtered ❌ (0.014%)
- SNX: filtered ❌

AVAX, POPCAT, SAGA all at exactly 0.050% — the minimum viable breakout. User noted these are all right at the floor and may want to raise threshold to 0.08-0.10%.

## Pattern to Prevent This
Before comparing any threshold constant against a computed value:
1. Find where the computed value is created and check its unit
2. Find where the threshold is defined and check its unit  
3. Normalize before comparing

**Variable names are NOT reliable unit indicators.** Always trace the actual formula.