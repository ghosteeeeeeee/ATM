# accel_300 — June 2026 Audit Fixes Applied

## Session: 2026-06-08 — Five P0 fixes implemented

File: `/root/.hermes/scripts/signals/accel_300.py` (was 494 lines, now 564 lines after fixes)

---

## What was fixed

### P0 #1 — Regime slope check
Added 20-bar simple linear regression slope filter in `detect_accel_300`, right before the return dict.

- Imports `ACCEL_300_REGIME_SLOPE_PCT` (0.003%/bar) from hermes_constants
- LONG blocked if pct_slope <= 0.003%/bar
- SHORT blocked if pct_slope >= -0.003%/bar

### P0 #2 — Stale gap decay check
Added after regime slope check, before return dict.

- Imports `ACCEL_300_STALE_GAP_DECAY_THRESHOLD` (0.50) from hermes_constants
- Newest bar gap must be >= 50% of signal bar gap (uses `abs()` for both directions)

### P0 #3 — Chop filter params
Added after stale gap decay check, before return dict.

- Imports `CHOP_CROSS_GAP_PCT` (0.22), `CHOP_EMA_ANGLE_PCT` (0.07), `CHOP_AVG_GAP_PCT` (0.90)
- Applied at cross_bar (requires cross_bar >= 50)
- Checks: gap at cross, EMA angle, avg gap over 50 bars

### P0 #4 — Stale gate boundary
`bars_since_cross > 10` → `bars_since_cross >= 10` (line 284)

### P0 #5 — Gap expansion gate (both directions)
Added gap_expansion gate for both LONG and SHORT, right after `bars_since_cross` computation.

- LONG: `gap_now < gap_at_cross - ACCEL_300_MIN_GAP_EXPANSION` (block if contracting)
- SHORT: `gap_now > gap_at_cross + ACCEL_300_MIN_GAP_EXPANSION` (block if less negative)

**Critical sign trap:** Same threshold formula but OPPOSITE operators. First patch used `>` for both (wrong for LONG). Had to correct to `<` for LONG after Python trace. Always trace BOTH directions with concrete values before patching.

---

## P1 — Not yet fixed

### P1 #6 — Cross bar fallback range too narrow
Primary cross search `range(i - LOOKBACK, i + 1)` may miss crosses at index 378+. Need a second-pass fallback searching `range(i-1, -1, -1)`.

---

## Syntax
All fixes: `python3 -m py_compile /root/.hermes/scripts/signals/accel_300.py` → clean
