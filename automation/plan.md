# Plan: VEL 15m Velocity Gate for Mean-Reversion Signals

## Problem

Mean-reversion signals (bb_bounce, range_finder) fire at band edges when price is "oversold" or "overbought", but sometimes price keeps trending through the band instead of reversing. Result: entry goes opposite direction from start. Example: BCH LONG at $216.68 while in a 4-hour downtrend ($218.32→$216.62).

## Solution

Add a 15m velocity gate: block signal if price is moving >0.3% against the trade direction over the last 15 minutes. Catches the "still falling" problem directly.

## Backtest Results (140 historical mean-reversion signals)

| Filter | Trades Kept | WR% | PnL | Net Improvement |
|--------|------------|-----|-----|----------------|
| BASELINE | 140 | 55.0% | $+0.10 | — |
| VEL 15m (-0.3%) | 127 | 59.1% | $+1.11 | +9 net trades |
| VEL+MTF | 84 | 63.1% | $+1.50 | +8 net trades |
| VEL+MTF+1H | 79 | 64.6% | $+1.61 | +9 net trades |

CEO recommendation: VEL alone — conservative, preserves signal flow, mean-reversion fit is high.

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add `MEAN_REVERSION_VEL_ENABLED`, `MEAN_REVERSION_VEL_THRESHOLD` |
| `scripts/signals/bb_bounce.py` | Add velocity check before `add_signal()` |
| `scripts/signals/range_finder.py` | Add velocity check before `add_signal()` |
| `scripts/signals/range_finder_short.py` | Add velocity check before `add_signal()` |

## Constants

```python
MEAN_REVERSION_VEL_ENABLED = True
MEAN_REVERSION_VEL_THRESHOLD = 0.3   # block if 15m velocity > 0.3% against direction
```

## Velocity Check Pattern

```python
if MEAN_REVERSION_VEL_ENABLED:
    vel = _get_15m_velocity(token)
    if vel is not None:
        if direction == 'LONG' and vel < -MEAN_REVERSION_VEL_THRESHOLD:
            continue
        if direction == 'SHORT' and vel > MEAN_REVERSION_VEL_THRESHOLD:
            continue
```

## `_get_15m_velocity()` Implementation

- Query `price_history` for last 15 closes (15 minutes of 1m data)
- Calculate `(last - first) / first * 100`
- Return float (positive = upward, negative = downward)
- Return `None` on error (fail-open — don't block trades on data issues)

## Tracking

- Store `velocity_15m` in `signal_metadata` JSON via `add_signal()` for post-hoc analysis
- Log filtered signals to `automation/velocity_filter_log.json`
- Compare 24h/48h/7d stats for bb_bounce+ and range_finder+ source combos

## Rollback

Set `MEAN_REVERSION_VEL_ENABLED = False` in hermes_constants.py. Instant. No code deploy.

## Safety

- Negative gate only — doesn't change entry logic, just blocks bad entries
- Fail-open on data errors — no trades blocked on missing data
- Kill switch in constants — instant rollback without code changes
