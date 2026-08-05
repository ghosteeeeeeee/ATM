# EMA-Angle Crossover Guard Fix — Bug #20 (2026-05-15)

## Problem

LONG fires on every bar where `angle >= p75` — even during sustained uptrends where the angle has been above p75 for 20+ consecutive bars. SHORTS do not have this problem.

**Asymmetric behavior:**
- `angle >= p75` with near-zero/negative p75 = fires on ANY positive angle (even micro-jitter) → over-fires LONG
- `angle <= p25` with negative p25 = fires only when angle is deeply negative → naturally filters SHORT

**CHIP example:** 500-bar p75 = -0.000319°. Any positive angle (even 0.000047°) exceeds it → fires. Last 20 bars all above p75 → sustained uptrend, not a fresh crossover.

## Fix

Add crossover guard to LONG block (ema_angle.py ~line 188):

```python
# LONG block conditions (before fix):
if EMA_ANGLE_PLUS_ENABLED and latest_angle > 0 and latest_angle >= p75 and latest_speed > EMA_ANGLE_MIN_SPEED:

# LONG block conditions (after fix):
angle_was_below_p75 = all(angles[j] < p75 for j in range(max(speed_period, latest_idx - 20), latest_idx))

if (EMA_ANGLE_PLUS_ENABLED and latest_angle > 0 and
    latest_angle >= p75 and latest_speed > EMA_ANGLE_MIN_SPEED and
    angle_was_below_p75 and  # ← ADD THIS
    ...):
```

**Crossover guard logic:**
- `was_below = True`: all 20 prior bars below p75 → angle just crossed from flat → **FIRE**
- `was_below = False`: angle has been above p75 for 20+ bars → sustained steep, not fresh → **BLOCK**

## Verification

**PURR 06:21 signal (correctly fires):**
```
angle=0.003926°, p75=0.003931° (2640-bar)
angles[1314:1334]: 0.003032° → 0.003260° → 0.003429° → 0.003596° → 0.003761° — all below p75
was_below=True → FIRE ✓
```

**KLUNC (correctly blocked):**
```
angle=0.009666°, 500-bar p75=0.002771°
Last 20 angles: 0.007161°–0.009666° — all ABOVE p75
was_below=False → BLOCKED ✓
```

**CHIP (correctly blocked):**
```
angle=0.000863°, 500-bar p75=-0.000319°
was_below=False → BLOCKED ✓
```

## Critical Consistency Rule

The `was_below_p75` check must use the SAME p75 as the `angle >= p75` check. Mixing windows produces false negatives:

- 500-bar p75 for threshold + 2640-bar p75 for crossover → was_below=True even when angle already 6x above threshold (PURR 06:21 at 500-bar p75=0.000696°, angle=0.004089°)
- Use ONE window for both → correct behavior

## Why SHORTS Don't Need the Guard

`angle <= p25` with negative p25 requires the angle to be deeply negative. In chop/sideways:
- Near-zero or slightly negative p25 → condition requires angle to go deeply negative → hard to satisfy → naturally blocked
- Sustained downtrend → angle well below p25 → condition satisfied AND was_below is true → fires on first cross

The asymmetric over-firing is a LONG-specific problem.