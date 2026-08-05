# Float-Tolerance Gates for Difference and Second-Difference Checks

Pattern: when a detector checks "is this value strictly greater than
zero?" (or strictly less than) on a quantity that comes from a
**difference** of floats, equal-looking inputs can produce signed
noise that fails the gate in the wrong direction.

## Concrete failure (accel-300, 2026-07-19)

```python
# WRONG — equal raw price moves subtract to signed float noise.
# `price_velocity = closes[-1] - closes[-2] - 0.6 - 0.6` can be
# `-1.4e-14` (signed zero), not `+0.0`. The SHORT velocity gate
# `velocity <= 0` therefore passes, and the detector concludes
# "accelerating downward" when the actual price is constant-speed
# downward.
price_velocity = closes[latest_idx] - closes[latest_idx - 1]
prior_price_velocity = closes[latest_idx - 1] - closes[latest_idx - 2]
price_acceleration = price_velocity - prior_price_velocity
if direction == 'LONG':
    if price_velocity <= 0 or price_acceleration <= 0:
        return None
else:
    if price_velocity >= 0 or price_acceleration >= 0:
        return None
```

The trap: when two consecutive prices are equal, the difference is
`-1.4e-14` (signed zero, not +0.0). Any gate using `<= 0` / `>= 0`
will misclassify.

## Fix: scale tolerance to the local magnitude

```python
price_epsilon = max(abs(closes[latest_idx]) * 1e-12, 1e-12)
if direction == 'LONG':
    if price_velocity <= price_epsilon or price_acceleration <= price_epsilon:
        return None
else:
    if price_velocity >= -price_epsilon or price_acceleration >= -price_epsilon:
        return None
```

The `1e-12` is small enough to never swallow real market movement
(at a price of $1, that's $1e-12 movement; at $100, $1e-10). The
`abs(price) * 1e-12` floor keeps the tolerance tight for small-cap
tokens (sub-$0.01 prices are common) but allows more headroom on
high-priced ones.

## When to use this pattern

Any time your detector emits or blocks based on:

- Bar-over-bar velocity (Δ price, Δ gap, Δ EMA distance)
- Second difference / acceleration
- A "is X strictly greater than threshold" gate where X is a
  difference of two floats

If you can write a unit test where you put two identical numbers
into the gate and it should NOT fire, you need this tolerance.

## Verification

Write a RED test that constructs the failure case directly:

```python
def test_blocks_short_when_price_speed_is_flat_even_if_ema_gap_accelerates():
    closes = [100.0] * 12 + [99.8, 99.0, 97.8, 97.2, 96.6]
    # Two equal -0.6 raw drops in a row, EMA catching up
    signal = accel_300.detect_accel_300("TEST", make_prices(closes))
    assert signal is None
```

This test will fail on a naive `<= 0` gate and pass once the
epsilon-scaled gate is in place.

## Related

- Parent skill: `latest-bar-signal-contracts` — class-level design
  and four-pass verification flow.
- Sibling reference: `references/accel-300-rewrite-2026-07-19.md`
  — the accel-300 case study that produced this pitfall.
