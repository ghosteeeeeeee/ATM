# ema_angle LONG Fires Without EMA Cross — 2026-05-16

## Executive Summary

Three recent LONG signals fired despite price not genuinely crossing above EMA300:
- **BCH LONG** at 23:08 — `close=426.40, ema=425.71, ratio=+0.16%` (barely above by $0.68)
- **MORPHO LONG** at 21:19 — `close=1.837, ema=1.835, ratio=+0.13%` (barely above by $0.002)
- **ZK LONG** at 21:49 — `close=0.016670, ema=0.016688, ratio=-0.11%` (BELOW EMA)

All three lost money (-0.07% to -0.76%).

## Root Causes

### Bug A: One-Bar EMA Cross Is Enough to Fire

Current code at line 185:
```python
price_above_ema = closes[-1] > ema300[-1]
```

A single bar crossing by 0.07% (MORPHO) or 0.16% (BCH) is sufficient. The next bar reverts, but the signal already fired.

**ZK at 21:48-21:49** — the clearest case:
```
21:48: close=0.016700, ema=0.016688, ratio=+0.07%  ← ABOVE (noise)
21:49: close=0.016670, ema=0.016688, ratio=-0.11%  ← BACK BELOW
```

The EMA was falling toward price, not price rising through EMA. The cross was EMA convergence, not price breakout.

### Bug B: 500-Bar p75 Is Negative or Near-Zero in Choppy Markets

MORPHO's 500-bar p75 = -0.000138° (NEGATIVE). Any positive angle crosses it. The percentile threshold is measuring the recent chop window, not the token's genuine steepness history.

| Token | 500-bar p75 | Full-history p75 | Signal fired? |
|-------|------------|-----------------|---------------|
| MORPHO | **-0.000138°** | +0.001407° | YES (wrong) |
| BCH | +0.000421° | +0.000416° | YES (barely) |
| ZK | +0.000608° | +0.001664° | YES (wrong) |

MORPHO: 500-bar window happened to capture sideways grind, producing near-zero p75.

### Bug C: Angle Magnitude Too Compressed for Discrimination

BCH fires at `angle=0.000596°`. PURR's real fires are at `0.003-0.004°`. The `arctan(slope/ema)` compression makes 6x difference in steepness look like noise-level difference. The arctan transform obscures what slope directly shows.

## What Slope Would Have Caught

Slope of close over 20 bars (linear regression equivalent):

| Token | slope_20 (%/bar) | Positive? | Would Fire? |
|-------|-----------------|----------|-------------|
| BCH | +0.0047%/bar | Yes | Marginally — but note BCH IS slightly rising |
| MORPHO | +0.0054%/bar | Yes | Marginally — but chop (oscillating ±0.02%) |
| ZK | -0.0150%/bar | **No** | **Correctly blocked** |

ZK's slope was negative. Slope would have blocked ZK. MORPHO/BCH are marginal — slope barely positive, not a clear trend.

## PURR Reference Signal Profile

PURR's genuine flat-to-steep transitions:
- Price clearly above EMA: ratio 0.5-1.5%
- Angle at crossover: 0.003-0.005°
- Slope positive AND price rising (not EMA falling)
- p75 from relevant window (not 500-bar chop window)

## Decision

Create `ema_slope.py` as duplicate of `ema_angle.py` with:
1. Slope of close (linear regression over N bars) instead of arctan(angle)
2. Same crossover guard (`angle_was_below_p75`)
3. Same percentile-based thresholds
4. `price_above_ema` guard kept — confirmed working, not the problem
5. SHORTS untouched (working correctly)

The `ema_angle.py` code is preserved as-is. ema_slope is the new refined version for LONG.