# Python Chained Comparison with Negative Thresholds

## The Bug

Python's chained comparison `a <= b <= c` is equivalent to `(a <= b) and (b <= c)`. This behaves counter-intuitively when the limits have opposite signs or when the range is "negative" (e.g., loss thresholds where both min and max are negative).

## Concrete Example from cut_loser.py

```python
LOSS_MIN_PCT = -3.0  # more negative = worse loss
LOSS_MAX_PCT = -0.5  # less negative = cut if worse than this

# WRONG — always returns False for any loss in (-0.5, 0) range
if min_pct <= live_pnl <= max_pct:
    filtered.append(pos)

# Example: live_pnl = -0.35 (loss of 0.35%)
#   -3.0 <= -0.35  → True
#   -0.35 <= -0.5  → False  (because -0.35 > -0.5 on number line)
#   Result: False  ← WRONG — should be True
```

## The Fix

Use explicit `and` with separate comparisons:

```python
# CORRECT
if (live_pnl <= max_pct) and (live_pnl >= min_pct):
    filtered.append(pos)
```

Or for profit-like ranges (both positive), the chained comparison works fine:

```python
PROFIT_MIN_PCT = 0.5
PROFIT_MAX_PCT = 2.0
# For profit: live_pnl = 1.0%
#   0.5 <= 1.0  → True
#   1.0 <= 2.0  → True
#   Result: True  ← correct
```

## When to Use Which

| Range type | Example values | Use chained comparison? |
|---|---|---|
| Positive range (profit) | 0.5 to 2.0 | ✅ Yes — `min <= x <= max` works |
| Negative range (loss) | -3.0 to -0.5 | ❌ No — use `(x <= max) and (x >= min)` |
| Zero-crossing range | -1.0 to 1.0 | ✅ Yes — works because 1.0 > -1.0 |
| Mixed signs | -0.5 to 5.0 | ❌ No — test explicitly |

## Python Disection

```python
# Python semantics:
a <= b <= c  ==  (a <= b) and (b <= c)

# Not mathematical interval notation.
# The middle value is compared TWICE — once to each bound.
# When bounds have different signs or inverted relationships,
# the semantics diverge from the intended interval check.
```

## Pattern to Search For

```
min_pct.*<=.*<=.*max_pct
LOSS.*<=.*<=.*
threshold.*<=.*<=.*
```