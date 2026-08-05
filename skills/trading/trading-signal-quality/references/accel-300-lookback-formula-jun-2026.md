# accel-300: LOOKBACK Formula (Jun 6 2026)

## The Counter-Intuitive Formula

Cross search window in `detect_accel_300()`:
```python
search_start = max(PERIOD + LOOKBACK, n - 1 - LOOKBACK)
# n = number of 1m bars (all tokens have n=700)
# PERIOD = 300 (EMA period)
```

For n=700, PERIOD=300:

| LOOKBACK | search_start | window (bars from search_start to n-1) |
|----------|-------------|----------------------------------------|
| 20 | max(320, 679) = **679** | 679 to 699 = **21 bars** |
| 100 | max(400, 599) = **599** | 599 to 699 = **101 bars** |
| 182 | max(482, 517) = **517** | 517 to 699 = **183 bars** |
| 250 | max(550, 449) = **550** | 550 to 699 = **150 bars** |
| 300 | max(600, 399) = **600** | 600 to 699 = **100 bars** |
| 400 | max(700, 299) = **700** | 700 to 699 = **1 bar** |

**Smaller LOOKBACK = wider search window (more historical bars searched)**
**Larger LOOKBACK = narrower search window (fewer bars searched)**

This is because the formula uses `n - 1 - LOOKBACK` as the alternative — when LOOKBACK is small, `n-1-LOOKBACK` is large, giving a wider window.

## Actual Cross Ages (Jun 6 2026)

All actual crosses are at bars 320-517 (from n=700):
```
ZORA  182 bars ago  ← most recent cross
LTC   219 bars ago
PURR  225 bars ago
TON   229 bars ago
MNT   256 bars ago
... (most at 300-380 bars ago)
```

**To capture ZORA (most recent at 182 bars ago):**
- LOOKBACK must be >= 182
- With LOOKBACK=182: window starts at bar 517, covers bars 517-699 (183 bars)

**With LOOKBACK=20 (current):**
- Window starts at bar 679, covers bars 679-699 (21 bars)
- ZERO actual crosses are within 21 bars of current price
- Result: 0 signals found

## The Fix

Set `ACCEL_300_LOOKBACK = 250` in hermes_constants to capture crosses from bar 550 onward.
This captures all crosses at bar 517+ (ZORA and newer), giving a 150-bar search window.

## Also: ACCEL_300_LOOKBACK Was Not Being Imported

The signal code at accel_300.py line 70 had:
```python
LOOKBACK = 30  # hardcoded, NOT reading ACCEL_300_LOOKBACK
```

Only 2 constants were imported from hermes_constants for accel-300:
- ACCEL_300_REGIME_SLOPE_PCT
- ACCEL_300_STALE_BARS

All other accel-300 constants (PERIOD, LOOKBACK, PERSISTENCE_BARS, MIN_GAP_GROWTH_PCT, etc.)
were hardcoded locally and ignored hermes_constants values.

**Fixed Jun 6:** Added ACCEL_300_LOOKBACK to the import and changed line 70 to use it.

## When Debugging "accel-300 0 signals"

Always trace the cross detection manually:
```python
# Check if any tokens have crosses within the search window
n = 700  # all tokens
PERIOD = 300
LOOKBACK = 20  # current value in hermes_constants
search_start = max(PERIOD + LOOKBACK, n - 1 - LOOKBACK)
print(f"Search window: bars {search_start} to {n-1} ({n-search_start} bars)")

# Then check where actual crosses are
for token in tokens:
    prices = _get_1m_prices(token)
    closes = [p['price'] for p in prices]
    # Find cross bar
    for j in range(PERIOD + LOOKBACK, len(closes)):
        if direction == 'LONG' and closes[j] > ema300[j] and closes[j-1] <= ema300[j-1]:
            bars_ago = len(closes) - 1 - j
            print(f"{token}: cross at bar {j}, {bars_ago} bars ago")
            break
```

If all crosses are older than `n - search_start`, the signal will find 0 coins.