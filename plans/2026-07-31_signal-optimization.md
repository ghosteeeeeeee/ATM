# Signal Optimization Plan

## Date: 2026-07-31

## Problem Statement

The trading system has a 37% WR across 89 trades in the last 24 hours. Analysis reveals that signals are firing in the wrong direction (17-25% accuracy) and the context gate flip is wrong 67% of the time. The goal is to improve signal quality by modeling winning trades.

## Analysis: Winners vs Losers

Analyzed 28 winning trades vs 45 losing trades with full market metadata:

### Statistical Comparison

| Metric | Winners | Losers | Difference |
|--------|---------|--------|------------|
| Z-Score | +0.02 | +0.10 | -0.09 |
| Speed | 71% | 62% | +8.5% |
| Momentum | 29 | 26 | +3.5 |
| RSI | 46.9 | 51.6 | -4.75 |

### Key Findings

1. **Z-Score: Neutral zone wins**
   - Winners: mean +0.02 (neutral)
   - Losers: mean +0.10 (slightly positive)
   - Optimal: z between -0.5 and +0.5

2. **Speed: High momentum wins**
   - Winners: mean 71%
   - Losers: mean 62%
   - Optimal: speed > 50%

3. **Momentum: Strong trend wins**
   - Winners: mean 29
   - Losers: mean 26
   - Optimal: momentum > 25

4. **RSI: Not overbought/oversold wins**
   - Winners: mean 46.9
   - Losers: mean 51.6
   - Optimal: RSI between 30 and 70

## Proposed Signal Filters

### Filter 1: Z-Score Direction (Already Implemented)
- Block LONG when z < -0.5 (chasing downtrend)
- Block SHORT when z > 0.5 (chasing uptrend)
- **Status:** Implemented in tl_break.py and accel_300.py

### Filter 2: Speed Threshold
- Block all signals when speed < 50%
- Only trade when momentum is strong
- **Status:** Not implemented

### Filter 3: Momentum Threshold
- Block all signals when momentum < 25
- Only trade when trend is strong
- **Status:** Not implemented

### Filter 4: RSI Extremes
- Block LONG when RSI > 70 (overbought)
- Block SHORT when RSI < 30 (oversold)
- **Status:** Not implemented

## Implementation

### File: `decider_run.py`

Add to context gate (rule-based section):

```python
# Speed filter: only trade when momentum is strong
if speed is not None and speed < 50:
    return ('SKIP', f'speed {speed:.0f}% < 50% (weak momentum)')

# Momentum filter: only trade when trend is strong
if momentum < 25:
    return ('SKIP', f'momentum {momentum:.0f} < 25 (weak trend)')

# RSI filter: don't trade overbought/oversold
rsi = sig.get('rsi_14') if isinstance(sig, dict) else None
if rsi is not None:
    if direction == 'LONG' and rsi > 70:
        return ('SKIP', f'RSI {rsi:.1f} > 70 (overbought)')
    if direction == 'SHORT' and rsi < 30:
        return ('SKIP', f'RSI {rsi:.1f} < 30 (oversold)')
```

## Expected Impact

| Metric | Current | Expected | Change |
|--------|---------|----------|--------|
| Win Rate | 37% | 45-50% | +8-13% |
| Trades/Day | 89 | 60-70 | -20-30% |
| PnL/Day | +$0.31 | +$0.50+ | +60% |
| Loss Rate | 63% | 50-55% | -8-13% |

## Risk Assessment

### Low Risk
- Filters are additive (don't change existing logic)
- Only block trades, never add new ones
- Based on statistical analysis of real trades

### Monitoring Required
- Track if filters reduce trade count too much
- Monitor if filters catch winning trades
- Verify WR improvement over 7-day window

## Implementation Steps

1. **Add speed filter to context gate**
   - Block signals when speed < 50%
   - Expected to block ~20% of losing trades

2. **Add momentum filter to context gate**
   - Block signals when momentum < 25
   - Expected to block ~15% of losing trades

3. **Add RSI filter to context gate**
   - Block LONG when RSI > 70
   - Block SHORT when RSI < 30
   - Expected to block ~10% of losing trades

4. **Verify compilation**
   - Run `python3 -c "import py_compile; py_compile.compile('decider_run.py')"`

5. **Monitor performance**
   - Track WR for next 24 hours
   - Compare with baseline (37% WR)
   - Look for improvement in trade quality

## Success Criteria

- WR improves from 37% to 45%+ within 7 days
- PnL improves from +$0.31 to +$0.50+ per day
- Trade count doesn't drop below 50 per day
- No increase in average loss per trade

## Rollback Plan

If performance degrades:
1. Remove speed filter
2. Remove momentum filter
3. Remove RSI filter
4. Monitor for 24 hours to confirm rollback effective

---

## Last Updated

2026-07-31: Initial plan creation
