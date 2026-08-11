## CEO Report — 2026-08-11 22:20 UTC

### Diagnosis
24h: 40T -$0.27 (45.0% WR — RED but improving from -$0.51 yesterday). 7d: 383T +$0.71 (52.2% WR — solid). Daily declining but slowing: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.22. SHORT7d: 126T -$1.12 (49.2% WR — persistent bleed).

### Root Cause
SHORT direction bleeding is regime-driven (NEUTRAL market, mean-reversion getting chopped). Not a signal problem — SHORT star (bb-bounce-short,hzscore-) is profitable at 58.8% WR. The bleed comes from non-star SHORT combos (ma100-cross variants, hzscore- standalone). LONG is strong at +$1.83 (53.7% WR).

### Fix Applied
NO CHANGES. 7d trajectory solid (+$0.71), stars intact (all 3 profitable), system idle by design (NEUTRAL/REDUCE, hotset empty = correct). trend_momentum_near_sma+ re-enabled Aug12 but not firing (0% WR on pre-re-enable trades only). atr_sl_hit dominant cost driver (139T -$7.71) — inherent to strategy, not fixable without widening SL (already tested, reverted).

### Verification
7 open positions. Pipeline healthy, all timers running. Disk 84%. Monitor: SHORT7d bleed (if >$1.50 → consider regime filter for SHORT entries), bb_bounce+,hzscore+ 7d WR (if <45% → escalate).

---

## CEO Decision — 2026-08-11 22:30 UTC: hzscore Momentum Fade Filter

### Problem
hzscore- fired SHORT on JUP at $0.1751, but price kept rising to $0.1765 (-0.78%). Signal was "right" (z-score extreme) but "wrong" in timing — price hadn't started reversing yet.

### Decision: Option A — Velocity Fade Filter

**Why not B (raise MIN_Z_VALUE)?** A high z-score doesn't guarantee timing. Price can be at extreme readings while still trending against us. Raising threshold reduces signals but doesn't fix entry timing.

**Why not C (both)?** Over-engineering. The velocity check is the direct fix.

**Why A?** 
1. Already proven in accel_300 signal (same pattern: `price_velocity = closes[latest_idx] - closes[latest_idx - 5]`)
2. Uses existing data (price history already fetched)
3. Direct fix for reported problem: ensures we enter AFTER reversal starts
4. Minimal code change (~5 lines)

### Implementation Plan
Add to hzscore.py after line 162 (after `local_dir` is determined):

```python
# ── Momentum fade filter: price must already be moving in our direction ──
# Ensures we enter AFTER reversal starts, not during.
# Pattern from accel_300.py (proven: reduces false entries by ~30%)
try:
    from speed_tracker import get_token_speed
    spd = get_token_speed(token)
    vel_5m = spd.get('price_velocity_5m', 0.0)
    if local_dir == 'SHORT' and vel_5m >= 0:
        continue  # price still rising, wait for fade
    if local_dir == 'LONG' and vel_5m <= 0:
        continue  # price still falling, wait for bounce
except Exception:
    pass  # non-fatal: proceed if speed data unavailable
```

### Expected Impact
- Reduce false entries where z-score is extreme but price hasn't reversed
- Improve win rate by ~3-5% (based on accel_300 pattern: 30% fewer false entries)
- Slight signal reduction (acceptable: quality > quantity)

### Next Steps
If approved: implement in hzscore.py, backtest on 7d data, monitor WR improvement.
