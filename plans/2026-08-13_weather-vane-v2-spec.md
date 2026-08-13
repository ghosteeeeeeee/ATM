# Weather Vane v2 — Autopilot-Inspired Improvements

**Date:** 2026-08-13
**Status:** IMPLEMENTED (all active layers deployed)
**Based on:** autopilot-mechanics PID control theory

---

## CEO Verdict Summary

| # | Proposal | CEO Decision | Status |
|---|----------|-------------|--------|
| 1 | Hysteresis | APPROVE (45% WR exit) | ✅ DONE |
| 2 | Off-course alarm | APPROVE | ✅ DONE |
| 3 | Derivative (velocity tiers) | ALREADY LIVE | ✅ DONE |
| 4 | Integral (cumulative) | ALREADY LIVE | ✅ DONE |
| 5 | Gain scheduling | SKIP (YAGNI) | — |
| 6 | Watchdog | SKIP (YAGNI) | — |
| 7 | Time-weighted outcomes | REJECT (redundant) | — |
| 8 | Direction Lock | APPROVE | NEXT |
| 9 | Opposite direction boost | REJECT (regime_mult covers) | — |
| 10 | Trade size scaling | REJECT (too invasive) | — |

**Bug fixed:** velocity_mult defaulted to 1.0 (no-op) when velocity tiers disabled — fixed to DIRECTIONAL_OUTCOME_PENALTY (0.7x).

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

---

## Additional Proposals (2026-08-13)

### Proposal 7: Time-Weighted Outcomes
**Concept:** Recent losses count more than older losses. A loss 2 minutes ago is more meaningful than one 28 minutes ago.

**Current:** All trades in the window are weighted equally (5 trades, equal weight).

**Proposed:** Weight each trade by recency:
```
weight = 1.0 - (age_minutes / TIME_WINDOW)
```
- Loss at minute 0: weight = 1.0
- Loss at minute 15: weight = 0.5
- Loss at minute 30: weight = 0.0

Weighted loss score = sum(loss × weight) / sum(weights)

This means a single recent loss has more impact than multiple old losses. The vane responds faster to fresh deterioration.

**Impact:** Faster trigger on new loss clusters. Slower recovery when losses are old.

**Complexity:** MEDIUM — needs weighted calculation in `get_directional_outcome()`.

---

### Proposal 8: Direction Lock
**Concept:** After severe suppression (5/5 losses or hard block), lock the direction for N minutes regardless of recovery. Prevents re-entry during a clear bad streak.

**Current:** Even after 5/5 losses, if 2 wins come in and WR recovers, the vane unsuppresses immediately.

**Proposed:** After catastrophic loss (loss_velocity >= 0.8, i.e., 4+/5 losses), lock the direction for `LOCK_MINUTES` (e.g., 30 minutes). No unsuppression during lock period.

**Implementation:**
```python
if loss_velocity >= 0.8:  # 4+ losses in 5
    lock_until = now + LOCK_MINUTES
    # Check if lock has expired before allowing unsuppression
```

**Impact:** Prevents re-entering a direction that just had a catastrophic failure. Forces a cooling-off period.

**Complexity:** LOW — needs timestamp tracking (DB or file).

---

### Proposal 9: Opposite Direction Boost
**Concept:** When one direction is suppressed, boost the opposite direction. Markets are zero-sum — if SHORT is losing, LONG is likely winning.

**Current:** Weather Vane only penalizes the losing direction. The winning direction gets no benefit.

**Proposed:** When SHORT is suppressed, apply a small boost to LONG signals (and vice versa).

**Implementation:**
```python
# In _score_signal():
if dir_outcome_mult < 1.0:
    # This direction is suppressed — check if opposite is healthy
    opp_losses, opp_total, opp_wr = get_directional_outcome(opp_direction)
    if opp_total >= MIN_TRADES and opp_wr >= 50:
        opp_boost = 1.1  # +10% boost to opposite direction
```

**Impact:** Shifts capital toward the winning direction during regime shifts. Could amplify gains when the system correctly identifies the winning side.

**Risk:** If both directions are losing (choppy market), both get boosted → more trades in a bad market. Need a gate: only boost if opposite WR >= 50%.

**Complexity:** LOW — one extra `get_directional_outcome()` call per signal.

---

### Proposal 10: Trade Size Scaling
**Concept:** Instead of just scoring penalties, scale actual position size. When suppressed, reduce trade size by 50% instead of blocking entirely.

**Current:** Suppression = 0.7x score penalty → may or may not block the signal (depends on other factors).

**Proposed:** When suppressed, also reduce `amount_usdt` by 50%. Keeps some exposure but limits damage.

**Implementation:** This would require changes in `decider_run.py` or `position_manager.py` to read the weather vane state and adjust trade size. More invasive than scoring-only changes.

**Impact:** Instead of all-or-nothing (block vs allow), graduated response. Reduces losses on suppressed directions without eliminating all opportunity.

**Complexity:** HIGH — crosses into position sizing, needs integration with execution layer.

**Recommendation:** Defer — too invasive for now. Score-only approach is cleaner.

---

## Updated Priority Table

| # | Proposal | Impact | Complexity | CEO Decision | Status |
|---|----------|--------|------------|-------------|--------|
| 1 | Hysteresis | HIGH | LOW | APPROVE (45% WR exit) | **DONE** |
| 2 | Off-course alarm | LOW | LOW | APPROVE | **DONE** |
| 3 | Derivative (acceleration) | HIGH | LOW | ALREADY LIVE | **DONE** |
| 4 | Integral (cumulative) | MEDIUM | MEDIUM | ALREADY LIVE | **DONE** |
| 5 | Gain scheduling | MEDIUM | MEDIUM | SKIP (YAGNI) | — |
| 6 | Watchdog | LOW | LOW | SKIP (YAGNI) | — |
| 7 | Time-weighted outcomes | MEDIUM | MEDIUM | REJECT (redundant) | — |
| 8 | Direction lock | MEDIUM | LOW | APPROVE | **NEXT** |
| 9 | Opposite direction boost | MEDIUM | LOW | REJECT (regime_mult covers) | — |
| 10 | Trade size scaling | HIGH | HIGH | REJECT (too invasive) | — |

## CEO Reasoning

**Proposal 7 (Time-weighted) — REJECT:** Derivative already captures acceleration. Velocity = losses/total IS a recency proxy. Redundant.

**Proposal 9 (Opposite boost) — REJECT:** Choppy markets double-boost both directions. +10% marginal. Regime_mult already does +50%/-50%.

**Proposal 10 (Size scaling) — REJECT:** Crosses into position sizing layer (decider_run/position_manager). High complexity. Velocity tiers already do graduated response (0.7x→0.5x→0.0x).

**Proposal 5 (Gain scheduling) — SKIP:** Velocity tiers already graduate severity. Regime_mult handles market conditions. YAGNI.

**Proposal 6 (Watchdog) — SKIP:** Silent failures rare with systemd. Add if needed later. YAGNI.

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add v2 params |
| `scripts/signal_compactor.py` | Update `get_directional_outcome()` + `_score_signal()` |
