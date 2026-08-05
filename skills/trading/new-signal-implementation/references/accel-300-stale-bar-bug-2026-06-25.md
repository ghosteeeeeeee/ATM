# accel-300 Stale-Bar Signal Bug — 2026-06-25

**Status:** BUG CONFIRMED, NOT YET FIXED. Plan at
`/root/.hermes/brain/plans/tpsl-profit-capture-2026-06-25.md` (Section
"Bug Analysis" — find "stale-bar" for the full writeup).

## The Bug

`/root/.hermes/scripts/signals/accel_300.py` `detect_accel_300()`
scans BACKWARD through price history to find the most recent bar where
price was below EMA300, then fires a SHORT signal with that OLD bar's
gap/direction. The 2026-06-23 "FIX" comment claims this returns the
most recent qualifying bar — but the loop also needs a check that the
CURRENT bar (`i = len(closes) - 1`) also satisfies the direction
condition.

Result: 8 of 12 losing accel-300- SHORT trades in the 24h audit
fired when the live price was ABOVE EMA300 by 0.4% to 2.1%. The
signal was based on a bar 32 min to 5 hours old where price HAD
been below EMA300.

## Trace Example (UMA #12196)

- Trade opened 2026-06-24 23:31:06 with `accel-300-` SHORT signal
- Live price at open: 0.389810
- Live EMA300: 0.388221
- Live gap: **+0.409% (ABOVE EMA300)**
- Signal bar found by detector: 296 bars before latest
  (4.9 hours earlier, at 19:51:20)
- At signal bar: price 0.380880, EMA 0.381548, gap **-0.175% (BELOW)**
- `ACCEL_300_STALE_LOOKBACK = 400` bars — 296 < 400, so the signal
  passes the stale check

## Verification Script

`/root/.hermes/scripts/analysis/simulate_accel_300_signal.py` reproduces
the detector logic in standalone form and identifies the stale-bar
that fired each signal. Run it to see all 8 trades that have this
pattern.

`/root/.hermes/scripts/analysis/check_signal_direction.py` checks
whether the live price at open time was above or below EMA300 for
each trade.

## Fix (not yet applied — needs T approval per "ATR TP/SL not to be changed" rule)

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
from 400 to 10 (or 5). 400 bars = 6.6 hours of 1m data — way too
old. A 5-10 minute window is the correct max for "live signal".

## Lesson: When the Detector Scans Backward, Verify Current Bar Matches

Any signal that scans backward to find a "qualifying" bar (cross,
breakout, gap expansion) must verify the LIVE/CURRENT bar is
still in the qualifying state. Otherwise the signal uses stale
data and fires in the wrong direction.

Same bug class likely exists in:
- `momentum_cache` reversal detection
- Any signal with `for i in range(N, ..., -1)` reverse scan
- Pattern-recognition signals that look for "the last time X happened"

## Detection Recipe for Future Sessions

When T reports "the signal is wrong direction" or "this trade shouldn't
have fired":

1. Pull the trade's `open_time` from PostgreSQL trades table
2. Query `price_history` table for the token at that time
3. Compute EMA300 standalone (period=300, multiplier=2/(301))
4. Check the LAST bar before `open_time`: was it above or below EMA?
5. If signal direction doesn't match the bar's position, the signal
   is wrong (either detector bug or stale-bar bug)
6. Run `/root/.hermes/scripts/analysis/check_signal_direction.py`
   across the last 24h of trades to find all instances

## Related Files

- Live signal: `/root/.hermes/scripts/signals/accel_300.py`
  (NOT `accel_300_signals.py` — that's a different/older file)
- Constants: `/root/.hermes/scripts/hermes_constants.py`
  - `ACCEL_300_PERIOD = 300`
  - `ACCEL_300_LOOKBACK = 30` (LONG)
  - `ACCEL_300_LOOKBACK_SHORT = 500` (SHORT — different!)
  - `ACCEL_300_PERSISTENCE_BARS = 2`
  - `ACCEL_300_STALE_LOOKBACK = 400` (TOO LENIENT)
  - `ACCEL_300_STALE_BARS = 60`, `ACCEL_300_STALE_BARS_SHORT = 55`
- Plan: `/root/.hermes/brain/plans/tpsl-profit-capture-2026-06-25.md`
- Old audit reference (2026-06-23): `references/accel-300-stale-bar-fix-2026-06-23.md`
  in `/root/.hermes/skills/hermes-signal-debugging/`
