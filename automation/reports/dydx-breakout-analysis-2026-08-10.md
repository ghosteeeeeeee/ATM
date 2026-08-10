# DYDX Breakout Analysis — 2026-08-10

## The Trade

| Field | Value |
|-------|-------|
| Token | DYDX |
| Signal | continuation+,range_breakout+ |
| Direction | LONG |
| Entry | $0.11539 |
| Exit | $0.11626 |
| PnL | +0.75% |
| Open | 2026-08-10 15:29:14 |
| Close | 2026-08-10 15:46:40 |
| Exit reason | profit-monster-trail |
| Highest | $0.11707 |

## Price Action

```
15:13:57  $0.11378  ← LOW (dip before breakout)
15:15:58  $0.11451  +0.55% ← FIRST BREAKOUT SPIKE
15:29:03  $0.11542  +0.49% ← SECOND SPIKE (trade opened here at 15:29:14)
15:31:03  $0.11570  +0.30% ← THIRD SPIKE
15:32:34  $0.11607  +0.31% ← FOURTH SPIKE
15:36:35  $0.11687  ← PEAK
15:41:37  $0.11707  ← HIGHEST
```

## What Happened

1. DYDX dipped to $0.11378 at 15:13:57
2. First breakout spike at 15:15:58 (+0.55%)
3. Trade entered at 15:29:14 during the SECOND leg ($0.11539)
4. Price peaked at $0.11707, trade exited at $0.11626 (+0.75%)

## Why range_breakout Missed the First Leg

range_breakout.py requires:
1. Range (BB width < threshold)
2. Breakout (price closes above upper band)
3. **Retest** (price pulls back near the band)
4. Bounce (price closes above previous close)

The retest requirement means it waits for price to pull back to the breakout level. By the time retest happens, the first leg is over.

## How to Catch It Earlier

| Approach | What | Trade-off |
|----------|------|-----------|
| A. Faster range_breakout | Remove retest requirement, fire on breakout itself | More false breakouts |
| B. New ATR momentum signal | Price moves >1x ATR in 1-3 candles → fire immediately | Needs tuning for ATR threshold |
| C. Volume spike detection | Volume >2x average + price surge | Volume data is 0 for 97% of candles |

## Recommendation

Create a new `momentum_ignition.py` signal that fires on sudden ATR-based price moves. This complements range_breakout (which catches confirmed breakouts) by catching the initial thrust.

Signal logic:
1. Compute ATR(14) on 1m or 5m candles
2. Detect price move >1x ATR in 1-3 candles
3. Confirm with velocity >threshold (price_velocity_5m from token_speeds)
4. Fire LONG if upward thrust, SHORT if downward thrust
5. No retest required — fire on the breakout itself

This would have caught DYDX at ~$0.11450 (first spike) instead of $0.11539 (second leg), capturing an extra ~0.8% profit.
