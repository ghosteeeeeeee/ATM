# accel_300 Fails on Clean Cross / Sustained Grind (2026-06-14)

## Symptom
UMA drove +3.74% over 5 hours with a clean one-bar EMA cross and no pullback.
accel_300 never fired — price was above EMA300 from bar ~170 (19:26 UTC) and never
crossed back. Gap grew from +0.02% to +3.13%.

## Root Cause: LOOKBACK Conflicts with STALE_BARS

The `was_below` check (ACCEL_300_LOOKBACK=30) requires price to have been below EMA
within 30 bars of the signal bar. On a clean sustained grind, price crosses once and
stays above for hundreds of bars.

UMA at bar 340 (20:54): gap=+0.64%, but `was_below=False` because the cross was
at bar ~170 (280 bars ago). Every bar fails the G2 check.

STALE_BARS=60 tries to catch this ("signal is too old") but it's a LATE filter —
by the time the stale gate fires, the G2 check has already blocked the signal.

## The Conflict

```
LOOKBACK=30  → "was_below within 30 bars"    ← BLOCKS sustained grinds
STALE_BARS=60 → "signal fires max 60 bars after cross" ← irrelevant after G2 blocks
```

The two parameters work against each other for this pattern:
- LOOKBACK tight → catches recent-cross pullbacks (good)
- LOOKBACK tight → misses sustained grinds (bad)
- STALE_BARS=60 → does not help because the signal never gets far enough to be checked

## Data

```
UMA 5h data (17:22 – 22:22 UTC):
  Open: 0.3936  High: 0.4114  Low: 0.3930  Current: 0.4084
  Change: +3.74%

First bar above EMA300: bar 170 (19:26) @ 0.3949, gap=+0.017%
Bars 171-470: 283/300 bars above EMA, gap growing every bar
Peak gap: +3.13% at bar 420 (21:51)

accel_300 signals (full simulation):
  bar 450 (20:24): gap=+0.24% → G2 blocked (was_below=False)
  bar 454 (20:27): gap=+0.23% → G2 blocked
  bar 456 (20:28): gap=+0.38% → G2 blocked
  bar 458 (20:30): gap=+0.51% → G2 blocked
  bar 462 (20:32): gap=+0.51% → G2 blocked
  All subsequent bars: gap large but G2 blocks

  → accel_300 would have fired at bar 450 if LOOKBACK >= 280
```

## Accel_300 Gate Order (for reference)

```
G1: abs(gap_now) < MIN_GAP_PCT (0.20%)     ← passes at bar ~220+
G2: was_below in LOOKBACK window             ← BLOCKS sustained grinds
G3: persistent above EMA for PERSISTENCE_BARS
G4: gap growing
G5: marginal acceleration (bars 3+ after cross)
G6: cross-back check
G7: bars_from_latest <= STALE_LOOKBACK (400)
G8: regime slope
G9: stale gap decay
G10: chop filter at cross bar
```

## Fix Options

### Option A: Raise ACCEL_300_LOOKBACK (conservative)
Raise from 30 to ~200. This lets the signal detect that price was below EMA within
200 bars. The STALE_BARS=60 still filters truly old signals. For UMA, the cross at
280 bars ago would pass LOOKBACK=200 but fail STALE_BARS=60 — meaning the signal
would fire but only if STALE_BARS is also raised.

**Conflict: raising LOOKBACK alone doesn't help** — the 280-bar cross is already beyond
STALE_BARS=60. Both must change together.

### Option B: Raise Both LOOKBACK and STALE_BARS Together
- `ACCEL_300_LOOKBACK`: 30 → 150
- `ACCEL_300_STALE_BARS`: 60 → 100

This allows detection of older crosses while still blocking truly stale signals.
The 80-bar gap between LOOKBACK and STALE_BARS is the "acceptable stale window."

### Option C: Accept accel_300 Isn't Built for This Pattern
accel_300 is momentum confirmation. gap_300 fires on the initial cross. If gap_300
was active, the entry would have been at 19:26. accel_300 adds confirmation but
isn't needed for clean, extended trends.

### Recommended
Option B is the most robust: raise LOOKBACK to 150 and STALE_BARS to 80 together.
This preserves filtering for choppy markets while catching sustained grinds.
Test on: ME, TOM, AERO, and other tokens that had clean one-bar crosses.

## Related
- refs: accel-300-sustained-breakdown-jun-2026.md (SHORT side of same pattern)
- refs: accel-300-gap-calibration-jun-2026.md (gap_pct threshold calibration)
