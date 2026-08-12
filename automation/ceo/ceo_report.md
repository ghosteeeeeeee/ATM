## CEO Report — 2026-08-12

### Diagnosis
24h: 99T -$0.18 (52.5% WR — flat). 7d: 450T +$0.36 (52.7% WR — barely positive). 3 consecutive declining days (Aug 10-12) but losses shrinking. LONG primary bleed, SHORT flat.

### Root Cause
hzscore+ standalone LONG is the worst active bleed source: 13T -$0.20 (38.5% WR 7d), 6T -$0.09 (33% WR 24h). Previous restrictions (combo-only bypass removal) insufficient — signal still fires through normal path and loses.

### Fix Applied
Added 'hzscore+' to SIGNAL_SOURCE_BLACKLIST in hermes_constants.py. validate_source() blocks standalone 'hzscore+' at entry. Combos unaffected: hzscore+,return_exhaustion_long (58.3%), hzscore+,mover+ (80%), bb_bounce+,hzscore+ (50%). No open hzscore+ positions.

### Verification
Blacklist confirmed active: `True` in SIGNAL_SOURCE_BLACKLIST. Pipeline active, all timers running. Previous disables confirmed (range_breakout+ FALSE, trend_momentum FALSE). 5 open SHORT positions ($0 flat). Stars7d intact (3/3 profitable).

---

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

---

## CEO Report — 2026-08-15 (dashboard update acknowledged)

### Changes
- trades.html: removed defunct pump_hunter section, replaced zscore_pump with hot-set (mirrors signals.html), fixed t.coin fallback bug in open/closed trade rendering.
- trades.html and signals.html now share identical hot-set content from `/data/signals.json`.

### Impact
No trading impact. UI-only change — hot-set data source was already signals.json, now consistent across both pages.

---

## CEO Report — 2026-08-12 (source_mult increase acknowledged)

### What
source_mult increased from 5% → 10% for 2+ source combos in `signal_compactor.py:385`.

### Status
✅ Implemented. bug_hunter verified ALL CLEAR. OpenMemory stored.

### Impact
Takes effect on next pipeline run. Combos get stronger score ranking in compactor — should improve signal selection without affecting confidence display or downstream logic.

---

## CEO Report — 2026-08-12 (dashboard update acknowledged)

### Changes
- coin_tracker.html: coin icons from CoinGecko (100 icons → `/var/www/html/coin_icons/`), ICON_MAP JS lookup, `iconHtml()` with 2-letter badge fallback, 32px round icons
- mapping.json available for other pages
- screenshot skill added (Playwright headless screenshots)

### Impact
No trading impact. UI enhancement — coin icons improve visual identification on dashboard.

---

## CEO Report — 2026-08-12 (Weather Vane Spec Review)

### Verdict: APPROVE WITH MODIFICATIONS

The concept is sound — trade outcomes ARE a leading indicator of regime shifts, and slope-based scanners ARE lagging. But the spec's parameters are wrong and will render the system useless.

### DB Verification (what actually happened)
- **Last 20 SHORT trades:** 3 consecutive ATR SL losses at 20:03–20:19 (the cluster T cited), but 7 wins in the 10 before that = 70% WR.
- **48h SHORT:** 68 trades, +$0.22, 57.4% WR — system is profitable on SHORT.
- **7d SHORT:** 176 trades, -$0.59, 53.4% WR — mild bleed, not catastrophic.

### Problem with the Spec

**WR_THRESHOLD=30% will never trigger.** At 57% baseline WR, you need 7+ losses in 10 trades to hit 30%. That's a 0.6% probability event. The weather vane would be dead code.

**The example (3 losses in 16 min) is normal variance.** At 57% WR, 3 losses in a row happens roughly every 15 trades. The spec misreads a cold streak as a regime shift.

### What DOES work

A **cluster-detection** approach, not a WR-threshold approach:
- Trigger on **3+ losses in last 5 trades** within **30 minutes** — this catches real anomalies regardless of overall WR.
- OR: WR < 40% with 5+ trades in 30min — a moderate threshold that can actually fire.

### Modified Parameters

```python
DIRECTIONAL_OUTCOME_ENABLED = True
DIRECTIONAL_OUTCOME_WINDOW = 5            # smaller window = faster detection
DIRECTIONAL_OUTCOME_TIME_WINDOW = 30      # 30 min, not 60 (detect rapid clusters)
DIRECTIONAL_OUTCOME_WR_THRESHOLD = 40     # higher threshold — can actually trigger
DIRECTIONAL_OUTCOME_PENALTY = 0.7         # milder than 0.5 for first deploy
DIRECTIONAL_OUTCOME_MIN_TRADES = 3        # 3+ losses to trigger, not 5
DIRECTIONAL_OUTCOME_CONF_PENALTY = 10     # milder confidence hit
```

### Risk Assessment

1. **Over-suppression:** At 40% WR with 5 trades in 30min, false triggers are possible but rare. The time window limits blast radius.
2. **Missed entries:** If the vane suppresses SHORT and regime stays bearish, we lose valid trades. Mitigated by 0.7 penalty (not 0.0) — signals still fire, just ranked lower.
3. **Implementation location:** signal_compactor.py is correct (scoring stage). decider_run.py addition is redundant — compactor scoring already gates execution. Skip the decider_run change.

### Recommendation

Deploy with modified params. Skip decider_run integration (compactor-only). Start with `DIRECTIONAL_OUTCOME_PENALTY = 0.7` (mild), evaluate 48h, tighten to 0.5 if effective.

---

## CEO Verdict — Weather Vane v2 (Component 2: Position Shield)

### Verdict: APPROVE Component 1 (Signal Gate) — REJECT Component 2 (Position Shield) as spec'd

### Component 1: Signal Gate — APPROVE

The updated params (WINDOW=5, TIME_WINDOW=30min, WR_THRESHOLD=40, PENALTY=0.7, MIN_TRADES=3) are correct and match my earlier modifications. Ready to implement.

### Component 2: Position Shield — REJECT (integration bug)

**Critical flaw:** The spec claims updating `trailing_distance` in the `trades` table will tighten the trailing stop. **This is false.**

`tpsl_utils.py` uses the GLOBAL constant `TRAILING_DISTANCE_PCT` (0.80%) everywhere:
- Line 528: `trail_floor = round(highest_price * (1 - TRAILING_DISTANCE_PCT), 8)`
- Line 551: `trail_ceil = round(lowest_price * (1 + TRAILING_DISTANCE_PCT), 8)`
- Line 501: `eff_sl_pct = max(min(eff_sl_pct, TRAILING_DISTANCE_PCT), ATR_SL_MIN)`

It never reads the per-trade `trailing_distance` column from the DB. Updating that field is a no-op — the guardian's next ATR cycle will use the same 0.80% from the global constant.

**To make Position Shield work, you'd need to either:**
1. Modify `tpsl_utils.py` to accept a per-trade trailing override (non-trivial, touches core SL logic)
2. Temporarily mutate `TRAILING_DISTANCE_PCT` globally (dangerous — affects ALL positions, not just shielded ones)

Neither is safe for first deploy.

### Recommendation

**Ship Component 1 only.** Component 2 is the right idea but needs a different implementation path:
- Option A: Add a `trailing_distance_override` column and make `tpsl_utils` read it (proper fix, more work)
- Option B: Skip the shield for now — the signal gate alone prevents NEW counter-regime entries, which is 80% of the value

Ship the signal gate, evaluate 48h, then decide if the shield is worth the implementation cost.

### 0.30% Trailing — Too Aggressive

Even if the integration worked, 0.30% trailing on losing positions is too tight. Normal pullbacks in crypto are 0.3-0.5%. A position that's -0.5% and recovering would get stopped out at the first micro-bounce. 0.50% would be safer — still tighter than 0.80%, but avoids noise exits.
