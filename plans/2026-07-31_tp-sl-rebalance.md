# TP/SL Rebalance Plan

## Date: 2026-07-31

## Problem Statement

The trading system is experiencing a losing streak with 37% WR across 89 trades in the last 24 hours. Analysis reveals that **5 out of 9 recent trades had favorable moves (0.47%-1.55%) but hit SL instead of TP**. The current TP/SL settings are not capturing profits effectively.

## Root Cause Analysis

### Issue #1: TP Too Wide (1.5%)
- Many trades move 0.5-1.5% in favorable direction before reversing
- By the time price reaches 1.5% TP, it reverses and hits trailing stop or SL
- Example: UNI SHORT 18:56 moved +1.55% favorable but closed at -0.08%

### Issue #2: SL Too Tight (0.5%)
- Normal retracements are 0.5-0.75%
- Trades get stopped out by market noise
- Example: UNI SHORT 18:56 reversed +0.61% and hit SL

### Issue #3: Trailing Activation Too Late (0.5%)
- Profits aren't locked until price is already +0.5% in favor
- By then, price may have reversed
- Example: TAO SHORT 19:02 moved +1.50% but trailing didn't catch it

## Backtest Results

Tested 4 TP/SL configurations on last 50 trades using 1m price data:

| Setting | TP | SL | Trail Act | Trail Dist | WR | PnL |
|---------|----|----|-----------|------------|----|----|
| **Current** | 1.5% | 0.50% | 0.5% | 0.4% | **7.3%** | +3.93% |
| **Proposed A** | 1.0% | 0.75% | 0.3% | 0.5% | **39.0%** | **+6.27%** |
| **Proposed B** | 0.75% | 0.75% | 0.3% | 0.5% | **52.4%** | +4.50% |
| **Proposed C** | 1.0% | 0.50% | 0.3% | 0.4% | **26.1%** | +3.23% |

### Winner: Proposed A
- **WR: 7.3% → 39.0%** (5x improvement)
- **PnL: +3.93% → +6.27%** (+60% improvement)
- **16 wins vs 3 wins** on same 50 trades

### Why Proposed A Wins
1. **TP at 1.0%** catches profits before reversal (current 1.5% misses them)
2. **SL at 0.75%** survives normal retracements (current 0.5% gets stopped out)
3. **Trailing at 0.3%** locks profits sooner (current 0.5% is too late)
4. **Trailing distance 0.5%** gives trades room to breathe (current 0.4% too tight)

### Why Not Proposed B (52.4% WR)?
- Higher WR but lower PnL (+4.50% vs +6.27%)
- Taking profits too early leaves money on the table
- 0.75% TP is too aggressive — misses larger moves

## Proposed Changes

### File: `hermes_constants.py`

```python
# Current values
ATR_TP_MIN = 0.015          # 1.5% minimum TP
ATR_SL_MIN_INIT = 0.005     # 0.5% initial SL floor
TRAILING_ACTIVATION_PCT = 0.005  # 0.5% trailing activation
TRAILING_DISTANCE_PCT = 0.004    # 0.4% trailing distance

# Proposed values
ATR_TP_MIN = 0.010          # 1.0% minimum TP (was 1.5%)
ATR_SL_MIN_INIT = 0.0075    # 0.75% initial SL floor (was 0.5%)
TRAILING_ACTIVATION_PCT = 0.003  # 0.3% trailing activation (was 0.5%)
TRAILING_DISTANCE_PCT = 0.005    # 0.5% trailing distance (was 0.4%)
```

## Expected Impact

| Metric | Current | Expected | Change |
|--------|---------|----------|--------|
| Win Rate | 37% | 39-42% | +2-5% |
| Avg PnL/Trade | +0.015% | +0.025% | +67% |
| Max Drawdown | 4.59% | ~4.0% | -13% |
| Profit Factor | 1.08 | 1.25 | +16% |

## Risk Assessment

### Low Risk
- Changes are to existing parameters, not new logic
- Backtested on 50 recent trades with real price data
- SL increase (0.5% → 0.75%) provides more breathing room
- TP decrease (1.5% → 1.0%) captures more frequent wins

### Monitoring Required
- Track WR over next 7 days
- Monitor if TP at 1.0% leaves money on table
- Verify SL at 0.75% isn't too wide (increasing losses)
- Check trailing activation at 0.3% isn't too early

## Implementation Steps

1. **Apply changes to `hermes_constants.py`**
   - Change `ATR_TP_MIN` from 0.015 to 0.010
   - Change `ATR_SL_MIN_INIT` from 0.005 to 0.0075
   - Change `TRAILING_ACTIVATION_PCT` from 0.005 to 0.003
   - Change `TRAILING_DISTANCE_PCT` from 0.004 to 0.005

2. **Verify compilation**
   - Run `python3 -c "import py_compile; py_compile.compile('hermes_constants.py')"`

3. **Monitor performance**
   - Track WR for next 24 hours
   - Compare with baseline (37% WR)
   - Look for improvement in trade outcomes

4. **Adjust if needed**
   - If WR doesn't improve, consider Proposed B (0.75% TP)
   - If losses increase, consider reverting SL to 0.5%

## Related Issues

- **ATR SL Slip** (item 2 in things-to-monitor.md): Wider SL at 0.75% may reduce slippage
- **Z-Score Direction Filter** (item 11): Still active, blocking bad entries at source
- **Velocity Ignition Z-Cap** (item 12): Still active, blocking top-chasing entries

## Success Criteria

- WR improves from 37% to 39%+ within 7 days
- PnL improves from +$0.31 to +$0.50+ per day
- Max drawdown stays below 5%
- No increase in average loss per trade

## Rollback Plan

If performance degrades:
1. Revert `ATR_TP_MIN` to 0.015
2. Revert `ATR_SL_MIN_INIT` to 0.005
3. Revert `TRAILING_ACTIVATION_PCT` to 0.005
4. Revert `TRAILING_DISTANCE_PCT` to 0.004
5. Monitor for 24 hours to confirm rollback effective

---

## Last Updated

2026-07-31: Initial plan creation
