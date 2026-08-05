# zscore-pump+ Failure: Momentum Signal is Anti-Momentum (2026-05-17)

## Problem
zscore-pump+ (LONG) is catching market tops, not riding rockets. Combined with RS (support), every combo loses catastrophically.

## Root Cause: z-score measures exhaustion, not momentum

zscore-pump uses a 60-bar (1-hour) lookback:
```python
ZSCORE_PUMP_LOOKBACK = 60   # bars
ZSCORE_PUMP_THRESHOLD = 2.0  # |z| must exceed this
```

z = (price - mean) / std_dev

When z = +2.5, price is 2.5 standard deviations ABOVE its 1-hour average. This is NOT a bullish continuation signal — it's an exhaustion/reversal signal. The move already happened. Buying at z=2.5 means you're buying at the top of a 1-hour reversion to the mean.

Compare this to accel-300 which fires when price is PERSISTENTLY above EMA300 (300-bar mean) — that's trend continuation. zscore-pump+ fires when price is ALREADY FAR from the mean — mean reversion territory.

## Evidence from signal_outcomes

All zscore-pump+ (LONG) combos since May 16 are losers:
```
rs-r126,zscore-pump-  : +203% (ETH SHORT) — GOOD
ema-angle-,zscore-pump-: -183% (DYDX SHORT) — BAD
rs-s30,zscore-pump+   : -234% (BRETT LONG) — BAD
rs-s58,zscore-pump+   : -258% (STBL LONG) — BAD
```

zscore-pump- (SHORT) has some wins (ETH SHORT at +203%) but is inconsistent. The SHORT direction may work in strong downtrends but fails in choppy markets.

## Key Insight: zscore-pump+ is anti-momentum for LONG

For LONG signals: you want price ABOVE average (confirmed uptrend). But a z-score of +2.5 on 60 bars means price has already had a 1-hour surge and is likely to pull back. It's the opposite of what you want for trend-riding.

For SHORT signals: z < -2.5 means price is 2.5 std devs BELOW its 1-hour average. In a downtrend this can be a continuation signal (price keeps falling). In a bounce scenario it catches falling knives.

## What to Do

1. **Block zscore-pump+ entirely** (`ZSCORE_PUMP_PLUS_ENABLED = False`) until direction logic is fixed
2. **Raise threshold** to 2.5 — only the most extreme deviations
3. **Extend lookback** to 90 bars — more robust mean, less noise
4. The zscore-momentum tuner (zscore_momentum.py) tunes per-token params but cannot fix the fundamental direction problem — a tuned z-score on 60 bars is still measuring exhaustion, not momentum

## Why the Tuner Doesn't Help Here

The tuner finds optimal lookback/threshold per token based on historical WR. But if the signal type itself (LONG on +z-score) is fundamentally flawed, tuning just finds the least-bad parameters for a bad signal. The 94.4% WR on 0G from the tuner means nothing if the signal direction is backwards.