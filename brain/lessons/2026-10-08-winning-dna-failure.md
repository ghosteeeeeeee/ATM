# Lesson Learned: Winning DNA Project Failed (3x)

**Date:** 2026-10-08
**Status:** Project killed — no predictive pre-entry edge exists
**Auditor:** Independent subagent (own-conclusions skill) — DISAGREE verdict, HIGH confidence

---

## What Was Attempted

Design a "Winning DNA" signal by analyzing pre-entry conditions (2 hours before trade) of top winning trades. Goal: find patterns that predict +20% winners.

---

## Three Fatal Flaws (All Caught by Auditor)

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

---

## The Honest Truth

**There is no pre-entry edge in the conditions we analyzed.**

When correctly measured at `open_time`:
- Winners were NOT already pumping before entry (+0.37% vs +0.40%)
- Winners did NOT have higher RSI before entry (52.1 vs 58.6 — reversed!)
- Winners did NOT have stronger trend structure (0.46 vs 0.48)
- Volume acceleration was mostly calculation bugs (47.7% of candles have volume=0)

The proposed 5-condition signal would have caught **0/11 winners** it was derived from.

---

## Why This Matters

Winners are winners because of what happens **AFTER** entry, not before. The market doesn't leave a predictable trail 2 hours before big moves.

**Implication:** Trying to predict winners from pre-entry conditions is a fool's errand. The "winning DNA" is survivorship bias, not a real pattern.

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

1. **Independent verification is non-negotiable.** The auditor caught fatal flaws I missed three times.
2. **Survivorship bias is insidious.** It's easy to see patterns in winners without checking losers.
3. **Time anchoring matters.** Always verify you're measuring the right window.
4. **Small samples lie.** 11 winners isn't enough to draw conclusions.
5. **Correlation ≠ causation.** Even if winners had higher RSI before entry, it doesn't mean high RSI causes wins.
6. **The market is efficient.** If there was a predictable 2-hour pre-entry signal, it would be arbitraged away.

---

## What NOT To Do

- ❌ Don't analyze only winners without losers (survivorship bias)
- ❌ Don't select winners by outcome magnitude and compare to all losers (selection-on-outcome)
- ❌ Don't anchor time windows at close_time when you mean open_time
- ❌ Don't trust candle volume data without checking for zeros (47.7% are zero)
- ❌ Don't design signals from group averages applied conjunctively (ecological fallacy)
- ❌ Don't skip independent verification

---

## Action Items

1. ✅ Kill the Winning DNA project
2. ✅ Clean up failed artifacts (plan, analysis DB, scripts)
3. ⏳ Investigate payoff ratio problem (why avg loss > avg win?)
4. ⏳ Consider RSI 50-70 confluence filter (only defensible finding: 59% vs 44%, n=206)
5. ⏳ Investigate 14 signals with >50% WR (r2_trend_short 75%, bb_bounce_v2_long 74%)

---

## Files

- **Failed report v1:** `brain/reports/winning-dna-report.md` (survivorship bias)
- **Failed report v2:** `brain/verdicts/2026-10-08-winning-dna-verification.md` (selection-on-outcome)
- **Failed report v3:** `brain/verdicts/2026-10-08-winning-dna-v2-verification.md` (time-anchor bug)
- **CEO briefing:** `brain/briefings/2026-10-08-ceo-winning-dna-failure.md`
- **This lesson:** `brain/lessons/2026-10-08-winning-dna-failure.md`

---

## Quote from Auditor

> "my corrected n=22 test suggests no real pre-entry edge exists for price change"

> "winners are winners because of what happens AFTER entry, not before"

> "improving loss size (payoff ratio) matters more than hunting DNA"
