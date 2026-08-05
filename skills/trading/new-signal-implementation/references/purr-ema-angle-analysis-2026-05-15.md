# ema_angle PURR Analysis — 2026-05-15

## PURR Data Summary

- **Source:** candles_1m (17,361 rows, all is_closed=0, ts range 1777396440–1778878800)
- **Timeframe:** 2026-04-28 to 2026-05-15
- **Note:** PURR has NO data in candles_5m, candles_15m, candles_1h, candles_4h — only 1m
- **Signal inspiration:** T's reference — dropped → flat EMA → went straight up ~36-40 hours ago

## PURR Angle Trace (2026-04-28)

```
full-history p75 = 0.002046°
full-history p25 = -0.002472°

First angle crossing (angle >= p75): 2026-04-28T23:08:00
  close = 0.06748, ema300 = 0.06709
  slope = 0.00000306/bar, angle = 0.002613°
  EMA slope: UP (ema going up)
  Price above EMA: YES

Signal would fire at angle=0.002613° (6 hours into data)
```

## Current PURR State (2026-05-15 ~21:00 UTC)

```
prices: 500 (most recent)
close range: 0.073391 → 0.069794
EMA300[-1]: 0.070208
latest_angle: -0.000653° (NEGATIVE — EMA still sloping down)
latest_speed: -0.000750 (negative — angle still falling)
price_above_ema: False (0.069794 < 0.070208)
p75 (500-bar): -0.000317°

PURR correctly returns None right now — pullback phase after initial spike
```

## PURR 4 Rules (from T)

1. **EMA300 flat** → angle near 0 then rising (captured by positive angle + positive speed)
2. **Price above EMA300** → `price_above_ema` guard
3. **Angle > threshold** (0.002° or slope equivalent) → `latest_angle >= full_p75` (full_p75=0.002046°)
4. **Price accelerating** (good but not required) → `latest_speed > 0`

## Why PURR Inspires the Fix

PURR's full-history p75 = 0.002046°. The signal should fire when:
- `latest_angle > 0` (positive, not flat/negative)
- `latest_angle >= full_p75` (0.002046°)
- `price_above_ema = True`
- `latest_speed > 0` (angle rising)

## False Fire Tokens (2026-05-15)

| Token | 500-bar p75 | Latest angle | Fires? | Should? |
|-------|------------|--------------|--------|---------|
| CHIP | -0.000319° | 0.000863° | YES | NO |
| MORPHO | -0.000256° | 0.000863° | YES | NO |
| MOVE | -0.000080° | 0.000047° | YES | NO |
| ZK | +0.000002° | 0.000155° | YES | NO |
| BLUR | -0.001124° | 0.000863° | YES | NO |

All have **negative or near-zero 500-bar p75** — the 500-bar window captures only chop, so any micro-green candle exceeds the tiny threshold.

## Working LONGs (borderline/correct)

| Token | 500-bar p75 | Latest angle | Fires? | Verdict |
|-------|------------|--------------|--------|---------|
| KLUNC | +0.004156° | 0.004648° | YES | Correct — p75 is positive and reasonable |
| HEMI | +0.001759° | 0.002038° | YES | Borderline — p75 from 500-bar vs full=0.002625° |
| SAGA | +0.000360° | 0.002471° | YES | Suspicious — p75 very small (0.000360°), angle 7x p75 |

## The Asymmetry That Reveals the Bug

SHORT fires correctly because:
```python
latest_angle < 0 and latest_angle <= p25 and latest_speed < -EMA_ANGLE_MIN_SPEED
```
When p25 is negative (bear market), `angle <= p25` is HARDER to satisfy — requires genuinely steep downward movement.

LONG fires incorrectly because:
```python
latest_angle > 0 and latest_angle >= p75 and latest_speed > EMA_ANGLE_MIN_SPEED
```
When p75 is negative (chop), `angle >= p75` is EASIER to satisfy — any micro-positive angle exceeds a negative threshold.

**The fix is identical logic, not different logic.** Use full-history p75 so the threshold is always anchored to meaningful steepness.