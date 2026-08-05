# zscore-pump Divergence — SHORT is Unprotected (2026-05-24)

## The Bug

`_check_divergence()` in `signals/zscore_pump.py` (line 129):

```python
peak_z = max(recent_zs)
if peak_z < ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:  # only fires for POSITIVE z
    return False  # never got extreme — no divergence possible
```

**Effect:** For a **negative** z-score (SHORT signal), this check NEVER fires. A z=-5.63 on SHORT passes straight through without any divergence examination.

## Real Examples from 2026-05-24

| Token | Signal | z-score | Outcome |
|-------|--------|---------|---------|
| GRIFFAIN SHORT | zscore-pump- | -4.81 | Entered at blow-off bottom, price reversed up → -0.77% |
| GALA SHORT | zscore-pump- | -5.63 | Entered at z=-5.63, recovered to -4.047 in 1 bar → -1.67% |
| MORPHO LONG | zscore-pump+ | +5.43 | Entered at z=+5.43, mean-reverted → -0.91% |
| ME SHORT | zscore-pump- | -4.65 | Entered at z=-4.65, recovered → -0.28% |

**Pattern:** All four are blow-off moves at extreme z. LONG gets divergence protection. SHORT has NONE.

## Why the Check Fails for SHORT

The divergence check tracks the **highest** z-score via `max()`. For SHORT, we need the **lowest** (most negative):

```python
# Current — only finds peak (highest), good for LONG
peak_z = max(recent_zs)  # z=-5.63 → peak_z=2.0 (higher positive z existed earlier)

# What SHORT needs:
nadir_z = min(recent_zs)  # z=-5.63 → nadir_z=-5.63
```

When GALA fires at z=-5.63, there may have been z=+2.0 earlier, so `peak_z=+2.0` < DIVERGENCE_EXTREME_Z=3.5 → check returns False → no block.

## Proposed Fix (Code Change)

In `signals/zscore_pump.py`, add SHORT-specific divergence check after existing LONG logic:

```python
# SHORT divergence: z was extremely negative (blow-off) then RECOVERING
if direction == 'SHORT':
    nadir_z = min(recent_zs)
    if nadir_z < -ZSCORE_PUMP_DIVERGENCE_SHORT_Z:  # new constant, e.g. 3.0
        nadir_idx = min(i for i, z in enumerate(recent_zs) if z == nadir_z)
        bars_since_nadir = len(recent_zs) - 1 - nadir_idx
        if bars_since_nadir >= ZSCORE_PUMP_DIVERGENCE_BARS:
            pos_vel_bars = 0
            for i in range(nadir_idx + 1, len(recent_zs)):
                vel = recent_zs[i] - recent_zs[i - 1]
                if vel > 0:
                    pos_vel_bars += 1
                else:
                    pos_vel_bars = 0
            if pos_vel_bars >= ZSCORE_PUMP_DIVERGENCE_BARS:
                return True  # recovery = reversal bounce → REJECT SHORT
```

## Constants to Add in hermes_constants.py

```python
ZSCORE_PUMP_DIVERGENCE_SHORT_Z = 3.0  # z below -3.0 = blow-off bottom on SHORT
```

## Reference

- `signals/zscore_pump.py` line 93-153: `_check_divergence()` function
- `signals/zscore_pump.py` line 261-271: where `_check_divergence()` is called