# EMA-Angle Signal Debugging Reference
**Session:** 2026-05-15 | **Signal:** ema_angle | **Fix:** price-vs-EMA guard for LONG

## The Bug
LONG ema_angle signals firing when price was BELOW EMA300, or during sideways chop where angle briefly twitched above p75 without a real cross.

**Symptom:** Signals like XLM, MET firing at price below EMA (price < EMA300), OR in chop with minimal cross-to-EMA distance.

**SHORT working correctly because:** angle<0 inherently means price below EMA. No extra check needed.

## Root Cause
LONG condition only checked `angle > 0 and angle >= p75 and speed > MIN_SPEED`.
It never verified price was actually ABOVE EMA300.
In sideways markets, a small green bar can temporarily lift the angle above p75 while price is still below EMA — phantom LONG.

## The Fix (ema_angle.py ~line 183)
```python
# Before:
if EMA_ANGLE_PLUS_ENABLED and latest_angle > 0 and latest_angle >= p75 and latest_speed > EMA_ANGLE_MIN_SPEED:

# After:
price_above_ema = closes[-1] > ema300[-1]   # compute once, only gates LONG
if EMA_ANGLE_PLUS_ENABLED and price_above_ema and latest_angle > 0 and latest_angle >= p75 and latest_speed > EMA_ANGLE_MIN_SPEED:
```

Key points:
- `price_above_ema` is computed but NOT used to block SHORT
- SHORT is gated by `angle < 0` which already implies price below EMA
- Adding price check to SHORT would incorrectly block valid SHORT signals (ZK, XMR confirmed above EMA but failed on speed condition)

## Validation
All test cases pass:
- XLM, MET: BLOCKED (price below EMA) ✓
- AVNT, ORDI: FIRE (price above EMA) ✓
- S, SNX: SHORT unchanged ✓
- ZK, XMR: SHORT blocked on speed (unrelated to fix) ✓

## Why NOT require price-to-have-recently-crossed-EMA for LONG
Checking actual cross in last N bars was considered but rejected — it adds fragility (what lookback? what if cross was 50 bars ago?), and the price-above-EMA guard alone is sufficient: if price is genuinely above EMA, some cross happened. The cross requirement would over-complicate.

## Recency bonus bug found
`bars_ago = len(angle_speeds) - 1 - latest_idx` for LONG — `latest_idx` is the angle-array index, not the speed-array position. This is asymmetric with SHORT which uses `len(angle_speeds) - 1 - latest_idx` (same but SHORT only). The LONG formula is actually correct for computing position-in-speed-array once you trace it through. The SHORT `bars_ago` computation is also correct (latest_idx is the speed-array index here too).

## Constants (from hermes_constants.py)
```
EMA_ANGLE_LOOKBACK = 500
EMA_ANGLE_SLOPE_PERIOD = 20
EMA_ANGLE_SPEED_PERIOD = 10
EMA_ANGLE_MIN_SPEED = 0.00005
EMA_ANGLE_MIN_BARS = 310
```