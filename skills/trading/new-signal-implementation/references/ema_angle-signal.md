# EMA300 Angle Signal — Implementation Notes

## Overview

Angle = `arctan(slope_20 / ema_val)` in degrees. Signed — distinguishes uptrend from downtrend.

- `+angle` = price above EMA, trending up
- `-angle` = price below EMA, trending down
- `0°` = price at EMA (flat)

LONG: angle >= p75 (75th percentile of angle distribution) AND speed > 0.
SHORT: angle <= p25 (25th percentile) AND speed < 0.

Fires once per token+direction per cooldown (15 min default), not every minute while above threshold.

## Signed Angle — Critical Fix

**Bug:** Original code used `abs(slope)` in angle calculation:
```python
# WRONG — all angles positive, no sign distinction
angle = math.atan(abs(slope_n) / ema_val) * (180 / math.pi)
```

**Fix:**
```python
# CORRECT — signed angle distinguishes uptrend from downtrend
angle = math.atan(slope_n / ema_val) * (180 / math.pi)
```

Without the fix: all angles positive, LONG always fires in bull markets, SHORT never fires. With the fix: SHORT fires when angle is deeply negative (below p25) and still falling — catches beginning of down moves.

## Cooldown — Two Layers

1. **In-memory** (`_last_signal_ts` dict): fast, per-run dedup
2. **DB** (`get_cooldown()`): shared across signal runs

Both use `EMA_ANGLE_COOLDOWN_MIN = 15` minutes. The signal will not re-fire for the same token+direction within the cooldown window even if angle stays elevated — must dip below threshold then cross back.

## Confidence Scoring

Base: 62. Max bonuses:
- Steepness bonus: up to 15 (angle in extreme territory)
- Momentum bonus: up to 10 (angle_speed very high)
- Recency bonus: up to 8 (recent crossing)

Max theoretical: 95, capped at 92 in signal_schema.

## Post-Entry Win Rate Analysis (2026-05-14)

Universe-wide: 187 LONG, 188 SHORT entries per 48h.

| Direction | 15-bar WR | 30-bar WR | Falling Knife Rate |
|-----------|-----------|-----------|---------------------|
| LONG      | 95.8%     | ~same     | 15.9%              |
| SHORT     | 95.2%     | ~same     | 12.2%              |

Conclusion: signal catches beginning of moves, not end. Low false-start rate.

## Files

- `signals/ema_angle.py` — 412 lines, main detection engine
- `signals/__init__.py` — registered in signal registry
- `signal_schema.py` — Layer 2 kill-switch for `ema-angle+`, `ema-angle-`
- `hermes_constants.py` — all EMA_ANGLE_* constants (lines ~497-517)

## Testing

```python
# Verify signed angle fires correctly
import os
os.environ['EMA_ANGLE_DEBUG'] = '1'
import signals.ema_angle as ema_angle
result = ema_angle.scan_ema_angle_signals()
# Should see both ema-angle+ (LONG) and ema-angle- (SHORT) signals
```

```bash
# Check signals written to DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, confidence, created_at \
   FROM signals WHERE source LIKE 'ema-angle%' ORDER BY created_at DESC LIMIT 10;"
```

## Constants Summary

| Constant | Value | Purpose |
|----------|-------|---------|
| EMA_ANGLE_LOOKBACK | 500 | candles for EMA300 + angle history |
| EMA_ANGLE_SLOPE_PERIOD | 20 | bars for slope calculation |
| EMA_ANGLE_SPEED_PERIOD | 10 | bars for angle speed (rolling diff) |
| EMA_ANGLE_PERCENTILE_LONG | 75 | p75 threshold for LONG |
| EMA_ANGLE_PERCENTILE_SHORT | 25 | p25 threshold for SHORT |
| EMA_ANGLE_MIN_SPEED | 5e-05 | minimum angle_speed to confirm direction |
| EMA_ANGLE_MIN_BARS | 310 | minimum bars for EMA300 + angle |
| EMA_ANGLE_COOLDOWN_MIN | 15 | minutes between signals |
| EMA_ANGLE_CONFIDENCE_BASE | 62 | base confidence |