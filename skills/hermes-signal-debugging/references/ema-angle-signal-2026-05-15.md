# EMA-Angle Signal (ema_angle.py) — Signed Angle & Cooldown Pattern

**Date:** 2026-05-15  
**Signal type:** EMA300 angle steepness — pattern signal  
**Source tags:** `ema-angle+` (LONG), `ema-angle-` (SHORT)  
**File:** `/root/.hermes/scripts/signals/ema_angle.py`

---

## Core Mechanism

EMA300 angle in degrees, computed from 20-bar linear regression slope vs EMA value:

```python
slope_n = slope_20 / ema_val          # normalized slope
angle = math.atan(slope_n / ema_val)  # radians → degrees (SIGNED)
```

**Sign is critical:**
- `+angle` = price above EMA, trending up
- `-angle` = price below EMA, trending down
- `0°` = price at EMA (flat)

Before fix: `math.atan(abs(slope_n) / ema_val)` — all angles positive. Signal could not distinguish uptrend from downtrend.

---

## Detection Logic

For each token, compute percentile thresholds from recent angle history:

- **LONG** (`ema-angle+`): `angle >= p75` AND `speed > EMA_ANGLE_MIN_SPEED`
- **SHORT** (`ema-angle-`): `angle <= p25` AND `speed < -EMA_ANGLE_MIN_SPEED`

Percentiles are computed from raw signed angle distribution per token — adapts to each token's regime. In a bear market, p25/p75 are negative; in a bull market, they're positive.

**Key params (hermes_constants.py):**
```python
EMA_ANGLE_LOOKBACK          = 500   # bars for angle history
EMA_ANGLE_SLOPE_PERIOD     = 20    # regression window
EMA_ANGLE_SPEED_PERIOD     = 10    # speed = angle change over N bars
EMA_ANGLE_PERCENTILE_LONG  = 75    # p75 threshold for LONG
EMA_ANGLE_PERCENTILE_SHORT = 25    # p25 threshold for SHORT
EMA_ANGLE_MIN_SPEED        = 5e-05 # minimum angle speed (°/bar)
EMA_ANGLE_MIN_BARS         = 310   # minimum warmup bars
EMA_ANGLE_COOLDOWN_MIN     = 15    # minutes between signals per token+direction
EMA_ANGLE_ENABLED          = True
EMA_ANGLE_PLUS_ENABLED     = True
EMA_ANGLE_MINUS_ENABLED    = True
```

---

## Cooldown Mechanism (In-Memory)

ema_angle uses a **process-level in-memory cache** — NOT the shared DB cooldown:

```python
_last_signal_ts = {}  # token+direction → last signal timestamp (ms)

def _cooldown_ok(token: str, direction: str, now_ts: int) -> bool:
    key = f"{token}:{direction}"
    last = _last_signal_ts.get(key, 0)
    if (now_ts - last) < EMA_ANGLE_COOLDOWN_MIN * 60 * 1000:
        return False
    _last_signal_ts[key] = now_ts
    return True
```

**Behavior:**
- Signal fires ONCE at the flat→steep crossing
- Next 15 min: `_cooldown_ok()` returns `False` — signal skipped even if angle stays elevated
- After 15 min: if angle dips back below threshold then re-crosses, fires again
- In-memory cache means cooldown resets on process restart

**Critical:** This in-memory cooldown is SEPARATE from the shared DB cooldown (`get_cooldown()` in signal_schema.py). The in-memory cache prevents rapid re-firing within the same process run. The DB cooldown is checked afterward as a secondary guard.

---

## Signed Angle Fix (Bug #15)

**Bug:** `abs(slope)` in angle calculation made all angles positive. SHORT logic (`angle <= p25`) could never fire correctly in a downtrend — all angles were positive, so "angle below p25" was meaningless.

**Fix:** Remove `abs()`:
```python
# BEFORE (broken):
angle = math.degrees(math.atan(abs(slope_n) / ema_val))

# AFTER (correct):
angle = math.degrees(math.atan(slope_n / ema_val))
```

**Test with bear market simulation:**
```
BTC bear: angle=-0.022° to -0.430°, p25=-0.249°, p75=-0.092°
Latest: -0.430° < p25, speed=-0.035° < -5e-05 → SHORT fires ✓
```

**Test with live data (2026-05-15 02:XX UTC):**
```
TIA SHORT: angle=-0.0075°, speed=-0.00073
ETH SHORT: angle=-0.0040°, speed=-0.00055
EIGEN SHORT: angle=-0.0090° (deepest)
ICP LONG:  angle=-0.0008°, speed=+0.00021 (slight bounce)
```

---

## Integration Points

- **Register:** `signals/__init__.py` registry + hermes_constants imports
- **Kill-switch:** `signal_schema.py` Layer 2 checks `EMA_ANGLE_ENABLED`, `EMA_ANGLE_PLUS_ENABLED`, `EMA_ANGLE_MINUS_ENABLED`
- **Hot-set:** `signal_compactor.py` needs `SIGNAL_SOURCE_WEIGHTS` entry for `ema-angle+`/`ema-angle-`
- **Data source:** local `candles.db` → `candles_1m` table (no HL API calls)

---

## Common Failures

| Failure | Cause | Fix |
|---------|-------|-----|
| SHORT never fires | `abs()` in angle makes all angles positive | Remove `abs()` |
| LONG/SHORT both fire same token | p25/p75 computed from unsigned distribution | Use signed angles for percentile calculation |
| Signals fire every minute | `_cooldown_ok` not called or in-memory cache not shared | Check `_cooldown_ok()` called before `add_signal()` |
| 0 signals across universe | `EMA_ANGLE_ENABLED=False` or DB query uses wrong param | Check `prices_dict` vs `cutoff_ts` fallback in scan |
| Confidence too low | `flatness_pct` negative when angle deeply below p25 | Use `max(0, (p25 - latest_angle) / angle_range)` |