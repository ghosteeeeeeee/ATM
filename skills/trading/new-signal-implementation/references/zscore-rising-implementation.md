# zscore_rising — Implementation Reference

## What happened

Session 2026-05-29: T asked about catching XLM's 20-hour pump with mtp-zscore. We built a new `zscore_rising` signal.

## Key finding: mtp-zscore vs zscore_rising — different move types

XLM's pump was a **gradual grind** (+4.7% over 20 bars, z peaked at 1.96 — never crossed TH=2.5).
SNX 16:24 was a **sharp spike** (z=2.52 crossing — fires cleanly).

| Signal | Gradual grind (XLM) | Sharp spike (SNX) |
|---|---|---|
| mtp-zscore | ✅ Catches via LB=80 lagging mean | ✅ Catches |
| zscore_rising (TH=2.5) | ❌ Never crossed | ✅ Fires at cross |

**Root cause:** zscore_rising requires `prev_z < TH <= cur_z` (crossing). A grind has z rising but never crossing 2.5 — it's already elevated for a long time. mtp-zscore's multi-LB ensemble (20/40/80) catches it because the LB=80 mean hasn't caught up yet.

## Files created

- `/root/.hermes/scripts/signals/zscore_rising.py` — signal implementation
- `/root/.hermes/scripts/signals/__init__.py` — registered (import + SIGNAL_REGISTRY entry)
- `hermes_constants.py` — `ZSCORE_RISING_*` constants added (lines 655-661)

## PENDING — still needs

- **signal_compactor.py `SIGNAL_SOURCE_WEIGHTS`**: Add `('zscore-rising+', 'zscore-rising+'): 1.25` and `('zscore-rising-', 'zscore-rising-'): 1.25` — without this, zscore_rising signals are invisible to the hot-set even though they write to the DB
- **`signals/__init__.py` `name_to_module`**: Should map `'zscore_rising': 'zscore_rising'` if `_run_signal` dispatch is used
- **signal_schema.py Layer 2 kill-switch**: Add `ZSCORE_RISING_PLUS_ENABLED` / `ZSCORE_RISING_MINUS_ENABLED` checks to `add_signal()` if Layer 2 protection is desired (same pattern as `ZSCORE_PUMP_PLUS_ENABLED`)

## Signal params

```python
ZSCORE_RISING_LOOKBACK = 20      # bars for z-score
ZSCORE_RISING_THRESHOLD = 2.5   # must cross this
ZSCORE_RISING_VEL_BARS = 5      # z-velocity: cur_z - z_5bars_ago
ZSCORE_RISING_COOLDOWN_BARS = 10
```

## z-velocity formula

```python
z_past = compute_zscore(closes[:-VEL_BARS], LB)
z_vel = z_cur - z_past  # positive = z is rising
```

Crossing logic:
- LONG: `prev_z < TH <= cur_z AND z_vel > 0`
- SHORT: `prev_z > -TH >= cur_z AND z_vel < 0`

## Source tags

- LONG: `zscore-rising+`
- SHORT: `zscore-rising-`