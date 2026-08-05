# 78% SL Hit Rate — Root Cause Analysis (2026-05-10)

## The Problem

Across 41 closed trades:
- **78% (32/41) hit ATR SL**
- **0% (0/41) hit ATR TP**
- **29.3% WR**, avg +0.346%/trade

The first counter-candle immediately hits SL on 78% of entries. This means entries are happening AFTER the move has already peaked.

## Signal Quality Evidence

8 big winners (>1%): all LONG, all accel-300+, 6/8 had RS co-signal (8-112 touches).
28 small losses (-1-0%): 25/28 were accel-300+, many with RS co-signal but at wrong touch counts (>100 or <8).

**The 78% of trades that hit SL are losing 0.1-0.8%** — these are small losses consistent with T's philosophy. The bigger lever is entry timing.

## Two-part Fix

### Part 1: RS improvements (done 2026-05-10)
- RS_PROXIMITY_K: 1.00 → 0.70 (fire closer to level)
- Recency scoring (prioritize fresh levels over ancient)
- Lower MIN_TOUCHES: 8 → 3

### Part 2: Monitor confluence pass rate
After RS improvements: goal is >40% of early accel-300+ entries having RS co-signal. Check pipeline.log for confluence-gate pass/fail ratio.

## Recommended Next Steps

1. Monitor RS new behavior — see if RS fires more on fresh levels
2. Check confluence pass rate in pipeline.log — goal is >40% of early accel entries having RS co-signal
3. If confluence still low, consider adding a 3rd signal type (e.g., momentum+) to increase combo formation rate
4. Re-run PnL analysis on 50+ new trades to measure impact