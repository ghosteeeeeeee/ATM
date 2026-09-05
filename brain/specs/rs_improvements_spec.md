# RS Signal Improvements — Spec

**Date:** 2026-09-05
**Problem:** TURBO fires LONG+SHORT at same price with low effective confidence (28.6)
**Root cause:** Tight-range tokens inflate touch counts and create meaningless S/R levels

---

## Current Issues

### 1. Touch Count Inflation
- TURBO: 2448 touches on a single level
- Cause: `touch_threshold_pct = 0.15%` — in a tight range, EVERY bar is a "touch"
- Impact: False sense of structural significance

### 2. Level Differentiation
- 960 swing highs, 890 swing lows — all clustering at $0.001012
- No separation between support and resistance — they're the same level
- Signal fires both LONG and SHORT at the same price

### 3. No Bounce Confirmation
- TURBO signal fires with `bounce=False`
- Price is AT the level, not bouncing FROM it
- Missing the key quality filter

### 4. Confidence Inflation
- Raw signal: conf=88 (capped at max)
- After downstream adjustments: conf=28.6
- The engine knows the signal is weak, but the RS detection doesn't

---

## Proposed Fixes

### Fix 1: Normalize Touch Counts by Range

Instead of raw touch count, normalize by the token's typical range:

```python
# Current: raw touches (inflated for tight ranges)
touch_count = _build_level_touches(...)

# Proposed: normalized touches
range_20 = (max(closes[-20:]) - min(closes[-20:])) / min(closes[-20:]) * 100
if range_20 < 1.0:
    # Tight range — discount touch counts
    touch_count = touch_count * (range_20 / 1.0)  # scale down
```

### Fix 2: Require Minimum Level Separation

Support and resistance must be separated by at least X%:

```python
# If nearest support and resistance are within 0.5% of each other,
# it's a ranging market — don't fire signal
if nearest_support and nearest_resistance:
    separation = abs(nearest_support[0] - nearest_resistance[0]) / price * 100
    if separation < 0.5:
        return None  # ranging — no clear direction
```

### Fix 3: Strengthen Bounce Confirmation

Require bounce to be more than just a touch:

```python
# Current: touch + bullish candle = bounce
# Proposed: touch + bullish candle + close above open by >0.1%
def _bounce_confirmation(candles, level, direction, lookback=200):
    for c in recent:
        touch_pct = abs(c['low'] - level) / level * 100.0
        if touch_pct < 0.33 * atr_pct:  # ATR-normalized touch
            body = (c['close'] - c['open']) / c['open'] * 100
            if direction == 'LONG' and body > 0.10:  # meaningful bullish candle
                return True
            elif direction == 'SHORT' and body < -0.10:  # meaningful bearish candle
                return True
    return False
```

### Fix 4: Add Price-Distance Penalty

If price is essentially AT the level (within 0.1%), penalize confidence:

```python
# Price at level = no clear direction
if dist_pct < 0.10:
    confidence -= 20  # heavy penalty
```

---

## Implementation Priority

1. **Fix 2 (level separation)** — highest impact, catches the TURBO case
2. **Fix 3 (bounce confirmation)** — prevents false signals without bounce
3. **Fix 1 (touch normalization)** — reduces inflated touch counts
4. **Fix 4 (distance penalty)** — fine-tuning

---

## Expected Impact

- TURBO: would NOT fire (support ≈ resistance = ranging)
- Tight-range tokens: reduced false signals
- Normal tokens: unchanged (good signals still fire)
