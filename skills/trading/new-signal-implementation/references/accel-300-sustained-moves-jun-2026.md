# accel-300 sustained moves fix — June 2026

## Problem
accel-300 designed for sustained bleeds/rises, but C1's 30-bar lookback was too short.
Tokens like BLUR (399 bars below EMA), ME (80 bars above EMA) weren't firing.
Also: AXS fired SHORT when price was above EMA — late entry after tiny cross expanded 12x.

## Fixes Applied (accel_300.py)

### 1. C1 directional lookback
- Added `ACCEL_300_LOOKBACK_SHORT = 500` to hermes_constants.py (near line 475)
- SHORT: lookback=500 bars, LONG: lookback=30 bars
- If `was_ever_above_in_window=False` (price never crossed above EMA in window) → implied cross
- Added `implied_cross_bar` and `is_sustained_bleed` flag

### 2. C4 sustained move growth measurement
- When `bars_since_cross > ACCEL_300_MARGINAL_ACCEL_BARS` (3 bars), use growth from cross bar instead of 2-bar lookback
- 2-bar growth too short for sustained trends (ME: 1.06% from cross, -0.15% over 2 bars)

### 3. Warmup boundary fix
- At j=PERIOD-1 (299), ema300[j-1] is None → relaxed check allows cross detection

### 4. Late entry guard (AXS bug fix)
- Block if `bars_since_cross > 3` AND `gap_expansion > 0.75%` (3x MIN_GAP_PCT_SHORT)
- AXS: cross=-0.075%, gap_now=-0.924%, expansion=0.849% > 0.75% → blocked

### 5. Stale bars skip for sustained bleeds
- `is_sustained_bleed=True` bypasses stale bars check (bars_since_cross meaningless for implied_cross_bar)

## Key Constants
- `ACCEL_300_LOOKBACK = 30` (LONG), `ACCEL_300_LOOKBACK_SHORT = 500` (SHORT)
- `ACCEL_300_MARGINAL_ACCEL_BARS = 3`
- `ACCEL_300_MIN_GAP_PCT_SHORT = 0.25`, `ACCEL_300_MIN_GAP_PCT_LONG = 0.20`
- `MIN_GAP_GROWTH_PCT = 0.05` (LONG), `ACCEL_300_MIN_GAP_GROWTH_SHORT = 0.07` (SHORT)
- `ACCEL_300_MIN_GAP_EXPANSION = 0.01`

## T's Market Rules
- T knows market: "I could find 10 coins right now in a trend" — trust his judgment
- Signal direction: price ABOVE EMA → LONG, price BELOW EMA → SHORT
- Sustained move: no pullback to EMA in extended window, gap expanding from cross
- Late entry guard: gap expanded >3x from tiny cross → block (signal chasing, not catching)
- Counter-regime signals: never hard-block, per-coin regime filter decides

## Data Source Note
- `signals_hermes.db` price_history: ME has 114,570 bars (more complete)
- `candles.db` candles_1m: ME has 59,704 rows (less complete)
- accel-300 reads from candles_1m via hl-sync-guardian pipeline