# accel-300: 2026-06-23 Backward-Scan Fix Was Incomplete (2026-06-25)

## Symptom (User-Reported, Recurring)

> "I'm sure the accel_300 is firing incorrectly (short when price is over
> the EMA300, and long when price is below ema 300, both incorrect
> behaviours)"

User observed this AFTER the 2026-06-23 fix was deployed. So the previous
fix did NOT fully resolve the directional-inversion bug. See
`references/accel-300-stale-bar-break-bug-2026-06-23.md` for the
original finding.

## Why the 2026-06-23 Fix Was Not Enough

The previous fix changed the scan direction from forward-to-backward
(`for i in range(PERIOD + LOOKBACK, len(closes) - 1)`) to
backward-to-forward (`for i in range(len(closes) - 2, ...)`).
That made the FIRST match the most recent qualifying bar.

But the fix did NOT add: a check that the LATEST bar also qualifies.

**Scenario (how the bug survives the previous fix):**

1. Price crosses ABOVE EMA at bar 400 (e.g., 4 hours ago)
2. Price stays ABOVE EMA from bar 400 to bar 410, then drops
3. Price recovers ABOVE EMA from bar 415 onward — for the next
   5 hours (bars 415-699) — all above EMA
4. Price drops briefly below EMA at bar 700 (current bar)
5. Wait — most recent cross BACK below EMA happened *within last 5
   bars* (a tiny recent dip). So the detector finds bar 700 qualifies
   for SHORT.
6. But bar 700 is a temporary 0.2% dip in a 5-hour uptrend. By the
   time the trade opens (1-2 min later), price is back ABOVE EMA.
   Trade is squeezed.

This is what happened on 27 of 121 accel_300 trades (22%) between
2026-06-25 and 2026-07-05.

## Measured Impact (2026-07-05)

Checked 121 accel-300 trades from 7-day window:

```
WRONG DIRECTION (price on wrong side of EMA at signal time): 27/121 (22%)
```

Both directions affected:
- 22 are accel-300- SHORTs firing when price was ABOVE EMA
- 5 are accel-300+ LONGs firing when price was BELOW EMA

Bars stale (signal bar age relative to LIVE bar at signal time):
- Range: 1 to 265 bars (5 sec to 4.4 hours)
- Most common: 50-200 bars (45 min to 3.3 hours)

The `ACCEL_300_STALE_LOOKBACK = 400` value (≈6.6 hours) is the
**primary culprit** — too lenient. Even the
`ACCEL_300_STALE_GAP_DECAY_THRESHOLD = 0.50` check didn't catch
most cases because the gap often doesn't decay much.

## Verification Reproduction

Script: `/root/.hermes/scripts/analysis/check_all_accel_direction.py`
Replays the detector's EMA calc on the same 700-bar window the
live system uses. Compares the LIVE bar's direction vs. the
recorded signal direction. 22% mismatch.

## The Complete Fix (Two Parts)

### Part 1 — Code patch in `signals/accel_300.py`

Before the `signal_bar = {...}` block (line 617), add:

```python
# ── LIVE-BAR DIRECTION CHECK (2026-07-05 fix) ───────────────
# The 2026-06-23 fix finds the most recent qualifying bar going
# backward. But the LATEST bar may have reversed through EMA by
# the time the signal is reported — making the signal direction
# wrong for the current price action. Verify the current bar's
# direction matches the signal bar's.
last_idx = len(closes) - 1
if last_idx > i and ema300[last_idx] is not None:
    last_price = closes[last_idx]
    last_above = last_price > ema300[last_idx]
    last_below = last_price < ema300[last_idx]
    if direction == 'SHORT' and not last_below:
        continue  # signal direction SHORT but latest bar is above EMA — stale
    if direction == 'LONG' and not last_above:
        continue  # signal direction LONG but latest bar is below EMA — stale
```

### Part 2 — Tighten two stale constants in `hermes_constants.py`

```python
ACCEL_300_STALE_LOOKBACK = 10  # was 400 — was 6.6 hours, way too lenient
ACCEL_300_STALE_GAP_DECAY_THRESHOLD = 0.80  # was 0.50 — only allow 20% decay
```

## Why the 2026-06-23 Fix Surfaces a New "Direction == Live" Check

The 2026-06-23 fix's "scan backward, return first match" assumes
that signal direction = signal bar's direction = live bar's direction.
That assumption only holds when bars don't oscillate around EMA
across the LIVE bar's window. When live bar oscillates (price
just crossed EMA back recently), the assumption breaks.

The new check makes the assumption explicit and verifiable.

## The "value" Field Stores gap_growth, NOT gap_pct (Trap)

This caused a 30-minute debug false-start in the 2026-06-25 session.

In `signals/accel_300.py` line 734:
```python
value=float(sig['gap_growth']),  # not sig['gap_pct']!
```

So `signals.value = -0.30` looks like "gap_pct is -0.30%". It isn't.
The `gap_growth` is the delta of `gap_pcts[i] - gap_pcts[i - PERSISTENCE_BARS]`.
Always cross-check by computing `gap_pct` from `price` directly:
```python
ema = price_history.ema(closes_at_signal_time)
gap_pct = (price - ema) / ema * 100
```

## Related

- `references/accel-300-stale-bar-break-bug-2026-06-23.md` — the
  partial-fix-before-2026-06-23. This NEW reference completes that
  fix.
- `references/signal-code-audit-methodology.md` step 7 — "trace
  live signals against bar-level state." Required to catch this bug.
  Static code review cannot find it: every gate is wired correctly,
  the bug is in the live vs. stale bar direction mismatch.
- `references/accel-300-root-cause-jun-2026.md` — earlier mean-reversion
  trap finding (separate bug, same script).
- Detection docstring at lines 213-223: STILL says "5 conditions" but
  the code has 10. Stale docstring contributes to this kind of bug
  being missed in review. When fixing the detector, also update the
  docstring to list ALL gates including the new live-bar check.
