# zscore_rising — Acceleration-First Z-Score Momentum Signal

**Date:** 2026-05-29
**Status:** Constants added to hermes_constants.py. Signal file NOT YET CREATED.

## Problem Statement

Neither mtp-zscore (3-period agreement, too slow for gradual grinds) nor zscore_pump (elevated |z| > TH, fires on plateaus) catches the **momentum onset** — when z crosses threshold from below AND is still rising.

- mtp-zscore: fires 372 times on XLM in 48h (noise, Z_MIN too low, 14-bar too fast)
- mtp-zscore: 42 min late on SNX slow grind (+8.67% over 3h)
- zscore_pump: fires when z is persistently elevated, not just crossing

## Design

```python
# Fire condition (single lookback, no multi-period confluence)
z_now   = compute_zscore(closes[-LOOKBACK:])
z_past  = compute_zscore(closes[-LOOKBACK-VEL_BARS:-VEL_BARS])
z_vel   = z_now - z_past

# Crossing: prev_z was BELOW threshold, now ABOVE
fire_long  = z_past < TH <= z_now and z_vel > 0
fire_short = z_past > -TH >= z_now and z_vel < 0
```

**Crossing requirement eliminates:** persistent elevation fires (z was 2.8, now 3.1 = no fire)
**Rising requirement eliminates:** exhausted blow-offs (z is high but rolling over)

## Backtest Results

### SNX Slow Grind (+8.67% over 3h, 15:25–18:30 UTC)

| Config | Fires | Clusters | Notes |
|--------|-------|----------|-------|
| naive z>TH LB=20 (no crossing) | 73 | 20 | Too noisy |
| **cross+hold LB=20 TH=2.5 hold=2** | **20** | **14** | **Best balance** |
| cross_LB20_TH3.0 | 4 | 4 | Too tight — misses move start |

**Fires at 16:24:43** (SNX=0.30008, z20=+2.52) — clean crossing, NOT at 16:18 (z=+3.16 but persistently elevated).

### XLM Stair-Step Choppy Run (+22% in 3 legs, 48h)

Config: LB=20, TH=2.5, VEL_BARS=5, HOLD=2 bars

| Phase | Time | Price Move | Clusters |
|-------|------|------------|----------|
| Phase1 | 05-27 08:00–00:00 | +5.3% | 29 |
| Phase2 | 05-27 00:00–16:00 | +6.9% | 33 |
| Phase3 | 05-27 16:00–05-28 08:00 | +8.9% | 30 |

**Evenly distributes across all 3 legs** — catches each pump start without spamming.

## Constants (hermes_constants.py — already patched)

```python
ZSCORE_RISING_ENABLED         = True
ZSCORE_RISING_PLUS_ENABLED   = True   # LONG
ZSCORE_RISING_MINUS_ENABLED   = True  # SHORT
ZSCORE_RISING_LOOKBACK        = 20
ZSCORE_RISING_THRESHOLD       = 2.5
ZSCORE_RISING_VEL_BARS        = 5
ZSCORE_RISING_HOLD_BARS       = 2     # prevent re-fire during same burst
ZSCORE_RISING_MIN_VEL         = 0.0   # z_vel > 0 for LONG, < 0 for SHORT
ZSCORE_RISING_COOLDOWN_BARS   = 60
```

## What Was NOT Built (Pending)

- `signals/zscore_rising.py` — signal file (imports from signal_schema, signal_gen, hermes_constants; emits source `zscore-rising+`/`zscore-rising-`)
- `signals/__init__.py` — register zscore_rising in SIGNAL_REGISTRY, add to run_all_signals()
- Add to hot-set signals once tested

## Signal vs mtp-zscore vs zscore_pump

| Signal | Trigger | Best For |
|--------|---------|----------|
| mtp-zscore | 3 periods agree on z magnitude | Multi-timeframe confluence confirmation |
| zscore_pump | |z| > TH any time elevated | Sustained elevated momentum (blow-offs) |
| **zscore_rising** | **z crosses TH from below, still rising** | **Early acceleration detection at leg starts** |

## Key Insight: SNX 16:18 Was NOT a False Fire

zscore_pump at 16:18 (z=+3.16) was a valid fire — SNX moved +0.55% in a tight range
(stdev=0.00084), giving legitimate z=3.16. zscore_rising avoids it because z wasn't
*crossing* — it was already elevated. Both signals are correct for their own purposes.

## Data Source

`signals_hermes.db::price_history` (fresh, 230 tokens, anchored to 2026-05-29 00:44 UTC).
Timestamp in seconds. Query: `WHERE token=? ORDER BY timestamp DESC LIMIT <N>`.