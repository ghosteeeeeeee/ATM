# ema_angle Bugs Found Post-Deployment — 2026-05-15

## Bug #16: Asymmetric ABS_ANGLE_FLOOR on LONG — SHORT Works, LONG Doesn't

**Symptom:** ema_angle fires LONG at flat angles (0.001-0.003°) in choppy/sideways markets. SHORTS are "mostly working" but LONGS fire where they shouldn't.

**Root cause — asymmetric condition in ema_angle.py lines 190-191:**

```python
ABS_ANGLE_FLOOR = 0.003   # hardcoded floor in degrees
angle_meets_minimum = latest_angle >= max(p75, ABS_ANGLE_FLOOR)

# LONG gated by angle_meets_minimum:
if EMA_ANGLE_PLUS_ENABLED and price_above_ema and latest_angle > 0 and angle_meets_minimum and latest_speed > EMA_ANGLE_MIN_SPEED:

# SHORT has NO equivalent floor:
if EMA_ANGLE_MINUS_ENABLED and latest_angle < 0 and latest_angle <= p25 and latest_speed < -EMA_ANGLE_MIN_SPEED:
```

For tokens where p75 < 0.003° (most tokens in flat/bear markets), the floor overrides p75:
- HEMI: p75 = 0.000845°, floor = 0.003° → threshold becomes **0.003°**
- Any angle below 0.003° is blocked even if it genuinely crosses p75

**Why SHORT works:** No floor. `angle <= p25` adapts naturally to the distribution. In a bear market, p25 is deeply negative — threshold adapts with the market.

**Why LONG breaks:** The floor prevents any signal below 0.003°, even when that angle genuinely crosses p75 (i.e., the steepest positive the token has seen).

### HEMI Data (signal times):

```
p25=-0.010072  p75=0.000845  ABS_ANGLE_FLOOR=0.003

TIME    ANGLE      P75    FLOOR   MEETS?  SPEED_OK?  PRICE>EMA?  LONG_FIRE?
19:50  0.001308  0.000845  0.003  False    True       True        False
19:51  0.001359  0.000845  0.003  False    True       True        False
19:52  0.001410  0.000845  0.003  False    True       True        False
19:53  0.001460  0.000845  0.003  False    True       True        False  ← signal in signals.json
...
```

Manual trace shows NO signal should fire (angle < floor). Yet signals.json shows HEMI LONG at 19:53 and 19:58. **The floor was NOT in the code when those signals fired** — the floor was added or modified after.

## Bug #17: No Cross Confirmation — Fires Without Actual EMA Break

**Symptom:** LONG fires even when price hasn't crossed EMA300, or during sideways chop when angle briefly lifts above p75 during a small green candle.

**Root cause:** `price_above_ema = closes[-1] > ema300[-1]` is static — only verifies current price is above EMA, not that price RECENTLY crossed EMA300.

## Combined Fix

```python
# BEFORE (broken):
ABS_ANGLE_FLOOR = 0.003
angle_meets_minimum = latest_angle >= max(p75, ABS_ANGLE_FLOOR)
if EMA_ANGLE_PLUS_ENABLED and price_above_ema and latest_angle > 0 and angle_meets_minimum and latest_speed > EMA_ANGLE_MIN_SPEED:

# AFTER (correct — mirrors SHORT pattern exactly):
if EMA_ANGLE_PLUS_ENABLED and price_above_ema and latest_angle > 0 and latest_angle >= p75 and latest_speed > EMA_ANGLE_MIN_SPEED:
```

## Asymmetry Rule

When adding a safety constraint to one direction (LONG), always ask: **"does SHORT have the equivalent constraint?"** If SHORT works without it, the constraint is likely a bug, not a feature.

## Verification Script

```python
import math, sqlite3
def ema(vals, period):
    k = 2/(period+1); e = [vals[0]]
    for v in vals[1:]: e.append(v*k + e[-1]*(1-k))
    return e

# For each token: compute p75. If p75 < 0.003 (floor threshold), the floor is
# blocking valid signals. Any angle that crosses p75 but stays below 0.003°
# gets blocked — even though it's the steepest the token has seen.
```