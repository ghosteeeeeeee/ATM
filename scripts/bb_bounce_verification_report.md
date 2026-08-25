# BB Bounce Filter Analysis — Independent Verification Report

**Author:** Skeptical Quantitative Analyst  
**Date:** 2026-08-25  
**Status:** VERIFICATION COMPLETE  

---

## VERDICT: PARTIALLY AGREE

The momentum slope filter shows genuine improvement in win rate, but the previous analyst's claims are **overstated** and the recommendation carries **HIGH RISK** without out-of-sample validation.

---

## 1. Previous Analyst's Key Claims vs My Independent Numbers

| Claim | Previous Analyst | My Verification | Assessment |
|-------|-----------------|-----------------|------------|
| Baseline WR | 59.3% | 59.3% | ✓ Confirmed |
| Momentum filter WR | 85.9% | 84.1% | ⚠ Slightly overstated |
| Combined filter WR | 85.9% | 85.9% | ✓ Confirmed |
| Velocity gate loser kill | 11% → 43.9% | 43.9% at -0.3 threshold | ⚠ Discrepancy explained |
| Spike exhaustion usefulness | "Useless" | Partially correct | ✓ Mostly confirmed |
| Volume paradox | High vol = losers | Correlation -0.17 (weak) | ⚠ Real but weak |

---

## 2. Critical Findings

### A. OVERFITTING — HIGH RISK
- **~421 filters tested** on only **140 trades**
- **3.0 tests per trade** — classic p-hacking territory
- Bonferroni-adjusted significance: α = 0.00012
- At α=0.05, expect **21+ false positives** by chance
- **The -0.001% threshold was cherry-picked from many tested values**

### B. THRESHOLD SENSITIVITY — MODERATE (Better Than Expected)
The momentum filter shows a **plateau**, not a fragile peak:

| Threshold | Trades | WR% | Avg PnL |
|-----------|--------|-----|---------|
| mom30 > -0.003% | 94 | 80.9% | $+0.0378 |
| mom30 > -0.002% | 91 | 82.4% | $+0.0405 |
| **mom30 > -0.001%** | **88** | **84.1%** | **$+0.0430** |
| mom30 > 0.000% | 83 | 84.3% | $+0.0431 |
| mom30 > +0.001% | 81 | 85.2% | $+0.0420 |

**Good news:** The filter is relatively robust to threshold choice. Any value from -0.003% to +0.001% gives similar results.

**Bad news:** The -0.001% threshold kills 75% of trades. A safer threshold like -0.003% keeps more trades with only 3% lower WR.

### C. TIME REGIME — FRAGILE
| Period | Trades | Base WR | Filtered WR |
|--------|--------|---------|-------------|
| First half (Aug 5-11) | 70 | 51.4% | 76.2% |
| Second half (Aug 11-24) | 70 | 67.1% | 91.3% |
| **WR GAP** | | | **15.1%** |

⚠ The filter performs **significantly better in the second half** of the data. This raises look-ahead bias concerns — the filter may be fitting to market conditions that existed only in the later period.

### D. DIRECTION BIAS — CRITICAL PROBLEM
| Direction | Trades | Base WR | Filtered WR |
|-----------|--------|---------|-------------|
| LONG | 126 | 61.1% | 92.4% |
| SHORT | 14 | 42.9% | 11.1% |

⚠ **Only 14 SHORT trades** — statistically meaningless. The filter actually **WORSENS** SHORT performance (from 42.9% to 11.1%). Any recommendation to apply this to SHORT trades is dangerous.

### E. 1M CANDLE COVERAGE — PRACTICAL BLOCKER
- **92/232 trades (39.7%)** lack 1m candle data
- The momentum filter **requires** 1m candles (30 minimum)
- **Coverage rate: 60.3%** — filter cannot be applied to ~40% of signals
- Missing-data trades have similar WR (57.6% vs 59.3%), suggesting the sample is representative, but the coverage gap is a real implementation problem

---

## 3. Velocity Gate Discrepancy — Explained

The first analysis reported "11% loser kill" and the second reported "43.9%." My investigation shows:

| Threshold | Blocked | Losers Blocked | Kill Rate |
|-----------|---------|----------------|-----------|
| vel15 <= -0.3 | 26 | 25 | **43.9%** |
| vel15 <= -0.4 | 16 | 16 | 28.1% |
| vel15 <= -0.5 | 12 | 12 | 21.1% |

**The 43.9% number is correct for the -0.3 threshold on the 140 analyzed trades.** The earlier "11%" was likely from a different sample or metric definition. The velocity gate is actually quite effective at -0.3 (blocks 25 of 57 losers while killing only 1 winner).

**My recommendation: DO NOT tighten from 0.3 to 0.15.** The current threshold is already effective. Tightening to 0.15 would block 35 trades including 18 winners (21.7% of all winners) — a terrible trade-off.

---

## 4. Volume Paradox — Real But Weak

| Volume Bucket | Trades | WR% | Avg PnL |
|---------------|--------|-----|---------|
| Very Low (<0.5) | 22 | 45.5% | -$0.018 |
| Low (0.5-0.75) | 7 | 71.4% | +$0.027 |
| Normal (0.75-1.25) | 89 | 69.7% | +$0.028 |
| High (1.25-2.0) | 5 | 20.0% | -$0.025 |
| Very High (≥2.0) | 17 | 29.4% | -$0.016 |

**Point-biserial correlation: -0.17** (weak)

The pattern exists but is too weak to use as a standalone filter. The "Normal" volume bucket dominates (89/140 trades) and performs well. Very high volume does correlate with losses, but the sample sizes for extreme buckets are tiny (5-22 trades).

---

## 5. Spike Exhaustion — Mostly Useless at Default Threshold

At |vel5| < 0.5% (the tested threshold):
- Blocks 11 trades
- Kills 6 winners (7.2%) and 5 losers (8.8%)
- **Nearly random** — slightly worse for winners than losers

At tighter thresholds (|vel5| < 0.2%), it becomes more effective but kills too many trades.

**Verdict: The previous analyst is correct** — at the default threshold, spike exhaustion is not useful. However, removing it entirely is also fine since it has minimal impact.

---

## 6. My Independent Recommendation

### DO NOT DEPLOY as proposed. Instead:

**Step 1: Fix 1m candle data coverage**
- Currently 39.7% of trades lack data
- The filter is impractical until coverage improves
- Investigate why candles_1m is missing for so many tokens

**Step 2: Run out-of-sample validation**
- Hold out the most recent 30% of data
- Test the filter on that held-out set
- If results hold, proceed; if not, the filter is overfit

**Step 3: If validated, deploy with conservative settings**
- Use mom30 > -0.003% (not -0.001%) to keep more trades
- Keep velocity gate at 0.3 (do NOT tighten to 0.15)
- Keep spike exhaustion filter (no downside, marginal upside)
- **Do NOT apply to SHORT trades** (insufficient sample)

**Step 4: Monitor and validate live**
- Track filter performance weekly
- Compare filtered vs unfiltered trades
- Re-evaluate after 50+ live filtered trades

---

## 7. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Overfitting | HIGH | Out-of-sample validation required |
| Time regime dependency | MODERATE | Monitor weekly, set review date |
| SHORT trade damage | CRITICAL | Do not apply filter to SHORT |
| 1m data coverage | HIGH | Fix data pipeline first |
| False precision | MODERATE | Use -0.003% threshold, not -0.001% |

**Overall Risk Rating: HIGH**  
**Confidence in my assessment: HIGH**  
**Confidence in the filter's value: MODERATE** (real but overstated)

---

## 8. Summary

The momentum slope filter is a **genuine improvement** with a solid economic rationale (don't enter when price is still falling hard). My numbers confirm ~84% WR on the analyzed sample, close to the analyst's claim.

However, the previous analysis commits several sins:
1. **Overfitting**: 421 tests on 140 trades
2. **Cherry-picking**: -0.001% threshold was selected from many tested
3. **Overstatement**: Claimed 85.9% WR, actual is 84.1% for the momentum-only filter
4. **Direction blindness**: Applied to SHORT trades with only 14 samples
5. **Implementation blindness**: Ignored that 40% of trades lack required data

The filter should be deployed **conservatively** after fixing data coverage and running out-of-sample validation. The velocity gate should NOT be tightened. The spike exhaustion filter can stay or go — it doesn't matter much.

**Bottom line: The filter is good but not as good as claimed. Validate before deploying.**
