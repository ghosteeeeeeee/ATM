# SPEC: EMA9/SMA20 Rate-of-Change Signal

## Overview
New standalone signal script that measures the **rate of change (slope)** of 9 EMA and 20 SMA on 1m closes. Fires when both indicators are trending in the same direction with sufficient momentum, filtered by a minimum gap threshold to remove noise.

Pattern: similar to gap-300 but measuring momentum (slope) rather than gap width.

---

## Concept

**LONG:** Both 9 EMA and 20 SMA are rising (positive slope) AND are properly aligned (price > EMA9 > SMA20) AND the rate-of-change gap exceeds X%.

**SHORT:** Both 9 EMA and 20 SMA are falling (negative slope) AND are properly aligned (price < EMA9 < SMA20) AND the rate-of-change gap exceeds X%.

Rate-of-change gap = `|slope_ema9 - slope_sma20|` as % of price.

X = minimum rate-of-change gap threshold (start: 0.05%, backtest to find optimal).

---

## Key Design Questions (Answered)

| Question | Answer |
|---|---|
| Gap definition | Rate of change: `\|slope_ema9 - slope_sma20\| / price * 100%` |
| Rising/falling definition | Slope-based: indicator is trending in that direction (sign of recent slope) |
| Alignment | Price above both for LONG; price below both for SHORT |
| X threshold | 0.05% start, backtest range: 0.03%, 0.05%, 0.08%, 0.10%, 0.15% |
| Architecture | Standalone script → `signal_schema.add_signal()` → `signals_hermes_runtime.db` → signal_compactor → hotset.json |

---

## File Structure

- **Script:** `/root/.hermes/scripts/ema9_sma20_signals.py`
- **Source names:** `ema9-sma20+` (LONG), `ema9-sma20-` (SHORT)
- **Signal types:** `ema9_sma20_long`, `ema9_sma20_short`

---

## Constants

| Constant | Value | Notes |
|---|---|---|
| `PERIOD_FAST` | 9 | EMA period |
| `PERIOD_SLOW` | 20 | SMA period |
| `MIN_GAP_PCT` | 0.05 | Initial threshold (% of price) |
| `SLOPE_PERIOD` | 5 | Bars used to compute slope (5 = ~5min lookback) |
| `COOLDOWN_MINUTES` | 10 | Same as gap-300 |
| `LOOKBACK_1M` | 200 | 1m prices to fetch (enough for warmup + slope calc) |
| `MIN_VALID_BARS` | 30 | Minimum valid EMA+SMA bars before signals are valid |

---

## Data Source

- **Price DB:** `signals_hermes.db` → `price_history` table (same as gap-300)
- Freshness guard: skip if most recent price > 2 minutes old
- Data gap guard: skip if bar-to-bar gap > mean + 3σ or window span exceeds expected

---

## Indicator Computations

### Slope Computation
Slope over `SLOPE_PERIOD=5` bars:
```
slope_ema9 = (ema9[-1] - ema9[-SLOPE_PERIOD]) / SLOPE_PERIOD
slope_sma20 = (sma20[-1] - sma20[-SLOPE_PERIOD]) / SLOPE_PERIOD
```
Rate-of-change gap = `abs(slope_ema9 - slope_sma20) / price * 100`

### EMA Series
Standard EMA with k = 2/(period+1). SMA uses simple moving average.

### Alignment Check
- LONG: `price > ema9[-1] AND ema9[-1] > sma20[-1]`
- SHORT: `price < ema9[-1] AND ema9[-1] < sma20[-1]`

### Slope Direction
- Rising: `slope > 0` (indicator value increasing over last SLOPE_PERIOD bars)
- Falling: `slope < 0`

---

## Signal Logic

### Entry Conditions (ALL must be true)

**LONG:**
1. `ema9[-1] > ema9[-2] > ema9[-3]` (EMA9 rising for 3 consecutive bars)
2. `sma20[-1] > sma20[-2] > sma20[-3]` (SMA20 rising for 3 consecutive bars)
3. `price > ema9[-1] > sma20[-1]` (full alignment)
4. `rate_of_change_gap >= MIN_GAP_PCT`
5. Gap is **widening** (gap_now > gap_SlOPE_PERIOD bars ago)

**SHORT:**
1. `ema9[-1] < ema9[-2] < ema9[-3]` (EMA9 falling for 3 consecutive bars)
2. `sma20[-1] < sma20[-2] < sma20[-3]` (SMA20 falling for 3 consecutive bars)
3. `price < ema9[-1] < sma20[-1]` (full alignment)
4. `rate_of_change_gap >= MIN_GAP_PCT`
5. Gap is **widening**

### Confidence
```
confidence = min(80, 55 + (rate_of_change_gap - MIN_GAP_PCT) * 400)
```
Range: ~55-80%. Fires on cross above MIN_GAP_PCT.

### Guards (same pattern as gap-300)
- Collapse guard: reject if gap has pulled back >30% from recent peak (30 bars lookback)
- Direction flip guard: reject if gap direction changed since cross
- Minimum warmup: require `PERIOD_SLOW * 2` valid bars before firing

---

## Backtesting Plan

Run after script is implemented.

### X Threshold Sweep
Test values: `0.03, 0.05, 0.08, 0.10, 0.15, 0.20` (%)

### Metrics per X value:
- Total LONG signals, total SHORT signals
- Win rate per direction
- Average PnL % per direction
- Average bars held
- False positive rate (signals that reverse within 5 bars)

### Baseline tokens for backtest:
BTC, ETH, SOL, AVAX, LINK, ARB, MATIC, ADA, DOT, ATOM

### Compare:
- LONG X vs SHORT X (same X or asymmetric?)
- 9/20 vs other period pairs if time allows (e.g., 9/21, 8/20)

---

## Integration

In `signal_gen.py`, add:
```python
from ema9_sma20_signals import scan_ema9_sma20_signals

# In run() function:
ema920_added = scan_ema9_sma20_signals(prices_dict)
if ema920_added:
    print(f'  EMA9/SMA20 signals: {ema920_added} ema9-sma20 emitted')
```

---

## Output Signal Schema

Written via `signal_schema.add_signal()`:
```python
{
    'token': 'SOL',
    'direction': 'LONG',
    'signal_type': 'ema9_sma20_long',
    'source': 'ema9-sma20+',
    'confidence': 65,       # 55-80
    'value': 65,
    'price': 22.50,
    'exchange': 'hyperliquid',
    'timeframe': '1m',
    'z_score': None,
    'z_score_tier': None,
}
```

---

## Rejected / Deferred
- Asymmetric LONG/SHORT X values → defer to backtest results
- Per-token tuned periods → future enhancement
- Use with cascade flip → future enhancement (after backtest)
