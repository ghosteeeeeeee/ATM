# accel-300 Regime Slope Threshold — Why 0 Signals Fire (2026-06-05)

## Core Finding
ACCEL_300_REGIME_SLOPE_PCT = 0.03 (3% per bar) is blocking ALL signal generation.
Every token in the market is in NEUTRAL/FLAT regime — no token has slope > +0.03% or < -0.03%.

## Token Regime Measurements (candles.db candles_1m, 400 bars)
```
BTC:  slope=-0.0056%/bar [FLAT] — cross=999 (no cross in 400 bars)
ETH:  slope=-0.0100%/bar [FLAT] — cross=193 bars ago, gap=-1.51%
SOL:  slope=-0.0068%/bar [FLAT] — cross=999 (no cross in 400 bars)
AVAX: slope=-0.0149%/bar [FLAT] — cross=71 bars ago, gap=-2.54%
BNB:  slope=-0.0056%/bar [FLAT] — cross=999
XRP:  slope=-0.0100%/bar [FLAT] — cross=345 bars ago, gap=-1.99%
ADA:  slope=-0.0142%/bar [FLAT] — cross=83 bars ago, gap=-2.66%
LINK: slope=-0.0161%/bar [FLAT] — cross=999
```

LONG requires slope > +0.03%/bar. SHORT requires slope < -0.03%/bar.
Nothing qualifies. The threshold is mathematically correct for trending markets but
completely blocks the current flat/correcting market phase.

## Why This Happened
Previous session raised threshold from 0.02 → 0.10 → 0.03 trying to reduce chop.
The 0.03 value seems reasonable in isolation but in a flat market every single token
has slope between -0.005 and -0.016 — all blocked equally.

## The Real Chop Filter
The chop problem should be addressed via gap growth and gap expansion, NOT via
the regime slope threshold. The slope threshold's job is to identify trending vs
flat markets — it shouldn't also try to solve chop.

## What T Said
T said: "We're still getting trades in market chop" — the regime filter was
intended to fix this but it's now over-blocking everything.

## Constants That Actually Affect Chop (in hermes_constants.py)
- ACCEL_300_MIN_GAP_GROWTH: raise from 0.05 to 0.08-0.10
- ACCEL_300_MIN_GAP_EXPANSION: raise from 0.10 to 0.15
- RS_DECIDER_CONF_FLOOR: raise from 60 to 65-70
- RS_DECIDER_MIN_TOUCHES: raise from 150 to 175-200

## Constants That Affect Regime (in hermes_constants.py)
- ACCEL_300_REGIME_SLOPE_PCT = 0.03 — CURRENTLY CORRECT for trending markets
  but too tight for flat/correcting phases. Consider 0.02 as a middle ground
  that still filters flat but allows more tokens through.

## Hardcoded Values in accel_300.py (NOT in hermes_constants)
- Regime filter: lines ~406-410 — hardcoded slope threshold, NOT in constants
- Chop filter: lines ~312-321 — hardcoded cross_gap/ema_angle/avg_gap_mag, NOT in constants
- Stale threshold: ACCEL_300_STALE_THRESHOLD_BARS (in constants, was raised 10→40)

## Data Pipeline Status (2026-06-05)
- price_history (signals_hermes.db): only 1 row per token — BROKEN
- candles_1m (candles.db): 400 bars but 8.7 days stale — BROKEN upstream
- Both tables stale simultaneously = upstream HL data feed problem
- Reverted _get_1m_prices to price_history (T instruction: candles_1m confirmed stale)