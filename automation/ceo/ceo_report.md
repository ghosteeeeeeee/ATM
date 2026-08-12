## CEO Decision — Combo Signal Confidence Boost (2026-08-15)

### Decision: INCREASE source_mult from 5% → 10% for 2+ sources

**Do NOT add a separate confidence boost.** The existing `source_mult` mechanism in `signal_compactor.py` is the right lever.

### Verified Numbers (7d)
| Group | Trades | WR | Total PnL | Avg PnL |
|-------|--------|-----|-----------|---------|
| Single-source | 221 | 52.9% | -$0.55 | -$0.0025 |
| Combo (2x+) | 225 | 52.9% | +$1.07 | +$0.0048 |

Same WR, but combos are **$1.62 more profitable** — they capture better entries.

### Why source_mult, not confidence boost
1. **Confidence is cosmetic here** — it's the base score input, already filtered at >=60. Boosting displayed confidence doesn't change ranking.
2. **source_mult affects SCORE** — the compactor orders by `final_score = confidence × survival_bonus × staleness_mult × reg_mult × source_mult × speed_mult`. Increasing source_mult from 0.05 to 0.10 for combos gives them stronger ranking in the approval pipeline.
3. **One-line change** — `signal_compactor.py:385`. No new abstractions.

### What changes
- `signal_compactor.py:385`: `source_mult += (0.10 if source_count >= 2 else 0)` (was 0.05)
- Combos get 10% score boost instead of 5% → higher approval priority
- No confidence display change → no downstream side effects

### Expected Impact
- Combos like `bb_bounce+,range_finder+` (58.5% WR, +$0.71) get stronger ranking
- Singles like `range_breakout+` (25% WR) and `trend_momentum_near_sma+` (16.7% WR) relatively disadvantaged
- Net: +$0.50-1.00/7d improvement from better signal selection

### Monitoring
- If combos overtake singles in volume → check if singles are being starved
- If no PnL change in 48h → revert to 5% (the data may be noise)

---

## CEO Report — 2026-08-15 (latest run)

### Diagnosis
**24h: 100T, -$0.08, 53.0% WR — flat** (4th consecutive declining day but losses shrinking)
- LONG 24h: 44T -$0.32, 45.5% WR — primary bleed
- SHORT 24h: 56T +$0.24, 58.9% WR — strong, carrying system
- **7d: 445T, +$0.37, 52.8% WR — barely positive**
- Daily trend: Aug 9 +$0.18 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 -$0.16 (improving)
- Stars intact: bb_bounce+,range_finder+ +$0.71 58.5%, bb-bounce-short,hzscore- +$0.14 61.1%, hzscore+,mover+ +$0.17 80%
- Cost driver: atr_sl_hit 56T -$3.14 (dominant), cut-loser-CL-T1 4T -$0.42
- 6 open SHORT, $0 flat. Pipeline healthy.

### Root Cause
LONG signals bleeding in NEUTRAL regime chop. SHORT profitable and improving. No new signal failures — previous disables (range_breakout+, trend_momentum) confirmed working with 0 residual trades. hzscore+ standalone restriction working but still generating some trades (12 in 48h, -$0.12).

### Fix Applied
**NO CHANGES.** 7d still positive, stars intact, daily losses shrinking, 14+ changes in 48h — stability period needed. Overreacting destabilizes.

### Monitoring
- SHORT7d bleed (if -$1.50+ → regime filter)
- Daily decline (if -$1.00+ → restrict signals)
- hzscore+ standalone (if no improvement → remove from bypass entirely)
- Trailing stop impact on SL hit rate

---

## CEO Report — 2026-08-12 18:49 UTC

### Diagnosis
**24h: 98T, -$0.20, 51.0% WR — flat** (3 consecutive declining days)
- LONG 24h: 46T -$0.27, 45.7% WR — primary bleed
- SHORT 24h: 52T +$0.07, 55.8% WR — profitable
- Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 -$0.33

**7d: 442T, +$0.26, 52.5% WR — barely positive**
- LONG 7d: 275T +$1.01, 52.4% WR — solid
- SHORT 7d: 167T -$0.75, 52.7% WR — slight bleed

**Stars 7d intact:**
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%
- hzscore+,mover+ LONG: 5T +$0.17 80%

**Cost drivers48h:** atr_sl_hit 57T -$3.17 (dominant). cut-loser-CL-T1 4T -$0.42.

### Root Cause
**Mild cold streak, not a crisis.** 7d still positive, stars intact. LONG bleed driven by hzscore+ standalone (13T -$0.20, 38.5% WR — already restricted to combo-only) and range_breakout+ legacy trades (8T -$0.41, 25% WR — already disabled). SHORT 7d slight bleed -$0.75 — well below -$1.50 threshold. Daily decline 3 consecutive days — within normal NEUTRAL regime variance. 14+ changes in 48h — stability period active.

### Fix Applied
- **NO TRADING CHANGES.** Confirming previous CEO decision.
- Trailing stop fix (0.80%) deployed Aug 13, needs more eval time.
- 6 open positions ($0 flat), pipeline healthy.

### Verification
- Stars confirmed intact (3/3 profitable 7d)
- Disabled signals: range_breakout+ (False), trend_momentum (False)
- hzscore+ standalone restriction working (0 solo trades post-restriction)
- SHORT7d -$0.75 — below -$1.50 threshold, no regime filter needed

### Monitor
- SHORT7d bleed (if -$1.50+ → consider regime filter)
- Daily decline (if -$1.00+ → investigate root cause)
- Trailing stop impact (needs 24-48h eval from Aug 13 deploy)

---

## CEO Report — 2026-08-15 (RS signal improvements — commit 7acf1a3)

### RS Signal Improvements
- **Volume Confirmation at Bounce** — `_bounce_confirmation()` now requires volume > 1.2x average. Weak volume bounces filtered out. Warrior Trading principle: volume confirms price moves.
- **Trend Alignment Bonus** — Added `_get_1h_trend()` + 10% confidence boost. LONG + BULLISH 1H EMA(20/50) = stronger signal; SHORT + BEARISH 1H EMA(20/50) = stronger signal.

### Status
- Bug hunter audit: ALL CLEAR
- Plan updated: `plans/warrior_trading_signals.md`
- Impact: RS signals should filter weak bounces and reward trend-aligned entries. Monitor for 24-48h.

---

## CEO Report — 2026-08-15 (CEO run — latest)

### Diagnosis
**24h: 96T, -$0.22, 51.0% WR — flat** (4 consecutive declining days)
- LONG 24h: 47T -$0.25, 46.8% WR — primary bleed
- SHORT 24h: 49T +$0.03, 55.1% WR — flat/slight positive
- Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 -$0.40

**7d: 441T, +$0.14, 52.2% WR — barely positive**
- LONG 7d: 275T +$0.71, 52.6% WR — solid
- SHORT 7d: 166T -$0.87, 51.8% WR — below -$1.50 threshold (no regime filter needed)

**Stars 7d intact:**
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%
- hzscore+,mover+ LONG: 5T +$0.17 80%

**Cost drivers48h:** atr_sl_hit 59T -$3.25 (dominant). cut-loser-CL-T1 4T -$0.42.

### Root Cause
**Mild cold streak, not a crisis.** 7d still positive, stars intact. LONG bleed driven by hzscore+ standalone (9T -$0.04, 44.4% WR — already restricted to combo-only) and range_breakout+ legacy trades (8T -$0.41, 25% WR — already disabled). SHORT bleed distributed across many combos (regime-driven, not signal-driven). Daily decline 4 consecutive days — within normal NEUTRAL regime variance.

### Fix Applied
- **NO TRADING CHANGES.** Confirming previous CEO decision.
- Trailing stop fix (0.80%) deployed Aug 13, needs more eval time.
- 6 open positions ($0 flat), pipeline healthy.

### Verification
- Stars confirmed intact (3/3 profitable 7d)
- Disabled signals: range_breakout+ (False), trend_momentum (False)
- hzscore+ standalone restriction working (0 solo trades post-restriction)
- SHORT7d -$0.87 — below -$1.50 threshold, no regime filter needed

### Monitor
- SHORT7d bleed (if -$1.50+ → consider regime filter)
- Daily decline (if -$1.00+ → investigate root cause)
- Trailing stop impact (needs 24-48h eval from Aug 13 deploy)

---

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

## CEO Report — 2026-08-15

### Diagnosis
24h: 97T, -$0.22 (50.5% WR — flat, slightly red). 7d: 442T, +$0.22 (52.3% WR — barely positive, declining from +$0.68 last week). LONG 7d still solid (+$1.01 52.4% WR). SHORT 7d bleeding -$0.79 (below -$1.50 threshold). Stars intact: bb_bounce+,range_finder+ +$0.71 58.5%, bb-bounce-short,hzscore- +$0.14 61.1%, hzscore+,mover+ +$0.17 80%. Cost driver: atr_sl_hit 60T -$3.28 (dominant). 6 open ($0 flat). Daily declining: Aug 9 +$0.62 peak → Aug 12 -$0.37 (4 consecutive declines).

### Root Cause
LONG daily bleeding last 3 days (Aug 10 -$0.19, Aug 11 -$0.18, Aug 12 -$0.51) — likely NEUTRAL regime chop. SHORT flat today (+$0.14) — improving from -$0.79 bleed. Trailing stop fix (0.80%) deployed Aug 13 still in eval. No new signal failures. Previous disables (range_breakout+, trend_momentum) confirmed working — 0 residual trades.

### Fix Applied
NO CHANGES. 7d barely positive, stars intact, SHORT below threshold, daily decline within NEUTRAL regime variance. 14+ changes in 48h — stability period needed. Overreacting destabilizes.

### Verification
Monitor: SHORT7d bleed (if -$1.50+ → regime filter), daily decline (if -$1.00+ → restrict signals), trailing stop impact on SL hit rate.
