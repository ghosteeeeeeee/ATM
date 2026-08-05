# rs.py / accel_300.py — Known Bugs (Verified 2026-06-02)

## rs.py: rs-s-broken SHORT fires without bounce confirmation

**File:** `/root/.hermes/scripts/signals/rs.py`  
**Line:** 527  
**Bug:** `bounces=False` hardcoded in the broken-support SHORT path, ignoring the pre-computed bounce result.

```python
# Line 515: bounce IS computed
bounces = _bounce_confirmation(candles, level, 'LONG', atr_value=atr)

# Line 519-527: broken path — bounces discarded
if broken:
    confidence = _compute_confidence(atr_pct, best_support_dist, touch_count, bounces=False, recency_score=recency)
```

**Normal bounce path (line 545) — correct:**
```python
confidence = _compute_confidence(atr_pct, best_support_dist, touch_count, bounces, recency)
```

**Fix:** Change line 527 from `bounces=False` to `bounces=bounces`.

**Why it fires in uptrends:** `RS_LEVEL_BROKEN_LOOKBACK = 200` (~3.3h on 1m). In an uptrend, price breaks support and retraces up. `_level_recently_broken()` returns True (level was crossed 50 bars ago), signal fires SHORT with no bounce filter. The level was "broken" hours ago but we're SHORTING on the retrace.

**Key constants (hermes_constants.py):**
- `RS_LEVEL_BROKEN_LOOKBACK = 200` — lookback for level invalidation check
- `_BOUNCE_LOOKBACK = 6` — lookback for bounce confirmation (~6 candles)
- `_BOUNCE_THRESH_ATR = 1.00` — touch threshold for bounce (1.0 × ATR14)

---

## accel_300.py: condition 4c removed for SHORT only

**File:** `/root/.hermes/scripts/signals/accel_300.py`  
**Line:** 343  
**Bug:** Gap-expansion gate (condition 4c) only applies to LONG. For SHORT it was explicitly removed, making the SHORT filter weaker.

```python
# Line 341-349
# For SHORT: REMOVED — condition 4a (gap growth) already captures acceleration for SHORT.
#   The expansion gate was fundamentally broken for negative gaps (asymmetric comparison).
if cross_bar is not None and gap_pcts[cross_bar] is not None:
    gap_at_cross = gap_pcts[cross_bar]
    if direction == 'LONG':
        if gap_now < gap_at_cross + MIN_GAP_EXPANSION:
            continue
```

**Effect:** accel-300 fires ~7.9x more SHORT than LONG signals. The LONG path has an extra filter (gap expansion must exceed `MIN_GAP_EXPANSION`) that SHORT doesn't.

**Note from code:** The removal was intentional ("fundamentally broken for negative gaps") but resulted in an asymmetric filter. The SHORT path only has condition 4a (gap growth). LONG has 4a + 4c.

---

## Regime penalty — symmetric (no bug)

Both paths get 15% haircut in NEUTRAL regime (lines 530 and 550). The asymmetry is the **bounce requirement**, not the penalty.