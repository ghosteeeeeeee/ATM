# accel-300 sustained breakdown fix (2026-06-10)

## Problem
accel-300 was NOT firing on BLUR and ME — both coins had been below EMA300 for 400+ consecutive bars (sustained downtrend/bleed). The signal was designed for exactly this pattern but was blocked.

## Root causes

### 1. LOOKBACK too short (30 bars)
`ACCEL_300_LOOKBACK = 30` for SHORT direction. The cross happened ~400 bars ago — the signal literally couldn't see it because it only looked back 30 bars.

### 2. C1 "was above within last N bars" check
The condition `was_above_recently` was always False for BLUR/ME because price had never crossed back above EMA within the 30-bar window. The signal path always exited at C1.

### 3. Cross bar fallback skips EMA warmup zone
The fallback cross_bar search (pass 2) skips indices 0-298 because `ema300[j] is None` during warmup. The actual cross for BLUR/ME was at index 299 (first valid EMA bar) — which was also blocked because `ema300[j-1]` was None.

### 4. bars_since_cross stale gate
When implied_cross_bar was used, bars_since_cross could be 500+, failing the STALE_BARS_SHORT=55 check.

## Fix applied

### hermes_constants.py
```python
ACCEL_300_LOOKBACK        = 30   # for LONG only
ACCEL_300_LOOKBACK_SHORT  = 500  # NEW — much longer for SHORT sustained bleeds
```

### accel_300.py — Directional lookback in C1
```python
direction = 'LONG' if current_above else 'SHORT'
lookback_dir = ACCEL_300_LOOKBACK_SHORT if direction == 'SHORT' else ACCEL_300_LOOKBACK
# ... C1 check uses lookback_dir instead of fixed LOOKBACK
```

### accel_300.py — Sustained bleed fallback
When `current_below and not was_above_recently`:
- If `was_ever_above_in_window = False` (price was NEVER above EMA in the entire lookback window): set `implied_cross_bar = max(i - lookback_dir, 0)`. This is a pre-existing downtrend — treat the first bar of our data as the implied cross point.
- If `was_ever_above_in_window = True`: block (never went above at all)

### accel_300.py — Warmup boundary cross detection
Fallback cross search now allows `j == PERIOD - 1` (299) even when `ema300[j-1]` is None:
```python
prev_ema_valid = (j - 1 >= 0 and ema300[j-1] is not None) or j == PERIOD - 1
if direction == 'SHORT' and closes[j] < ema300[j]:
    if j == PERIOD - 1:
        prev_cond = True  # warmup boundary, allow cross
    else:
        prev_cond = closes[j-1] >= ema300[j-1]
```

### accel_300.py — Stale bars skip for sustained bleed
```python
is_sustained_bleed = False
if cross_bar is None and implied_cross_bar is not None:
    cross_bar = implied_cross_bar
    is_sustained_bleed = True

# In stale bars check:
if not is_sustained_bleed and bars_since_cross >= max_stale:
    continue
```

## Key lesson
accel-300 was designed for "slow breakouts" and "sustained bleeds" — moves that persist and accelerate. The original implementation had a 30-bar LOOKBACK that worked for fresh crosses but completely blocked sustained moves where the cross was far in the past. The fix is directional: SHORT gets a 500-bar lookback vs 30 for LONG.

**Always check what the user INTENDED vs what the code actually does. The docstring said "slow breakouts" and "persistent moves" — the 30-bar lookback contradicted that entirely.**

---

## Audit verification (2026-06-10)

Confirmed all 5 changes are correct via concrete value traces:

| Change | Line(s) | Verdict |
|--------|---------|---------|
| ACCEL_300_LOOKBACK_SHORT=500 | 62,75 | ✓ Constant imported and aliased |
| Directional lookback (lookback_dir=500 for SHORT) | 246-273 | ✓ C1 correctly allows signal when `was_ever_above_in_window=False` |
| Warmup boundary j=299 | 346,351-352,359-360 | ✓ `prev_ema_valid` correctly bypasses `ema300[j-1]` check |
| is_sustained_bleed flag | 372-376 | ✓ `cross_bar=None` + `implied_cross_bar` set → flag set |
| Stale bars skip for sustained bleeds | 398 | ✓ `not is_sustained_bleed and bars_since_cross >= max_stale` evaluates False when `is_sustained_bleed=True` |

**Key verified behaviors:**
- `implied_cross_bar` is always initialized to `None` at line 241 before any conditional — `'implied_cross_bar' in dir()` at line 373 is always True within the loop body (redundant but harmless)
- Gap expansion gate (`gap_now > gap_at_cross + EXP`) correctly blocks contracting gaps for SHORT with negative values: `-0.50 > -0.89` = True (blocked)
- `is_sustained_bleed` affects only line 398 — no downstream effects on gap expansion, marginal acceleration, regime slope, stale gap decay, or chop filter
- Normal SHORT cross within 55 bars: passes stale check ✓
- Sustained bleed with bars_since_cross=400: stale check bypassed ✓