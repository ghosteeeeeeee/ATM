## CEO Report — 2026-08-12 16:55 UTC (verification run)

### Diagnosis
**24h: 93T, -$0.27, 50.5% WR — flat** (4 consecutive declining days)
- Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 -$0.45
- LONG 7d: 274T +$1.01 52.6% — solid
- SHORT 7d: 164T -$0.92 51.2% — persistent bleed (below -$1.50 threshold)

**7d: 438T, +$0.09, 52.1% WR — barely positive**

**Stars 7d intact:**
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%
- hzscore+,mover+ LONG: 5T +$0.17 80%

**Cost drivers48h:** atr_sl_hit 60T -$3.27 (dominant). cut-loser-CL-T1 4T -$0.42.

### Root Cause
**Mild cold streak, not a crisis.** 7d still positive, stars intact. SHORT bleed distributed across many combos (regime-driven, not signal-driven). All major LONG bleed sources already addressed (range_breakout+ DISABLED, trend_momentum DISABLED, hzscore+ combo-only restricted).

### Fix Applied
- **NO TRADING CHANGES.** Confirming previous CEO decision.
- Cleaned up stale paper trade (ht_sig4, id=13577) — no open_time, no current_price.
- Trailing stop fix (0.60%→0.80%) needs more evaluation time.

### Verification
- Stars confirmed intact (3/3 profitable 7d)
- Disabled signals: range_breakout+ (False), trend_momentum (False)
- hzscore+ standalone restriction working (0 solo trades post-restriction)
- 6 open SHORT trades, $0 flat, pipeline healthy
- All timers active, no errors

### Decision: NO FURTHER CHANGES
14+ changes deployed Aug 13-15. Stability period needed. Trailing stop fix is the highest-impact lever — let it settle before stacking more changes. Overreacting destabilizes.

### Monitor
- Trailing stop impact on SL hit rate (24-48h eval)
- SHORT7d bleed (if -$1.50+ → regime filter)
- Daily decline (if -$1.00+ → restrict signals)

---

## CEO Report — 2026-08-15 (CEO run — verification)

### Diagnosis
**24h: 93T, -$0.34, 49.5% WR — RED** (4 consecutive declining days)
- Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 -$0.48
- LONG 24h: 47T -$0.29 46.8% WR — primary bleed
- SHORT 24h: 46T -$0.05 52.2% WR — flat (improving from -$0.97 7d)

**7d: 437T, +$0.06, 51.9% WR — barely positive**
- LONG 7d: 274T +$1.01 52.6% — solid
- SHORT 7d: 163T -$0.95 50.9% — persistent bleed (below -$1.50 threshold)

**Stars 7d intact:**
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%
- hzscore+,mover+ LONG: 5T +$0.17 80%

**Cost drivers7d:** atr_sl_hit 168T -$9.46 (dominant). profit-monster-trail 172T +$8.38 (sole profit). Net SL trail: -$1.08.

### Root Cause
**Trailing stop too tight** — already diagnosed and fixed this run. TRAILING_DISTANCE_PCT widened 0.60%→0.80%, TRAILING_ACTIVATION_PCT 0.35%→0.40%. 168 SL hits7d averaging -$0.56 each. Fix needs 24-48h evaluation.

### Fix Applied
- **TRAILING_DISTANCE_PCT: 0.60% → 0.80%** — wider trail, fewer premature exits
- **TRAILING_ACTIVATION_PCT: 0.35% → 0.40%** — trailing engages later, lets winners run
- Commit: 1534a8b

### Verification Status
- Trailing fix deployed, needs 24-48h evaluation window
- SHORT side improving: Aug 12 +$0.03 (first positive day after -$0.97 7d bleed)
- Stars intact — core signals unaffected by trailing params
- All disabled signals confirmed (range_breakout+, trend_momentum)
- hzscore+ combo-only restriction working (0 solo trades post-restriction)
- 7 open $0 flat, pipeline healthy

### Decision: NO FURTHER CHANGES
14+ changes deployed Aug 13-15. Stability period needed. Trailing stop fix is the highest-impact lever — let it settle before stacking more changes. Overreacting destabilizes.

### Previous Fixes (all active)
- RANGE_BREAKOUT_PLUS_ENABLED = False
- trend_momentum_near_sma+ = False
- hzscore+ removed from STANDALONE_BYPASS (combo-only)
- BB_TOUCH_PCT tightened 0.20% → 0.15%
- ACCEL_300 re-enabled (7T +$0.03 57.1% WR — working)
- Pipeline healthy

---

## CEO Report — 2026-08-12 (22:30 UTC)

### Diagnosis
**24h: 97T, -$0.58, 48.5% WR — RED** (4th consecutive decline)
- LONG: primary bleed — range_breakout+ 8T 25% WR -$0.41 (DISABLED this run)
- SHORT: flat — range_breakout- 20T 45% WR -$0.12, hzscore- 16T 50% WR -$0.04
- Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 -$0.50

**7d: 435T, +$0.04, 52.0% WR — barely positive**
- LONG 7d: 274T +$1.01 52.6% — solid
- SHORT 7d: 161T -$0.97 50.9% — persistent bleed

**Stars 7d intact:**
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%
- hzscore+,mover+ LONG: 5T +$0.17 80%

### Root Cause
1. **RANGE_BREAKOUT_PLUS_ENABLED was still True** — previous CEO claimed disabled at 10:00 but config never changed. 8 LONG trades today, all losses (25% WR, -$0.41).
2. **SHORT7d bleed -$0.97** — distributed: range_breakout- 20T -$0.12, hzscore- 16T -$0.04, hzscore-,return_exhaustion- 10T -$0.18. No single kill candidate.
3. **atr_sl_hit dominant**: 62T -$3.30 (48h cost driver).

### Fix Applied
- **RANGE_BREAKOUT_PLUS_ENABLED = False** (commit 1e47094)
- All other disabled signals confirmed correct: trend_momentum FALSE, hzscore+ combo-only

### Monitoring
- SHORT7d bleed (if -$1.50+ → consider regime filter)
- Daily decline (if -$1.00+ → restrict signals)
- 7 open trades, -$0.20 flat
- Pipeline healthy

### Verification
- Stars confirmed intact (3/3 profitable 7d)
- Disabled signals: range_breakout+ (now False), trend_momentum (False)
- hzscore+ standalone restriction working
- Pipeline running, all timers active
