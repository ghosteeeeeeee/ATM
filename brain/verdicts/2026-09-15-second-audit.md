# 🔍 SECOND INDEPENDENT AUDIT: Hermes Trading System Profitability
**Date:** 2026-09-15 | **Auditor:** Second Independent (no prior analysis loaded) | **Data Source:** PostgreSQL (brain)

---

## Executive Summary

**System: +$1.81 over 7 days (278 trades, 55.4% WR, $0.0065/trade).**

The first auditor's analysis is **largely correct in direction but has numerical discrepancies on 3 of 9 claims.** The critical NEW finding the first auditor missed is that **rr_engine_resistance is destroying the system's BEST signal (pullback-entry- SHORT)** — 21 of 72 pullback-entry- trades get exits via rr_engine_resistance, producing a 38.1% WR on those exits vs 69% WR on ATR SL exits. Disabling rr_engine_resistance could recover ~$0.76/7d from pullback-entry- alone.

**System structure**: SHORT provides ALL profitability (+$3.28/7d). LONG is net negative (-$1.47/7d). This is an asymmetric system where the LONG side is a net cost of doing business, not a profit center.

---

## Verdict on First Auditor's Claims

### Claim 1: "cut-loser-CL-T1 is the biggest problem: -$1.87/7d, 12T, 0% WR, fires too late at -4.5% avg"
**VERDICT: NUANCE** ⚠️

**My independent data:**
- cut-loser-CL-T1: **11 trades, 0% WR, -$1.76 total, -$0.16/trade avg**
- All 11 trades are losses, avg loss -4.51%
- Trades span Sep 8-12

**Discrepancy**: First auditor reports 12 trades and -$1.87. I find **11 trades and -$1.76**. The difference is 1 trade (~$0.11). This is likely a timing boundary issue (trades near the 7-day cutoff).

**The core finding is CONFIRMED**: This exit mechanism has 0% WR and is cutting trades too late. All 11 trades are losses. The -4.51% avg loss indicates the cut-loser fires well after the optimal exit point.

**However, I DISPUTE the claim that this is the "biggest problem"**: rr_engine_resistance bleeds -$1.33 on 37 trades, which is a higher trade count and systemic issue. cut-loser-CL-T1 affects only 11 trades (one-off damage), while rr_engine_resistance affects 37 trades (structural damage).

---

### Claim 2: "rr_engine_resistance exit bleeds: -$1.33/7d, 37T, 40.5% WR"
**VERDICT: CONFIRM** ✅

**My independent data:**
- rr_engine_resistance: **37 trades, 40.5% WR, -$1.33 total**
- Avg win at this exit: +2.97%, Avg loss: -4.11%
- Net per trade: -$0.036

**EXACT MATCH.** Every number matches the first auditor's report.

**But I found something the first auditor MISSED** — see "New Findings" below. The rr_engine_resistance exit is specifically destroying pullback-entry- SHORT, the system's best signal.

---

### Claim 3: "trend_purity+ LONG is the biggest signal loser: -$0.75/7d, 12T, 41.7% WR"
**VERDICT: DISPUTE** ❌

**My independent data:**
- trend_purity+ LONG: **11 trades, 36.4% WR, -$0.90 total**

**Key discrepancies:**
| Metric | First Auditor | My Data | Delta |
|--------|--------------|---------|-------|
| Trades | 12 | 11 | -1 |
| Win Rate | 41.7% | 36.4% | -5.3% |
| Total PnL | -$0.75 | -$0.90 | -$0.15 worse |

The first auditor understated the damage. trend_purity+ LONG is actually **worse** than reported (-$0.90 vs -$0.75).

**Note**: TREND_PURITY_PLUS_ENABLED was set to False on 2026-09-13 by auto_1hr. The 11 trades in the 7d window are from Sep 12-13, before the kill. **The signal is no longer firing.** This is already addressed.

---

### Claim 4: "PM Trail is the best exit: 91.1% WR, +$3.46/7d"
**VERDICT: CONFIRM** ✅

**My independent data:**
- profit-monster-trail: **45 trades, 91.1% WR, +$3.46 total**
- Avg win: +2.69%, Avg loss: -0.83%

**EXACT MATCH.** PM Trail is indeed the system's profit engine.

---

### Claim 5: "ATR SL is net positive: 53.8% WR, +$1.37/7d"
**VERDICT: CONFIRM** ✅

**My independent data:**
- atr_sl_hit: **158 trades, 53.8% WR, +$1.37 total**
- Avg win: +4.93%, Avg loss: -5.09%

**EXACT MATCH.** ATR SL is the workhorse — handles 158/278 trades (57% of all exits).

---

### Claim 6: "NORMAL regime bleeds: -$0.90/7d, 58T, 50% WR"
**VERDICT: NUANCE** ⚠️

**My independent data:**
- NORMAL: **57 trades, 50.9% WR, -$0.79 total, -$0.014/trade avg**

**Discrepancy**: First auditor reports -$0.90 on 58T. I find **-$0.79 on 57T**. The difference is 1 trade and $0.11 — again a timing boundary issue.

**BUT I found a much deeper issue the first auditor missed:**

**LONG in NORMAL is catastrophic:**
| Direction | Regime | Trades | WR | PnL |
|-----------|--------|--------|-----|------|
| LONG | NORMAL | 26 | 38.5% | **-$0.99** |
| SHORT | NORMAL | 31 | 61.3% | +$0.20 |

The first auditor correctly identified NORMAL as a bleed regime but didn't drill into the direction-specific pattern: **LONG in NORMAL accounts for -$0.99 of the -$0.79 total** (offset by SHORT +$0.20).

---

### Claim 7: "pullback-entry- is the lifeline: +$2.58/7d, 61.1% WR, 72T"
**VERDICT: CONFIRM** ✅

**My independent data:**
- pullback-entry- SHORT: **72 trades, 61.1% WR, +$2.58 total**
- Avg win: +4.39%, Avg loss: -4.26% (nearly symmetric R:R)
- Generates more PnL (+$2.58) than the entire system (+$1.81)

**EXACT MATCH.** This signal is indeed the system's lifeline.

**But the first auditor MISSED how much rr_engine_resistance is damaging this signal** — see New Findings.

---

### Claim 8: "pump-chain SHORT wins (+$0.62), LONG loses (-$0.28)"
**VERDICT: CONFIRM** ✅

**My independent data:**
- pump-chain- SHORT: **55T, 63.6% WR, +$0.62**
- pump-chain+ LONG: **25T, 40.0% WR, -$0.28**

**EXACT MATCH.** Killing the entire pump-chain signal would be wrong — SHORT is profitable.

---

### Claim 9: "rr-struct-v2+ is NOT the biggest problem — trend_purity+, bb-bounce, ema300-dip lose more"
**VERDICT: CONFIRM** ✅

**My independent data (losing signals ranked by total PnL):**
| Signal | Trades | WR | Total PnL |
|--------|--------|-----|-----------|
| trend_purity+ | 11 | 36.4% | **-$0.90** |
| pullback-entry+ | 6 | 16.7% | -$0.57 |
| ema300-dip-long | 5 | 20.0% | -$0.55 |
| rr-struct-v2+ | 10 | 40.0% | -$0.45 |
| bb-bounce-v2-long+ | 5 | 40.0% | -$0.45 |

**CONFIRMED**: rr-struct-v2+ is 4th, not 1st. trend_purity+ is the biggest signal loser (though already killed).

---

## What the First Auditor MISSED

### 1. 🔴 CRITICAL: rr_engine_resistance is destroying the system's BEST signal

This is the single biggest finding in this audit.

**pullback-entry- SHORT + rr_engine_resistance = disaster:**
- 21 of 72 pullback-entry- trades (29%) exit via rr_engine_resistance
- rr_engine_resistance exit on pullback-entry-: **38.1% WR, -$0.76**
- ATR SL exit on pullback-entry-: **69.0% WR, +$2.68**
- rr_engine_support_tp exit on pullback-entry-: **83.3% WR, +$0.30**

**The rr_engine_resistance exit is cutting profitable SHORT trades at resistance when they would have continued lower.** On pullback-entry- specifically, it costs the system $0.76/7d — that's 29% of the total signal PnL.

**If rr_engine_resistance were disabled and those 21 trades held to ATR SL instead, the estimated improvement would be +$0.50 to +$1.00/7d** (based on ATR SL WR of 69% on this signal).

### 2. 🔴 CRITICAL: LONG in NORMAL is the worst direction-regime combo

| Direction | Regime | Trades | WR | PnL |
|-----------|--------|--------|-----|------|
| **LONG** | **NORMAL** | **26** | **38.5%** | **-$0.99** |
| LONG | HIGH | 46 | 52.2% | -$0.89 |
| SHORT | EXTREME | 59 | 61.0% | +$1.59 |
| SHORT | HIGH | 69 | 60.9% | +$1.49 |

The first auditor identified NORMAL as a bleed regime but didn't surface that **LONG in NORMAL** is the #1 worst combo. This should be the primary target for regime gating.

### 3. 🟡 Token-level drag: AIXBT, ENA, KAS still actively trading

These three tokens are in the LOSERS list but still generating trades:

| Token | Trades 7d | WR | Total PnL | Status |
|-------|-----------|-----|-----------|--------|
| AIXBT | 8 | 37.5% | -$0.60 | In LOSERS set |
| ENA | 11 | 36.4% | -$0.56 | Not in LOSERS or blacklists |
| KAS | 10 | 40.0% | -$0.43 | In LOSERS set |

**Combined drag: -$1.59/7d** — more than the entire system profit.

**ENA is NOT blacklisted at all** — it's generating 11 trades with 36.4% WR and -$0.56. This should be investigated.

**KAS** is in the LOSERS set (LOSERS_MULT = 0.5, LOSERS_CONF_PENALTY = -30) but still generating 10 trades. The LOSERS penalty isn't aggressive enough — it reduces score and size but doesn't block.

### 4. 🟡 Time-of-day dead zones are wider than the current block

Current time block: 03:00-07:00 UTC (0.7x penalty)

**My data shows:**
| Hour UTC | Trades | WR | PnL | Assessment |
|----------|--------|-----|------|------------|
| 03 | 9 | 33.3% | -$0.91 | WORST HOUR |
| 05 | 13 | 38.5% | -$0.95 | 2nd WORST |
| 04 | 12 | 41.7% | -$0.29 | Bad |
| 09 | 19 | 57.9% | -$0.50 | Surprising bleed |
| 14 | 18 | 55.6% | -$0.37 | Moderate bleed |

**Hour 09 (9AM UTC) bleeds -$0.50 despite 57.9% WR** — this means wins are small and losses are large at this hour. The time block doesn't cover this.

**Hour 19 is the GOLDEN HOUR**: 90.0% WR, +$1.71/7d (10 trades). The system should be aggressive here.

### 5. 🟡 Speed percentile reveals a LONG-specific weakness

| Speed Bucket | Direction | Trades | WR | PnL |
|-------------|-----------|--------|-----|------|
| Speed < 30 (slow) | LONG | 31 | 38.7% | **-$1.32** |
| Speed < 30 (slow) | SHORT | 41 | 58.5% | +$0.50 |
| Speed 30-60 | LONG | 30 | 43.3% | **-$1.50** |
| Speed 30-60 | SHORT | 57 | 68.4% | +$1.97 |
| Speed 60-80 | LONG | 25 | 56.0% | **+$1.62** |
| Speed > 80 (fast) | LONG | 33 | 54.5% | -$0.27 |

**LONG trades at speed < 60 lose -$2.82 combined** (61 trades). Speed 60-80 LONG is the only profitable LONG tier (+$1.62).

The current SPEED_MIN_THRESHOLD = 30 allows slow LONG trades through. **Raising the LONG-specific speed threshold to 45-50 would filter out the worst LONG entries.**

### 6. 🟡 Daily PnL is highly volatile

| Date | Trades | WR | PnL |
|------|--------|-----|------|
| Sep 08 | 11 | 18.2% | **-$1.10** |
| Sep 09 | 43 | 65.1% | +$2.03 |
| Sep 10 | 39 | 66.7% | +$2.48 |
| Sep 11 | 58 | 48.3% | **-$1.74** |
| Sep 12 | 29 | 65.5% | +$0.58 |
| Sep 13 | 36 | 58.3% | +$0.61 |
| Sep 14 | 42 | 47.6% | **-$0.87** |
| Sep 15 | 20 | 50.0% | -$0.18 |

3 out of 8 days are negative. The system is essentially alternating between good and bad days, which suggests it's riding market regimes rather than having consistent edge.

---

## Exit System Deep Analysis

| Exit Mechanism | Trades | WR | Total PnL | Assessment |
|---|---|---|---|---|
| ATR SL | 158 | 53.8% | +$1.37 | ✅ Net positive workhorse |
| PM Trail | 45 | 91.1% | +$3.46 | ✅ Best exit by far |
| rr_engine_resistance | 37 | 40.5% | -$1.33 | ❌ **Structural bleed** |
| cut-loser-CL-T1 | 11 | 0.0% | -$1.76 | ❌ **Fires too late** |
| rr_engine_support_br | 12 | 33.3% | -$0.23 | ⚠️ Marginal |
| rr_engine_support_tp | 9 | 77.8% | +$0.28 | ✅ Good |
| hard_tp | 2 | 100.0% | +$0.48 | ✅ Good (tiny sample) |
| hard_sl | 2 | 0.0% | -$0.33 | ⚠️ Hard SL = errors |
| cut-loser-MAE-GUARD | 2 | 0.0% | -$0.13 | ⚠️ Tiny sample |

**Key insight**: The exit system has 3 profit generators (ATR SL, PM Trail, rr_engine_support_tp) totaling +$5.11, and 2 drags (rr_engine_resistance, cut-loser-CL-T1) totaling -$3.09. The net is +$2.02, but the system's actual PnL is only +$1.81 — the gap is explained by hard_sl and rr_engine_support_br losses.

---

## Scenario Analysis: What If We Fix the Top Issues?

| Scenario | Adjusted PnL | Trades | Impact vs Base |
|----------|-------------|--------|----------------|
| Base system | +$1.81 | 278 | — |
| Remove trend_purity+ LONG (already killed) | +$2.71 | 267 | +$0.90 |
| Remove trend_purity+ and ema300-dip-long | +$3.26 | 262 | +$1.45 |
| Remove top 5 losing signals | +$4.73 | 241 | +$2.92 |

**Removing just the 5 worst signal-direction combos would 2.6x the system's PnL.**

Note: trend_purity+, pullback-entry+, and bb-bounce-v2-long+ are already killed or in NEVER_REENABLE. The remaining active drags are ema300-dip-long (still enabled!) and rr-struct-v2+.

---

## Recommendations (Ranked by Expected Impact)

### Priority 1: Exit System Fix (Expected: +$0.50-1.00/7d)
1. **Disable rr_engine_resistance exit** — Let ATR SL and PM Trail handle exits. The rr_engine_resistance is cutting profitable pullback-entry- SHORT trades prematurely, costing $0.76/7d on that signal alone. This is the single highest-impact change.
2. **Tighten cut-loser-CL-T1** — Current CUT_LOSER_PNL = -1.75% is too wide. All 11 trades exit at -4.51% avg. Tighten to -1.0% to -1.5% range. Estimated savings: $0.30-0.50/7d.

### Priority 2: Signal Kills (Expected: +$0.50/7d)
3. **Kill ema300-dip-long** — Still enabled (EMA300_DIP_LONG_ENABLED = True), generating 5 trades at 20% WR and -$0.55. The volatility_gate_v2 blocks it in EXTREME but it's bleeding in HIGH (-$0.40). Kill it.
4. **Verify pullback-entry+ is actually dead** — PULLBACK_ENTRY_PLUS_ENABLED = False but 6 trades in 7d window. Last trade closed Sep 10 09:42. Confirm it's not re-enabled by any mechanism.

### Priority 3: Regime Gating (Expected: +$0.30/50/7d)
5. **Block LONG in NORMAL regime** — LONG NORMAL = -$0.99/7d, 38.5% WR, 26 trades. This is the worst direction-regime combo. Apply a heavy penalty or hard block for LONG signals in NORMAL.
6. **Block slow LONG trades** — Speed < 60 LONG = -$2.82/7d (61 trades). Consider raising SPEED_MIN_THRESHOLD for LONG specifically to 50.

### Priority 4: Token Management (Expected: +$0.30-0.50/7d)
7. **Blacklist ENA** — 11T, 36.4% WR, -$0.56. Not in any blacklist. Token should be blocked.
8. **Increase LOSERS penalties** — AIXBT and KAS are in LOSERS but still generating trades. Consider hard-blocking tokens with LOSERS_HARD_BLOCK_WR = 40.0% (currently set but needs enforcement check).

### Priority 5: Time-of-Day Optimization (Expected: +$0.10-0.20/7d)
9. **Extend time block to 03:00-09:00 UTC** — Hours 03-05 are the worst, but hour 09 also bleeds -$0.50. The current block at 03-07 misses this.
10. **Boost hour 19** — 90% WR, +$1.71/7d. Consider a confidence boost during this golden hour.

---

## What the First Auditor Got Right ✅

1. ✅ NORMAL regime bleeds (confirmed: -$0.79/7d)
2. ✅ pullback-entry- is the system's lifeline (+$2.58/7d)
3. ✅ rr-struct-v2+ is NOT the biggest problem (confirmed: 4th place)
4. ✅ pump-chain SHORT is profitable, LONG is not
5. ✅ PM Trail is the best exit (91.1% WR, +$3.46)
6. ✅ ATR SL is net positive (53.8% WR, +$1.37)
7. ✅ Exit system structural issue identified

## What the First Auditor Got Wrong or Missed ❌

1. ❌ **trend_purity+ numbers**: Reported 12T/41.7%/-$0.75, actual is 11T/36.4%/-$0.90. Understated the damage.
2. ❌ **cut-loser-CL-T1 count**: Reported 12T, actual is 11T. Minor but affects accuracy.
3. ❌ **NORMAL regime count**: Reported 58T/-$0.90, actual is 57T/-$0.79. Slightly overstated.
4. ❌ **MISSED: rr_engine_resistance destroying pullback-entry-** — This is the #1 finding. 21 of 72 pullback-entry- trades exit via rr_engine_resistance at 38.1% WR vs 69% WR on ATR SL. Cost: $0.76/7d.
5. ❌ **MISSED: LONG in NORMAL as worst combo** — -$0.99/7d, 38.5% WR, 26 trades. The first auditor identified NORMAL as a bleed regime but didn't isolate that LONG is the primary culprit.
6. ❌ **MISSED: Token-level drag** — AIXBT (-$0.60), ENA (-$0.56), KAS (-$0.43) still actively trading. ENA has no blacklist protection at all.
7. ❌ **MISSED: Speed percentile LONG weakness** — Speed < 60 LONG trades lose -$2.82/7d. The speed filter should be LONG-direction-aware.
8. ❌ **MISSED: Time-of-day hour 09 bleed** — 57.9% WR but -$0.50/7d (wins are small, losses are large).
9. ❌ **MISSED: ema300-dip-long is still enabled** — EMA300_DIP_LONG_ENABLED = True, actively losing -$0.55/7d.

---

## Confidence Level

**HIGH (88%)** — All claims independently verified against raw PostgreSQL data.

The remaining 12% uncertainty:
- Sample sizes are small (5-12 trades per signal) — some findings may not be statistically significant
- 7-day window is short for regime-level conclusions
- rr_engine_resistance fix estimate is based on extrapolation from ATR SL performance on the same signal — actual results may vary
- Some trade counts differ by 1 from first auditor due to timing boundary precision

---

*Second independent audit completed: 2026-09-15 12:00 UTC*
*Data source: PostgreSQL (brain) — independent queries, no reliance on first auditor's numbers*
*Method: Full independent SQL analysis with additional pattern searches*
