# STRK + PROVE SHORT Loss Analysis — 2026-05-24

## What Happened

Both trades entered at 14:18 UTC. Both were SHORT at z-score extremes. Both lost via ATR SL.

| Token | Direction | z-score | Conf | RS Level | Entry Price | PnL |
|-------|-----------|---------|------|---------|-------------|-----|
| STRK | SHORT | -5.777 | 83.8% | r478 | 0.03914 | -1.303% |
| PROVE | SHORT | -4.606 | 82.0% | r478 | 0.26411 | -1.028% |

Price immediately pumped against both for 107 minutes before ATR SL hit.

## Root Cause: _check_divergence() Asymmetry

**Confirmed in `signals/zscore_pump.py` lines 93-153:**

```python
def _check_divergence(prices: list, lookback: int) -> bool:
    ...
    recent_zs = []
    for i in range(spot_lookback, len(closes) + 1):
        chunk = closes[i - spot_lookback:i]
        z = compute_zscore(chunk)
        recent_zs.append(z)
    ...
    peak_z = max(recent_zs)          # ← max, NOT abs(max)
    if peak_z < ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:
        return False  # never got extreme — no divergence possible
```

- `max(recent_zs)` checks only the highest positive z in the spot window
- For STRK (z=-5.777), the spot window showed a steady decline from +0.5 to -5.0 — never crossed +3.5
- So `peak_z = +0.5`, below threshold → divergence check returns False (passes)
- **Negative z never gets scrutinized regardless of magnitude**

## Why These Signals Passed

1. **zscore-pump threshold (3.0)**: Both exceeded it easily (|z|=5.777 and 4.606)
2. **DIVERGENCE_EXTREME_Z (3.5)**: Never crossed on the way down — no divergence trigger
3. **RS level r478**: Passed zbonus check (|z|>2.5 → min_touches=50, level 478 >> 50)
4. **Conf was inflated by RS**: 83-84% conf made entry feel high conviction

## Constants-Only Changes Evaluated

| Constant | Current | Proposed | Helps? |
|----------|---------|----------|--------|
| ZSCORE_PUMP_DIVERGENCE_EXTREME_Z | 3.5 | 2.5 | Partial — catches weaker positive spikes, doesn't fix SHORT path |
| ZSCORE_PUMP_THRESHOLD | 3.0 | 3.5 | **NO** — both exceed 3.5 |
| ZSCORE_PUMP_COOLDOWN_BARS | 5 | 20 | Yes — prevents repeated re-fires into falling knife |
| RS_DECIDER_MIN_TOUCHES | 200 | 300 | Partial — zbonus (|z|>2.5 → min=50) saves r478 |

## What Actually Fixes It

**Code change required** — `_check_divergence()` needs a negative-side check:

```python
# Add symmetric check for SHORT blow-off:
trough_z = min(recent_zs)
if trough_z < -ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:
    # Negative z went extreme — was there recovery?
    trough_idx = min(idx for idx, z in enumerate(recent_zs) if z == trough_z)
    bars_since_trough = len(recent_zs) - 1 - trough_idx
    if bars_since_trough < ZSCORE_PUMP_DIVERGENCE_BARS:
        return False  # still at bottom — not a recovery yet
    # Check for recovery (positive velocity bars)
    pos_vel_bars = 0
    for i in range(trough_idx + 1, len(recent_zs)):
        vel = recent_zs[i] - recent_zs[i - 1]
        if vel > ZSCORE_PUMP_DIVERGENCE_VEL_THD:
            pos_vel_bars += 1
        elif vel < 0:
            pos_vel_bars = 0
    if pos_vel_bars >= ZSCORE_PUMP_DIVERGENCE_BARS:
        return True  # blow-off detected — REJECT signal
```

## Lessons

1. **Asymmetric filters are dangerous** — a check that only fires for +z creates a systematic SHORT blind spot
2. **High |z| is a warning sign, not a confirmation** — z=-5.777 screams exhaustion, not continuation
3. **RS boost inflates conf at exactly the wrong time** — r478 at conf=84% feels strong but level is marginal
4. **Constant tweaks reduce probability but don't close the hole** — code-level fix needed