# accel-300 Latest-Bar Rewrite — 2026-07-19

**Status:** Fix applied to `signals/accel_300.py`. New regression
tests live at `scripts/tests/test_accel_300.py` (7 tests, all pass).
This is a class-level reference; the parent skill
`latest-bar-signal-contracts` is the engineering flow.

## Why a rewrite, not a patch

The 2026-06-25 plan proposed an additive fix: a current-bar
direction check inside the legacy backward-scanning loop. That fix
would have closed the most visible wrong-side emissions but would
not have closed the underlying class of failure. Once the RED tests
were written, three distinct bugs fell out:

1. **Decel-in-disguise**: a "growing" gap whose latest bar of growth
   is smaller than the prior bar. Velocity positive, acceleration
   ≤ 0. The legacy `MARGINAL_ACCEL_BARS` early-entry bypass let
   this through: bars 0-2 after the cross fired with **no
   acceleration requirement at all**.
2. **EMA-catch-up artifact**: equal raw price moves downward can
   still make the EMA-gap second difference more negative, because
   EMA300 itself is moving toward the new level. A detector that
   only checks EMA-gap second difference concludes "accelerating
   downward" when the actual price is constant-speed downward.
3. **Forward-looking slope window**: the regime-slope block read
   `closes[i:i + SLOPE_WINDOW]`, which is bars **after** the
   candidate bar. When the candidate is the latest bar, this reads
   the *developing* window, which is meaningless as a "trending"
   check.

Patching fix #1 from the 2026-06-25 plan would have left #2 and #3
in place. The 2026-07-19 rewrite replaces the entire
`detect_accel_300()` body.

## Detector contract enforced (the three layers)

For a LONG signal at time `t`:

1. **Direction** — `price[t] > ema300[t]`.
2. **Velocity** — `price[t] - price[t-1] > 0` AND
   `(price[t] - ema300[t]) - (price[t-1] - ema300[t-1]) > 0`.
3. **Acceleration** — `velocity[t] > velocity[t-1]` AND
   `(velocity[t] - velocity[t-1]) > 0`.

For SHORT, mirror all three with reversed signs.

Plus, for both directions:

- Latest gap must exceed per-direction minimum (`MIN_GAP_PCT_LONG`,
  `MIN_GAP_PCT_SHORT`).
- Persistence: last `PERSISTENCE_BARS` closes must all be on the
  correct side of EMA.
- Gap growth (over the persistence window) must exceed per-direction
  minimum.
- Trailing regime slope (last `SLOPE_WINDOW` bars) must point in
  the signal direction.
- Float-tolerance epsilon: `max(|price| * 1e-12, 1e-12)`.

Cross-bar is diagnostic only; it does not gate.

## RED→GREEN trace

The 4 original RED tests:

- `test_blocks_stale_long_after_latest_price_crosses_below_ema` —
  closes [..., 100.6, 101.0, 101.5, 99.0]. Naive backward scan
  returned `{direction: 'LONG', price: 100.6}` even though
  `closes[-1] = 99.0` is below EMA. Failed.
- `test_blocks_long_when_latest_gap_is_widening_but_decelerating` —
  latest move +0.3, prior +0.8. Naive returned LONG because the
  legacy early-entry bypass skipped the acceleration check entirely.
  Failed.
- `test_returns_long_from_latest_bar_when_upward_acceleration_strengthens`
  — naive returned `price: 100.5` instead of the latest `103.0`.
  Failed.
- `test_returns_short_from_latest_bar_when_downward_acceleration_strengthens`
  — naive returned `price: 98.2` instead of the latest `97.0`.
  Failed.

After the rewrite: 4/4 pass. Then 3 more tests added (decelerating
SHORT, stale SHORT, flat-price-but-EMA-gap-accelerates SHORT).
After float-epsilon fix on the raw-price gate: 7/7 pass.

## Live-data verification

- **41 historical accel-300 trades in PostgreSQL** (7d window).
  Replay: 40 now correctly blocked. 1 re-emitted (GALA #12504)
  with matching direction and positive price acceleration. Zero
  wrong-side emissions.
- **83 fresh `price_history` tokens right now**. 0 wrong-side, 0
  stale-price emissions. (The market is just not currently
  accelerating; the detector isn't dead, it's correctly quiet.)
- **100,000 random 19-point walks**: 15,196 emissions, 0 contract
  violations. Catches the EMA-catch-up artifact that historical
  data alone doesn't surface.

## Scanner-side cleanups (not signal logic, but related)

- `scan_accel_300_signals` now persists `sig['price']` (the latest
  `price_history` point) rather than the separate `prices_dict`
  snapshot, which can be from a different collector tick.
- The undirected `SHORT_BLACKLIST` check that was applied BEFORE
  direction determination has been removed. The downstream
  direction-aware check (already correct) handles it.
- Confidence formula uses `abs(gap_growth)` so SHORT can earn the
  growth-strength bonus symmetrically. (Old formula:
  `gap_growth - 0.05`, which is always negative for SHORT, so
  the bonus was always 0.)
- The detector's `_log()` was restored (had been pruned by a
  previous edit but was still referenced by `scan_accel_300_signals`).

## Constants now unused (cleanup TBD)

After the rewrite, these are dead weight in `hermes_constants.py`:

- `ACCEL_300_STALE_LOOKBACK = 400`
- `ACCEL_300_STALE_GAP_DECAY_THRESHOLD = 0.50`
- `ACCEL_300_STALE_BARS` and `ACCEL_300_STALE_BARS_SHORT`
- `ACCEL_300_MARGINAL_ACCEL_BARS`
- `ACCEL_300_LOOKBACK_1M` (still used for fetch window, fine)
- `ACCEL_300_CROSS_LOOKBACK` (used in the diagnostic cross-bar
  search, but no longer gates)

Leave them in place for this commit. T-approved cleanup is a
separate change.

## Reference relationships

- Parent skill: `latest-bar-signal-contracts` — the class-level
  design + verification flow.
- Sibling reference: `references/float-tolerance-difference-gates.md`
  — the standalone pitfall for `<= 0` / `>= 0` gates on float
  differences.
- Sibling skill: `hermes-signal-debugging` (read-only, manually
  authored) has the 2026-06-23 and 2026-06-25 threads on the same
  bug. The 2026-07-19 rewrite supersedes those threads' proposed
  fixes; the parent skill there is not currently writable, so
  this rewrite is documented in the new umbrella instead.
