# accel-300 Market Chop — Signal Correctly Suppresses (Not a Bug)

##2026-06-06 Late PM Session

### The Finding

accel-300 is returning 0 signals. The market looks trending (positive EMA angles0.1-1.3%/bar). But the signal correctly fires 0 times.

**Root cause: market is mid-pullback after initial move, not a signal bug.**

The signal fires at the START of trending moves. During consolidation after the initial move:
- `gap_growth` fails (gap is contracting, not expanding)
- `marginal_accel` fails (recent momentum delta is flat/negative)
- `gap_expansion` fails (gap has narrowed from the cross point)

All 423 "signal opportunities" found in the full scan were bars where tokens briefly passed early filters — those moments were transient. By the time the scanner checks the latest bar, gaps have contracted and the opportunity has passed.

### How to Tell It's Market Conditions vs a Bug

Run the full scan across all bars (not just latest) to find "signal opportunities":
```python
# Scan all bars, print which filter blocks each token at latest bar
# vs how many bars they passed early filters in the lookback window
```

If opportunities exist but latest-bar returns None → market is mid-pullback, signal is working correctly.

### Parameters Doing Their Job in Chop

| Filter | Constant | Current Market Effect |
|---|---|---|
| Regime slope | ACCEL_300_REGIME_SLOPE_PCT=0.003 | Tokens have slopes 0.1-1.3% — PASS |
| Gap growth | ACCEL_300_MIN_GAP_GROWTH=0.05 | Gap contracting — FAIL |
| Persistence | ACCEL_300_PERSISTENCE_BARS=4 | Most tokens still holding — PASS |
| Gap expansion | ACCEL_300_MIN_GAP_EXPANSION=0.05 | Gap narrowed from cross — FAIL |
| Marginal accel | (internal delta check) | Delta flat/negative — FAIL |

### The Real Win Rate Problem (Different from the 0 Signals)

The 0 signals in the 96h scan is market conditions. The **actual win rate problem** is accel-300 LONG historically:
- accel-300 LONG: 9.4% WR, -58% avg return — catastrophic
- accel-300 SHORT: 51.6% WR, +0.18% avg — working correctly
- rs-s-broken SHORT:52.9% WR — also working

**accel-300 LONG is the problem, not the0-signal state.**

### What NOT to Change

Don't relax `ACCEL_300_MIN_GAP_GROWTH` or `ACCEL_300_MIN_GAP_EXPANSION` to get more signals in chop. That will lower win rate — the parameters are doing exactly what they're designed to do (filtering out chop).

### What TO Change (If Anything)

Only if T wants to fight chop:
- `ACCEL_300_MIN_GAP_GROWTH = 0.03` — fires when gap is still expanding (lower quality)
- `ACCEL_300_MARGINAL_ACCEL_LOOKBACK` (new constant) — use longer window for momentum check

But this is the wrong direction. The signal correctly suppresses in chop. The real work is fixing accel-300 LONG's terrible win rate.

### Debug Pattern

```python
# Test a token manually
from signals.accel_300 import detect_accel_300
prices = _get_1m_prices(token)  # returns list of dicts
result = detect_accel_300(token, prices)
print(f'Result: {result}')

# Full scan across all bars to find transient opportunities
# (run once, capture the output, compare to latest-bar result)
```
