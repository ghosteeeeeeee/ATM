# Weather Vane v2 — Autopilot-Inspired Improvements

**Date:** 2026-08-13
**Status:** PROPOSED
**Based on:** autopilot-mechanics PID control theory

---

## Problem with Current Weather Vane (v1)

The current system has a binary threshold: 3 losses in 5 trades → suppress, then ages out → unsuppress. This creates two issues:

1. **Thrashing**: If losses hover around the trigger point, the vane toggles on/off every compaction round. Each toggle changes signal scoring, which changes which signals enter, which changes outcomes — a feedback loop.

2. **Blind to acceleration**: 2 losses in 3 trades (rapid deterioration) is treated the same as 2 losses in 10 trades (slow bleed). The vane can't tell the difference.

3. **No early warning**: By the time 3 losses hit, the damage is done. A warning at 2 losses would let the system tighten stops earlier.

---

## Improvement 1: Hysteresis (Dead Zone)

**Concept from autopilot:** A dead zone prevents oscillation. The autopilot doesn't correct every 0.1° heading error — it allows a range where no correction happens. This prevents the rudder from constantly moving back and forth.

**Current behavior (thrashing):**
```
Trade 1: LOSS  → 1/5 losses (20% WR) → no trigger
Trade 2: LOSS  → 2/5 losses (40% WR) → no trigger
Trade 3: LOSS  → 3/5 losses (60% WR) → TRIGGER (0.7x penalty)
Trade 4: WIN   → 2/5 losses (60% WR) → still triggered (3 losses in window)
Trade 5: WIN   → 1/5 losses (80% WR) → still triggered (2 losses in window)
Trade 6: LOSS  → 2/5 losses (60% WR) → still triggered
Trade 7: WIN   → 1/5 losses (80% WR) → UNSUPPRESSED (losses aged out)
Trade 8: LOSS  → 1/5 losses (80% WR) → not triggered
Trade 9: LOSS  → 2/5 losses (60% WR) → not triggered
Trade 10: LOSS → 3/5 losses (60% WR) → TRIGGER AGAIN (oscillation!)
```

**Improved behavior (hysteresis):**
```
Trade 1-3: 3 losses → TRIGGER (activate suppression)
Trade 4-7: mixed results → STAY SUPPRESSED (don't unsuppress until WR > 50%)
Trade 8-10: 3 wins → WR hits 60% → UNSUPPRESS (recovery confirmed)
```

**Implementation:**
```python
# Two separate thresholds — enter and exit are different
DIRECTIONAL_OUTCOME_TRIGGER_THRESHOLD = 3    # losses to ACTIVATE suppression
DIRECTIONAL_OUTCOME_EXIT_WR = 50             # WR% required to DEACTIVATE suppression

# In _score_signal():
if currently_suppressed:
    # Only unsuppress if WR recovers above exit threshold
    if wr >= DIRECTIONAL_OUTCOME_EXIT_WR:
        dir_outcome_mult = 1.0  # unsuppress
    else:
        dir_outcome_mult = DIRECTIONAL_OUTCOME_PENALTY  # stay suppressed
else:
    # Not suppressed — check if we should trigger
    if losses >= DIRECTIONAL_OUTCOME_TRIGGER_THRESHOLD:
        dir_outcome_mult = DIRECTIONAL_OUTCOME_PENALTY  # suppress
```

**State tracking:** Need a lightweight state file or DB column to track which directions are currently suppressed. Options:
- `signal_outcomes` table: add `suppressed_directions` column
- New file: `data/weather_vane_state.json` with `{"SHORT": true, "LONG": false}`
- In-memory: recompute each compaction round from outcomes (current approach — simpler)

**Recommended:** Recompute from outcomes each round. The "currently suppressed" state is just: "does the current window meet trigger conditions AND WR < exit threshold?" No state file needed.

**Params:**
```python
DIRECTIONAL_OUTCOME_TRIGGER_THRESHOLD = 3    # losses to activate
DIRECTIONAL_OUTCOME_EXIT_WR = 50             # WR% to deactivate
```

---

## Improvement 2: Derivative (Acceleration Detection)

**Concept from autopilot:** The D term detects the RATE of change. If the boat is turning fast, the autopilot applies opposite rudder aggressively. If turning slowly, gentle correction.

**Current v1:** Doesn't distinguish between 3 losses in 5 trades vs 3 losses in 10 trades. Both trigger the same penalty.

**v2 with derivative:** Detect how fast losses are accumulating.

**Metric: Loss Velocity**
```
loss_velocity = losses_in_window / total_in_window
```

- `loss_velocity = 0.6` (3/5) → fast deterioration → STRONG penalty
- `loss_velocity = 0.3` (3/10) → slow bleed → MILD penalty
- `loss_velocity = 1.0` (5/5) → catastrophic → HARD BLOCK (not just penalty)

**Implementation:**
```python
# Tiered response based on loss velocity
loss_velocity = losses / total if total > 0 else 0

if loss_velocity >= 0.8:        # 4+ losses in 5 trades → catastrophic
    dir_outcome_mult = 0.0      # HARD BLOCK — no trade in this direction
elif loss_velocity >= 0.6:      # 3 losses in 5 trades → severe
    dir_outcome_mult = 0.5      # strong penalty
elif loss_velocity >= 0.4:      # 2 losses in 5 trades → moderate
    dir_outcome_mult = 0.7      # mild penalty (current default)
else:
    dir_outcome_mult = 1.0      # normal
```

**Params:**
```python
DIRECTIONAL_OUTCOME_VELOCITY_TIERS = {
    0.8: 0.0,   # catastrophic → hard block
    0.6: 0.5,   # severe → strong penalty
    0.4: 0.7,   # moderate → mild penalty
    0.0: 1.0,   # normal → no penalty
}
```

---

## Improvement 3: Integral (Cumulative Loss Tracking)

**Concept from autopilot:** The I term tracks accumulated error over time. Even if each individual error is small, the integral grows — triggering correction before the system drifts too far.

**Current v1:** Only looks at the last 5 trades in 30 minutes. Ignores longer-term patterns.

**v2 with integral:** Track total losses over a longer window (4 hours) to catch slow bleeds that don't hit the 5-trade threshold.

**Example:** A system loses 1 trade every hour for 4 hours. Each loss ages out of the 30-minute window before the next one arrives. The Weather Vane never triggers. But 4 losses in 4 hours is a clear problem.

**Implementation:**
```python
# Long window: 4 hours, lower threshold
INTEGRAL_WINDOW = 240           # minutes
INTEGRAL_THRESHOLD = 5          # losses in long window
INTEGRAL_PENALTY = 0.8          # milder than short-window penalty

# In _score_signal():
long_losses, long_total, long_wr = get_directional_outcome_long(direction)
if long_total >= INTEGRAL_THRESHOLD and long_losses >= INTEGRAL_THRESHOLD:
    # Slow bleed detected — mild suppression
    dir_outcome_mult = min(dir_outcome_mult, INTEGRAL_PENALTY)
```

**Params:**
```python
DIRECTIONAL_OUTCOME_INTEGRAL_ENABLED = True
DIRECTIONAL_OUTCOME_INTEGRAL_WINDOW = 240     # minutes (4 hours)
DIRECTIONAL_OUTCOME_INTEGRAL_THRESHOLD = 5    # losses to trigger
DIRECTIONAL_OUTCOME_INTEGRAL_PENALTY = 0.8    # milder than short-window
```

---

## Improvement 4: Off-Course Alarm (Early Warning)

**Concept from autopilot:** Off-course alarm alerts when heading deviates beyond a threshold, BEFORE the situation becomes critical.

**Current v1:** Silent until 3 losses hit. No warning.

**v2 with alarm:** Log a warning at 2 losses (pre-trigger), so the human can monitor.

**Implementation:**
```python
# In _score_signal():
if losses == DIRECTIONAL_OUTCOME_TRIGGER_THRESHOLD - 1:  # 2 losses (one before trigger)
    log(f"  ⚠️ [WEATHER-VANE] {token} {direction}: "
        f"{losses}/{total} losses — approaching trigger threshold")
    # No penalty yet — just a warning
```

This is a logging-only improvement — no param changes needed.

---

## Improvement 5: Gain Scheduling (Volatility-Adaptive)

**Concept from autopilot:** Gain scheduling adjusts PID gains based on sea state. Calm water = higher gains (responsive). Heavy seas = lower gains (slower, avoid over-correction).

**Application to Weather Vane:** In high-volatility markets, losses happen faster and are more noise. In low-volatility markets, losses are more meaningful.

**Implementation:**
```python
# Check market volatility (ATR or speed percentile)
# High volatility → widen window, raise threshold (less sensitive)
# Low volatility → tighten window, lower threshold (more sensitive)

from speed_tracker import get_market_speed_percentile
market_speed = get_market_speed_percentile()  # 0-100

if market_speed >= 70:  # high volatility
    effective_window = DIRECTIONAL_OUTCOME_WINDOW + 2  # 7 instead of 5
    effective_threshold = DIRECTIONAL_OUTCOME_LOSS_THRESHOLD + 1  # 4 instead of 3
elif market_speed <= 30:  # low volatility
    effective_window = DIRECTIONAL_OUTCOME_WINDOW - 1  # 4 instead of 5
    effective_threshold = DIRECTIONAL_OUTCOME_LOSS_THRESHOLD  # stays 3
else:
    effective_window = DIRECTIONAL_OUTCOME_WINDOW
    effective_threshold = DIRECTIONAL_OUTCOME_LOSS_THRESHOLD
```

**Params:**
```python
DIRECTIONAL_OUTCOME_GAIN_SCHEDULING = True
DIRECTIONAL_OUTCOME_HIGH_VOL_WINDOW_ADJ = 2    # add 2 to window in high vol
DIRECTIONAL_OUTCOME_HIGH_VOL_THRESHOLD_ADJ = 1 # add 1 to threshold in high vol
DIRECTIONAL_OUTCOME_LOW_VOL_WINDOW_ADJ = -1    # subtract 1 from window in low vol
```

---

## Improvement 6: Watchdog (Self-Monitoring)

**Concept from autopilot:** Watchdog timer restarts the system if software hangs. Catches silent failures.

**Application:** If Weather Vane hasn't triggered in 24 hours AND there have been 50+ trades, something might be wrong (function not running, DB query failing silently).

**Implementation:**
```python
# In main compaction loop, track last trigger time
# If >24h since last trigger and >50 trades processed, log warning
WEATHER_VANE_WATCHDOG_HOURS = 24
WEATHER_VANE_WATCHDOG_MIN_TRADES = 50
```

---

## Priority Order

| # | Improvement | Impact | Complexity | Priority |
|---|-------------|--------|------------|----------|
| 1 | Hysteresis | HIGH — prevents thrashing | LOW — threshold logic | **NOW** |
| 2 | Derivative | HIGH — tiered response | LOW — velocity calc | **NOW** |
| 3 | Integral | MEDIUM — catches slow bleeds | MEDIUM — second query | **NEXT** |
| 4 | Off-course alarm | LOW — logging only | LOW — one log line | **NOW** |
| 5 | Gain scheduling | MEDIUM — adapts to volatility | MEDIUM — speed lookup | **LATER** |
| 6 | Watchdog | LOW — catches silent failures | LOW — time tracking | **LATER** |

## Implementation Plan

### Phase 1 (Now): Hysteresis + Derivative + Alarm
- Add `DIRECTIONAL_OUTCOME_EXIT_WR = 50` to hermes_constants.py
- Add velocity tier logic to `_score_signal()`
- Add warning log at pre-trigger threshold
- Update `get_directional_outcome()` to return loss_velocity

### Phase 2 (Next): Integral
- Add `get_directional_outcome_long()` with 240-minute window
- Integrate into `_score_signal()` as secondary check

### Phase 3 (Later): Gain Scheduling + Watchdog
- Add market speed lookup
- Add time-since-last-trigger tracking

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add v2 params |
| `scripts/signal_compactor.py` | Update `get_directional_outcome()` + `_score_signal()` |
