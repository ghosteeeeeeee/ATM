# EMA300 Angle Signal — Final Implementation (2026-05-16)

## Radian Scale — T's Preference

T speaks in **radians via arctan**: "0.5-1.0 radians via arctan" means the angle whose arctan gives 0.5 to 1.0.
- `arctan(0.5)` ≈ 28.6° ≈ **30°** (STEEP threshold for LONG)
- `arctan(1.0)` = 45° (CEILING — don't fire past this)

**Angle formula (final):**
```python
delta_20 = closes[i] - closes[i - 20]
angle = math.atan(delta_20 / closes[i])  # RADIANS, not degrees
```

The old formula `arctan(slope_n / ema_val)` was orders of magnitude too small — a 20% move gives ~0.20 rad (11°), not 45°. With the old formula, 45° requires price to double in 20 bars (impossible). The new formula makes 45° achievable at ~100% move over 20 bars.

**Radian equivalent table:**

| arctan input | angle (rad) | angle (degrees) |
|---|---|---|
| 0.01 | 0.010 rad | 0.57° |
| 0.05 | 0.050 rad | 2.86° |
| 0.10 | 0.100 rad | 5.71° |
| 0.20 | 0.197 rad | 11.31° |
| 0.50 | 0.463 rad | 26.57° |
| **0.5 (STEEP)** | **0.5 rad** | **28.6°** ≈ 30° |
| **1.0 (CEILING)** | **1.0 rad** | **45°** |

## Constants (hermes_constants.py, updated 2026-05-16)

```python
# ── EMA300 Angle Signal ────────────────────────────────────────────────────────
# LONG (ema-angle+): flat → steep transition using arctan(Δprice_20 / price) in RADIANS
#   STEEP threshold = 0.5 rad (30°)  |  CEILING = 1.0 rad (45°)  |  FLAT_WINDOW = 10 bars
#   was_flat: all angles < 0.5 rad for last FLAT_WINDOW bars
#   is_steep: angle >= 0.5 rad AND < 1.0 rad
#   accelerating: angle_speed > EMA_ANGLE_MIN_SPEED
#
# SHORT (ema-angle-): angle <= p25 (25th percentile) with negative speed — unchanged
#
EMA_ANGLE_STEEP_THRESHOLD_RAD = 0.5   # 30° — minimum angle for LONG steep territory
EMA_ANGLE_CEILING_RAD         = 1.0   # 45° — ceiling, don't fire into parabolic
EMA_ANGLE_FLAT_WINDOW         = 10    # bars to check was_flat before crossing
EMA_ANGLE_MIN_SPEED          = 0.001   # radians/bar (raised from 0.00005)
```

## LONG Guard (final code in ema_angle.py)

```python
price_above_ema = closes[-1] > ema300[-1]

preflat_start = max(speed_period, latest_idx - EMA_ANGLE_FLAT_WINDOW)
preflat_angles = angles[preflat_start:latest_idx]
was_flat     = all(a < EMA_ANGLE_STEEP_THRESHOLD_RAD for a in preflat_angles)
is_steep     = latest_angle >= EMA_ANGLE_STEEP_THRESHOLD_RAD and latest_angle < EMA_ANGLE_CEILING_RAD
crossover    = all(angles[j] < EMA_ANGLE_STEEP_THRESHOLD_RAD for j in range(preflat_start, latest_idx))
accelerating = latest_speed > EMA_ANGLE_MIN_SPEED

_log(f"[ema-angle DEBUG] {token}: close={closes[-1]:.6f} ema300={ema300[-1]:.6f} "
     f"above={price_above_ema} angle={latest_angle:.6f} rad ({math.degrees(latest_angle):.2f}°) "
     f"speed={latest_speed:.6f} was_flat={was_flat} is_steep={is_steep}")

if EMA_ANGLE_PLUS_ENABLED and price_above_ema and was_flat and is_steep and crossover and accelerating:
    # signal fires — confidence calc unchanged
```

Signal output includes `angle_radians` and `angle_degrees` fields for T's reference.

## T's Design Rules (2026-05-16)

**Reference coin: PURR** — flat-to-45° EMA300 angle transition ~48h ago (May 14, 2026 ~03:00 EST).

**LONG (ema-angle+) — flat → steep transition:**
1. Price must be above EMA300
2. Angle was FLAT (< 0.5 rad) for last 10 bars
3. Angle is now STEEP (>= 0.5 rad AND < 1.0 rad)
4. Angle crossed 0.5 rad (was below, now above — the actual transition)
5. Angle speed > 0 (still accelerating)

**SHORT (ema-angle-):** unchanged — `angle <= p25` with negative speed on the same radian scale.

**Confluence rule:** ema-angle is NEVER solo — always needs another direction-aligned signal.

## T's Angle Communication Preference

- T says "between 30-45 degrees, that is 0.5-1.0 radians via arctan" → translate to `0.5 rad <= angle < 1.0 rad`
- Always output both `angle_radians` and `angle_degrees` in debug/log for T's verification
- PURR is the reference coin for flat-to-45° EMA300 angle pattern

## Files Modified (2026-05-16)

- `/root/.hermes/scripts/signals/ema_angle.py` — angle formula + LONG guard updated
- `/root/.hermes/scripts/hermes_constants.py` — new constants added, docstring updated
- SHORTS: unchanged, still uses p25 percentile on the same radian scale