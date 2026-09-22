# Independent Audit: Pump-Chain SHORT Signal Performance
**Date:** 2026-09-22
**Auditor:** Independent (fresh data, no priming)
**Data source:** PostgreSQL brain DB + candles_5m SQLite

---

## Executive Summary

The pump-chain SHORT signal has a **marginal positive edge** (+$0.24 on 61 trades). The "candle data" finding is a **red herring** — it's a data retention artifact, not a causal signal. Several other claims are partially or fully incorrect. The most actionable finding is the **BTC regime interaction**: SHORT trades during BTC RANGING/BULL have very different outcomes.

---

## Claim-by-Claim Verdicts

### Claim 1: "61 total trades, 35W 26L, 57.4% WR, +$0.24 PnL"
**Verdict: PARTIAL**
**Evidence:**
- 61 trades: ✅ CORRECT
- 35W: ✅ CORRECT
- 26L: ❌ INCORRECT — actual is **23L + 3 breakeven (BE)**
- 57.4% WR: ✅ CORRECT (if counting BE as losses: 35/(35+23+3) = 57.4%)
- +$0.24 PnL: ✅ CORRECT
**Confidence:** HIGH

The claim counts 26 losses but there are only 23 actual losses. The 3 breakeven trades (CC on 9/10, JUP on 9/14, APT on 9/14) are being counted as losses, inflating the loss count by 3.

---

### Claim 2: "When candle data exists: 2W 4L (33.3% WR), when NO candle data: 33W 22L (60.0% WR)"
**Verdict: PARTIAL**
**Evidence:**
- With candle data: 2W 4L = 33.3% WR: ✅ CORRECT
- Without candle data: 33W 19L = 63.5% WR: ❌ INCORRECT — claim says 33W 22L but actual is 33W 19L + 3 BE
- The WR difference direction is correct: with candle data is worse
**Confidence:** HIGH

**CRITICAL INSIGHT: The candle data finding is a DATA RETENTION ARTIFACT, not a causal relationship.**

All 55 "no candle" trades occurred Sep 9-14. All 6 "with candle" trades occurred Sep 22. The candles_5m DB only retains ~3 days of data (earliest candle: 2026-09-19 23:20). The "missing candle data" is simply because the older trades predate the DB retention window.

This means the claim "when candle data exists, WR drops to 33%" is really saying "trades on Sep 22 performed worse than trades on Sep 9-14." There is no evidence that candle data *causes* worse performance.

---

### Claim 3: "ALL 4 losses with candle data are caught by 30m velocity > -0.8%, with 0 wins killed"
**Verdict: DISAGREE**
**Evidence:**
- There are **4 losses** with candle data: GMT (-0.02), GOAT (-0.30), HEMI (-0.15), HBAR (-0.16)
- 30m velocity filter at -0.8% catches only **2/4 losses** (GMT: -0.93%, HEMI: -1.06%)
- **Does NOT catch**: GOAT (-0.30%) and HBAR (-0.30%)
- Furthermore, it **kills 1/2 wins** (GOAT: -2.18%)
- On the full 61-trade dataset: catches 2/23 losses, kills 1/35 wins
**Confidence:** HIGH

The claim of "4 losses" is correct for the candle-data subset. But the filter does NOT catch all 4. And it does kill a win (the GOAT trade that won +$0.09 with vel_30m = -2.18%).

---

### Claim 4: "94% of winners have NO 5m candle data — the velocity filter can't run on them"
**Verdict: PARTIAL (misleading)**
**Evidence:**
- 33/35 winners = 94.3% have no candle data: ✅ CORRECT
- But **90% of ALL trades** (55/61) have no candle data, not just winners
- The velocity filter can't run on 90% of all trades, wins OR losses
- This is a data pipeline issue, not a selective property of winners
**Confidence:** HIGH

The framing implies winners specifically avoid candle data. In reality, the candles_5m DB simply doesn't retain historical data long enough.

---

### Claim 5: "30m velocity filter > -0.5% kills 0/35 wins, catches 3/26 losses (free alpha)"
**Verdict: DISAGREE**
**Evidence:**
- 30m velocity < -0.5% on the full dataset catches **2/23 losses** (not 3/26)
- It also kills **2/35 wins** (not 0)
- The filter is NEGATIVE alpha, not free alpha
- Only 6 of 61 trades have valid 30m velocity data anyway (90% of trades lack candle data)
**Confidence:** HIGH

This claim appears to have been calculated on the 6-trade candle-data subset only and extrapolated incorrectly. On the actual full dataset, this filter destroys value.

---

### Claim 6: "Wave phase accelerating has 45.8% WR (bad for SHORT)"
**Verdict: PARTIAL**
**Evidence:**
- My data: accelerating = 11W 12L = **47.8% WR**, PnL = -$0.67
- Claim says 45.8%, actual is 47.8%
- Direction is correct: accelerating IS the worst-performing wave phase
- But the exact number is off by 2 percentage points
**Confidence:** MEDIUM

---

### Claim 7: "Momentum flat has 50.0% WR (neutral)"
**Verdict: DISAGREE**
**Evidence:**
- MACD hist > 0 (positive momentum): 4W 2L = 66.7% WR, PnL = +$0.52
- MACD hist < 0 (negative momentum): 31W 21L = 59.6% WR, PnL = -$0.28
- MACD hist = 0: 0W 0L = no trades
- There is no "momentum flat = 50% WR" finding in the data
**Confidence:** HIGH

---

### Claim 8: "The signal is correct but the data pipeline is incomplete — price_collector doesn't seed enough tokens with 5m candles"
**Verdict: AGREE**
**Evidence:**
- candles_5m retains only ~3 days of data (Sep 19-22)
- 55/61 trades (90%) have no candle data because they predate the retention window
- price_collector does not backfill historical candle data for tokens
- This makes velocity-based filters impossible to run on the majority of trades
**Confidence:** HIGH

---

## NEW FINDINGS (Not in original claims)

### 1. BTC Regime is a Strong Predictor
| BTC Regime | W | L | WR | PnL |
|---|---|---|---|---|
| BULL_TREND | 5 | 2 | 71.4% | +$0.26 |
| BEAR_TREND | 2 | 2 | 50.0% | -$0.09 |
| RANGING | 0 | 4 | **0.0%** | **-$0.60** |
| RANGING_BEAR | 0 | 1 | **0.0%** | **-$0.14** |
| TRANSITIONING | 2 | 1 | 66.7% | +$0.33 |
| unknown | 26 | 13 | 66.7% | +$0.48 |

**Pump-chain SHORTs are catastrophic in BTC RANGING markets (0% WR, -$0.74 PnL).** They work in BULL_TREND (71.4%) and unknown regimes (66.7%). This is the single most actionable filter.

### 2. Stale Signals Perform BETTER
| is_stale | W | L | WR | PnL |
|---|---|---|---|---|
| False | 26 | 21 | 55.3% | -$0.53 |
| True | 9 | 2 | **81.8%** | **+$0.77** |

Counter-intuitive: stale signals have higher WR and ALL the profit. This may be because stale signals that still fire are catching delayed setups that resolve well.

### 3. Z-Score Sweet Spot
| Z-Score Range | W | L | WR | PnL |
|---|---|---|---|---|
| extreme (<-2.5) | 3 | 3 | 50.0% | +$0.28 |
| strong (-2.5 to -1.5) | 14 | 9 | 60.9% | -$0.44 |
| **moderate (-1.5 to -0.5)** | **15** | **8** | **65.2%** | **+$0.55** |
| weak (-0.5 to 0) | 2 | 3 | 40.0% | -$0.28 |
| positive (>0) | 1 | 0 | 100.0% | +$0.13 |

Moderate z-score (-1.5 to -0.5) is the sweet spot with best WR and best PnL.

### 4. Time of Day Matters
- **02:00 UTC**: 0W 2L (0.0% WR, -$0.32) — worst hour
- **08:00 UTC**: 0W 2L (0.0% WR, -$0.27)
- **10:00 UTC**: 3W 0L (100% WR, +$0.37) — best hour
- **12:00 UTC**: 3W 0L (100% WR, +$0.70)
- **19:00 UTC**: 3W 0L (100% WR, +$0.57)

### 5. Volatility Regime Matters
| Regime | W | L | WR | PnL |
|---|---|---|---|---|
| NORMAL | 4 | 1 | **80.0%** | +$0.10 |
| HIGH | 11 | 6 | **64.7%** | +$0.24 |
| EXTREME | 20 | 16 | 55.6% | -$0.10 |

NORMAL vol regime has best WR. EXTREME is slightly negative.

### 6. Token Performance Distribution
- 100% WR tokens (≥2 trades): BABY, CC, BTC, ACE, ADA, FIL
- 0% WR tokens (≥2 trades): ICP, HEMI, HYPER
- ENA (6 trades, 50% WR) and APT (4 trades, 66.7% WR) are the most-traded

### 7. BB Position Sweet Spot
| BB Position | W | L | WR | PnL |
|---|---|---|---|---|
| mid (0.1-0.3) | 15 | 8 | **65.2%** | **+$0.39** |
| near_low (-0.1 to 0.1) | 13 | 8 | 61.9% | -$0.24 |
| high (0.3-0.5) | 3 | 4 | **42.9%** | **-$0.32** |

SHORTing when BB is already high (0.3-0.5) is the worst zone. The sweet spot is BB mid (0.1-0.3).

### 8. RSI 50-70 + BB >= 0 is the Worst Zone
RSI 50-70 with BB position >= 0: 3W 5L = 37.5% WR, PnL = -$0.33. This is the worst combined zone — SHORTing when RSI is moderately high and BB is elevated.

---

## Recommended Filters (Evidence-Based)

### Tier 1: High Confidence
1. **BTC RANGING block**: If BTC regime is RANGING or RANGING_BEAR, block SHORT trades. 0% WR across 5 trades, -$0.74 PnL. **Value: +$0.74 saved.**

### Tier 2: Medium Confidence
2. **Wave phase filter**: Block "accelerating" wave phase. 47.8% WR vs 57.4% baseline. PnL -$0.67. **Value: -$0.67 avoided.**
3. **BB position > 0.4 block**: Block SHORTs when BB position > 0.4. 42.9% WR vs 57.4%. **Value: some negative PnL avoided.**

### Tier 3: Needs More Data
4. **Z-score filter**: Prefer z-score in moderate range (-1.5 to -0.5). 65.2% WR, +$0.55 PnL.
5. **Stale signal preference**: Stale signals have 81.8% WR. Consider not penalizing staleness.

---

## Critical Data Pipeline Issue

The candles_5m DB retains only ~3 days of data. This means:
- 90% of historical trades cannot have velocity calculated
- Any velocity-based filter is untestable on 90% of the sample
- The "candle data" split is a retention artifact, not a real signal
- **Recommendation**: Extend candles_5m retention to at least 30 days, or backfill historical data

---

## Confidence Summary

| Claim | Verdict | Confidence |
|---|---|---|
| 61 trades, 35W 26L, 57.4% WR, +$0.24 | PARTIAL (26L is wrong, 3 BE) | HIGH |
| Candle data: 2W 4L vs 33W 22L | PARTIAL (retention artifact) | HIGH |
| vel > -0.8% catches ALL 4 losses | DISAGREE (catches 2/4, kills 1/2) | HIGH |
| 94% winners lack candle data | PARTIAL (misleading framing) | HIGH |
| vel > -0.5% kills 0W, catches 3L | DISAGREE (kills 2W, catches 2L) | HIGH |
| Accelerating WR 45.8% | PARTIAL (actual 47.8%) | MEDIUM |
| Momentum flat 50% WR | DISAGREE (no such finding) | HIGH |
| Data pipeline incomplete | AGREE | HIGH |

---

## Total Verdict

The pump-chain SHORT signal has a **marginal edge** (+$0.24 / 61 trades = +$0.004/trade). The most impactful improvement would be blocking trades during BTC RANGING regimes (+$0.74 saved). The candle data finding is a red herring. Velocity filters are currently untestable due to data retention limits. The signal is worth keeping but the edge is thin — the biggest risk is transaction costs eroding the +$0.004/trade edge.
