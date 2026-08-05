# phase_accel Signal — Bug Fix (2026-05-10)

## What happened

The phase_accel signal (`/root/.hermes/scripts/signals/phase_accel.py`) was rewritten to catch LAYER-type monster moves. Original had 4 critical bugs that prevented it from ever firing correctly.

---

## The 4 Bugs

### Bug 1: momentum_state=neutral blocked ALL signals

**Original:**
```python
if momentum_state == 'bullish': direction = 'LONG'
elif momentum_state == 'bearish': direction = 'SHORT'
else: continue  # neutral → SKIP
```

At phase transitions (building→accelerating), momentum_state is often `neutral`. Signal skipped entirely even though phase was transitioning correctly.

**Fix:** Use `avg_z` as primary direction signal:
- avg_z < -0.3 → suppressed price → LONG
- avg_z > 0.3 → elevated price → SHORT
- Fall back to momentum_state only if avg_z is neutral

---

### Bug 2: Only fired in 'accelerating' phase

**Original:**
```python
if phase != 'accelerating': continue  # BLOCKS exhaustion and extreme
```

LAYER trajectory: building(04:30) → accelerating(04:45) → exhaustion(04:55) → extreme(05:05)

Signal only fires in accelerating phase. When LAYER hit exhaustion at 04:55 and extreme at 05:05, signal was silent even though momentum was still clearly bullish.

**Fix:** Fire on TRANSITIONS, not on phases. Allow:
- building → accelerating (classic acceleration)
- accelerating → exhaustion (momentum still building)
- exhaustion → extreme (continued momentum)
- building → exhaustion (fast move, skipped accelerating)

---

### Bug 3: prev_phase read from DB was stale

**Original:** `_get_previous_phase()` read `prev_phase` from `momentum_cache` table via SQLite.

The ON CONFLICT clause in signal_gen.py did write `prev_phase` correctly, but:
- DB round-trip adds latency
- If signal_gen.py hadn't run yet for a token, prev_phase was None
- The `_get_previous_phase` in phase_accel.py was a separate function that could get out of sync

**Fix:** In-memory `_PHASE_TRACKER` dict — updated each cycle, no DB latency:
```python
_PHASE_TRACKER = {}  # token -> prev_phase string

# Each cycle:
prev_phase = _PHASE_TRACKER.get(token, None)
_PHASE_TRACKER[token] = curr_phase  # update for next cycle
```

---

### Bug 4: First-cycle detection was wrong

**Original:** prev_phase=None → signal skipped. But prev_phase=None means "no history yet" which is a valid starting state.

**Fix:** prev_phase=None is still skipped (can't confirm transition without history), but the in-memory tracker ensures prev_phase is set by cycle 2 and correct transitions fire from cycle 3 onward.

---

## Key Constants

```python
# In hermes_constants.py — to enable:
PHASE_ACCEL_ENABLED = True        # was False (blocks inline version in signal_gen.py)
PHASE_ACCEL_PLUS_ENABLED = True  # was True (LONG signals)
PHASE_ACCEL_MINUS_ENABLED = True # was True (SHORT signals)
```

---

## Transition Logic

**LONG (upward transitions):**
```python
def _is_upward_transition(prev_phase, curr_phase, velocity):
    if prev_phase is None: return False
    if velocity < 0.01: return False
    if prev_phase == 'extreme': return False  # terminal peak
    if prev_phase == 'quiet': return False    # too early, A/B zone
    if prev_phase == 'building' and curr_phase == 'accelerating': return True
    if prev_phase == 'building' and curr_phase in ('exhaustion', 'extreme'): return True
    if prev_phase == 'accelerating' and curr_phase in ('exhaustion', 'extreme'): return True
    if prev_phase == 'exhaustion' and curr_phase == 'extreme': return True
    return False
```

**SHORT (downward transitions):**
```python
def _is_downward_transition(prev_phase, curr_phase, velocity):
    if prev_phase is None: return False
    if velocity > -0.01: return False
    if prev_phase == 'quiet': return False
    if prev_phase == 'building': return False
    if prev_phase == 'extreme' and curr_phase in ('exhaustion', 'building'): return True
    if prev_phase == 'exhaustion' and curr_phase in ('accelerating', 'building', 'extreme'): return True
    if prev_phase == 'accelerating' and curr_phase in ('building', 'exhaustion', 'extreme'): return True
    return False
```

---

## LAYER Test Results

```
04:45 building→accelerating vel=+0.030 up=True(✓) down=False(✓)  ← LAYER entry here
04:55 accelerating→exhaustion vel=+0.040 up=True(✓) down=False(✓)
05:05 exhaustion→extreme vel=+0.030 up=True(✓) down=False(✓)
quiet→building vel=+0.020 — NO FIRE (correct, too early)
extreme→None vel=-0.020 — NO UPWARD (correct, reversal)
```

---

## Files

- Rewritten: `/root/.hermes/scripts/signals/phase_accel.py`
- Enable flag: `hermes_constants.py:430` — `PHASE_ACCEL_ENABLED = True`
- Plan doc: `/var/www/hermes/plans/signal-quality-plan.md` (item #5)

---

## Related

- accel-300+ signal: `references/accel-300-timing-fix-2026-05-10.md`
- LAYER trade analysis: `references/accel-rs-touch-count-pnl-2026-05-10.md`