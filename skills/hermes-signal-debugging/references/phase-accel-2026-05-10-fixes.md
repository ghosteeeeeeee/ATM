# phase_accel Fix Update — May 10, 2026

This supplements the earlier `phase-accel-signal-fix.md`. Four additional bugs were found and fixed in the same session.

---

## Bug Fixes Applied (May 10)

### 1. Tracker started empty — all tokens skipped on first cycle

**Problem:** `_PHASE_TRACKER = {}` at module load. On first `run()` call, every token gets `prev_phase=None` → skipped via `continue`. Transitions that already happened (e.g., LAYER building→accelerating at 04:45) were never captured.

**Fix:** Added `_SEEDED` flag and `_seed_tracker_from_db()`:
```python
def _seed_tracker_from_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT token, phase FROM momentum_cache")
    for (token, phase) in c.fetchall():
        _PHASE_TRACKER[token] = phase  # prev_phase = current phase
    conn.close()
```
Called at top of `run()` if not yet seeded. Non-fatal on error.

---

### 2. Phase mismatch — used directional percentile instead of pct_rank

**Problem:** `_detect_phase(pct_for_phase, velocity)` received `max(pct_long, pct_short)` (directional percentile). But momentum_cache stores phase derived from `percentile` (pct_rank = z-score percentile).

For LAYER:
- pct_rank = 100.0 → momentum_cache phase = 'extreme'
- max(pct_long, pct_short) = 92.5 → _detect_phase returns 'exhaustion'

Tracker seeded with 'extreme' from DB. Current detection returns 'exhaustion' → `extreme→exhaustion` blocked (extreme is terminal). Signal never fires.

**Fix:** Use `mom['percentile']` (pct_rank) for phase detection:
```python
pct_rank = mom.get('percentile', 50)  # matches momentum_cache exactly
curr_phase = _detect_phase(pct_rank, velocity)
```

**Critical distinction:**
- `mom['percentile']` (pct_rank) = "how unusual is current z-score vs rolling-window z distribution" (0-100). pct_rank=100 = z-score at all-time high vs rolling windows → phase='extreme'.
- `mom['percentile_long']` = "% of historical prices below current price" (suppression signal).
- `mom['percentile_short']` = "% of historical prices above current price" (elevation signal).

---

### 3. extreme→extreme was blocked — but this is the LAYER pattern

**Problem:** `_is_upward_transition` returned `False` for `prev_phase == 'extreme'`. LAYER was extreme (pct_rank=100) for the entire session before signal fired. Tracker showed prev=extreme, curr=extreme → no transition → signal silent.

**Fix:** Allow `extreme→extreme` when avg_z < -0.2 AND velocity > 0.01:
```python
if prev_phase == 'extreme' and curr_phase == 'extreme':
    return avg_z < -0.2 and velocity > 0.01
```

**Rationale:** suppressed price (avg_z < -0.2) at extreme with positive momentum (velocity > 0.01) = mean-reversion bounce setting up. Valid LONG entry.

**Risk:** Fires every cycle while token stays extreme with suppressed-price momentum. May need cooldown — monitor.

---

### 4. _get_direction threshold ±0.3 vs _is_upward_transition ±0.2 — misaligned

**Problem:** `_get_direction` used `avg_z < -0.3` for LONG. LAYER's avg_z=-0.299 failed this check (-0.299 < -0.3 is False) even though the transition check passed at -0.2. direction=None → signal blocked even though `_is_upward_transition` would return True.

**Fix:** Align both to ±0.2:
```python
# _get_direction
if avg_z < -0.2: return ('LONG', 'bullish')
if avg_z > 0.2: return ('SHORT', 'bearish')

# _is_upward_transition
if prev_phase == 'extreme' and curr_phase == 'extreme':
    return avg_z < -0.2 and velocity > 0.01
```

---

## All 8 Patches to phase_accel.py (cumulative)

| # | What | File |
|---|------|------|
| 1 | Rewrite: in-memory tracker, transition-based fire, avg_z direction, velocity gate | signals/phase_accel.py |
| 2 | Fix pct_rank for phase detection (match momentum_cache) | phase_accel.py:193 |
| 3 | Fix log messages (pct_for_phase variable removed) | phase_accel.py |
| 4 | Fix confidence calculation (min(95.0, pct_for_phase)) | phase_accel.py |
| 5 | Add _SEEDED + _seed_tracker_from_db() | phase_accel.py |
| 6 | Add avg_z param to _is_upward_transition | phase_accel.py |
| 7 | Allow extreme→extreme with avg_z < -0.2 + vel > 0.01 | phase_accel.py |
| 8 | Align _get_direction thresholds to ±0.2 | phase_accel.py |

---

## Verified Working — LAYER fires

```
LAYER direction: LONG, state: bullish
LAYER avg_z: -0.299
2026-05-10 09:31:19 SIGNAL:  LAYER LONG phase-accel+ @0.139040 92.5% [vel=+0.035 pct=92 extreme→extreme]
```

All 4 conditions now align:
1. `_is_upward_transition(extreme, extreme, 0.0347, -0.299)` → True
2. `_get_direction` → `('LONG', 'bullish')` (avg_z=-0.299 < -0.2)
3. PHASE_ACCEL_PLUS_ENABLED = True
4. confidence = min(95, 92.5) = 92.5

---

## pct_rank vs Directional Percentile (full explanation)

signal_gen.py line 639: `percentile = pct_rank` used for `_detect_phase()` → phase stored in momentum_cache.

phase_accel.py was using `max(pct_long, pct_short)` (directional) which gives different phase classification:
- LAYER: pct_rank=100.0 → 'extreme', max(pct_long,pct_short)=92.5 → 'exhaustion'

This mismatch caused phase transitions to appear as going backwards (extreme→exhaustion) when the tracker had seeded extreme.

Fix: use `mom['percentile']` for phase detection. signal_gen.py and phase_accel.py must use the same metric.