# RS Signal "Looks Near But Won't Fire" — ATR Normalization Debug (2026-05-24)

## Symptom

RS signal fires for one direction but cannot pair with the chart-validated level for the opposite direction. T's eye says "the level is right there" but rs.py says no.

Example on 2Z (2026-05-24 17:48):
- Price: $0.10347
- Nearest support level: $0.103750 (only **0.27% below** — looks extremely close)
- rs-s20 fires for LONG at that level
- BUT for SHORT: no nearby resistance level passes `_price_near_level()` at k=0.70
- zscore_pump SHORT fires instead (z=-3.228) — correctly showing downward momentum
- **Result:** rs-s20 LONG and zscore-pump- SHORT can't combine into one trade (opposing directions)

## Root Cause: ATR Normalization Creates Invisible Walls

The proximity formula in rs.py:
```
dist_pct = abs(price - level) / price * 100.0   # e.g. 0.27%
atr_dist = dist_pct / atr_pct                    # e.g. 0.27 / 0.0299 = 9.0 ATRs
return atr_dist <= RS_PROXIMITY_K (0.70)         # 9.0 > 0.70 → FALSE
```

For 2Z: ATR(14) = 0.000031 (0.0299% of price). A 0.27% move = **9.06 ATRs**.

The level IS 0.27% away. Your eye says near. The system says 9 ATRs away = not near.

## Debugging Recipe

When T says "rs signal looks right but won't fire / combine":

**Step 1: Identify the actual ATR and proximity threshold**
```python
import sqlite3, numpy as np
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
c.execute("SELECT timestamp, price FROM price_history WHERE token=? ORDER BY ts DESC LIMIT 500", (TOKEN,))
rows = list(reversed(c.fetchall()))
# compute ATR(14), print ATR%, print 0.70 * ATR in absolute terms
```

**Step 2: Find all clustered levels, sort by ATR distance**
```python
# Compute swing highs/lows (window=20), cluster, compute atr_dist for each
# Print top 15 nearest: price, touch_count, dist%, atr_dist
# Flag any at atr_dist <= 1.5 (marginally near)
```

**Step 3: Check what k value would capture the level**
```python
# For the level T says is "near": what k = atr_dist?
# If k=0.70 is the ceiling, what k would this level need?
```

**Step 4: Read the price action timeline**
```
17:49  0.103760  ← resistance zone
17:50  0.103625  ← broke below resistance
17:52  0.103610  ← support zone
17:55  0.103470  ← current price (dropped through support)
```
Context: rs-s20 fires at $0.103750 (level from ~17:36). Price has since moved below it. The signal is structurally valid but stale — price moved. For SHORT direction, resistance was at $0.103760 (just broken) but the nearest clustered resistance is much higher.

## The Calibrated k Problem

| Token | ATR(14) | ATR% | 0.70×ATR in % | 0.70×ATR in $ | 0.27% in ATRs |
|-------|---------|------|---------------|--------------|-------------|
| BTC | ~$100 | ~0.5% | 0.35% | ~$64 | ~0.5 ATRs |
| ETH | ~$3 | ~1.6% | 1.12% | ~$21 | ~0.2 ATRs |
| 2Z | $0.000031 | 0.03% | 0.021% | ~$0.00002 | **9.1 ATRs** |

At k=0.70: BTC needs to be within 0.35% of a level to fire — too tight.  
At k=0.70: 2Z needs to be within 0.021% — impossibly tight for a meme coin.

A single k value cannot work across all tokens.

## What T Wants vs What the Code Does

**T wants:** "fire when price is near a chart-validated level"
**RS does:** "fire when price is within k×ATR of a level"

For flat/ranging low-ATR tokens (2Z), ATR is so small that k=0.70 becomes sub-penny. The chart says near. The code says 9 ATRs away.

## Possible Fixes

1. **Adaptive k by ATR bracket** (recommended):
   - High-ATR tokens (ETH, SOL): k=0.70 (tight — level precision matters)
   - Mid-ATR tokens: k=1.0–1.5
   - Low-ATR tokens (2Z, small mcap): k=2.0–3.0
   - Tune by checking: at k=2.0 on 2Z, does rs-s20 STILL fire alone, or does a resistance also appear?

2. **Add `RS_MAX_K` constant**: Cap k per token based on recent ATR range — prevents k from becoming absurdly loose on low-ATR tokens.

3. **Separate R&S proximity from swing detection proximity**: The `_price_near_level()` check in `_find_swing_highs_lows` (lines 462-480) applies k=0.70 uniformly. Consider a looser k specifically for the "is price near a valid level" question vs "is this a real swing structure."

## Related

- `references/rs-proximity-ancient-levels.md` — k=1.20 too loose for different reason
- `references/rs-support-resistance-flip-2026-05-24.md` — BCH flip case, level broken hours before
- `references/zscore-pump-extreme-z-losses-2026-05-24.md` — zscore-pump divergence logic
- `signals/rs.py` lines 187-193 — `_price_near_level()` implementation
- `signals/rs.py` lines 462-480 — nearest level search using `_price_near_level()`
- `signals/rs.py` lines 35-41 — rs.py local constants (NOT from hermes_constants)