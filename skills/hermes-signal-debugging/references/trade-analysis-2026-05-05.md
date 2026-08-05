# Trade Analysis 2026-05-05 — All-Loser Session

## What Happened
Last 10-15 trades: pure losers. System putting us in losing positions at worst possible times.

## Root Cause Chain

### 1. OPP Penalty Floor Was a Kill Switch
`_get_opposing_penalty()` in `signal_compactor.py` had `floor=0.40`. Combined with staleness decay (0.4 at 3min), signals with 3+ opposing parts scored ~20-34 even at conf=88. Signals died in 2 cycles before reaching survival_round=1.

**Fix**: `floor=0.40` → `floor=0.65` in `signal_compactor.py` line 277.

### 2. Confluence Gate Was Too Strict (3+ → 2)
Without vel-hermes+ variants, clean signals only have 2 unique types (accel + rs). The gate required 3+ → blocked everything.

**Fix**: `unique_signal_types < 3` → `unique_signal_types < 2` in `signal_compactor.py` line 427.

### 3. vel-hermes+ Was Silently Blocking Everything
`SENTINEL_BASES = {'vel-hermes'}` suffix-agnostic matching in `validate_source()` blocked ALL vel-hermes variants (`vel-hermes+`, `vel-hermes-`) regardless of other signal quality. Example: `accel-300+,hzscore-,rs-s255,rs-s473,vel-hermes+` (conf=84.8) was blocked.

### 4. pct-hermes+ Was Bypassing Blacklist
`'pct-hermes'` in blacklist but `'pct-hermes+'` bypassed the component-level check because it strips `+` then checks exact match (fails) or SENTINEL_BASES (pct-hermes not in there).

**Fix**: Added explicit `'pct-hermes+'` to `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py` line 134.

## Why Signals Fired at Worst Times

The OPP penalty was correctly blocking good signals (accel-300+ based) while letting through only the weakest. The confluence gate then blocked those too. What DID get through was:
- RS-only signals (double RS = single type = blocked by _signal_type_key normalization... eventually)
- The system was starving, then when it DID fire, it was chasing after extended moves

## Current Hot-Set After Fixes
```
APEX  LONG accel-300+,rs-s4065         score=79.4
ETC   LONG accel-300+,rs-s78,rs-s80    score=63.8
LAYER LONG accel-300+,rs-s1533         score=48.3
EIGEN LONG accel-300+,rs-s10836,rs-s10878 score=46.4
MET   LONG accel-300+,rs-s2406         score=0.0 (OPP+staleness)
GALA  LONG accel-300+,rs-s1788,rs-s1800 score=0.0
MON   LONG accel-300+,rs-s1118         score=0.0
ICP   LONG accel-300+,rs-s294,rs-s296,rs-s855 score=0.0
```
All based on `accel-300+` (43% WR, +0.42% avg) — the best signal in the system.

## Key Files Changed
- `signal_compactor.py`: OPP floor (line 277), confluence gate (line 427)
- `hermes_constants.py`: `pct-hermes+` blacklist entry (line 134)
- `signal_schema.py`: `pct-hermes` exact-match component check (earlier session)

## What to Monitor
1. Watch APEX, ETC, LAYER, EIGEN over next 2-3 compaction cycles
2. If MET/GALA/MON/ICP persist with score=0 despite accel-300+ base, revisit staleness decay curve
3. OPP floor at 65% should let good signals survive 2-3 cycles
