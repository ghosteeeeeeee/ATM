# Lesson Learned: Winning DNA Project Failed (4x)

**Date:** 2026-10-08
**Status:** Project killed — no reliable pre-entry edge or habitat filters found
**Auditor:** Independent subagent (own-conclusions skill) — DISAGREE/PARTIAL verdicts, HIGH confidence

---

## What Was Attempted

1. Design a "Winning DNA" signal by analyzing pre-entry conditions of top winning trades
2. Design "habitat filters" to block signals when they fire outside their profitable regime

**Both attempts failed due to statistical errors caught by independent auditor.**

---

## Four Fatal Flaws (All Caught by Auditor)

### Attempt 1: Survivorship Bias
**Error:** Analyzed only 100 winners, claimed "pump-chain+ is #1 signal" (20.9% WR).
**Reality:** pump-chain+ has 48.4% WR — coin flip, not a losing signal.
**Auditor verdict:** DISAGREE — "compares top-100-by-PnL% survivors against ALL losers."

### Attempt 2: Selection-on-Outcome
**Error:** "Fixed" by comparing top-100 winners vs all losers, but still selected on outcome magnitude.
**Added errors:** Wrong time window (claimed "Oct 1-8" but data spans Aug 21-Oct 8), NULL-bucketing bug (68% of trades have NULL RSI), mislabeled counts (said "81 losers" but tables show 908).
**Auditor verdict:** DISAGREE — "did not fix the bias — it re-labeled it."

### Attempt 3: Wrong Time Anchor (Fatal)
**Error:** Analyzed "pre-entry" window anchored at `close_time` instead of `open_time`.
**Reality:** Winners averaged 290 minutes duration, so "pre-entry" window was actually INSIDE the winning trade. Measured the trade itself, not what led to it.
**Corrected results:** Price change +0.37% vs +0.40% (no difference), RSI reversed (52.1 vs 58.6), trend/volatility identical.
**Auditor verdict:** DISAGREE — "the 'winning DNA' is an artifact of a time-anchor bug."

### Attempt 4: Unreproducible Numbers + Filter Collision
**Error:** Proposed habitat filters based on signal × BTC zone × volatility analysis.
**Flaws found by auditor:**
- Two pump-chain- rows unreproducible (claimed n=46, actual n=10)
- Impact overstated 2.3x (+$3.64 claimed vs +$1.59 actual)
- Edge reversed sign in recent weeks (14d window shows blocking would LOSE money)
- Not statistically significant (p=0.18-0.29)
- Two of three proposals already live (didn't check existing implementations)
- Filter collision with SHORT_CONTINUUM (trapped trades in worst band: 40-60)
**Auditor verdict:** PARTIAL — "do not implement as written."

---

## The Honest Truth

**There is no reliable predictive edge in the conditions we analyzed.**

When correctly measured:
- Winners were NOT already pumping before entry
- Winners did NOT have higher RSI before entry
- Signal habitats exist but are not statistically significant
- Edges reverse sign in recent weeks
- Numbers don't reproduce

**The market doesn't leave a predictable trail we can exploit.**

---

## Why This Matters

Four attempts to find "winning DNA" or "signal habitats," four fatal flaws. The same pattern every time:
1. I find a "pattern" in the data
2. I don't verify it properly (reproducibility, statistical significance, out-of-sample validation)
3. The independent auditor catches fatal flaws
4. The pattern evaporates under scrutiny

**Key insight:** I cannot be trusted for quantitative analysis without independent verification.

---

## What Actually Works (Auditor's Recommendation)

The independent auditor found:

1. **True window win rate: 53.6%** (1005W/869L, n=1874)
2. **Expectancy is slightly NEGATIVE** — avg win +3.69% vs avg loss -4.01% (payoff ratio 0.92)
3. **The system is a 54% coin flip with negative payoff**

**The money is in fixing loss management (payoff ratio), not finding predictive signals.**

Why are avg losses 9% bigger than avg wins? That's the real problem to solve.

---

## Key Takeaways

1. **Independent verification is non-negotiable.** The auditor caught fatal flaws 4 times.
2. **Survivorship bias is insidious.** It's easy to see patterns in winners without checking losers.
3. **Time anchoring matters.** Always verify you're measuring the right window.
4. **Small samples lie.** n=5-8 isn't enough to draw conclusions.
5. **Correlation ≠ causation.** Even if winners had higher RSI before entry, it doesn't mean high RSI causes wins.
6. **Check existing implementations.** Don't re-propose shipped work.
7. **Check filter collisions.** New filters may conflict with existing ones.
8. **Require out-of-sample validation.** Edges that work in-sample often reverse out-of-sample.
9. **Statistical significance matters.** p>0.05 means the pattern could be noise.
10. **The market is efficient.** If there was a predictable signal, it would be arbitraged away.

---

## What NOT To Do

- ❌ Don't analyze only winners without losers (survivorship bias)
- ❌ Don't select winners by outcome magnitude and compare to all losers (selection-on-outcome)
- ❌ Don't anchor time windows at close_time when you mean open_time
- ❌ Don't trust candle volume data without checking for zeros (47.7% are zero)
- ❌ Don't design signals from group averages applied conjunctively (ecological fallacy)
- ❌ Don't skip independent verification
- ❌ Don't propose filters without checking existing implementations
- ❌ Don't propose filters without checking for collisions with existing filters
- ❌ Don't claim statistical significance without p-values
- ❌ Don't extrapolate from one week of data

---

## Action Items

1. ✅ Kill the Winning DNA project (4 attempts, all failed)
2. ✅ Clean up failed artifacts (plans, analysis DBs, scripts)
3. ⏳ Investigate payoff ratio problem (why avg loss > avg win?)
4. ⏳ Consider RSI 50-70 confluence filter (only defensible finding: 59% vs 44%, n=206, but needs validation)
5. ⏳ Investigate 14 signals with >50% WR (r2_trend_short 75%, bb_bounce_v2_long 74%)

---

## Files

- **Failed report v1:** `brain/reports/winning-dna-report.md` (survivorship bias)
- **Failed report v2:** `brain/verdicts/2026-10-08-winning-dna-verification.md` (selection-on-outcome)
- **Failed report v3:** `brain/verdicts/2026-10-08-winning-dna-v2-verification.md` (time-anchor bug)
- **Failed report v4:** `brain/verdicts/2026-10-08-signal-habitat-filters-verification.md` (unreproducible + collision)
- **CEO briefing:** `brain/briefings/2026-10-08-ceo-winning-dna-failure.md`
- **This lesson:** `brain/lessons/2026-10-08-winning-dna-failure.md`

---

## Quotes from Auditors

> "my corrected n=22 test suggests no real pre-entry edge exists for price change"

> "winners are winners because of what happens AFTER entry, not before"

> "improving loss size (payoff ratio) matters more than hunting DNA"

> "the plan's directional thesis has weak support, but its impact math is wrong by ~2.3x"

> "nothing is statistically significant (p=0.18–0.29)"

> "do not implement as written"

---

## Final Note

Four independent audits, four DISAGREE/PARTIAL verdicts. The pattern is clear: I cannot find reliable predictive edges in trading data. The market is efficient, and my analyses keep falling prey to statistical errors.

**The only path forward is:**
1. Fix the payoff ratio problem (why avg loss > avg win)
2. Focus on execution and risk management, not signal finding
3. Always use independent verification for any quantitative work
