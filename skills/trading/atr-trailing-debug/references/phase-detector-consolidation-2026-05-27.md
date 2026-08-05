# Phase Detector Consolidation — 2026-05-27 ✅ COMPLETED

## Status: DONE — All phase/k-value constants centralized in hermes_constants.py

The "consolidation pending" warning in the parent SKILL.md is now **RESOLVED**.

---

## What was done

### 1. hermes_constants.py — added (lines ~359-365)

```python
# ── Phase Detection Thresholds ────────────────────────────────────────────────
# Used by both signal_gen.detect_phase() and tpsl_utils._phase_from_pct()
# MUST be identical in both systems — consolidation complete as of 2026-05-27
PHASE_BUILDING         = 60   # percentile ≥60 → momentum starting
PHASE_ACCELERATING     = 75   # percentile ≥75 → strong momentum
PHASE_EXHAUSTION       = 88   # percentile ≥88 → late phase, watch for exit
PHASE_EXTREME          = 95   # percentile ≥95 → exhaustion/mean-reversion territory
PHASE_NEUTRAL          = 50   # percentile ≥50 → neutral (no strong direction)
PHASE_VEL_STALL_THRESH = 0.0  # velocity ≤ 0 = stalling (negative velocity at accel+ phase)
PHASE_ACCEL_FAST_THRESH = 70  # speed_percentile ≥70 → fast branch in _atr_sl_k_scaled
```

### 2. signal_gen.py — local PHASE_* defines REMOVED

- Were at lines ~156-159 (PHASE_BUILDING=60, PHASE_ACCELERATING=75, PHASE_EXHAUSTION=88, PHASE_EXTREME=95)
- Import line 33 updated to include PHASE_BUILDING, PHASE_ACCELERATING, PHASE_EXHAUSTION, PHASE_EXTREME from hermes_constants
- `detect_phase()` function unchanged — now uses imported constants

### 3. tpsl_utils.py — `_phase_from_pct` rewritten

- Uses PHASE_EXTREME, PHASE_EXHAUSTION, PHASE_ACCELERATING, PHASE_NEUTRAL, PHASE_VEL_STALL_THRESH
- Includes the `quiet` condition (same as signal_gen.detect_phase):
  `pct < PHASE_BUILDING and abs(velocity) < PHASE_VEL_STALL_THRESH` → 'quiet'
- Both `speed_percentile >= 70` occurrences (lines ~140, ~147) replaced with `>= PHASE_ACCEL_FAST_THRESH`

### 4. position_manager.py — also needed updating

- ai-engineer verification caught that position_manager also had `speed_percentile >= 70` hardcoded (lines ~1333 and ~1341)
- `PHASE_ACCEL_FAST_THRESH` added to import line 32
- Both `>= 70` replaced with constant

---

## AI Engineer Verification Results (2026-05-27)

All 4 files PASS `py_compile`. Codebase grep for remaining hardcoded `speed_percentile >= 70`: **0 matches**.

| Check | File | Status |
|---|---|---|
| New constants in hermes_constants | hermes_constants.py | ✅ PASS |
| Local defines removed | signal_gen.py | ✅ PASS |
| _phase_from_pct uses constants | tpsl_utils.py | ✅ PASS |
| Functional equivalence (90 test combos) | tpsl_utils vs signal_gen | ✅ PASS |
| position_manager updated | position_manager.py | ✅ PASS |
| No hardcoded >= 70 anywhere | codebase | ✅ PASS |

---

## Key files changed (final state)

| File | Change |
|------|--------|
| `/root/.hermes/scripts/hermes_constants.py` | PHASE_* constants at lines ~359-365 |
| `/root/.hermes/scripts/signal_gen.py` | Import line updated, local defines gone |
| `/root/.hermes/scripts/tpsl_utils.py` | Import block, `_phase_from_pct` rewritten, lines ~140/147 |
| `/root/.hermes/scripts/position_manager.py` | Import line updated, lines ~1333/1341 |

---

## Important note on signal_gen.py:495

Contains hardcoded `0.05` (VEL_STALE_THRESHOLD_PCT for signal staleness detection) — **intentional**, not a bug. Two different constants with different purposes:
- `VEL_STALE_THRESHOLD_PCT = 0.05` — signal filtering staleness threshold
- `PHASE_VEL_STALL_THRESH = 0.0` — phase stall detection for ATR k-scaling

---

## Original plan (superseded)

The plan below was the initial planning doc. The actual implementation differed:

- `_phase_from_pct` uses the FULL signal_gen.detect_phase logic including the `quiet` condition (not the simplified version originally planned)
- `PHASE_NEUTRAL=50` is defined but 'neutral' phase is reached via the building/exhaustion branches, not a standalone 'neutral' return
- Velocity check uses `PHASE_VEL_STALL_THRESH` (0.0) in the `quiet` condition, not the `> 0` branch logic originally planned

### Original plan (for reference)

```
Step 1: hermes_constants.py — add PHASE_BUILDING=60, PHASE_ACCELERATING=75, PHASE_EXHAUSTION=88,
        PHASE_EXTREME=95, PHASE_NEUTRAL=50, PHASE_VEL_STALL_THRESH=0.0, PHASE_ACCEL_FAST_THRESH=70

Step 2: signal_gen.py — remove local PHASE_* defines, update import line

Step 3: tpsl_utils.py — _phase_from_pct uses imported PHASE_* constants (mirrors signal_gen.detect_phase
        exactly, including velocity stall). Replace `speed_percentile >= 70` with PHASE_ACCEL_FAST_THRESH.

Step 4: position_manager.py — replace `speed_percentile >= 70` with PHASE_ACCEL_FAST_THRESH
```