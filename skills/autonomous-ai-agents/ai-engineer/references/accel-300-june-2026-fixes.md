# accel_300.py — June 2026 Audit Fixes (2026-06-08)

## Subagent Audit Result
- 5 P0 bugs, 1 P1 bug
- File: 494 lines → 565 lines after fixes
- All constants extracted to hermes_constants.py

## P0 Fixes Applied

### P0 #1 — Regime slope check (lines 329-345)
- **Bug**: `ACCEL_300_REGIME_SLOPE_PCT` existed in hermes_constants.py but was never imported or used
- **Fix**: Added simple linear regression slope over `ACCEL_300_SLOPE_WINDOW=20` bars; LONG blocked if slope ≤ threshold, SHORT blocked if slope ≥ -threshold
- **Constants added**: `ACCEL_300_REGIME_SLOPE_PCT=0.003`, `ACCEL_300_SLOPE_WINDOW=20`

### P0 #2 — Stale gap decay check (lines 347-355)
- **Bug**: `ACCEL_300_STALE_GAP_DECAY_THRESHOLD` existed in hermes_constants.py but never wired in
- **Fix**: Newest bar gap must be ≥ `ACCEL_300_STALE_GAP_DECAY_THRESHOLD` (0.50) fraction of signal bar gap
- **Constant**: `ACCEL_300_STALE_GAP_DECAY_THRESHOLD=0.50`

### P0 #3 — Chop filter params (lines 357-378)
- **Bug**: `CHOP_CROSS_GAP_PCT`, `CHOP_EMA_ANGLE_PCT`, `CHOP_AVG_GAP_PCT` existed but never implemented
- **Fix**: Three sub-checks at cross bar: (1) gap at cross ≥ threshold, (2) EMA angle ≥ threshold, (3) 50-bar avg gap ≥ threshold
- **Constants**: `ACCEL_300_CHOP_CROSS_GAP_PCT=0.22`, `ACCEL_300_CHOP_EMA_ANGLE_PCT=0.07`, `ACCEL_300_CHOP_AVG_GAP_PCT=0.90`, `ACCEL_300_CHOP_LOOKBACK=50`

### P0 #4 — Stale gate boundary (line 301)
- **Bug**: `bars_since_cross > 10` allowed bar 10 through (boundary off-by-one)
- **Fix**: Changed to `bars_since_cross >= ACCEL_300_STALE_BARS` (now = 10)
- **Constant**: `ACCEL_300_STALE_BARS=10`

### P0 #5 — Gap expansion gate (both directions, lines 287-294)
- **Bug**: Gap expansion gate was absent entirely — no SHORT or LONG check existed
- **Fix (corrected self-error)**: First patch used `>` for both directions — wrong for LONG
  - LONG: `gap_now < gap_at_cross - ACCEL_300_MIN_GAP_EXPANSION` (contracting = block)
  - SHORT: `gap_now > gap_at_cross + ACCEL_300_MIN_GAP_EXPANSION` (less negative = block)
- **Constant**: `ACCEL_300_MIN_GAP_EXPANSION=0.01`
- **Self-correction**: Python trace before first patch revealed LONG inequality was inverted; corrected to `<` before syntax check

## Post-Fix: Constant Extraction Pass
After initial fixes, two hardcoded values found and extracted:
1. `slope_window = 20` → `ACCEL_300_SLOPE_WINDOW` in hermes_constants.py
2. `ema_lookback = 50` → `ACCEL_300_CHOP_LOOKBACK` in hermes_constants.py

## P1 Fix Pending

### P1 #6 — Cross bar fallback range too narrow (line 273)
- **Bug**: `range(i - LOOKBACK, i + 1)` where LOOKBACK=30. With 600-bar fetches, crosses at index 378+ are missed.
- **Fix needed**: Add second-pass fallback: if no cross found in primary range, search `range(i-1, -1, -1)`
- **Status**: Not yet applied

## Final Constant Map (all in hermes_constants.py)
```
ACCEL_300_STALE_BARS = 10
ACCEL_300_STALE_LOOKBACK = 10
ACCEL_300_MIN_GAP_EXPANSION = 0.01
ACCEL_300_REGIME_SLOPE_PCT = 0.003
ACCEL_300_SLOPE_WINDOW = 20
ACCEL_300_STALE_GAP_DECAY_THRESHOLD = 0.50
ACCEL_300_CHOP_CROSS_GAP_PCT = 0.22
ACCEL_300_CHOP_EMA_ANGLE_PCT = 0.07
ACCEL_300_CHOP_AVG_GAP_PCT = 0.90
ACCEL_300_CHOP_LOOKBACK = 50
```
