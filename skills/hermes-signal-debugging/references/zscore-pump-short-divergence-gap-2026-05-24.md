# zscore_pump SHORT Divergence Gap — Bug #20 (2026-05-24)

## Finding

`_check_divergence()` in `signals/zscore_pump.py` (lines 93-153) has **zero SHORT divergence protection**.

The function computes `peak_z = max(recent_zs)` and only checks `peak_z >= ZSCORE_PUMP_DIVERGENCE_EXTREME_Z`.
For a SHORT signal with z=-5.777:

- `recent_zs` contains many negative values AND some positive ones from rolling windows
- `peak_z = max(recent_zs)` = the **least-negative** value in that list, e.g. +0.8
- `peak_z >= 3.5` → almost always False for negative z
- Function returns False at line 130 **without any SHORT analysis**
- Every SHORT signal with z < 0 passes through `_check_divergence()` unexamined

The asymmetry:

| Direction | What it catches | What it misses |
|-----------|----------------|----------------|
| LONG | z was +4, now crashing toward 0 = reversal trap | z was +4, stalling but not crashing |
| SHORT | **nothing** | z was -5, now recovering toward 0 = blow-off bottom reversal |

## The Fix (code change, not constants)

**Step 1 — Add `direction` parameter to `_check_divergence()`:**

```python
def _check_divergence(prices: list, lookback: int, direction: str) -> bool:
```

**Step 2 — In the function, compute both peak and nadir:**

```python
peak_z = max(recent_zs)
nadir_z = min(recent_zs)
```

**Step 3 — Mirror the SHORT logic:**

```python
# LONG divergence: z was extremely positive, now crashing
if peak_z >= ZSCORE_PUMP_DIVERGENCE_EXTREME_Z and direction == 'LONG':
    peak_idx = max(idx for idx, z in enumerate(recent_zs) if z == peak_z)
    bars_since_peak = len(recent_zs) - 1 - peak_idx
    if bars_since_peak < ZSCORE_PUMP_DIVERGENCE_BARS:
        return False
    neg_vel_bars = 0
    for i in range(peak_idx + 1, len(recent_zs)):
        vel = recent_zs[i] - recent_zs[i - 1]
        if vel < ZSCORE_PUMP_DIVERGENCE_VEL_THD:
            neg_vel_bars += 1
        elif vel > 0:
            neg_vel_bars = 0
    if neg_vel_bars >= ZSCORE_PUMP_DIVERGENCE_BARS:
        return True  # reject

# SHORT divergence: z was extremely negative (blow-off bottom), now recovering
if nadir_z <= -ZSCORE_PUMP_DIVERGENCE_EXTREME_Z and direction == 'SHORT':
    nadir_idx = min(idx for idx, z in enumerate(recent_zs) if z == nadir_z)
    bars_since_nadir = len(recent_zs) - 1 - nadir_idx
    if bars_since_nadir < ZSCORE_PUMP_DIVERGENCE_BARS:
        return False  # still near nadir, not yet recovering
    pos_vel_bars = 0
    for i in range(nadir_idx + 1, len(recent_zs)):
        vel = recent_zs[i] - recent_zs[i - 1]
        if vel > -ZSCORE_PUMP_DIVERGENCE_VEL_THD:  # z rising (less negative)
            pos_vel_bars += 1
        elif vel < 0:
            pos_vel_bars = 0  # reset if z keeps falling
    if pos_vel_bars >= ZSCORE_PUMP_DIVERGENCE_BARS:
        return True  # reject — SHORT divergence detected
```

**Step 4 — Update the call site (line 270):**

```python
# Before:
if _check_divergence(prices, lookback):

# After:
if _check_divergence(prices, lookback, direction):
```

## Line Reference

- `signals/zscore_pump.py` lines 93-153: `_check_divergence()` function
- `signals/zscore_pump.py` line 270: call site (no direction passed)
- `signals/zscore_pump.py` lines 258-273: divergence gate in `detect_zscore_pump()`

## Related

- `zscore-pump-extreme-z-losses-2026-05-24.md` — extreme z-losses pattern (blow-off tops/bottoms)
- `reversal-trap-pattern-2026-05-21.md` — same pattern, LONG-side focus