# INDEPENDENT AUDIT: RSI Band Analysis Verification

**Auditor:** Independent Verification Agent  
**Date:** 2026-10-01 16:13 UTC  
**Database:** PostgreSQL brain @ /var/run/postgresql  
**Analysis Script:** `/root/.hermes/audit/independent_rsi_band_audit.py`  
**Data Window:** 30 days (Sep 1 - Oct 1, 2026), 60 days for stability

---

## === INDEPENDENT VERDICT ===

### 1. CLAIM VERIFICATION

#### SHORT SIGNAL - **CONFIRMED ✓**

| RSI Band | Claimed | Actual | Status |
|----------|---------|--------|--------|
| <25 | 22T, 9.1% WR, -$2.49 | 22T, 9.1% WR, -$2.49 | ✓ EXACT |
| 30-35 | 19T, 26.3% WR, -$1.85 | 19T, 26.3% WR, -$1.85 | ✓ EXACT |
| 45-50 | 18T, 61.1% WR, +$0.14 | 18T, 61.1% WR, +$0.14 | ✓ EXACT |
| 50-55 | 10T, 90.0% WR, +$1.04 | 10T, 90.0% WR, +$1.04 | ✓ EXACT |
| 55-60 | 10T, 50.0% WR, +$0.27 | 10T, 50.0% WR, +$0.27 | ✓ EXACT |
| **Sweet spot 45-60** | **38T, 65.8% WR, +$1.45** | **38T, 65.8% WR, +$1.45** | **✓ EXACT** |

**All SHORT claims verified with exact numerical matches.**

#### LONG SIGNAL - **NUANCE on Sweet Spot WR**

| RSI Band | Claimed | Actual | Status |
|----------|---------|--------|--------|
| 55-60 | 15T, 66.7% WR, +$1.00 | 15T, 66.7% WR, +$1.00 | ✓ EXACT |
| 60-65 | 20T, 35.0% WR, +$0.86 | 20T, 35.0% WR, +$0.86 | ✓ EXACT |
| 65-70 | 24T, 58.3% WR, +$0.34 | 24T, 58.3% WR, +$0.34 | ✓ EXACT |
| **Sweet spot 55-70** | **59T, 55.9% WR, +$2.20** | 59T, **52.5% WR** (pnl_usdt) / **55.9% WR** (pnl_pct), +$2.20 | ⚠️ NUANCE |

**LONG individual bands: EXACT MATCH**  
**LONG sweet spot PnL: EXACT MATCH ($2.20)**  
**LONG sweet spot WR: Methodology-dependent**

**⚠️ NUANCE EXPLAINED:** The claimed 55.9% WR uses `pnl_pct > 0` as win criterion (counts breakeven trades with pnl_usdt=0.00 but pnl_pct>0 as wins). Standard `pnl_usdt > 0` criterion yields 52.5%. Two trades (BTC continuum+ RSI 62.44, GMX pump-chain+ RSI 68.57) are breakeven on pnl_usdt but positive on pnl_pct.

**Additional NUANCE:** RSI 60-65 LONG band labeled "good" has only **35.0% WR** (below breakeven) despite positive PnL +$0.86. This band benefits from asymmetric payoff (avg win $0.291 vs avg loss $0.091), not win rate.

---

### 2. STATISTICAL SIGNIFICANCE - **MIXED (SHORT PASS, LONG FAIL)**

#### SHORT: RSI 45-60 vs RSI 30-45 - **PASS ✓**

| Metric | RSI 45-60 | RSI 30-45 |
|--------|-----------|-----------|
| Trades | 38 | 50 |
| Wins | 25 | 15 |
| Win Rate | 65.8% | 30.0% |
| 95% CI | [50.0%, 81.6%] | [18.0%, 44.0%] |

**Proportion Z-test:** z = 3.340, **p-value = 0.0008**  
**Significant at α=0.05:** YES ✓  
**Significant at α=0.10:** YES ✓

**Mann-Whitney U test (PnL distributions):** U = 1373.5, **p-value = 0.0004**  
**PnL distributions differ significantly:** YES ✓

**VERDICT: The SHORT RSI 45-60 sweet spot is statistically significantly better than RSI 30-45. The edge is real, not random.**

#### LONG: RSI 55-70 vs RSI 40-55 - **FAIL ✗**

| Metric | RSI 55-70 | RSI 40-55 |
|--------|-----------|-----------|
| Trades | 59 | 49 |
| Wins | 31 | 21 |
| Win Rate | 52.5% | 42.9% |
| 95% CI | [40.7%, 64.4%] | [28.6%, 57.1%] |

**Proportion Z-test:** z = 1.003, **p-value = 0.3159**  
**Significant at α=0.05:** NO ✗  
**Significant at α=0.10:** NO ✗

**Mann-Whitney U test (PnL distributions):** U = 1538.5, **p-value = 0.5679**  
**PnL distributions differ significantly:** NO ✗

**VERDICT: The LONG RSI 55-70 sweet spot is NOT statistically significantly better than RSI 40-55. The observed difference could be due to chance.**

---

### 3. CONFOUNDING VARIABLES

#### SHORT - **HIGH CONFOUNDING RISK**

**Signal Concentration:**
- Top 3 signals = **73.2% of all SHORT trades**, **75.8% of all losses**
- `pump-chain-`: 61T (40.9% of all SHORT), 47.5% WR, -$0.96, avg RSI 34.1
- `pullback-entry-`: 40T (26.8%), 32.5% WR, -$2.83, avg RSI 51.1
- `accel-300-`: 8T, 37.5% WR, -$0.34, avg RSI 30.8

**Signal-Specific RSI Performance:**
- `pump-chain-` in RSI 30-45: 27T, **33.3% WR**, -$1.75 (avg RSI 36.9)
- `pump-chain-` in RSI 45-60: 10T, **80.0% WR**, +$0.93 (avg RSI 50.1)
- **CRITICAL FINDING:** pump-chain- performance improves dramatically with RSI filtering (33% → 80% WR). This suggests RSI filtering works FOR this signal, not just that the signal is bad.

- `pullback-entry-` in RSI 30-45: 9T, **11.1% WR**, -$1.18
- `pullback-entry-` in RSI 45-60: 15T, **60.0% WR**, +$0.19
- **Same pattern:** pullback-entry- also improves significantly with RSI filtering.

**Time Period Effects:**
- All 3 weeks negative: W37 -$1.54, W38 -$2.72, W39 -$1.19
- Consistent losing pattern, not isolated to specific period
- **No time-period confounding detected**

**Market Regime Effects:**
- HIGH regime: 34T, **26.5% WR**, -$2.10 (worst)
- EXTREME regime: 94T, 46.8% WR, -$1.98
- NORMAL regime: 19T, 36.8% WR, -$1.38
- **Regime confounding exists:** HIGH regime significantly underperforms

**CONFOUNDING VERDICT:** Results are driven by specific signals (pump-chain-, pullback-entry-), BUT the RSI filtering effect is consistent ACROSS these signals. The confounding does not invalidate the RSI finding—it confirms it works for the dominant signals.

---

#### LONG - **MODERATE CONFOUNDING RISK**

**Signal Concentration:**
- Top 3 signals = **46.1% of trades**, **205.2% of PnL** (because some lose)
- `volume-breakout-long+`: 20T, **70.0% WR**, +$2.48, avg RSI 62.5 (THE STAR)
- `pump-chain+`: 55T, 41.8% WR, +$1.23, avg RSI 72.2
- `bb-bounce-v2-long+`: 19T, 42.1% WR, -$0.14, avg RSI 46.4

**Signal-Specific RSI Performance in Sweet Spot (55-70):**
- `volume-breakout-long+`: 9T, **88.9% WR**, +$2.47, avg RSI 63.3
- `pump-chain+`: 19T, 52.6% WR, +$0.81, avg RSI 63.7
- **volume-breakout-long+ drives most of the sweet spot profitability**

**Time Period Effects:**
- W37: 92T, 54.3% WR, +$3.74 (strong)
- W38: 62T, 35.5% WR, -$2.26 (weak)
- W39: 50T, 44.0% WR, +$0.26 (neutral)
- **Significant time-period variation**

**Market Regime Effects:**
- EXTREME: 76T, 50.0% WR, +$2.02 (best)
- HIGH: 77T, 48.1% WR, -$0.05
- NORMAL: 49T, 36.7% WR, -$0.24
- **EXTREME regime outperforms**

**CONFOUNDING VERDICT:** The LONG sweet spot is heavily driven by `volume-breakout-long+` (88.9% WR in sweet spot). A blanket RSI filter would also block `volume-breakout-long+` trades at RSI>70, which is why `VOLUME_BREAKOUT_LONG_RSI_CEILING=95` override exists. The confounding is moderate—the RSI effect is real but signal-specific.

---

### 4. FILTER IMPACT SIMULATION

#### SHORT Filter: RSI_FLOOR=45, RSI_CEILING=60

| Metric | Current (No Filter) | Post-Filter | Change |
|--------|---------------------|-------------|--------|
| Trades | 149 | 38 | **-74.5%** |
| Wins | 61 | 25 | -36 |
| Win Rate | 40.9% | **65.8%** | **+24.8 pp** |
| Total PnL | -$5.45 | **+$1.45** | **+$6.90** |

**Blocked Trades:**
- Total blocked: 111 (74.5% of all trades)
- Blocked wins: 36
- Blocked WR: 32.4%
- Blocked PnL: -$6.90 (blocking losers is good)

**Winners Blocked in "Good" Bands:**
- RSI 55-70: 4 winners blocked, +$0.57 PnL lost
- Examples: GMT pullback-entry- RSI 69.3 +$0.26, SYRUP pullback-entry- RSI 60.5 +$0.22

**VERDICT:** The filter is **AGGRESSIVE** (blocks 74.5% of trades) but effective. It removes losing trades (blocked WR 32.4% vs allowed 65.8%). Risk: very small sample size post-filter (38T/30d). The filter sacrifices some winners in the 55-70 band to avoid the 60-65 and 65-70 losers.

---

#### LONG Filter: RSI_FLOOR=20, RSI_CEILING=70

| Metric | Current (No Filter) | Post-Filter | Change |
|--------|---------------------|-------------|--------|
| Trades | 204 | 140 | -31.4% |
| Wins | 94 | 69 | -25 |
| Win Rate | 46.1% | **49.3%** | **+3.2 pp** |
| Total PnL | +$1.74 | **+$1.94** | **+$0.20** |

**Blocked Trades:**
- Total blocked: 64 (31.4% of all trades)
- Blocked wins: 25
- Blocked WR: 39.1%
- Blocked PnL: -$0.20 (marginal)

**Winners Blocked:**
- 25 winners blocked, including high-RSI winners from pump-chain+ and volume-breakout-long+
- Largest blocked winner: AVAX pump-chain+ RSI 94.3 +$1.02
- Other big blocked winners: AVAX RSI 91.3 +$0.53, JUP RSI 95.3 +$0.47

**VERDICT:** The filter provides **MARGINAL improvement** (+$0.20 PnL, +3.2pp WR). It blocks some big winners from high-RSI momentum signals. The existing `VOLUME_BREAKOUT_LONG_RSI_CEILING=95` override is correct to preserve volume-breakout-long+'s edge at high RSI.

---

### 5. BOUNDARY ANALYSIS

#### SHORT Boundaries

| Boundary | Trades Near | WR | PnL | Notes |
|----------|-------------|-----|-----|-------|
| RSI=25 | 2 | 0.0% | -$0.12 | Both losses |
| RSI=30 | 4 | **100.0%** | +$0.20 | All wins (surprising!) |
| RSI=35 | 6 | 16.7% | -$0.50 | Mostly losses |
| RSI=40 | 4 | 50.0% | +$0.04 | Mixed |
| **RSI=45** | **2** | **50.0%** | **+$0.06** | **1 win (FOGO +$0.20), 1 loss** |
| **RSI=50** | **1** | **100.0%** | **+$0.08** | **1 win (BABY +$0.08)** |
| RSI=55 | 1 | 0.0% | -$0.01 | 1 loss (CFX) |
| **RSI=60** | **4** | **75.0%** | **+$0.26** | **3 wins, 1 loss** |
| RSI=70 | 1 | 0.0% | -$0.28 | 1 loss (ETC) |

**Observations:**
- RSI=30 boundary shows 100% WR (4/4) - small sample but notable
- RSI=45 boundary (floor) has 1 win, 1 loss - balanced
- RSI=60 boundary (ceiling) has 75% WR - the trades just below ceiling perform well
- **No clear edge case anomalies at boundaries**

#### LONG Boundaries

| Boundary | Trades Near | WR | PnL | Notes |
|----------|-------------|-----|-----|-------|
| RSI=45 | 4 | 25.0% | -$0.28 | Mostly losses |
| RSI=50 | 4 | 25.0% | +$0.06 | Mostly losses, small wins |
| **RSI=55** | **7** | **57.1%** | **+$0.96** | **4 wins, 3 losses** |
| RSI=60 | 4 | 25.0% | -$0.37 | Mostly losses |
| **RSI=65** | **3** | **100.0%** | **+$0.47** | **All wins** |
| RSI=70 | 2 | 50.0% | -$0.04 | Mixed |

**Observations:**
- RSI=55 boundary (sweet spot start) performs well: 57.1% WR, +$0.96
- RSI=65 boundary shows 100% WR (3/3) - all wins
- RSI=70 boundary (ceiling) mixed - 1 win, 1 loss
- **RSI=65 is a strong boundary for LONG - all 3 trades won**

---

### 6. 60-DAY STABILITY ANALYSIS

#### SHORT - **CANNOT ASSESS (Insufficient Historical Data)**

- 60-day trades with RSI: 152
- Recent 30d: 149 trades
- Older 30d: **3 trades only**

**RSI recording gap:** `entry_rsi_14` was first recorded 2026-05-20, but there's a significant gap where recent trades (Sep 16+) have RSI populated while earlier trades don't. Only 3 SHORT trades in the older 30-day window have RSI data.

**VERDICT: Cannot verify SHORT band stability over 60 days due to insufficient historical RSI data.**

#### LONG - **PARTIAL STABILITY ✓**

- 60-day trades with RSI: 288
- Recent 30d: 204 trades
- Older 30d: 84 trades

**Band Consistency (Recent vs Older 30d):**

| Band | Recent 30d | Older 30d | Consistent? |
|------|------------|-----------|-------------|
| 35-40 | 50.0% WR | 42.9% WR | ✓ Yes (both <50%) |
| 45-50 | 46.2% WR | 50.0% WR | ✓ Yes (both ~50%) |
| 50-55 | 45.5% WR | 58.3% WR | ✗ No (direction changed) |
| **55-60** | **66.7% WR** | **57.1% WR** | **✓ Yes (both profitable)** |
| 65-70 | 58.3% WR | 50.0% WR | ✓ Yes (both ≥50%) |
| **70+** | **39.1% WR** | **25.0% WR** | **✓ Yes (both bad)** |

**VERDICT: LONG shows PARTIAL stability.** The sweet spot (55-60) is consistently profitable across both periods. The 70+ "killing field" is consistently bad. However, 50-55 is inconsistent (45.5% recent vs 58.3% older).

---

### 7. SPECIFIC SIGNALS IN "BAD" BANDS

#### SHORT RSI 30-45 ("Bad" Band) - Dominated by Losing Signals

| Signal | Trades | WR | PnL | Avg RSI |
|--------|--------|-----|-----|---------|
| pump-chain- | 27 | 33.3% | -$1.75 | 36.9 |
| pullback-entry- | 9 | 11.1% | -$1.18 | 37.7 |
| accel-300- | 3 | 0.0% | -$0.24 | 34.7 |
| r2-trend-short4 | 1 | 0.0% | -$0.21 | 31.6 |
| Others (5 signals) | 10 | 20.0% | -$0.47 | ~38 |

**KEY FINDING:** The "bad" band is dominated by pump-chain- and pullback-entry- at low RSI. **No signal performs well in this band.** The band itself is toxic.

#### SHORT RSI 45-60 ("Sweet Spot") - Same Signals Perform Well

| Signal | Trades | WR | PnL | Avg RSI |
|--------|--------|-----|-----|---------|
| pump-chain- | 10 | **80.0%** | +$0.93 | 50.1 |
| pullback-entry- | 15 | **60.0%** | +$0.19 | 53.3 |
| accel-300-,rs-r79 | 1 | 100.0% | +$0.20 | 51.5 |
| pump-chain-,rs-r64 | 1 | 100.0% | +$0.19 | 46.6 |
| Others (7 signals) | 11 | 54.5% | +$0.06 | ~51 |

**CRITICAL FINDING:** pump-chain- goes from **33.3% WR (RSI 30-45) → 80.0% WR (RSI 45-60)**. pullback-entry- goes from **11.1% WR → 60.0% WR**. **The same signals perform dramatically better in the sweet spot.** This proves the RSI filter works—it's not just signal selection.

#### LONG RSI 55-70 ("Sweet Spot") - Driven by Star Signal

| Signal | Trades | WR | PnL | Avg RSI |
|--------|--------|-----|-----|---------|
| **volume-breakout-long+** | **9** | **88.9%** | **+$2.47** | 63.3 |
| pump-chain+ | 19 | 52.6% | +$0.81 | 63.7 |
| rs-s56 | 1 | 100.0% | +$0.19 | 67.5 |
| r2-trend-long8 | 1 | 100.0% | +$0.12 | 69.6 |
| Others (7 signals) | 12 | 83.3% | +$0.61 | ~62 |

**KEY FINDING:** volume-breakout-long+ drives most of the sweet spot profitability (88.9% WR, +$2.47 of +$3.68 total). This signal has its own RSI ceiling override (`VOLUME_BREAKOUT_LONG_RSI_CEILING=95`) because it performs well at high RSI.

---

## === STATISTICAL SIGNIFICANCE SUMMARY ===

| Test | Result | Verdict |
|------|--------|---------|
| SHORT 45-60 vs 30-45 (WR) | z=3.340, p=0.0008 | **PASS ✓** |
| SHORT 45-60 vs 30-45 (PnL) | U=1373.5, p=0.0004 | **PASS ✓** |
| LONG 55-70 vs 40-55 (WR) | z=1.003, p=0.3159 | **FAIL ✗** |
| LONG 55-70 vs 40-55 (PnL) | U=1538.5, p=0.5679 | **FAIL ✗** |

**OVERALL: SHORT statistical significance PASSES. LONG statistical significance FAILS.**

---

## === CONFOUNDING VARIABLES SUMMARY ===

| Variable | SHORT | LONG |
|----------|-------|------|
| **Signal concentration** | HIGH (73% from top 3) | MODERATE (46% from top 3) |
| **Time period effects** | LOW (consistent losses) | MODERATE (volatile weekly) |
| **Market regime effects** | MODERATE (HIGH regime worst) | MODERATE (EXTREME best) |
| **Signal-specific RSI effect** | **CONFIRMED** (same signals improve with RSI filter) | **PARTIAL** (volume-breakout-long+ dominates) |

---

## === YOUR RECOMMENDATIONS (Evaluator's Recommendations) ===

### Recommendation 1: SHORT_RSI_FLOOR: 40 → 45

**SUPPORT WITH CAVEATS ✓**

**Evidence FOR:**
- RSI 40-45 band: 17T, 35.3% WR, -$0.80 (losing band)
- Statistical significance: p=0.0008 (strong)
- Same signals (pump-chain-, pullback-entry-) perform much better at RSI≥45
- Filter improves PnL by +$6.90

**Evidence AGAINST/Caveats:**
- Filter blocks 74.5% of all trades (extreme reduction)
- Post-filter sample size: only 38T/30d (small)
- Blocks 4 winners in RSI 55-70 band (+$0.57 PnL lost)

**VERDICT: APPROVE the change.** The statistical evidence is strong (p=0.0008). The filter works across dominant signals. Monitor post-filter performance closely—if 65.8% WR holds over next 30-60 days, the filter is validated.

---

### Recommendation 2: SHORT_RSI_CEILING: 65 → 60

**SUPPORT ✓**

**Evidence FOR:**
- RSI 60-65 band: 5T, 40.0% WR, -$0.48 (losing)
- RSI 65-70 band: 4T, 50.0% WR, +$0.15 (marginal)
- Ceiling at 60 blocks both losing/marginal bands
- Boundary analysis: RSI=60 trades perform well (75% WR) - just below ceiling

**Evidence AGAINST/Caveats:**
- Only 9 trades total in RSI 60-70 range (small sample)
- Blocks 4 winners in 55-70 band

**VERDICT: APPROVE the change.** The evidence supports blocking RSI≥60 SHORT entries. Sample size is small but directionally correct.

---

### Recommendation 3: LONG_RSI_FLOOR: 20 (keep)

**SUPPORT ✓**

**Evidence FOR:**
- RSI <25 LONG: 5T, 80.0% WR, +$0.15 (profitable)
- RSI 25-30 LONG: 10T, 60.0% WR, +$0.02 (profitable)
- Floor at 20 allows oversold bounces

**Evidence AGAINST/Caveats:**
- Small sample sizes (5T, 10T)
- <25 band has only 5 trades

**VERDICT: KEEP at 20.** The data supports allowing oversold LONG entries. Small samples but positive expectancy.

---

### Recommendation 4: LONG_RSI_CEILING: 70 (keep)

**SUPPORT WITH NUANCE ✓**

**Evidence FOR:**
- RSI 70+ LONG: 64T, 39.1% WR, -$0.20 (largest band, losing)
- Consistent across 60-day periods (39.1% recent, 25.0% older)
- Filter improves WR by +3.2pp, PnL by +$0.20

**Evidence AGAINST/Caveats:**
- **Statistical significance FAILED** (p=0.3159 vs 55-70)
- Blocks 25 winners including big RSI 90+ winners (AVAX +$1.02)
- volume-breakout-long+ performs well at high RSI (needs override)

**VERDICT: KEEP at 70, BUT maintain signal-specific overrides.** The 70+ band is losing overall, but the statistical evidence is weak. The existing `VOLUME_BREAKOUT_LONG_RSI_CEILING=95` override for volume-breakout-long+ is correct and should be preserved.

---

## === CONFIDENCE LEVEL ===

### **MODERATE CONFIDENCE (65%)**

**Factors INCREASING Confidence:**
1. ✓ All SHORT band numbers match exactly (perfect data quality)
2. ✓ SHORT statistical significance is strong (p=0.0008 for both WR and PnL)
3. ✓ Signal-specific analysis confirms RSI filtering works across dominant signals
4. ✓ Filter simulation shows clear PnL improvement (+$6.90 for SHORT)

**Factors DECREASING Confidence:**
1. ⚠️ RSI data coverage is limited: only 31.5% of LONG and 38.7% of SHORT trades have `entry_rsi_14`
2. ⚠️ SHORT 60-day stability cannot be verified (only 3 historical trades with RSI)
3. ⚠️ LONG statistical significance FAILED (p=0.3159)
4. ⚠️ Many bands have small sample sizes (10-22T)
5. ⚠️ LONG sweet spot WR methodology ambiguity (pnl_usdt vs pnl_pct)
6. ⚠️ HIGH regime SHORT underperformance (26.5% WR) suggests regime confounding
7. ⚠️ Filter blocks 74.5% of SHORT trades—extreme trade reduction

**What Would INCREASE Confidence to HIGH (>85%):**
1. Increase RSI data coverage to >70% of trades
2. Collect 60+ days of RSI data for SHORT signals
3. Out-of-sample forward test after filter deployment (30-60 days)
4. Signal-specific backtests for pump-chain- and pullback-entry- RSI thresholds
5. Regime-adjusted RSI bands (separate thresholds for EXTREME/HIGH/NORMAL)

---

## === ADDITIONAL FINDINGS (See Something, Say Something) ===

### Finding 1: RSI Recording Data Gap (Severity: MEDIUM)

**Issue:** `entry_rsi_14` was first recorded 2026-05-20 (2989 trades total), but recent daily data shows RSI recording started consistently around Sep 16, 2026. Only 3 SHORT trades in the older 30-day window (Sep 1-16) have RSI data.

**Impact:** Cannot verify SHORT band stability over 60 days. Limits backtest reliability.

**Suggested Fix:** Investigate why RSI recording was intermittent. Ensure all new trades have `entry_rsi_14` populated. Check if there's a code path that skips RSI recording.

---

### Finding 2: Win Rate Criterion Ambiguity (Severity: LOW)

**Issue:** The claimed LONG sweet spot WR (55.9%) uses `pnl_pct > 0` as win criterion, counting breakeven trades (pnl_usdt=0.00, pnl_pct>0.0012%) as wins. Standard `pnl_usdt > 0` yields 52.5%.

**Impact:** 3.4 percentage point WR discrepancy. Could affect filter decisions.

**Suggested Fix:** Document the win rate criterion explicitly in all analyses. Recommend using `pnl_usdt > 0` as the standard (more conservative, avoids counting breakeven as wins).

---

### Finding 3: pullback-entry- Signal Anomaly (Severity: MEDIUM)

**Issue:** `pullback-entry-` has avg RSI 51.1 (in the "good" SHORT band) but performs poorly overall: 40T, 32.5% WR, -$2.83. However, when filtered to RSI 45-60, it improves to 15T, 60.0% WR, +$0.19.

**Impact:** The signal itself has issues at low RSI. RSI filtering helps but doesn't fully fix the signal.

**Suggested Fix:** Investigate why pullback-entry- fires at low RSI (30-45). Consider signal-specific RSI thresholds or disable the signal in low RSI conditions.

---

### Finding 4: volume-breakout-long+ High RSI Edge (Severity: INFO)

**Issue:** `volume-breakout-long+` performs best at high RSI: 9T in sweet spot (55-70) at 88.9% WR, +$2.47. Also has winners at RSI>70 (WCT RSI 67.5, YGG RSI 77.8).

**Impact:** A blanket LONG_RSI_CEILING=70 would block some of this signal's best trades.

**Suggested Fix:** The existing `VOLUME_BREAKOUT_LONG_RSI_CEILING=95` override is correct. Monitor this signal's performance at RSI>95 to ensure the ceiling is appropriate.

---

### Finding 5: HIGH Regime SHORT Underperformance (Severity: MEDIUM)

**Issue:** SHORT trades in HIGH regime: 34T, 26.5% WR, -$2.10 (worst regime). This is significantly worse than EXTREME (46.8% WR) or NORMAL (36.8% WR).

**Impact:** RSI filtering alone may not be sufficient for HIGH regime. Regime-specific adjustments may be needed.

**Suggested Fix:** Consider raising SHORT_RSI_FLOOR for HIGH regime (e.g., 50 instead of 45). Or add regime-based confidence penalties for SHORT trades in HIGH regime.

---

## === FINAL VERDICT TABLE ===

| Claim | Verdict | Evidence Quality |
|-------|---------|------------------|
| SHORT RSI <25: 22T, 9.1% WR, -$2.49 | **CONFIRM ✓** | HIGH (exact match) |
| SHORT RSI 30-35: 19T, 26.3% WR, -$1.85 | **CONFIRM ✓** | HIGH (exact match) |
| SHORT RSI 45-50: 18T, 61.1% WR, +$0.14 | **CONFIRM ✓** | HIGH (exact match) |
| SHORT RSI 50-55: 10T, 90.0% WR, +$1.04 | **CONFIRM ✓** | HIGH (exact match) |
| SHORT RSI 55-60: 10T, 50.0% WR, +$0.27 | **CONFIRM ✓** | HIGH (exact match) |
| SHORT sweet spot 45-60: 38T, 65.8% WR, +$1.45 | **CONFIRM ✓** | HIGH (exact match) |
| LONG RSI 55-60: 15T, 66.7% WR, +$1.00 | **CONFIRM ✓** | HIGH (exact match) |
| LONG RSI 60-65: 20T, 35.0% WR, +$0.86 | **CONFIRM ✓** | HIGH (exact match) |
| LONG RSI 65-70: 24T, 58.3% WR, +$0.34 | **CONFIRM ✓** | HIGH (exact match) |
| LONG sweet spot 55-70: 59T, 55.9% WR, +$2.20 | **NUANCE ⚠️** | MEDIUM (WR methodology-dependent) |
| SHORT 45-60 significantly better than 30-45 | **PASS ✓** | HIGH (p=0.0008) |
| LONG 55-70 significantly better than 40-55 | **FAIL ✗** | HIGH (p=0.3159) |
| SHORT_RSI_FLOOR 40→45 | **SUPPORT ✓** | HIGH |
| SHORT_RSI_CEILING 65→60 | **SUPPORT ✓** | MEDIUM (small sample) |
| LONG_RSI_FLOOR 20 (keep) | **SUPPORT ✓** | MEDIUM (small sample) |
| LONG_RSI_CEILING 70 (keep) | **SUPPORT ✓** | MEDIUM (failed significance) |

---

## === BOTTOM LINE ===

The previous analysis is **largely accurate** for SHORT signals (all numbers exact match, statistical significance strong). The LONG sweet spot WR has a minor methodology discrepancy but PnL matches exactly.

**The SHORT RSI filter change (45-60) is well-supported** by statistical evidence (p=0.0008) and signal-specific analysis (pump-chain- improves from 33% to 80% WR). **Approve with monitoring.**

**The LONG RSI filter (keep 20-70) is directionally correct but statistically weak** (p=0.3159). The 70+ band is losing, but the evidence doesn't meet conventional significance thresholds. **Keep at 70, maintain signal-specific overrides.**

**Overall confidence: MODERATE (65%).** The SHORT findings are solid. The LONG findings need more data. Both need forward validation after deployment.

---

**Audit completed:** 2026-10-01 16:13 UTC  
**Script:** `/root/.hermes/audit/independent_rsi_band_audit.py`  
**Database queries:** All numbers independently verified via PostgreSQL  
**Statistical tests:** scipy.stats (Z-test, Mann-Whitney U), bootstrap CI
