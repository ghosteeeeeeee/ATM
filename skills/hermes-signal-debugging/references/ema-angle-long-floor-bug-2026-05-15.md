# ema_angle LONG Floor Bug + Cross Confirmation — 2026-05-15

## Bug #16: Asymmetric ABS_ANGLE_FLOOR on LONG (silent killer)

**Symptom:** ema_angle fires LONG at flat angles (0.001-0.003°) in choppy/sideways markets, while SHORT fires correctly. SHORTS are "mostly working" — LONGS fire where they shouldn't.

**Root cause — asymmetric condition in ema_angle.py line 191:**

```python
ABS_ANGLE_FLOOR = 0.003   # hardcoded floor in degrees
angle_meets_minimum = latest_angle >= max(p75, ABS_ANGLE_FLOOR)

# LONG gated by angle_meets_minimum:
if EMA_ANGLE_PLUS_ENABLED and price_above_ema and latest_angle > 0 and angle_meets_minimum and latest_speed > EMA_ANGLE_MIN_SPEED:

# SHORT has NO equivalent floor — just checks p25 + speed:
if EMA_ANGLE_MINUS_ENABLED and latest_angle < 0 and latest_angle <= p25 and latest_speed < -EMA_ANGLE_MIN_SPEED:
```

For most tokens in flat/bear markets, `p75 < 0.003°`. The floor overrides p75:
- HEMI: p75 = 0.000845°, floor = 0.003° → threshold becomes **0.003°**
- Any angle below 0.003° is blocked even if it's the steepest the token has ever been
- p75 adapts to the token's distribution — floor overrides it with an arbitrary constant

**Why SHORT works:** No floor. `angle <= p25` adapts naturally to the distribution. In a bear market, p25 is deeply negative — the threshold adapts with the market.

**Why LONG breaks:** The floor prevents any signal below 0.003°, even when that angle genuinely crosses p75 (meaning it IS the steepest the token has seen in the lookback window).

### HEMI Data (where LONG signals fired at 19:53/19:58):

```
p25=-0.010072  p75=0.000845  ABS_ANGLE_FLOOR=0.003

TIME    ANGLE      P75    FLOOR   MEETS?   SPEED_OK?  PRICE>EMA?  LONG_FIRE?
19:50  0.001308  0.000845  0.003  False    True       True        False
19:51  0.001359  0.000845  0.003  False    True       True        False
19:52  0.001410  0.000845  0.003  False    True       True        False
19:53  0.001460  0.000845  0.003  False    True       True        False  ← signal exists
19:54  0.001510  0.000845  0.003  False    True       True        False
...
```

Manual trace shows NO signal should fire (angle < floor). Yet signals.json shows HEMI LONG at 19:53 and 19:58. **The floor was not in the code when those signals fired** — confirmed by tracing the actual condition chain. The floor was added or modified after the signals were written.

## Bug #17: No Cross Confirmation (fires in chop without actual EMA break)

**Symptom:** LONG fires even when price hasn't crossed EMA300, or during sideways chop when angle briefly lifts above p75 during a small green candle.

**Root cause:** The `price_above_ema` check is static — only verifies current price is above EMA. Doesn't verify price RECENTLY crossed EMA300. In choppy markets, price oscillates above/below EMA without establishing a trend, and the angle can briefly twitch above p75 during a small green candle.

```python
# Current (static — allows choppy false signals):
price_above_ema = closes[-1] > ema300[-1]

# Better: require price to have crossed EMA recently (within last 20 bars)
ema_cross_bar = None
for i in range(-2, -22, -1):
    # cross up: was below, now above
    if closes[i] < ema300[i] and closes[i-1] > ema300[i-1]:
        ema_cross_bar = i
        break
if ema_cross_bar is None:
    return None  # no recent cross = reject even if price above EMA
```

## Combined Fix for ema_angle LONG

```python
# BEFORE (broken):
ABS_ANGLE_FLOOR = 0.003
angle_meets_minimum = latest_angle >= max(p75, ABS_ANGLE_FLOOR)
if EMA_ANGLE_PLUS_ENABLED and price_above_ema and latest_angle > 0 and angle_meets_minimum and latest_speed > EMA_ANGLE_MIN_SPEED:

# AFTER (correct — mirrors SHORT pattern exactly):
if EMA_ANGLE_PLUS_ENABLED and price_above_ema and latest_angle > 0 and latest_angle >= p75 and latest_speed > EMA_ANGLE_MIN_SPEED:
    # removed ABS_ANGLE_FLOOR and angle_meets_minimum
```

The sign gate (`latest_angle > 0`) + p75 check is sufficient — mirrors the SHORT pattern exactly. The floor was a "safety" that created asymmetric behavior and blocked legitimate signals.

## Asymmetry Rule (lesson to encode)

When adding a safety constraint to one direction (LONG), always ask: **"does the opposite direction have the equivalent constraint?"** If SHORT works without it, the constraint is likely a bug, not a feature.

## Verification Script

```python
import math, sqlite3
def ema(vals, period):
    k = 2/(period+1); e = [vals[0]]
    for v in vals[1:]: e.append(v*k + e[-1]*(1-k))
    return e

# For each token: compute p75. If p75 < 0.003, the floor is blocking valid signals.
# p75 < 0.003 means the token's angle distribution is mostly flat/negative.
# Any angle that IS the steepest positive the token has seen (crosses p75) but is
# below 0.003° gets blocked by the floor.
```

## Constants (current in hermes_constants.py)

```
EMA_ANGLE_LOOKBACK = 500
EMA_ANGLE_SLOPE_PERIOD = 20
EMA_ANGLE_SPEED_PERIOD = 10
EMA_ANGLE_MIN_SPEED = 5e-05
EMA_ANGLE_PERCENTILE_LONG = 75
EMA_ANGLE_PERCENTILE_SHORT = 25
ABS_ANGLE_FLOOR = 0.003  ← the problematic constant (line 190 in ema_angle.py)
```