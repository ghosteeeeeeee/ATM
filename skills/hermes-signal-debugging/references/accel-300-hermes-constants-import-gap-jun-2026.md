# accel-300: Hermes Constants Import Gap (2026-06-06)

## Problem
Many accel-300 constants were set in `hermes_constants.py` but the signal code was NOT reading them.
Only 2 of ~10 declared constants were actually imported and used.

## What was imported (line 55-60, accel_300.py)
```python
from hermes_constants import (
    MIN_GAP_PCT_LONG, MIN_GAP_PCT_SHORT,
    ACCEL_300_MIN_GAP_GROWTH, ACCEL_300_MIN_GAP_EXPANSION,
    ACCEL_300_PERSISTENCE_BARS, ACCEL_300_COOLDOWN_MIN,
    ACCEL_300_REGIME_SLOPE_PCT, ACCEL_300_STALE_BARS,
    ACCEL_300_LOOKBACK,    # ← ADDED 2026-06-06 after this gap was found
)
```

## What was hardcoded in signal code (accel_300.py lines 69-74)
```python
PERIOD           = 300      # EMA(300) on 1m prices
LOOKBACK         = 30       # ← hardcoded, NOT reading ACCEL_300_LOOKBACK
PERSISTENCE_BARS = ACCEL_300_PERSISTENCE_BARS  # ✓ sourced from constants
MIN_GAP_GROWTH_PCT = ACCEL_300_MIN_GAP_GROWTH  # ✓ sourced from constants
MIN_GAP_EXPANSION  = ACCEL_300_MIN_GAP_EXPANSION  # ✓ sourced from constants
```

## Constants that WERE being read (OK)
- ACCEL_300_PERSISTENCE_BARS
- ACCEL_300_MIN_GAP_GROWTH
- ACCEL_300_MIN_GAP_EXPANSION
- ACCEL_300_REGIME_SLOPE_PCT (patched from hardcoded 0.015 → read from constants)
- ACCEL_300_STALE_BARS (patched from hardcoded 20 → read from constants)
- ACCEL_300_LOOKBACK (added 2026-06-06)

## Constants that were NEVER read (ignored)
- ACCEL_300_PERIOD — hardcoded at 300, never read from hermes_constants
- ACCEL_300_LOOKBACK — hardcoded at 30, not imported until 2026-06-06

## Root Cause
When T set `ACCEL_300_LOOKBACK=20` in hermes_constants, the signal used its own local
`LOOKBACK = 30` instead. The change had zero effect.

## Fix Applied (2026-06-06)
1. Added `ACCEL_300_LOOKBACK` to the import in accel_300.py:60
2. Changed `LOOKBACK = 30` → `LOOKBACK = ACCEL_300_LOOKBACK` at line 70

## LOOKBACK Formula — CRITICAL
The signal's cross search window is: `max(PERIOD + LOOKBACK, n - 1 - LOOKBACK)` to `n-1`

For n=700 (all tokens have 700 1m bars), PERIOD=300:
- LOOKBACK=20: window = max(320, 679) = bars 679-699 (21 bars) — very narrow
- LOOKBACK=400: window = max(700, 299) = bars 700-699 → only bar 699 (1 bar!)
- LOOKBACK=250: window = max(550, 449) = bars 550-699 (150 bars)

**Smaller LOOKBACK = wider search window** (searches more historical bars).
**Larger LOOKBACK = narrower search window** (only recent bars).

Most actual crosses are at bars 320-437 (182-379 bars ago).
With LOOKBACK=20, search window is bars 679-699 — NONE of those crosses are found.
With LOOKBACK=250, search window is bars 550-699 — captures crosses at bars 517+.

**Minimum needed**: LOOKBACK must be >= the oldest cross bar you want to catch.
For the most recent cross at bar 517 (ZORA, 182 bars ago): LOOKBACK >= 182.

## MIN_GAP_PCT_SHORT Logic — Maximum Not Minimum
```python
# Line ~267 in detect_accel_300:
if direction == 'SHORT' and abs(gap_pcts[i]) < MIN_GAP_PCT_SHORT:
    fail_counts['gap'] += 1
    continue
```

The check uses `abs(gap_pct) < threshold` — so for SHORT, it only accepts gaps
between 0% and -threshold%. A gap of -0.25% (abs=0.25 > 0.15) is REJECTED.
A gap of -0.05% (abs=0.05 < 0.15) is ACCEPTED.

This treats steep declines as "too volatile" and shallow dips as "safe" — inverted.

**Result**: Strong momentum moves (XLM -4.39%, FET -3.11%, MORPHO -0.25%) are blocked.
Only tiny shallow dips pass (TRX -0.032, CAKE -0.119).

To accept both: change `abs(gap) < threshold` → `gap < -threshold` (for SHORT).
Or set threshold higher (e.g., 0.50) to pass steeper declines.