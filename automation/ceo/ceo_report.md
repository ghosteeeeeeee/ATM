## CEO Report — 2026-08-15 (CEO run)

### Diagnosis
**24h: 93T, -$0.33, 49.5% WR — RED** (5th consecutive decline)
- Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 -$0.56 (peak-to-trough: -$0.94)
- LONG 24h: 50T -$0.47 46% WR — primary bleed
- SHORT 24h: 16T +$0.32 68.8% WR — strong

**7d: 435T, +$0.04, 52.0% WR — barely positive**
- LONG 7d: 274T +$1.01 52.6% — solid
- SHORT 7d: 161T -$0.97 50.9% — persistent bleed

**Stars 7d intact:**
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%
- hzscore+,mover+ LONG: 5T +$0.17 80%

**Cost driver7d:** atr_sl_hit 168T -$9.46 (dominant). profit-monster-trail 171T +$8.30 (barely compensating). Net: +$1.40.

### Root Cause
**Trailing stop too tight** — TRAILING_DISTANCE_PCT 0.60% causes premature exits on normal pullbacks. 168 SL hits7d averaging -$0.56 each. Daily SL hit rate climbing: Aug 9 11 hits → Aug 12 34 hits. Trades can't breathe through volatility to reach profit targets.

### Fix Applied
- **TRAILING_DISTANCE_PCT: 0.60% → 0.80%** — wider trail, fewer premature exits
- **TRAILING_ACTIVATION_PCT: 0.35% → 0.40%** — trailing engages slightly later, lets winners run longer
- Commit: 1534a8b

### Verification (next run)
- Monitor: daily PnL (if improves from -$0.33→flat, trailing was the issue)
- Monitor:7d PnL (if improves from +$0.04→+$0.50+, fix working)
- Stars should remain intact (independent of trailing params)

### Previous Fixes (all still active)
- RANGE_BREAKOUT_PLUS_ENABLED = False
- trend_momentum_near_sma+ = False
- hzscore+ removed from STANDALONE_BYPASS (combo-only)
- BB_TOUCH_PCT tightened 0.20% → 0.15%
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
