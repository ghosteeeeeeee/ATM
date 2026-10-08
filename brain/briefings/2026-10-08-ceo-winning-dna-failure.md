# CEO Briefing: Winning DNA Project Failed

**Date:** 2026-10-08
**Status:** Analysis flawed, auditor verified, recommendations attached
**Time spent:** ~2 hours
**Result:** Negative — project cannot deliver what was requested

---

## TL;DR

You asked me to "find winning DNA and design a new signal." I failed. Two independent audits found my analysis was statistically invalid. The honest answer: **there is no "winning DNA" to replicate.** The system is a 53.6% coin flip with slightly negative expectancy. The money is in fixing loss management (payoff ratio 0.92), not finding new signals.

**Recommendation:** Pivot from "find winning DNA" to "improve payoff ratio." Kill the new-signal project.

---

## What Went Wrong

### Attempt 1: Survivorship Bias
I analyzed the top 100 winning trades and claimed:
- "pump-chain+ is the #1 signal" (14 winners, +$7.68 total)
- "EXTREME volatility is king" (48% of winners)
- "RSI >85 has highest avg PnL" (+27.8%)
- "Overbought entries work!"

**Problem:** I only looked at winners, not losers. Every signal has both.

### Attempt 2: Selection-on-Outcome Bias  
I "fixed" it by comparing top-100 winners vs all losers in the window. Claimed:
- "pump-chain+ has 20.9% win rate" (loses 80%)
- "EXTREME has 12.5% win rate" (still best)
- "LONG has edge" (11.3% vs 7.8%)

**Problem:** Still compared top-100-by-PnL% winners (selected on outcome) vs all losers. Added wrong time window (claimed "Oct 1-8" but data spans Aug 21-Oct 8), NULL-bucketing bug (68% of trades have NULL RSI), and mislabeled counts (said "81 losers" but tables show 908).

### Auditor's Verdict: PARTIAL (most claims DISAGREE)

The independent auditor ran their own queries and found:

| My Claim | Reality |
|----------|---------|
| pump-chain+ WR 20.9% | **48.4%** (coin flip) |
| EXTREME best regime (12.5%) | **51.3%** (slightly WORSE than HIGH/NORMAL) |
| LONG has edge (11.3% vs 7.8%) | **53.5% vs 53.8%** (no edge) |
| No signal >35% WR | **14 signals exceed 50%** (r2_trend_short 75%) |
| System wins ~11% | **53.6%** |

---

## The Real Picture (Verified by Auditor)

**Window:** Aug 21 – Oct 8, 2026 (7 weeks)
**Total trades:** 1,874 (1,005 winners, 869 losers)
**True win rate:** 53.6%
**Expectancy:** Slightly negative

| Metric | Value |
|--------|-------|
| Avg win | +3.69% |
| Avg loss | -4.01% |
| Payoff ratio | 0.92 |
| Total PnL (paper) | -$8.56 |

**Translation:** We win 54% of trades but lose more on losers than we win on winners. The system is a coin flip with negative payoff.

---

## What's Actually Actionable

### 1. Payoff Ratio Problem (HIGH PRIORITY)
- Avg losses (-4.01%) are 9% bigger than avg wins (+3.69%)
- This is why the system is unprofitable despite 54% WR
- **Question for you:** Why are losses bigger? Bad stop-losses? No profit-taking? Letting losers run?

### 2. RSI 50-70 Edge (MEDIUM PRIORITY)
- The one defensible finding from the analysis
- Entries at RSI 50-70 have **59.2% win rate** vs 44% below 50 (n=206)
- Not 17-20% as I claimed — that was NULL-bucketing artifact
- **Recommendation:** Consider adding RSI 50-70 as a confluence filter (not a hard block)

### 3. `market_phase` Metadata Rollout (LOW PRIORITY)
- Currently missing from 98.6% of trades (3/211 in October)
- Auditor says it "never existed historically" — looks like a **partial rollout**, not a bug
- `btc_regime` and `wave_phase` are ~98% present (different keys)
- **Question for you:** Is someone actively rolling this out? Should we wait?

### 4. 14 Signals Exceed 50% WR (INFORMATIONAL)
Auditor found signals with >50% win rate that didn't appear in my analysis:
- r2_trend_short: 75.0% (n=20)
- bb_bounce_v2_long: 74.0% (n=?)
- pump_chain: 67.4% (n=?)
- volume-breakout-long+: 66.7% (n=?)
- bb-squeeze+: 60.9% (n=69)

**These might be worth investigating separately** — not as "winning DNA" but as "consistently profitable signals."

---

## What NOT To Do

Based on the auditor's findings, do NOT:

1. **Build a "Winning DNA" signal** — the DNA doesn't exist; winners are just the 54% that happened to work
2. **Trust my earlier reports** — pump-chain+ doesn't "lose 80%," EXTREME isn't "king," LONG has no edge
3. **Raise RSI ceiling to 95+** — RSI >85 has 51.3% WR (noise, n=39)
4. **Assume EXTREME volatility = good** — it's slightly worse than HIGH/NORMAL
5. **Chase monster winners** — the top-100 winners are outliers, not a formula

---

## My Recommendation

**Kill the Winning DNA project.** It cannot deliver what was requested because the premise is false: there is no secret formula in the winners.

**Pivot to:**
1. **Fix payoff ratio** — understand why avg loss > avg win. This is the real profitability lever.
2. **Investigate the 14 signals with >50% WR** — not as "DNA" but as consistently profitable systems worth scaling.
3. **Consider RSI 50-70 confluence filter** — the one real edge found (59% vs 44%).

**Time spent:** ~2 hours
**Value delivered:** Negative — I made errors that required auditor correction
**Lesson learned:** You were right to insist on independent verification. My "re-check" didn't catch the flaws; the auditor did.

---

## Files

- **Flawed analysis:** `brain/reports/winning-dna-report.md`
- **Auditor verdict:** `brain/verdicts/2026-10-08-winning-dna-verification.md`
- **Analysis DB (winner data only, do not use for win rates):** `data/winning_trades_analysis.db`

---

**Awaiting your decision on:**
1. Kill the Winning DNA project? (recommend: YES)
2. Investigate payoff ratio problem? (recommend: YES, high priority)
3. Investigate 14 signals with >50% WR? (recommend: YES, medium priority)
4. Add RSI 50-70 confluence filter? (recommend: MAYBE, needs backtest)
5. Wait for `market_phase` rollout to complete? (recommend: YES, low priority)
