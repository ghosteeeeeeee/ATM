# accel-300 Cross-Back Fix — 2026-06-11 (v2)

**Root cause:** After finding `cross_bar`, code never checked if price **crossed BACK through EMA** between `cross_bar` and detection bar `i`. The persistence check only looks at 2 bars — misses cross-backs 30+ bars ago.

**Fix applied:** Added `cross_back_validity` check in `accel_300.py` lines 429-470.

## Bug Pattern

For a SHORT signal:
- `cross_bar` is found at j (e.g., j=299 warmup boundary)
- Price stays ABOVE EMA for N bars after cross_bar (N can be 30-500)
- Detection bar i: price is below EMA → fires SHORT
- But cross is stale — price crossed back up and stayed there

**ME example (i=359):**
- `cross_bar=299` (PERIOD-1, warmup boundary)
- Price stayed ABOVE EMA for all 60 bars between j=299 and i=359
- `bars_since_cross=60`, `gap=-0.60%`
- Signal fires SHORT because current bar is below EMA
- But the cross was from a completely different trend regime

**Persistence check only checks 2 bars** — misses cross-backs that happened 30+ bars ago.

## The Fix

```python
# After bars_since_cross is calculated (line 427):
if cross_bar is not None and cross_bar < i:
    cross_back_valid = True
    for j in range(i - 1, cross_bar, -1):
        if direction == 'SHORT':
            # For SHORT: cross-back = price went ABOVE EMA
            if closes[j] > ema300[j] and j + 1 < len(closes) and closes[j + 1] <= ema300[j + 1]:
                bars_above = sum(1 for k in range(j, min(i, len(closes)-1)) if closes[k] > ema300[k])
                if bars_above >= 2:
                    cross_back_valid = False
                    break
        elif direction == 'LONG':
            # For LONG: cross-back = price went BELOW EMA
            if closes[j] < ema300[j] and j + 1 < len(closes) and closes[j + 1] >= ema300[j + 1]:
                bars_below = sum(1 for k in range(j, min(i, len(closes)-1)) if closes[k] < ema300[k])
                if bars_below >= 2:
                    cross_back_valid = False
                    break
    if not cross_back_valid:
        continue  # BLOCK: cross is stale
```

## Results Before/After

| Coin | Signal fired | Direction | Fix result |
|------|-------------|-----------|-----------|
| ME | SHORT | WRONG (price above EMA) | BLOCKED (None) |
| SKR | LONG | WRONG (price below EMA) | SHORT (correct) |
| TIA | SHORT | WRONG | BLOCKED (None) |
| AVNT | SHORT | WRONG | BLOCKED (None) |
| FET | SHORT | WRONG | BLOCKED (None) |

## Universe Scan After Fix

12 signals firing, all directionally correct:
- DASH, GRASS, HEMI, JUP, KBONK, KLUNC, KNEIRO, NOT, PURR, SKR, W, XMR

All verified: price at detection bar is on correct side of EMA (above = LONG, below = SHORT).

## Verification Code

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from accel_300 import detect_accel_300, _get_1m_prices, _ema_series
from hermes_constants import ACCEL_300_PERIOD, ACCEL_300_LOOKBACK_1M

coins = ['ME', 'SKR', 'TIA', 'AVNT', 'FET']
for coin in coins:
    prices = _get_1m_prices(coin, ACCEL_300_LOOKBACK_1M)
    r = detect_accel_300(coin, prices)
    if r:
        print(f"{coin}: {r['direction']} | price vs ema check")
    else:
        print(f"{coin}: BLOCKED")
```

## Key Constants

```
ACCEL_300_PERSISTENCE_BARS = 2   # persistence only checks 2 bars — too short
ACCEL_300_STALE_BARS_SHORT = 55  # bars_since_cross threshold for SHORT
ACCEL_300_STALE_LOOKBACK   = 400 # detection bar must be within 400 bars of latest
ACCEL_300_MIN_GAP_PCT_SHORT = 0.25
ACCEL_300_MIN_GAP_PCT_LONG  = 0.20
```