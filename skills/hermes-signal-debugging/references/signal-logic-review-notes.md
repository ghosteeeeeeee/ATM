# Signal Logic Review Notes — 2026-06-14

## Context
External review of `signals/accel_300.py` and `signals/rs.py` against an older copy.
Some review findings were already fixed in the current codebase; others were genuine bugs.

## Key lesson: External reviews can be OUTDATED
Before fixing anything from an external review:
1. Read the CURRENT source files (not just the review)
2. Check hermes_constants.py for the actual constant values
3. Verify each review item against the live code
4. Fix only what is actually broken — don't "fix" things the review thought were broken but were already corrected

## accel_300.py — What was actually wrong

### ACTUAL FIX: SHORT gap-growth sign was INVERTED (a1)
- **Bug**: `avg_gap_growth <= min_gap_growth_dir` — for SHORT (negative gaps), a widening gap (more negative growth) was always rejected because `-0.07 <= 0.07` is always TRUE
- **Fix**: sign-flipped comparison for SHORT: `avg_gap_growth >= -min_gap_growth_dir`
- **Symptom**: accel-300 SHORT could never fire on accelerating downside momentum
- **File**: `/root/.hermes/scripts/signals/accel_300.py` lines ~366-378

### ACTUAL FIX: SHORT_BLACKLIST checked before direction known (a5)
- **Bug**: `if token.upper() in SHORT_BLACKLIST: continue` was at line 649, BEFORE direction was determined at line 277
- **Effect**: tokens on SHORT_BLACKLIST (BRETT, XLM, etc.) had ALL accel-300 signals blocked, including valid LONG breakouts
- **Fix**: moved blacklist check to AFTER direction determination, applied only to SHORT signals
- **File**: `/root/.hermes/scripts/signals/accel_300.py` ~lines 681-689

## accel_300.py — Review was OUTDATED (already correct in code)
| Review item | Status in code |
|---|---|
| SHORT LOOKBACK=30 not 500 | WRONG — ACCEL_300_LOOKBACK_SHORT=500 already set |
| SHORT min gap 0.20 not 0.25 | WRONG — ACCEL_300_MIN_GAP_PCT_SHORT=0.25 already set |
| SHORT growth 0.05 not 0.07 | WRONG — ACCEL_300_MIN_GAP_GROWTH_SHORT=0.07 already set |
| Stale gate at 10 bars | WRONG — ACCEL_300_STALE_BARS=60 already set |
| Missing regime slope filter | WRONG — already implemented (ACCEL_300_REGIME_SLOPE_PCT) |
| Missing stale gap decay | WRONG — already implemented |
| Missing chop filter | WRONG — already implemented |

## rs.py — What was actually wrong

### ACTUAL FIX: Recency scoring INVERTED (r1)
- **Bug**: `recency_score = recency_touches + RS_RECENCY_BOOST_K * ancient_touches` — ancient touches received the multiplier (boosted), recent touches did not
- **Effect**: ancient exhausted levels scored higher than fresh reactive ones — opposite of intended behavior
- **Fix**: `recency_score = RS_RECENCY_BOOST_K * recency_touches + ancient_touches`
- **File**: `/root/.hermes/scripts/signals/rs.py` line ~389

### ACTUAL FIX: Bounce condition (a) dead code (r4)
- **Bug**: `c['close'] > c['open']` check for LONG bounce — candles are synthesized (open==close), so this is always False
- **Fix**: removed dead branch, kept only follow-through path (b)
- **File**: `/root/.hermes/scripts/signals/rs.py` ~lines 251-281

### ACTUAL FIX: add_signal missing params (r7)
- **Bug**: rs.py call to `add_signal()` was missing `value`, `exchange`, `timeframe` — review noted the old top-level copy passed these but migrated version didn't
- **Fix**: added all three params
- **File**: `/root/.hermes/scripts/signals/rs.py` ~lines 815-821

## rs.py — Review was OUTDATED (already correct in code)
| Review item | Status in code |
|---|---|
| Recency lookup fails after clustering | WRONG — `_get_clustered_recency()` already exists and is called |
| Level selection by distance not recency | WRONG — `_get_clustered_recency` used for best-level selection |
| Level broken check direction-agnostic | WRONG — `_level_recently_broken()` takes `direction` param |
| Returns bare 0 when disabled | WRONG — returns `(0, [])` tuple in current code |
| Missing regime slope filter in accel | WRONG — already implemented |
