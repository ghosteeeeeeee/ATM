# zscore-pump.py Signal Improvement Plan

**Date:** 2026-05-22
**Trigger:** FET missed the 5.14% pump in last hour — zscore_pump.py signals expired before the move

---

## ROOT CAUSE

zscore_pump.py missed the big move because the default lookback is 100 bars, and the z-score formula includes the current bar in both the mean and stdev. A 5.14% gradual 4-hour move doesn't produce a 100-bar z-score above 2.0 — the price rise is too smooth and distributed over too many bars. The z never spiked, so no signal fired.

**Evidence from backtesting:**
- lookback=100: 0 signals in the entire 4-hour window
- lookback=50: first signal fires at bar ~60 (02:08), price 0.19631, z=3.227
- lookback=30: first signal fires at bar ~58 (01:16), price 0.19468, z=5.024

The actual signals that DID fire (03:08, 03:18, 03:23 at z≈2.0-2.2) were borderline — barely above the 2.0 threshold and with only 80% confidence (base confidence). They were single-source (zscore-pump+ only) and expired before the big 03:25-03:36 move.

---

## RECOMMENDATIONS

### 1. Add a shorter lookback detection path (most impactful)
The current architecture fetches lookback + 50 bars but only computes ONE z-score with the full lookback. Add a second pass at lookback=30:
- If z_30 > 2.5 AND z_100 > 0.5 (confirming long-term bias matches direction), fire with elevated confidence
- This catches gradual pumps early instead of waiting for them to become extreme

### 2. Momentum-velocity scoring
Currently signals fire on absolute z threshold only. Add a velocity component:
```
z_velocity = z_current - z_5_bars_ago
```
If z_velocity > 0.3 AND z > 2.0 → boost confidence by 10%, log as "accelerating momentum"

### 3. Signal persistence window
The 03:08 LONG at z=2.13 expired before the 03:25+ move. Add a grace period:
- If a signal would expire within 3 bars of a stronger signal (same direction, same source, higher z), extend TTL to 10 minutes
- Or: if abs(z_30) > abs(z_100) > 1.5 and direction matches, the signal is still valid even if borderline on the longer lookback

### 4. Hot-set confidence floor for strong trends
The 03:08/03:18/03:23 signals only had 80% confidence as single-source zscore-pump+. The hot-set requires multi-source or high confidence. Add a minimum floor: if zscore-pump+ fires AND the 30-bar z > 2.5, always pass to hot-set regardless of source count.

### 5. Change default lookback from 100 to 50
100-bar lookback is too slow for moves that develop over 1-2 hours. Keep 100-bar as an optional wider window for divergence checking, but default the signal lookback to 50. This alone would have caught the FET move 65 minutes earlier at z=3.227.

### 6. Multi-window z-score scoring (best approach)
Rather than a single lookback, compute z-scores at multiple windows (20, 30, 50, 100) and score based on how many windows are signalling the same direction:
```
zscore_w20 = compute_zscore(closes[-20:])
zscore_w30 = compute_zscore(closes[-30:])
zscore_w50 = compute_zscore(closes[-50:])
```
If 3+ windows are LONG and at least 2 are above their respective thresholds, fire with high confidence. This catches moves at multiple timescales simultaneously.

---

## QUICK WINS (lowest effort, highest impact)

1. Change ZSCORE_PUMP_LOOKBACK = 100 → ZSCORE_PUMP_LOOKBACK = 50 in hermes_constants.py
2. Add the momentum-velocity boost (item 2 above) — ~10 lines of code
3. Add multi-window scoring (item 6) — ~15 lines of code, catches moves at multiple scales

---

## CONSTANTS AUDIT

| Constant | Current | Problem | Fix |
|---|---|---|---|
| ZSCORE_PUMP_LOOKBACK | 100 | Too slow for 1-2h moves | 50 |
| ZSCORE_PUMP_THRESHOLD | 2.0 | Works with lower lookback | Keep at 2.0 |
| ZSCORE_PUMP_COOLDOWN_BARS | 5 | Reasonable | No change |
| ZSCORE_PUMP_DIVERGENCE_ENABLED | True | Would not have blocked this move | No change |
| ZSCORE_PUMP_DIVERGENCE_VEL_THD | -0.5 | z was accelerating, not decelerating | No change |
| ZSCORE_PUMP_DIVERGENCE_EXTREME_Z | 3 | z peaked at ~3.2 with lookback=50 | No change needed |
| CONFLUENCE_REQUIRED | True | Blocks single-source zscore-pump+ from hot-set | False to let signal through |
| HOTSET_ENABLED | True | Gate active — borderline signals can't survive | Consider lowering hot-set threshold instead |

**Minimal change combo to catch the move:**
```
ZSCORE_PUMP_LOOKBACK = 50    # instead of 100
CONFLUENCE_REQUIRED = False    # instead of True
```

With lookback=50, at 02:08 the z would have been 3.23 → hot-set passes → trade executes around 0.196 with the full 4.4% move (0.196 → 0.203) still ahead.