# accel-300 Stale-Bar Signal Bug — 2026-06-25 (extends 2026-06-23 fix)

**Status:** ROOT CAUSE IDENTIFIED, NOT YET FIXED. See
`/root/.hermes/brain/plans/tpsl-profit-capture-2026-06-25.md` and
`/root/.hermes/scripts/analysis/simulate_accel_300_signal.py` for
the full picture.

## TL;DR

The 2026-06-23 "FIX" in `signals/accel_300.py` claims to scan
backward to find the most recent qualifying bar, but the fix
introduced a NEW bug: the signal uses the OLD bar's gap/direction
without verifying the CURRENT bar also qualifies. Result: SHORT
signals fire when live price is ABOVE EMA300 by 0.4% to 2.1%.

**8 of 12 losing accel-300- SHORT trades in the 24h audit had
this bug.** UMA #12196 is the canonical case — 4.9-hour-old
signal bar, 296 bars stale.

## The bug in plain terms

The detector loop at `signals/accel_300.py:273`:
```python
for i in range(len(closes) - 2, PERIOD + LOOKBACK - 1, -1):
    price = closes[i]
    ema_val = ema300[i]
    # ...
    direction = 'LONG' if current_above else 'SHORT'
```

Iterates backward, finds bar `i` where price was below EMA
(SHORT candidate), reports `direction='SHORT'`. The signal is
returned based on this OLD bar's gap.

**What's missing:** After finding this old below-EMA bar, the
detector does NOT verify that the LATEST bar (live data) also
has price below EMA. If the live price has crossed back above
EMA, the SHORT signal is using stale data.

## Trace (UMA #12196)

- Live bar (idx=799): price=0.389810, EMA=0.388221, gap=+0.41% (ABOVE)
- Most recent below-EMA bar (idx=503): price=0.380880, gap=-0.18%
- 296 bars between them (4.9 hours)
- `ACCEL_300_STALE_LOOKBACK=400` — 296 < 400, passes the stale check
- Signal fires as SHORT with gap=-0.18% from old bar's data
- But live gap is +0.41% — signal direction WRONG

## Why the 2026-06-23 fix didn't work

The comment claims:
> "Now: find ALL qualifying bars scanning forward, track the
> most recent one. Return the most recent (last) qualifying bar
> found."

The code actually:
- Scans BACKWARD
- Returns the FIRST bar that matches all conditions
- That first match is the MOST RECENT match, but it's a HISTORICAL bar
- Does not check that the latest bar also matches

The "fix" missed the fundamental requirement: the signal's
direction must match the CURRENT bar's position relative to EMA,
not just the historical qualifying bar's.

## The fix (not yet applied — needs T approval)

In `/root/.hermes/scripts/signals/accel_300.py`, BEFORE the
persistence check (around line 240), add:
```python
# STALE-BAR FIX: signal direction must match the CURRENT bar's
# position vs EMA. The detector finds a "qualifying" bar in the
# past, but if the live price has since crossed back, the
# signal is stale even if bars_from_latest < STALE_LOOKBACK.
last_idx = len(closes) - 1
if direction == 'SHORT' and closes[last_idx] >= ema300[last_idx]:
    continue  # current bar is above EMA — SHORT from old below-EMA bar is stale
if direction == 'LONG' and closes[last_idx] <= ema300[last_idx]:
    continue  # current bar is below EMA — LONG from old above-EMA bar is stale
```

Also tighten `ACCEL_300_STALE_LOOKBACK` in `hermes_constants.py`
from 400 to 10. 400 bars = 6.6 hours of 1m data — way too old
for a "live signal". A 5-10 minute window is correct.

## Bug class: "Backward-scan detector without current-bar verification"

Any signal that scans backward to find a "qualifying" event
(cross, breakout, gap expansion) must verify the LIVE/CURRENT
bar is still in the qualifying state. Otherwise the signal uses
stale data and fires in the wrong direction.

Other candidates for this bug class:
- `momentum_cache` reversal detection
- Pattern-recognition signals that look for "the last time X happened"
- Any signal with `for i in range(N, ..., -1)` reverse scan

## How to detect this bug class in future sessions

When T reports "the signal is wrong direction" or "this trade
shouldn't have fired":

1. Pull `open_time` from PostgreSQL trades table
2. Query `price_history` for the token at that time
3. Compute EMA300 standalone (period=300, multiplier=2/(301))
4. Check the LAST bar before `open_time`: was it above or below EMA?
5. If signal direction doesn't match the bar's position,
   the signal is wrong (detector bug or stale-bar bug)
6. Use `/root/.hermes/scripts/analysis/check_signal_direction.py`
   to find all instances across recent trades

## Verification scripts

- `/root/.hermes/scripts/analysis/check_signal_direction.py` —
  checks live price vs EMA at open time for each trade
- `/root/.hermes/scripts/analysis/simulate_accel_300_signal.py` —
  full detector simulation that finds the signal bar and shows
  if it's stale

## File locations (CRITICAL)

There are TWO accel_300 implementations:

| File | Used by live system? |
|------|---------------------|
| `/root/.hermes/scripts/accel_300_signals.py` | NO — orphan file (older code) |
| `/root/.hermes/scripts/signals/accel_300.py` | YES — this is what fires signals |

When fixing or auditing, **always read `signals/accel_300.py`**,
not `accel_300_signals.py`. The latter is a relic that looks
similar but is NOT called by the live signal_compactor pipeline.

## Related references in this skill

- `references/forward-scan-stale-bar-2026-06-23.md` — original
  2026-06-23 fix attempt (partial — didn't add current-bar check)
- `references/accel-300-sustained-moves-jun-2026.md` — earlier
  work on the same signal
- `references/accel-300-gap-calibration-jun-2026.md` — gap
  threshold tuning

## Constants that contributed to the bug

- `ACCEL_300_STALE_LOOKBACK = 400` — too lenient
- `ACCEL_300_LOOKBACK_SHORT = 500` — too lenient for SHORT
- `ACCEL_300_PERSISTENCE_BARS = 2` — only checks 2 most recent
  bars for persistence, not the full range

If the persistence check looked at MORE bars (e.g., the full
LOOKBACK range), the staleness would be detected at that layer.
But that's a much larger change than the simple "verify current
bar" fix.
