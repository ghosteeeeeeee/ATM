# ME/TON accel-300 Marginal Cross — June 8 2026

## What Happened
- ME SHORT fired at 13:36:03, price=0.06172 (gap=-0.17% from EMA300)
- TON SHORT fired at 13:36:08, price=1.73905 (gap=-0.06% from EMA300)
- Both closed by atr_sl_hit within 18 minutes — immediate reversal

## Root Causes

### 1. MIN_GAP_PCT_SHORT Bug (TON)
Code at `accel_300.py` condition 2 (SHORT path):
```python
if gap_now > -min_gap:  # min_gap = 0.15%
    continue
```
TON gap = -0.06%, -min_gap = -0.15%, check: `-0.06 > -0.15` → True → ALLOWED

This is backwards. A gap of -0.06% doesn't come close to the 0.15% minimum required.
The operator `>` allows gaps closer to zero than the threshold when it should require
`abs(gap_now) >= MIN_GAP_PCT_SHORT`.

ME gap=-0.17% barely passes: `-0.17 > -0.15` → False → passes (marginal).

### 2. CHOP Filter Too Loose
CHOP requires ALL 3 conditions to block:
- cross_gap < ACCEL_300_CHOP_CROSS_GAP_PCT (0.22%)
- ema_angle < CHOP_EMA_ANGLE (0.07%)
- avg_gap_mag < CHOP_AVG_GAP_PCT (0.90%)

| Token | cross_gap | ema_angle | avg_gap_mag | Result |
|-------|-----------|-----------|-------------|--------|
| ME | -0.34% ❌ | 0.28% ❌ | 0.89% ✅ | No block |
| TON | -0.19% ✅ | 0.10% ❌ | 0.32% ✅ | No block |

TON's ema_angle of 0.10% just barely exceeds 0.07% — the chop filter misses it.

## Both Were Micro-Crosses That Immediately Reversed
Price barely slipped below EMA300 for ~4 bars, then reversed above. These are exactly
the false breakout patterns that MIN_GAP_PCT_SHORT should filter but doesn't for TON,
and that CHOP should filter but doesn't for ME.

## Fixes Required
1. Fix SHORT gap check: `abs(gap_now) >= MIN_GAP_PCT_SHORT` (not `gap_now > -min_gap`)
2. Raise MIN_GAP_PCT_SHORT from 0.15% to 0.25-0.30%
3. Tighten ACCEL_300_CHOP_CROSS_GAP_PCT from 0.22% to 0.15%
4. Consider "recovery bar" check: if price crosses back above EMA within N bars of signal, block or invalidate