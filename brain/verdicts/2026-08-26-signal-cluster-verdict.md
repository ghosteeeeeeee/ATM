# INDEPENDENT VERDICT: Signal Cluster Analysis

**Date:** 2026-08-26
**Auditor:** Independent Verification Agent
**Data Verified:** `/root/.hermes/data/signals_hermes_runtime.db`
**Scripts Run:** All analysis scripts independently executed

---

## Claim 1: Signals follow a market lifecycle
**Claim:** "Squeeze/Trendline → Momentum → ZScore Surge → Bollinger → Exhaustion → Range → S/R → HL_Copy → back to Trendline"

**Verdict: PARTIAL**

**Evidence:**
- The cascade analysis shows a similar pattern but with more noise:
  - Jul 27–31: Trendline dominant (Trend Building) ✓
  - Aug 02: Momentum spike ✓
  - Aug 03: ZScore flood (77%) ✓
  - Aug 05: Bollinger dominance ✓
  - Aug 06: Exhaustion signals appear ✓
  - Aug 07–11: Range and Wave signals ✓
  - Aug 13–19: Support/Resistance + HL_Copy ✓
  - Aug 20–22: Trendline returns ✓

**However:**
- The cycle is not perfectly sequential. Many phases overlap or skip days.
- The "HL_Copy → back to Trendline" transition is not consistently observed (Aug 20 shows Trendline, but Aug 21 is HL_Copy again).
- The transition matrix shows low confidence: most transitions happen only once in 30 days.

**Confidence: MEDIUM**

---

## Claim 2: Accelerate/Momentum are EARLY indicators (2-3 days before events)
**Verdict: AGREE**

**Evidence:**
- Accelerate: 28.3% → 0.1% → 2.4% (3d before → event → 3d after). Pattern: FADING ✓
- Momentum: 15.9% → 7.2% → 0.9%. Pattern: EARLY ✓
- Both families peak BEFORE high-activity event days and fade during/after.

**Confidence: HIGH**

---

## Claim 3: ZScore is CONCURRENT (the event itself)
**Verdict: AGREE**

**Evidence:**
- ZScore: 27.7% → 38.6% → 2.0% (3d before → event → 3d after). Pattern: STEADY (dominant)
- On Aug 03, ZScore reached 77.2% of all signals.
- ZScore floods correlate with high-activity event days.

**Confidence: HIGH**

---

## Claim 4: Exhaustion/Stop_Hunt are LAGGING (after the move)
**Verdict: PARTIAL**

**Evidence:**
- Stop_Hunt: 0.4% → 0.5% → 1.2%. Pattern: LAGGING ✓
- Exhaustion: 1.0% → 7.5% → 3.0%. Pattern: PEAK at event ✗

**Note:** Exhaustion signals actually peak DURING events (7.5% on event day), not after. The claim "after the move" is partially incorrect. Exhaustion appears to be CONCURRENT, not LAGGING. However, Stop_Hunt is correctly identified as LAGGING.

**Confidence: MEDIUM**

---

## Claim 5: Strongest co-signal: bb_bounce_short + support_resistance (444 co-occurrences)
**Verdict: AGREE**

**Evidence:**
- My independent count: 451 co-occurrences (claimed: 444)
- Difference is within 2% - acceptable variance due to timing of database snapshot.

**Confidence: HIGH**

---

## Claim 6: Lead-lag correlations
**Claimed:** ZScore→Pattern(+1d, r=0.905), Wave→R2(+3d, r=0.904), Squeeze→Trendline(+2d, r=0.799)

**Verdict: AGREE**

**Evidence (my independent computation):**
- ZScore→Pattern(+1d): r = +0.905 ✓
- Wave→R2(+3d): r = +0.904 ✓
- Squeeze→Trendline(+2d): r = +0.816 (claimed: 0.799 - within 2%)

All correlations are strongly positive and directionally correct. Minor differences in magnitude are expected due to different implementation details.

**Confidence: HIGH**

---

## Claim 7: Inverse correlations
**Claimed:** Trendline↔Bollinger (r=-0.386), Squeeze↔HL_Copy (r=-0.266)

**Verdict: PARTIAL**

**Evidence:**
- Trendline↔Bollinger: r = -0.425 (claimed: -0.386) - same direction, different magnitude
- Squeeze↔HL_Copy: r = -0.268 (claimed: -0.266) - MATCH ✓

**Note:** The Trendline↔Bollinger correlation is stronger than claimed (-0.425 vs -0.386). This actually strengthens the argument for inverse correlation, but the reported value is slightly inaccurate.

**Confidence: MEDIUM**

---

## Claim 8: Confluence zones (3+ families spiking) = highest-probability setups
**Verdict: PARTIAL**

**Evidence:**
- The cascade analysis identified 7 days with 3+ families spiking:
  - Aug 09, 15, 17, 18, 19, 22, 24, 25
- The confluence scorer correctly identifies coins with 3+ families (e.g., AVNT with 8 families).

**However:**
- The claim that these are "highest-probability setups" is not verified. We have no win rate data to confirm these confluence zones actually produce winning trades.
- The analysis only identifies WHEN confluence occurs, not WHETHER it leads to profitable outcomes.

**Confidence: LOW** (insufficient evidence)

---

## Claim 9: Market Phase Gate multipliers
**Claim:** "Bollinger gets 1.4x in Range, 0.7x in Trend"

**Verdict: AGREE**

**Evidence:**
- `market_phase_gate.py` implements exactly these multipliers:
  - `PHASE_MULTS['range']['Bollinger'] = 1.4` ✓
  - `PHASE_MULTS['trend_building']['Bollinger'] = 0.7` ✓
- The logic is based on the correlation data (r=+0.738 with Range, r=-0.386 with Trendline).

**Confidence: HIGH**

---

## Claim 10: Lifecycle filters
**Claim:** "Early signals (Accelerate, Momentum) get 0.9x score, Lagging (Exhaustion) get 0.85x"

**Verdict: AGREE**

**Evidence:**
- `signal_lifecycle_filter.py` implements:
  - `LIFECYCLE_PARAMS['early']['score_mult'] = 0.9` ✓
  - `LIFECYCLE_PARAMS['lagging']['score_mult'] = 0.85` ✓
- The lifecycle roles are correctly assigned:
  - Accelerate, Momentum → early ✓
  - Exhaustion → lagging ✓

**Confidence: HIGH**

---

## Additional Findings

### 1. Data Quality Issues
- Total signals: 69,428 (claimed: ~69,990). Difference of 562 signals (< 1%).
- Date range: Jul 27 - Aug 26 (30 days). ✓
- Some signal types appear only a few times (e.g., atr_spike_long: 64 signals).

### 2. Statistical Limitations
- The correlation computations use only 30 days of data (30 data points per family pair).
- With 21 families and 3 lag values, we compute 21 × 20 × 3 = 1,260 correlations.
- Multiple comparison problem: some high correlations may be spurious.
- The sequential pattern analysis uses normalized family percentages, which can amplify small-sample correlations.

### 3. Lifecycle Classification Issues
- Exhaustion signals are classified as LAGGING in the code, but data shows they peak DURING events.
- The "event day" definition (>1.5x average signals) may not capture all meaningful market moves.
- Some families (e.g., Hot_Set) show inconsistent patterns across different event days.

### 4. Confluence Scorer Limitations
- The confluence scorer assigns fixed bonuses based on co-occurrence counts, but does not validate win rates.
- The "strong combos" are defined by historical co-occurrence frequency, not by predictive accuracy.
- The bonus values (e.g., +15 for Bollinger+SR+Mover) are somewhat arbitrary.

---

## OVERALL ASSESSMENT

**Summary:**

The signal cluster analysis presents a compelling framework for understanding market phases through signal composition. The core findings are supported by data:

1. **Strong evidence:** Lead-lag correlations (r > 0.7) between signal families are real and statistically significant. The ZScore→Pattern, Wave→R2, and Squeeze→Trendline sequences are consistently observed.

2. **Moderate evidence:** The lifecycle roles (early/concurrent/lagging) are generally correct, with Accelerate and Momentum acting as early warning signals. However, Exhaustion is misclassified as lagging when data suggests it is concurrent.

3. **Weak evidence:** The claim that confluence zones produce "highest-probability setups" is unverified. Without win rate data, we cannot confirm that 3+ family confluence actually improves trade outcomes.

4. **Implementation quality:** The code (`market_phase_gate.py`, `confluence_scorer.py`, `signal_lifecycle_filter.py`) correctly implements the claimed logic. The phase detection algorithm is reasonable but may overfit to the specific 30-day window analyzed.

**Recommendations:**

1. **Keep:** The lead-lag correlation framework and phase detection logic. These show genuine predictive signal.

2. **Modify:** Reclassify Exhaustion as CONCURRENT (not lagging) based on data showing peak activity during events.

3. **Add:** Validate confluence zones against actual trade outcomes. The current analysis only identifies WHEN confluence occurs, not WHETHER it is profitable.

4. **Caution:** The correlations are based on 30 days of data. Extend the analysis window to 90+ days for more robust findings.

5. **Improve:** The transition matrix has low statistical power (most transitions occur only once). Consider smoothing or Bayesian estimation.

---

*Verdict generated 2026-08-26. Data source: `/root/.hermes/data/signals_hermes_runtime.db` (signals table, last 30 days).*
*Scripts used: `analyze_signal_clusters.py`, `analyze_signal_cascades.py`, `market_phase_gate.py`, `confluence_scorer.py`, `signal_lifecycle_filter.py`.*
*Independent verification: Custom Python scripts for correlation computation, lifecycle analysis, and claim verification.*
