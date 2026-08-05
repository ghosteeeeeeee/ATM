# RS Signal Diagnostic — Reference Sheet
## Session: 2026-06-17 — RS signal drought investigation

---

## Finding 1: Proximity Filter Impossibly Tight for Low-Vol Tokens

**Symptom:** RS signals written to DB but not reaching hot-set. All levels show `near=False`.

**Root cause formula:**
```
max_proximity_pct = RS_PROXIMITY_K × ATR%
for 0G: ATR% = 0.0417%, RS_PROXIMITY_K = 0.70
  → max = 0.70 × 0.0417% = 0.029%
  
level 0.30508 vs price 0.30344 = 0.54% away → 18x over budget
```

**Diagnostic one-liner:**
```python
atr_pct = atr / price * 100
max_allowed = RS_PROXIMITY_K * atr_pct
for each level:
    dist_pct = abs(price - level) / price * 100
    near = dist_pct <= max_allowed
```

---

## Finding 2: Bounce Threshold Inverted Logic

**Symptom:** `bounce_confirmation()` always returns False even when level was recently touched.

**Root cause:**
```
RS_BOUNCE_THRESH_ATR = 1.0
  touch_thresh = 1.0 ATR × 0.2 = 0.2 ATR  (what "touched" means)
  
Bounce follow-through = 0.025% of level
  = 0.30508 × 0.00025 = 0.000076

Ratio: follow_through / touch_thresh = 3.0x
  → required bounce move is 3x larger than what "touched" means
```

**Fix direction:** `RS_BOUNCE_THRESH_ATR` should be ~0.33 so that:
```
touch_thresh = 0.33 × 0.2 = 0.067 ATR
follow_through = 0.025% of level
ratio ≈ 0.9x (achievable)
```

---

## Finding 3: Swing Detection Creates Massive Touch Clusters

**Symptom:** Touch counts in millions (e.g., tc=6,821,892 for 0G resistance).

**Root cause:** 2,463 swing highs all cluster into 1 level (within 1 ATR of each other).
Each has 2,772 touches. Clustering sums them: 2,463 × 2,772 = 6.8M.

This means:
- `RS_TOUCH_HARD_CAP=120` instantly blocks all clustered levels
- `RS_DECIDER_MIN_TOUCHES=80` is exceeded, then decider penalizes

**Diagnostic one-liner:**
```python
swing_highs, swing_lows = rs._find_swing_highs_lows(candles, RS_LEVEL_LOOKBACK)
# If len(swing_highs) >> 1 and cluster_pct is large, clustering will multiply counts
```

---

## Finding 4: ATR% Determines Everything

The entire RS signal system is governed by `ATR% = ATR / price × 100`:

| ATR% range | Behavior |
|------------|----------|
| > 0.5% | High volatility — proximity filter manageable, touch counts moderate |
| 0.1–0.5% | Medium — system works as designed |
| < 0.1% | Low volatility — proximity filter becomes impossibly tight, touch counts explode from clustering |

**Tokens to watch:** high-market-cap, low-vol tokens (0G, ALT, CC at time of writing).

---

## Diagnostic Workflow (copy-paste)

```python
import sys, numpy as np
sys.path.insert(0, '/root/.hermes/scripts')
from signals import rs

token = 'TOKEN'
candles = rs._get_candles_1m(token)
if candles is rs._STALE_SENTINEL or not candles:
    print("STALE or empty"); exit()

price = get_price(token)  # your price source
atr = rs._atr(candles, RS_ATR_PERIOD)
atr_pct = atr / price * 100
max_prox = RS_PROXIMITY_K * atr_pct

print(f"ATR={atr:.6f}, ATR%={atr_pct:.4f}%, max_prox={max_prox:.4f}%")

highs = np.array([c['high'] for c in candles], dtype=np.float64)
lows  = np.array([c['low']  for c in candles], dtype=np.float64)

swing_highs, swing_lows = rs._find_swing_highs_lows(candles, RS_LEVEL_LOOKBACK)
print(f"Swing highs={len(swing_highs)}, lows={len(swing_lows)}")

# Check resistance levels
for _, level in swing_highs[:5]:
    thresh = atr * RS_BOUNCE_THRESH_ATR
    dist_pct = abs(price - level) / price * 100
    touch_count = np.sum(np.abs(highs - level) < thresh)
    print(f"  R lvl={level:.6f} dist={dist_pct:.3f}% near={dist_pct<=max_prox} touches={touch_count}")
```

---

## Parameter Reference (hermes_constants.py)

| Constant | Value | Status |
|----------|-------|--------|
| RS_PROXIMITY_K | 0.70 | **TOO TIGHT** — needs 3.0–4.0 for low-vol tokens |
| RS_BOUNCE_THRESH_ATR | 1.0 | **INVERTED** — needs ~0.33 |
| RS_TOUCH_HARD_CAP | 120 | Too aggressive given clustering amplification |
| RS_DECIDER_MIN_TOUCHES | 80 | Works after proximity fix |
| RS_BROKEN_SHORT_ENABLED | True | Counter-trend trap — should be False |
| RS_BROKEN_RESISTANCE_LONG_ENABLED | True | Counter-trend trap — should be False |
