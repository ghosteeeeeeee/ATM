# Lesson Learned: Winning DNA Project Failed (6x)

**Date:** 2026-10-08
**Status:** Project killed — no reliable predictive edge exists
**Auditors:** 2 independent subagents (own-conclusions skill) — PARTIAL verdicts, HIGH confidence

---

## What Was Attempted

1. Design a "Winning DNA" signal by analyzing pre-entry conditions of top winning trades
2. Design "habitat filters" to block signals when they fire outside their profitable regime
3. Design "BEAR_TREND + falling" filter to block trades in worst market conditions
4. Design "Winning DNA Formula" based on comprehensive comparison of 20 winners vs 20 losers

**All attempts failed due to statistical errors caught by independent auditors.**

---

## Six Fatal Flaws (All Caught by Auditor)

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

### Attempt 5: BEAR_TREND + Falling Filter
**Error:** Proposed blocking trades during BEAR_TREND + falling wave phase.
**Flaws found by auditor:**
- "Period 3" was full sample relabeled (no genuine out-of-sample validation)
- Fails multiple-comparison correction (p=0.024 raw, Bonferroni p=0.39)
- Interaction isn't statistically real (within BEAR_TREND, falling vs non-falling p=0.168)
- Time period wrong (btc_regime starts Sep 12, not Sep 1)
- Wave-phase table unreproducible (plan says 46.8%, actual 43.7%)
**What DID reproduce:** 12/14 claims exact, PnL effect solid (p=0.0077) but dollars trivial ($13.57 avg position).
**Auditor verdict:** PARTIAL — "shadow mode only — don't treat '+1.6% WR' as validated."

### Attempt 6: Winning DNA Formula (20 Winners vs 20 Losers)
**Error:** Comprehensive comparison of top 20 winners vs 20 losers to find "winning DNA."
**Flaws found by auditor:**
- "75% SHORT losers" manufactured by undisclosed signal filter (raw losers are 10L/10S)
- Direction claim DISAGREE: full population 59.4% vs 58.7% LONG (p=1.000)
- Signal RSI claim DISAGREE: full population 52.4 vs 52.2 (p=0.880)
- Speed claim DISAGREE: effect REVERSES in full population
- Trailing exits claim PARTIAL: mechanically circular (trailing only fires in profit)
- "No losers use 10x" vacuous: only ONE 10x trade exists in window
**What DID reproduce:** All numbers exact, but only under undisclosed cohort definition.
**Auditor verdict:** PARTIAL — "do not implement Phases 1-4 as written."

---

## The Honest Truth

**There is no reliable predictive edge in the conditions we analyzed.**

When correctly measured with proper statistical tests:
- Winners were NOT already pumping before entry
- Winners did NOT have higher RSI before entry
- Winners do NOT favor LONG (full population: p=1.000)
- Winners do NOT have higher speed (effect reverses)
- Signal habitats exist but are not statistically significant
- Edges reverse sign in recent weeks
- Numbers don't reproduce when you remove hidden filters

**The market doesn't leave a predictable trail we can exploit.**

---

## What Actually Works (Auditor-Verified)

The independent auditors found:

1. **True window win rate: 53.6%** (1005W/869L, n=1874)
2. **Expectancy is slightly NEGATIVE** — avg win +3.69% vs avg loss -4.01% (payoff ratio 0.92)
3. **The system is a 54% coin flip with negative payoff**
4. **profit-monster-trail already handles 45% of winning exits** (79.7% WR) — already shipped
5. **BTC regime spread is a genuine null** (p=0.93) — winners ARE spread across all regimes
6. **RSI-band confluence might have something** (needs own validation)

**The money is in fixing loss management (payoff ratio), not finding predictive signals.**

Why are avg losses 9% bigger than avg wins? That's the real problem to solve.

---

## Data Bugs Found (See-Something-Say-Something)

1. **`trailing_activated` column is dead** — 0/832 populated, but trailing exits clearly fire (exit_reason shows them). Fix the writer.
2. **`signal_rsi_14` column populated in only 36/892 rows** — feature recording gap.
3. **`entry_rsi_14` NULL in ~33% of trades** — data completeness issue.
4. **`trade_duration` column is in seconds, not minutes** — footgun for future analysts.

---

## Key Takeaways

1. **Independent verification is non-negotiable.** The auditor caught fatal flaws 6 times.
2. **Survivorship bias is insidious.** It's easy to see patterns in winners without checking losers.
3. **Selection-on-outcome is subtle.** Comparing top-K winners vs all losers still has bias.
4. **Time anchoring matters.** Always verify you're measuring the right window.
5. **Small samples lie.** n=5-20 isn't enough to draw conclusions.
6. **Correlation ≠ causation.** Even if winners had higher RSI before entry, it doesn't mean high RSI causes wins.
7. **Check existing implementations.** Don't re-propose shipped work.
8. **Check filter collisions.** New filters may conflict with existing ones.
9. **Require out-of-sample validation.** Edges that work in-sample often reverse out-of-sample.
10. **Statistical significance matters.** p>0.05 means the pattern could be noise.
11. **Multiple-comparison correction matters.** Testing 16 cells and picking the best is not discovery.
12. **Full population may reverse cohort findings.** Top-K samples can mislead.
13. **The market is efficient.** If there was a predictable signal, it would be arbitraged away.

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
- ❌ Don't use top-K samples without checking full population
- ❌ Don't hide cohort definitions (auditor will find them)
- ❌ Don't relabel in-sample slices as "out-of-sample validation"
- ❌ Don't ignore multiple-comparison correction

---

## Action Items

1. ✅ Kill the Winning DNA project (6 attempts, all failed)
2. ✅ Clean up failed artifacts (plans, analysis DBs, scripts)
3. ⏳ Investigate payoff ratio problem (why avg loss > avg win?)
4. ⏳ Validate RSI-band confluence (only surviving lead)
5. ⏳ Fix data bugs (trailing_activated, signal_rsi_14, trade_duration units)
6. ⏳ Investigate 14 signals with >50% WR (r2_trend_short 75%, bb_bounce_v2_long 74%)

---

## Files

- **Failed report v1:** `brain/reports/winning-dna-report.md` (survivorship bias)
- **Failed report v2:** `brain/verdicts/2026-10-08-winning-dna-verification.md` (selection-on-outcome)
- **Failed report v3:** `brain/verdicts/2026-10-08-winning-dna-v2-verification.md` (time-anchor bug)
- **Failed report v4:** `brain/verdicts/2026-10-08-signal-habitat-filters-verification.md` (unreproducible + collision)
- **Failed report v5:** `brain/verdicts/2026-10-08-bear-trend-filter-verification.md` (no out-of-sample)
- **Failed report v6:** `brain/verdicts/2026-10-08-winning-dna-formula-verification.md` (hidden filters)
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

> "shadow mode only — don't treat '+1.6% WR' as validated"

> "all plan numbers reproduce exactly — but only under a cohort definition the plan never discloses"

> "full population 59.4% vs 58.7% LONG (p=1.000)"

> "do not implement Phases 1-4 as written"

---

## Final Note

Six independent audits, six DISAGREE/PARTIAL verdicts. The pattern is clear: I cannot find reliable predictive edges in trading data. The market is efficient, and my analyses keep falling prey to statistical errors.

**The only path forward is:**
1. Fix the payoff ratio problem (why avg loss > avg win)
2. Focus on execution and risk management, not signal finding
3. Always use independent verification for any quantitative work
4. Fix the data bugs found during this analysis

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
