# rs.py Broken-Level Recovery Fix

**Date:** 2026-06-03
**File:** `/root/.hermes/scripts/signals/rs.py`
**Bug:** `rs-s-broken` SHORT fires when price has RECOVERED above a broken support (bounce scenario). Same for `rs-r-broken` LONG when price fell back below a broken resistance.

## Root Cause
`broken` flag is set by `_level_recently_broken()` based on historical cross events (200-candle lookback). When price later recovers, the flag stays True but the price-vs-level check was never applied.

## Fix Applied

### Patch 1 — Support (lines 543-558)
```python
if broken:
    if price > level:
        broken = False
        bounces = True
```
Redirects to LONG bounce path when price is now above the broken level.

### Patch 2 — Resistance (lines 607-618)
```python
if broken:
    if price < level:
        broken = False
```
Skips broken LONG when price is now below the broken level.

## Verification
- Compile/import: clean
- 4 logic scenarios tested: all pass
- AI engineer audit: no new bugs
- CAKE/LTC correctly flipped from SHORT→LONG in live trace
- GALA still SHORT because price < level (correct — fix only applies when price recovers)

## Edge Cases
- `price == level`: equality goes to original broken path (neither patch fires)
- `bounces=True` override only affects signal dict — no downstream consumers
- `source` field changes from `rs-s-broken` → `rs-s{touch_count}` on redirect (correct)