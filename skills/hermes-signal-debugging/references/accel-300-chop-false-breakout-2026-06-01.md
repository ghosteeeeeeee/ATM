# accel-300 chop false breakout — 2026-06-01

## Problem
accel_300 fires SHORT on brief EMA dips that immediately reverse to LONG.
- ME: crossed DOWN bar 608, max depth -0.37%, back above EMA in 15 bars → now +1.51% above EMA
- UNI: crossed DOWN bar 610, max depth -0.42%, back above EMA in 15 bars → now +0.59% above EMA
- CHIP: crossed DOWN bar 589, max depth -0.24%, back above EMA in 15 bars → now +0.37% above EMA

Signal detected cross DOWN, emitted SHORT, but price immediately snapped back above EMA.
These were noise crosses, not directional momentum.

## Root cause
Cross detection (lines 192-193 of accel_300.py) fires on ANY cross, even the brief 3-5 bar kind that immediately reverses. The signal logic has no chop filter to distinguish real breakdowns from temporary oscillations.

## Key diagnostic queries

```sql
-- Find all cross events for a token in recent bars
SELECT timestamp, price, ema300, (price - ema300) / ema300 * 100 as gap_pct
FROM price_history
WHERE token = 'ME' AND timestamp > (SELECT MAX(timestamp) - 7200 FROM price_history WHERE token = 'ME')
ORDER BY timestamp DESC LIMIT 100;

-- Check bars between cross and re-cross (chop measurement)
-- For each cross DOWN, count bars until price crosses back above EMA
```

## Diagnostic trace script
```python
# Trace why accel_300 fired for a specific token at a specific time
# Run this in the signals_hermes_runtime.db context
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from signals.accel_300 import detect_accel_300, _get_1m_prices, _ema_series, PERIOD

token = 'ME'
prices = _get_1m_prices(token, lookback=700)
closes = [p['price'] for p in prices]
ema300 = _ema_series(closes, PERIOD)

# Find cross bars
for i in range(50, len(closes)-1):
    if closes[i] < ema300[i] and closes[i-1] >= ema300[i-1]:
        gap_at_cross = (closes[i] - ema300[i]) / ema300[i] * 100
        bars_below = 0
        for j in range(i+1, min(i+20, len(closes))):
            if closes[j] < ema300[j]:
                bars_below += 1
            else:
                break
        print(f"Cross DOWN at bar {i}: gap={gap_at_cross:.4f}%, stayed below EMA for {bars_below} bars")
```

## Chop filter design options

**Option A: Return-on-cross test** (recommended)
- For cross DOWN (SHORT), check if price crosses BACK above EMA within N bars (e.g., 5)
- If yes → suppress SHORT (chop), optionally flag for LONG consideration
- Add as new condition after condition 1 (cross detection) in detect_accel_300

**Option B: Bars-below threshold**
- After cross DOWN, require price stays below EMA for X bars before signal can fire
- e.g., if price returns to above EMA within 3 bars of cross → no SHORT

**Option C: Gap-at-cross confirmation**
- At cross bar, gap must be <= -0.20% (not a shallow -0.05% dip) to be real breakdown
- Shallow cross = likely chop

**Option D: Combine with EMA angle**
- If EMA is flat (< 0.02% change over 30 bars), suppress SHORT signals
- Flat EMA = ranging/chop market

## Chop vs momentum diagnostic metrics

| Metric | Chop signal | Real breakdown |
|--------|-------------|----------------|
| Bars below EMA after cross | < 10 bars | 20+ bars |
| Max depth vs gap at cross | < 2x | > 3x |
| Gap std dev after cross | high | low/stable |
| Re-cross speed | < 5 bars | never / 50+ bars |
| EMA angle | flat (< 0.02%) | angled (> 0.05%) |

## Fix applied 2026-06-01
Three patches applied to accel_300.py:
1. Regime filter: candles.db → price_history (signals_hermes.db) — stale data bug
2. SHORT expansion gate removed — 4a gap growth covers SHORT acceleration
3. Staleness gate line 353: `<= 0` → `>= 0` for SHORT — inverted condition was blocking valid SHORTs

Chop filter NOT yet implemented — pending user decision on Option A/B/C/D.