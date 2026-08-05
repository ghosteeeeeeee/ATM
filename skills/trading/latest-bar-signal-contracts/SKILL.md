---
name: latest-bar-signal-contracts
description: "Design and verify 'latest-bar' momentum / acceleration signals in Hermes. Covers the three-layer contract (direction + velocity + acceleration at the latest price_history point), the 1m data source rule, float-tolerance gates, and a four-pass verification pattern (synthetic RED tests, historical-trade replay, fresh-token live scan, random-sequence fuzz). Use when building or rewriting any signal that claims to confirm acceleration, momentum, or persistence using EMA, gap, or slope thresholds."
---

# Latest-Bar Signal Contracts

A class-level skill for any Hermes signal that emits a "momentum is
strong right now" assertion (accel-300, macd_accel, phase_accel,
hh_hl confirmation, any signal currently called a "momentum
confirmation" in `hermes_constants.py`).

The legacy approach (scan history for a qualifying bar, then trust
that bar's state) is wrong for these signals. The right contract
evaluates the **latest** `price_history` point with three layers
that all must hold simultaneously.

## The Three-Layer Contract

For a LONG signal at time `t`:

1. **Direction** — `price[t] > ema[t]` (or the relevant reference).
2. **Velocity** — `price[t] - price[t-1] > 0` AND
   `(price[t] - ema[t]) - (price[t-1] - ema[t-1]) > 0`.
3. **Acceleration** — `velocity[t] > velocity[t-1]` AND
   `(velocity[t] - velocity[t-1]) > 0`.

For SHORT, mirror all three with reversed signs.

All three must be true at the literal `t = latest` point in
`price_history`. Never trust a historical bar's state.

## Why a Historical Bar Is Never Enough

Even with a "current-bar consistency check" (the 2026-06-25
partial fix), a backward-scanning detector can still emit:

- **Decel-in-disguise**: latest bar's growth smaller than the prior
  bar's. Velocity > 0, but acceleration ≤ 0. The signal name
  contains "accel" but the emission isn't accelerating.
- **EMA catch-up artifact**: equal raw price moves downward can make
  the EMA-gap second difference *more negative* as EMA300 catches
  up to the new price. A detector that only checks EMA-gap
  acceleration concludes "accelerating downward" when the actual
  price is constant-speed downward.
- **Forward-looking window**: a regime-slope check that reads
  `closes[i:i + SLOPE_WINDOW]` looks into the future from a
  candidate bar. When the candidate is the latest bar it reads the
  *developing* window, which is meaningless as a "trending" check.

The fix is structural: stop scanning, evaluate only the latest bar,
use trailing windows for context. Diagnostic fields (`bars_since_cross`,
`cross_bar`) can still scan backward but must not gate the signal.

## Data Source Rule

The 1-minute source of truth for live signals is
`signals_hermes.db.price_history`. T confirmed explicitly
(2026-07-19): use `price_history` for 1m data, candles are not up
to date. `candles.db` aggregations can lag the live collector
because of lock contention between `price_collector.py` and
`_aggregate_1m.py`, plus timer drift on `hermes-5m-candle.timer`.
See the `verify-prices` skill, Known Root Causes for details. The
freshness guard in `_get_1m_prices` (5-minute staleness) is the
contract. **Never** read 1m signal inputs from `candles.db`.

## Float-Tolerance Gates

Two equal-looking floats subtract to signed noise (about `-1e-14`),
not `+0.0`. A gate like `velocity <= 0` will misclassify equal
inputs as negative velocity and fire on numerical noise. Scale
tolerance to the local price magnitude:

```python
price_epsilon = max(abs(price) * 1e-12, 1e-12)
# LONG:  velocity >  price_epsilon AND acceleration >  price_epsilon
# SHORT: velocity < -price_epsilon AND acceleration < -price_epsilon
```

The `1e-12` is small enough to never swallow real market movement
and large enough to absorb float subtraction noise. RED-test this
explicitly: construct a sequence with two equal bar-over-bar moves
and assert the signal does NOT fire.

## The Four-Pass Verification Pattern

Run all four passes in order. Each catches a class the previous
pass would miss.

1. **RED-then-GREEN unit tests on synthetic series** at
   `scripts/tests/test_<signal>.py`. At minimum:
   - blocks when latest price has reversed through reference
   - blocks when EMA-gap velocity is positive but raw price velocity
     is flat or opposite
   - blocks when velocity is positive but acceleration is zero
   - returns when both raw and EMA-gap velocity AND acceleration
     strengthen
   - returns the correct direction with `sig['price']` equal to
     the literal last input
2. **Replay every historical trade from PostgreSQL** against the
   new detector. Tag filter: `signal LIKE '<name>%'`. For each
   trade, fetch 700 1m points from `price_history` ending at
   `open_time`, run detection, compare to the trade's direction.
   Any disagreement is a known correctness regression.
3. **Live scan over all fresh `price_history` tokens** (last 5 min).
   For every emission verify:
   - `sig['price']` equals the literal last `price_history` point
   - `sig['direction']` matches `(closes[-1] > ema[-1])`
   - raw price velocity AND acceleration both agree with direction
4. **Random-sequence fuzz**: 100,000+ random 19-point walks. Assert
   the directional contract (raw price velocity AND acceleration
   in the signal direction) is never violated. EMA catch-up
   artifacts are rare on real history but common in random walks;
   this pass fails fast on a detector that lacks a raw-price gate.

For accel-300 specifically, post-2026-07-19 rewrite: 7/7 unit
tests pass, 41/41 historical trades replay (40 now blocked, 1
re-emitted with matching direction), 83/83 fresh-token scan
(0 wrong-side, 0 stale-price), 100k random fuzz
(15,196 emissions, 0 contract violations).

## Signals in Scope (verify each against this contract)

Anything in the `Momentum Killswitches` section of
`hermes_constants.py` and any signal currently in
`/root/.hermes/scripts/signals/`. For each, ask:

- Does it use `price_history` (1m) or `candles.db`? Must be
  `price_history`.
- Does it emit based on a historical bar's state, or the latest?
  Must be the latest.
- Does it require both velocity and acceleration, or just one?
  Must require both, with float tolerance.
- Does it have a forward-looking window anywhere? Must use a
  trailing window only.

If any answer is wrong, the signal has a variant of this bug class.
The four-pass verification pattern will catch the variant.

## Reference Files

- `references/accel-300-rewrite-2026-07-19.md` — full case study
  of the accel-300 latest-bar rewrite, including the
  pre/post-fix detector code, the unit tests, and the RED to GREEN
  trace.
- `references/float-tolerance-difference-gates.md` — standalone
  pitfall for difference / second-difference gates that
  misclassify float subtraction noise as movement.
