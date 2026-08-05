# Hardcoded Constants → hermes_constants Refactor Pattern

**Date:** 2026-06-08
**Signal:** accel_300.py (signals/signals/accel_300.py)
**Pattern:** Local constants at top of signal file shadow hermes_constants with different values

---

## The Problem

Signal files can accumulate local constants at the top:

```python
# accel_300.py — BEFORE (581 lines)
PERIOD             = 300
LOOKBACK           = 30
PERSISTENCE_BARS   = 2
MIN_GAP_PCT        = 0.20
MIN_GAP_GROWTH_PCT = 0.05
COOLDOWN_BARS      = 10
LOOKBACK_1M        = 700
```

Meanwhile `hermes_constants.py` already defines:
```python
ACCEL_300_LOOKBACK        = 100  # ← DIFFERENT VALUE
ACCEL_300_PERSISTENCE_BARS = 4   # ← DIFFERENT VALUE
ACCEL_300_MIN_GAP_GROWTH  = 0.01 # ← DIFFERENT VALUE
```

**The local constants take precedence.** The hermes_constants values are the "tuned" layer but are never actually used by the signal. Any Tune via hermes_constants has zero effect.

---

## Detection Checklist

When auditing an existing signal for this pattern:

1. grep for `= [0-9]` at top of signal file (numeric literals assigned to ALL-CAPS names)
2. Cross-reference each against `hermes_constants.py` — same name prefix?
3. If same name prefix exists in hermes_constants with different value → CONFLICT
4. Run `python3 -c "from hermes_constants import ACCEL_300_LOOKBACK; print(ACCEL_300_LOOKBACK)"` to verify actual runtime value

---

## The Fix

**Step 1 — Update hermes_constants.py**

Add missing constants + align divergent values to match what the signal actually uses (the local values are the "truth" for existing signals):

```python
ACCEL_300_PERIOD          = 300  # already correct
ACCEL_300_LOOKBACK        = 30   # was 100 → updated (signal uses local value)
ACCEL_300_PERSISTENCE_BARS = 2   # was 4 → updated
ACCEL_300_MIN_GAP_GROWTH  = 0.05 # was 0.01 → updated
ACCEL_300_MIN_GAP_PCT     = 0.20 # missing → added
ACCEL_300_COOLDOWN_BARS   = 10   # missing → added
ACCEL_300_LOOKBACK_1M     = 700  # missing → added
```

**Step 2 — Replace local block in signal file**

```python
# ── Signal constants (from hermes_constants) ──────────────────────────────────
from hermes_constants import (
    ACCEL_300_PERIOD, ACCEL_300_LOOKBACK, ACCEL_300_PERSISTENCE_BARS,
    ACCEL_300_MIN_GAP_PCT, ACCEL_300_MIN_GAP_GROWTH, ACCEL_300_COOLDOWN_BARS,
    ACCEL_300_LOOKBACK_1M,
)
# Alias local names for readability in detection logic
PERIOD           = ACCEL_300_PERIOD
LOOKBACK         = ACCEL_300_LOOKBACK
PERSISTENCE_BARS = ACCEL_300_PERSISTENCE_BARS
MIN_GAP_PCT      = ACCEL_300_MIN_GAP_PCT
MIN_GAP_GROWTH_PCT = ACCEL_300_MIN_GAP_GROWTH
COOLDOWN_BARS    = ACCEL_300_COOLDOWN_BARS
LOOKBACK_1M      = ACCEL_300_LOOKBACK_1M
```

**Step 3 — Add to detect_* function import block**

Inside the detection function, import the constants from hermes_constants (not from module-level — local aliasing at function scope keeps detection logic readable):

```python
def detect_xxx_signals(...):
    from hermes_constants import (
        # Detection params
        ACCEL_300_PERIOD, ACCEL_300_LOOKBACK, ACCEL_300_PERSISTENCE_BARS,
        ACCEL_300_MIN_GAP_PCT, ACCEL_300_MIN_GAP_GROWTH,
        # Gate constants (existing)
        ACCEL_300_STALE_BARS, ACCEL_300_STALE_LOOKBACK, ...,
    )
    # Alias short names
    PERIOD           = ACCEL_300_PERIOD
    LOOKBACK         = ACCEL_300_LOOKBACK
    ...
```

**Step 4 — Verify syntax + runtime**

```bash
python3 -m py_compile signals/accel_300.py && echo "SYNTAX OK"
python3 -c "
from hermes_constants import ACCEL_300_LOOKBACK, ACCEL_300_PERSISTENCE_BARS
print(f'LOOKBACK={ACCEL_300_LOOKBACK}, PERSISTENCE_BARS={ACCEL_300_PERSISTENCE_BARS}')
"
```

---

## Key Principle

**All tunable numeric literals must live in hermes_constants.py — one authoritative location.**

The alias pattern (import from hermes_constants, assign to local short names) preserves readability in detection logic while ensuring T can tune from one place without editing signal files.

---

## Accel-300 Constants Summary (post-fix, 2026-06-08)

| Constant | Value | Notes |
|---|---|---|
| `ACCEL_300_PERIOD` | 300 | EMA period |
| `ACCEL_300_LOOKBACK` | 30 | bars to look back for cross |
| `ACCEL_300_PERSISTENCE_BARS` | 2 | consecutive bars above/below EMA |
| `ACCEL_300_MIN_GAP_PCT` | 0.20 | minimum gap % to fire |
| `ACCEL_300_MIN_GAP_GROWTH` | 0.05 | gap growth vs PERSISTENCE_BARS ago |
| `ACCEL_300_MIN_GAP_EXPANSION` | 0.01 | gap expansion gate (both dirs) |
| `ACCEL_300_COOLDOWN_BARS` | 10 | dedup bars |
| `ACCEL_300_LOOKBACK_1M` | 700 | 1m prices to fetch |
| `ACCEL_300_REGIME_SLOPE_PCT` | 0.003 | regime slope threshold |
| `ACCEL_300_SLOPE_WINDOW` | 20 | slope calculation window |
| `ACCEL_300_STALE_BARS` | 10 | stale gate (bars since cross) |
| `ACCEL_300_STALE_LOOKBACK` | 10 | stale gate (detection bar age) |
| `ACCEL_300_STALE_GAP_DECAY_THRESHOLD` | 0.50 | newest bar gap vs signal bar gap |
| `ACCEL_300_CROSS_LOOKBACK` | 100 | primary cross-bar search window |
| `ACCEL_300_CHOP_CROSS_GAP_PCT` | 0.22 | chop filter — gap at cross |
| `ACCEL_300_CHOP_EMA_ANGLE_PCT` | 0.07 | chop filter — EMA angle |
| `ACCEL_300_CHOP_AVG_GAP_PCT` | 0.90 | chop filter — avg gap magnitude |
| `ACCEL_300_CHOP_LOOKBACK` | 50 | chop filter — lookback |
| `ACCEL_300_TOKEN_ALLOWLIST` | set() | empty = fire on all tokens |
| `ACCEL_300_BLOCK_COSIGS` | {'ma-cross-5m+', 'pct-hermes+'}

Total: 24 ACCEL_300 constants in hermes_constants.py (lines 473-499)