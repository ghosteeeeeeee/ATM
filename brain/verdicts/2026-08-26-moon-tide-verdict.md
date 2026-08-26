# Independent Audit: Moon-Tide Correlation Claims

**Audit Date:** 2026-08-26
**Auditor:** Independent subagent (no prior exposure to analysis)
**Data Sources:** candles.db (89 days BTC), signals_hermes_runtime.db (70,536 signals over 31 days), PostgreSQL brain (4,057 trades over 91 days, May 20 – Aug 26 2026)
**Methodology:** Fresh code execution from raw databases, no prior analysis trusted

---

## Claim 1: "Moon phases correlate with market behavior"

**Verdict:** PARTIAL
**Confidence:** MEDIUM

**Evidence:**
- Moon illumination vs BTC daily range: Pearson r = -0.019 (n=89), p ≈ 0.86 → **NOT significant**
- Moon illumination vs BTC daily return: Pearson r = +0.082 (n=89), p ≈ 0.91 → **NOT significant**
- Moon illumination vs trade win rate: Pearson r = -0.275 (n=82, filtered for trades > 5), t = -2.56, permutation p = 0.012 → **Significant at α=0.05**
- Moon age vs trade win rate (no filtering): Pearson r = +0.0002 (n=91), p ≈ 1.0 → **NOT significant**
- Partial correlation controlling for time: r drops from -0.275 to -0.124 → **Time confounding present**

**Assessment:** There is a statistically significant negative correlation between moon illumination and trade win rate, BUT this correlation diminishes substantially when controlling for time (the WR trended downward from 45.9% in the first half to 40.6% in the second half of the period). The correlation with BTC price metrics is essentially zero. The claim is partially true for trade outcomes but not for BTC behavior directly.

---

## Claim 2: "Week 4 (Waning) is the ONLY profitable week (+$1.43) — SHORT dominates"

**Verdict:** PARTIAL (depends on methodology)
**Confidence:** MEDIUM

**Evidence:**
- Script's illumination-based classification: Week 4 PnL = +$1.44 ✅ (verified)
- BUT: Script's classification is **methodologically flawed** — it maps by illumination level, not moon phase direction
- **Corrected classification (moon age-based):**
  - Week 3 (Full→LastQ): PnL = **+$2.84** ← actually the most profitable!
  - Week 4 (LastQ→New): PnL = **-$5.45** ← actually LOSING
- **Boundary sensitivity test:**
  - Cutoffs 0.10/0.45/0.80: Week 2 = +$0.36, Week 4 = +$0.67 (TWO profitable weeks)
  - Cutoffs 0.15/0.50/0.85: Only Week 4 = +$1.44 (the claimed result)
  - Cutoffs 0.20/0.55/0.90: Only Week 4 = +$1.47
  - Cutoffs 0.25/0.60/0.95: Only Week 4 = +$3.11
- **Statistical significance:** No week-to-week PnL difference is statistically significant (Mann-Whitney U tests: all p > 0.63)
- SHORT dominance in Week 4: Week 4 SHORT PnL = +$4.44 (verified), but Week 4 SHORT WR = 43.3% which is mediocre

**Assessment:** The claim reproduces with the script's own methodology, but the methodology has a critical flaw (illumination-level bucketing instead of age-based bucketing). With corrected bucketing, Week 3 (Full→LastQ) is the most profitable, not Week 4. The result is also sensitive to boundary choices. The SHORT dominance is partially true (SHORT PnL positive, LONG PnL negative in Week 4).

---

## Claim 3: "Week 2 (Waxing) is best for LONG (48.9% WR, +$1.90)"

**Verdict:** AGREE (with caveats)
**Confidence:** MEDIUM

**Evidence:**
- Week 2 LONG WR: 49.4% (claimed 48.9% — close match, minor rounding difference) ✅
- Week 2 LONG PnL: +$1.90 ✅ (exact match)
- **BUT:** Week 1 LONG WR = 49.3% (virtually identical to Week 2's 49.4%)
- Week 2 LONG PnL = +$1.90 is the only positive LONG PnL across weeks
- **Caveats:**
  - Difference between Week 1 and Week 2 LONG WR is only 0.1pp (noise)
  - Week 2 SHORT PnL = -$4.92 (overall week is LOSING despite LONG being positive)
  - Not statistically significant vs other weeks

**Assessment:** The raw numbers are verified. Week 2 does have the best LONG performance in terms of PnL. However, the WR difference between Week 1 and Week 2 is negligible (0.1pp), and the overall Week 2 is a losing week due to SHORT losses. This is a cherry-picked metric.

---

## Claim 4: "Day 3 (First Quarter) has 59.3% WR — best day"

**Verdict:** AGREE (numbers correct), BUT
**Confidence:** LOW

**Evidence:**
- Day 3 WR: 59.3% (108 trades, 64 wins) — **exact match** ✅
- z-score vs overall WR (43.4%): 3.32, p ≈ 0.0009 → statistically significant
- **CRITICAL CAVEAT:** Day 3 occurs on only **3 unique calendar days** in the 91-day dataset
  - 2026-05-20, 2026-06-19, 2026-08-17
  - These are clustered in time (same general market regime)
  - Effective sample size = 3 days, NOT 108 trades
  - Within-day trades are highly correlated (same market conditions)
- The high WR could be driven by a single favorable trading day

**Assessment:** The number is correct, but the sample is critically small (3 days). With only 3 independent observations, this result has enormous variance and should NOT be used as a trading signal. The z-test treating each trade as independent is invalid — trades within the same day share market conditions.

---

## Claim 5: "Day 11 (New Moon) has 20.3% WR — worst day"

**Verdict:** AGREE (numbers correct), BUT
**Confidence:** LOW

**Evidence:**
- Day 11 WR: 20.3% (128 trades, 26 wins) — **exact match** ✅
- z-score vs overall WR (43.4%): -5.28, p ≈ 0.0000 → statistically significant
- **CRITICAL CAVEAT:** Day 11 occurs on only **4 unique calendar days**
  - 2026-05-28, 2026-06-27, 2026-07-26, 2026-08-25
  - Effective sample size = 4 days, NOT 128 trades
- The low WR could be driven by one or two bad trading days

**Assessment:** The number is correct, but the sample is critically small (4 days). Same caveat as Day 3 — the z-test is invalid due to within-day trade correlation.

---

## Claim 6: "Moon Illumination vs Trade WR: Pearson r = -0.277 (weak-moderate negative)"

**Verdict:** AGREE (numbers approximately correct)
**Confidence:** MEDIUM

**Evidence:**
- Independent reproduction: r = -0.2754 (n=82, filtered for trades > 5)
- Claimed value: r = -0.277 — **very close match** ✅
- t-statistic: -2.56, significant at α=0.05 ✅
- Permutation test p-value: 0.012 → significant ✅
- **BUT:** Partial correlation controlling for time: r drops to -0.124 (not significant)
- **BUT:** Without the >5 trade filter: r = -0.192 (n=91)
- **BUT:** Moon age (more physically meaningful) vs WR: r = +0.0002 (zero correlation)
- The >5 trade filter is arbitrary and could introduce selection bias

**Assessment:** The correlation is reproducible with the same filtering, but it's fragile — it depends on the arbitrary >5 trade filter, diminishes when controlling for time, and disappears when using moon age instead of illumination. The p-value of 0.012 survives the permutation test but does NOT survive Bonferroni correction for multiple testing (39 tests, corrected α = 0.0013).

---

## Claim 7: "New Moon = low volatility, negative BTC returns"

**Verdict:** PARTIAL
**Confidence:** LOW

**Evidence:**
- Week 1 (New) BTC data: 28 days, Avg Range = 2.80%, Avg Return = -0.34%
- Week 1 has the **lowest** average range among weeks → supports "low volatility" ✅
- Week 1 has **negative** average return → supports "negative returns" ✅
- **BUT:** Only 28 data points, and the range (2.80%) is close to Week 4 (2.74%)
- **BUT:** The difference between 2.74% and 2.80% is negligible
- **BUT:** With only 28 days per group, these averages have high variance

**Assessment:** The numbers loosely support the claim, but the effect sizes are tiny and the sample sizes too small to draw conclusions. The volatility ranking is New < Waning < Full < Waxing, which partially matches but "New Moon = lowest" is only barely true vs Waning.

---

## Claim 8: "Waxing Moon = highest volatility, best BTC returns"

**Verdict:** AGREE (numbers correct)
**Confidence:** MEDIUM

**Evidence:**
- Week 2 (Waxing) BTC data: 22 days, Avg Range = 3.58% → **highest** volatility ✅
- Week 2 Avg Return = +0.88% → **best** returns ✅
- Ranking: Waxing (3.58%) > Full (3.29%) > New (2.80%) > Waning (2.74%)
- **Caveats:**
  - Only 22 days of data for Waxing
  - Standard error of mean range with 22 samples is large
  - Could be driven by a few high-volatility days

**Assessment:** Numbers verified. The Waxing period does show the highest volatility and best returns in this dataset. However, with only 22 days, this is not a robust finding.

---

## OVERALL ASSESSMENT

### Summary

The moon-tide analysis scripts produce **technically reproducible numbers** for most claims, but the analysis suffers from **severe methodological flaws** that undermine the conclusions:

1. **Critical bucketing flaw:** `get_moon_week()` classifies by illumination level rather than moon phase direction. A waxing gibbous moon (80% illumination, increasing) is categorized the same as a waning gibbous moon (80% illumination, decreasing). This makes the "weeks" physically meaningless.

2. **Tiny effective sample sizes:** Each moon day occurs only 3-4 times in the 91-day dataset. The high/low WR claims for specific days are based on 3-4 calendar days, making them extremely unreliable. The z-tests incorrectly treat within-day trades as independent observations.

3. **Multiple testing:** ~39 statistical tests were performed without correction. At Bonferroni-corrected α = 0.0013, the illumination-vs-WR correlation (p = 0.012) is NOT significant.

4. **Time confounding:** The system's WR degraded over the observation period (45.9% → 40.6%). Any cyclical variable (including moon phases) could appear correlated with WR due to this secular trend. The partial correlation drops from -0.275 to -0.124 when controlling for time.

5. **Boundary sensitivity:** The "Week 4 is the only profitable week" claim flips depending on which illumination cutoffs are used (different cutoffs produce different "profitable" weeks).

6. **No causal mechanism:** There is no physical mechanism by which moon illumination affects crypto trading outcomes. The correlations are likely spurious.

7. **tide_detector.py confusion:** This script detects market phase changes using signal family clustering and has **nothing to do with moon phases** despite the "tide" name. It should be separated from the moon analysis.

### Recommendations

1. **Do NOT use moon phases for trading decisions.** The correlations are not robust to methodology changes, not significant after multiple testing correction, and confounded by time trends.

2. **Fix the bucketing algorithm** if moon analysis is to be continued: use `moon_age % synodic_month` to determine waxing vs waning, not illumination level.

3. **Separate tide_detector.py from moon analysis.** It's a useful signal-family phase detector that should not be contaminated by moon-phase pseudoscience.

4. **Stop making day-level claims.** With 91 days of data, each moon day has only 3-4 occurrences — this is statistically meaningless.

5. **If moon correlation is to be tested properly:** Need at minimum 2-3 years of data (for adequate moon-day sample sizes), proper Bonferroni correction, and permutation tests for each hypothesis.

6. **Focus on what works:** The signal family clustering, lead-lag detection, and phase transition detection in tide_detector.py are grounded in actual market data and have stronger empirical support.
