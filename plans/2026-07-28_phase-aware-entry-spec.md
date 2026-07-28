# Spec: Phase-Aware Entry Plugin

**Date:** 2026-07-28
**Status:** READY TO IMPLEMENT
**Files:** `signals/accel_300.py`, `signals/inverse_accel_300.py`, `hermes_constants.py`

---

## Problem

The phase system (quiet → building → accelerating → exhaustion → extreme) exists in `tpsl_utils.py` and affects SL/TP trailing. But `accel_300` and `inv_accel_300` are **completely phase-agnostic** — they fire regardless of market phase.

This causes:
- `accel_300` fires during **exhaustion/extreme** phases → enters after the move is done → price reverses → SL hit
- `inv_accel_300` fires during **building/accelerating** phases → enters too early before the move exhausts → price keeps moving against → SL hit

The LINK trades are perfect examples: SHORT at the bottom of a move (exhaustion), LONG at the top (exhaustion).

---

## Solution

Add a phase gate to both signal detectors that blocks entries during inappropriate phases.

### Phase Definitions (from `tpsl_utils._phase_from_pct()`)

```python
Phase 0 (quiet):      speed_percentile < 60, velocity near 0
Phase 1 (building):   speed_percentile >= 60
Phase 2 (accelerating): speed_percentile >= 70
Phase 3 (exhaustion):  speed_percentile >= 88
Phase 4 (extreme):     speed_percentile >= 95
```

### Phase Gate Rules

**For `accel_300` (momentum signal — "ride the wave"):**
| Phase | Action | Reason |
|-------|--------|--------|
| quiet | ALLOW | Fresh start, early entry possible |
| building | ALLOW | IDEAL — momentum just starting |
| accelerating | ALLOW | Still OK — momentum confirmed |
| exhaustion | **BLOCK** | Move is over — don't chase |
| extreme | **BLOCK** | Exhausted — high reversal risk |

**For `inv_accel_300` (mean reversion signal — "catch the turn"):**
| Phase | Action | Reason |
|-------|--------|--------|
| quiet | BLOCK | No move to revert from |
| building | BLOCK | Move still building — too early to catch turn |
| accelerating | CAUTION | Move may be too far gone — allow but penalize |
| exhaustion | ALLOW | IDEAL — reversal prime |
| extreme | ALLOW | Maximum exhaustion — best reversion |

---

## Implementation Details

### 1. New Constants in `hermes_constants.py`

```python
# ── Phase Entry Filter ────────────────────────────────────────────────────────
# Blocks signal entries during inappropriate market phases.
# Based on surfing.md: "Don't chase exhausted waves, don't enter whitewater."
PHASE_ENTRY_FILTER_ENABLED = True   # Master toggle

# accel_300: which phases are ALLOWED (momentum entry)
ACCEL_300_ALLOWED_PHASES = {'quiet', 'building', 'accelerating'}
# Block: exhaustion, extreme

# inv_accel_300: which phases are ALLOWED (mean reversion entry)
INVERSE_ACCEL_300_ALLOWED_PHASES = {'exhaustion', 'extreme'}
INVERSE_ACCEL_300_CAUTION_PHASES = {'accelerating'}
# Block: quiet, building
```

### 2. Changes to `signals/accel_300.py`

In `detect_accel_300()`, add phase check after the price position filter (line ~348), before the return statement:

```python
    # ── Phase entry filter (FIX 2026-07-28) ────────────────────────────────────
    # Don't enter during exhaustion/extreme phases — the move is over.
    # Requires speed_percentile from momentum_cache or token_speeds.
    if PHASE_ENTRY_FILTER_ENABLED:
        phase = _get_current_phase(token)
        if phase and phase not in ACCEL_300_ALLOWED_PHASES:
            return None
```

Need to add a helper function `_get_current_phase()` that:
1. Reads `speed_percentile` from `token_speeds` table (or momentum_cache)
2. Reads `velocity` from the same source
3. Calls `tpsl_utils._phase_from_pct(pct, velocity)` to get phase string

```python
def _get_current_phase(token: str) -> Optional[str]:
    """Get current market phase for token from token_speeds cache."""
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT speed_percentile, velocity_5m
            FROM token_speeds
            WHERE token = ?
            ORDER BY updated_at DESC LIMIT 1
        """, (token.upper(),))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        pct = float(row[0] or 50)
        velocity = float(row[1] or 0)
        from tpsl_utils import _phase_from_pct
        return _phase_from_pct(pct, velocity)
    except Exception:
        return None
```

### 3. Changes to `signals/inverse_accel_300.py`

In `detect_inverse_accel_300()`, add phase check after the price position filter (line ~305), before the return statement:

```python
    # ── Phase entry filter (FIX 2026-07-28) ────────────────────────────────────
    # Mean reversion only works during exhaustion/extreme phases.
    # During quiet/building, the move hasn't exhausted yet — too early.
    if PHASE_ENTRY_FILTER_ENABLED:
        phase = _get_current_phase(token)
        if phase:
            if phase in ('quiet', 'building'):
                return None  # too early — move hasn't exhausted
            # accelerating is caution — allow but could add penalty later
```

Same `_get_current_phase()` helper as accel_300 (can be shared via a base module or duplicated).

### 4. Return Value Enhancement

Add `phase` to the signal return dict for both signals:

```python
return {
    'direction': direction,
    'gap_pct': round(gap_now, 4),
    # ... existing fields ...
    'phase': phase or 'unknown',  # NEW: market phase at detection time
}
```

This allows downstream (compactor, decider) to see the phase and potentially use it for scoring.

---

## Data Flow

```
token_speeds table (updated every minute by price_collector)
    ↓
_get_current_phase(token) → speed_percentile, velocity
    ↓
tpsl_utils._phase_from_pct(pct, velocity) → 'quiet'|'building'|'accelerating'|'exhaustion'|'extreme'
    ↓
Phase gate check:
    accel_300: block if phase in {exhaustion, extreme}
    inv_accel_300: block if phase in {quiet, building}
    ↓
Signal passes → add_signal() → compactor → hotset → trade
```

---

## Config Toggles

| Constant | Default | Purpose |
|----------|---------|---------|
| `PHASE_ENTRY_FILTER_ENABLED` | `True` | Master toggle for phase gating |
| `ACCEL_300_ALLOWED_PHASES` | `{'quiet', 'building', 'accelerating'}` | Which phases allow accel_300 entries |
| `INVERSE_ACCEL_300_ALLOWED_PHASES` | `{'exhaustion', 'extreme'}` | Which phases allow inv_accel_300 entries |
| `INVERSE_ACCEL_300_CAUTION_PHASES` | `{'accelerating'}` | Phases that allow but may penalize |

---

## Expected Impact

| Metric | Before | After (Expected) |
|--------|--------|------------------|
| accel_300 exhaustion entries | ~15% of total | 0% (blocked) |
| inv_accel_300 building entries | ~20% of total | 0% (blocked) |
| Overall WR | 29% | 35-40% |
| False signal rate | ~70% | ~55-60% |

---

## Testing Plan

1. **Backtest**: Run `backtest_flags.py` equivalent for phase filter — check how many historical losses would have been blocked
2. **Dry run**: Enable filter, run pipeline for 24h, count blocked signals vs passed signals
3. **Verify signal count**: Ensure filter doesn't block too many signals (target: >10/day)
4. **A/B test**: Run with filter ON for 48h, compare WR to previous 48h

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Blocks too many signals | Make `ACCEL_300_ALLOWED_PHASES` configurable — add 'exhaustion' back if too restrictive |
| Phase data stale | `_get_current_phase()` returns None → signal passes (fail-open) |
| Velocity data missing | Default to 'quiet' phase → accel_300 allowed, inv_accel_300 blocked |
| Performance impact | Phase lookup is a single DB query — negligible (<1ms) |
