# Independent Verification — Winning DNA Report

**Auditor:** independent subagent (fresh read, no priming beyond the task brief)
**Date:** 2026-10-08
**Sources verified directly:**
- `/root/.hermes/brain/reports/winning-dna-report.md` (read in full)
- `/root/.hermes/data/winning_trades_analysis.db` (SQLite — 1 table, `winning_trades`, 100 rows)
- PostgreSQL `brain` — `trades` (5,619 closed all-time) and the pre-computed `winner_loser_comparison` table (1,008 rows: 100 WINNER + 908 LOSER)
- All numbers below were produced by running my own queries. Nothing taken on trust.

---

## OVERALL VERDICT: **PARTIAL** (the report's own bottom line is directionally right; its "corrected" analysis and nearly every headline number are statistically invalid)

The single most important discovery, which the report missed: **the comparison window is not Oct 1–8. It is Aug 21 – Oct 8 (~7 weeks).** Only 8 of the 100 "winners" closed during Oct 1–8; 92 closed Aug 21 – Sep 30. The `winner_loser_comparison` table spans 2026-08-21 → 2026-10-08 for both outcomes. The report's header ("Top 100 winners + 81 losers in same period (Oct 1-8)") is wrong three ways: the window is 7 weeks, the loser count is 908 not 81, and winners and losers were never restricted to Oct 1–8.

Second most important: **the true win rate in that window is 53.6%** (1,005 winners / 1,874 closed trades), not ~11%. The report's "win rate" column is not a win rate of anything — it is (top-100-by-PnL% survivors in signal X) ÷ (those survivors + ALL losers in X). Since the window contains 1,005 real winners, the top-100 cut keeps only ~10% of them, so every "win rate" in the report is roughly an order of magnitude too low, and signals with fat-tailed winners are over-represented.

---

## Claim-by-claim verdicts

### 1. "pump-chain+ has 20.9% win rate (14 winners, 53 losers)"

**Verdict: DISAGREE**
**Evidence:**
- 53 losers ✓ — verified: `pump-chain+` has exactly 53 trades with `pnl_usdt <= 0` in the Aug 21 – Oct 8 window (the report's loser set is all-losers-in-window, matching `winner_loser_comparison`).
- 14 winners is only the number that made the top-100-by-PnL% cut. The true window record: **95 trades, 46W / 49L = 48.4%** (`pnl_pct > 0`). In Oct 1–8 alone: 15 trades, 9W / 6L = 60.0%.
- pump-chain+ is a coin flip, not a signal that "loses 80% of the time." The report's own reality-check sentence ("it's not a winning signal") is factually false in the opposite direction.
**Confidence: HIGH**

### 2. "EXTREME volatility has 12.5% win rate (48 winners, 337 losers)"

**Verdict: DISAGREE**
**Evidence:**
- The 48/337 counts exist in `winner_loser_comparison`, but the true window rates are: EXTREME **51.3%** (347W/330L, n=677), HIGH **55.0%** (338W/276L, n=614), NORMAL **55.3%** (308W/249L, n=557), FLAT **84.6%** (11W/2L, n=13).
- The relative ranking is **inverted** by the report: it claims EXTREME is best and HIGH worst; in reality EXTREME is *slightly worse* than HIGH/NORMAL. The report's recommendation "EXTREME is OK, don't filter it out" happens to still be defensible (51% vs 55% is not a disaster), but its supporting numbers and ranking are wrong.
**Confidence: HIGH**

### 3. "RSI 50-85 is the sweet spot with 17-20% win rate"

**Verdict: PARTIAL**
**Evidence:**
- **Methodology bug confirmed:** `entry_rsi_14` is NULL for 1,267 of 1,874 window trades (68%). The report's RSI bucketing silently folds NULLs into the "<30" bucket. Verified: its "<30: 701 trades (61W/640L)" = 49 genuinely-≤30 trades + **652 NULL-RSI trades**. Likewise, 58 of the 61 "<30 winners" in SQLite are NULL-RSI rows (only 3 winners truly had RSI ≤ 30).
- True NULL-separated rates in window: 50-70 = **59.2%** (206 trades) — genuinely the best bucket; >85 = 51.3% (n=39, 20W/19L); 70-85 = 49.5% (n=99); 30-50 = 44.2% (n=181); ≤30 = 43.9% (n=82); NULL = 55.1%.
- So the qualitative direction ("moderately overbought 50-70 is the best bucket") survives at ~59% vs ~44%, but: (a) the claimed 17–20% magnitudes are artifacts; (b) ">85 is best (20%)" does not hold — 51.3% with n=39 is within noise of 70-85's 49.5%; (c) "sweet spot 50-85" merges a real edge (50-70) with a middling bucket (70-85). A 50-70 floor/ceiling band is the defensible version of this finding.
**Confidence: HIGH** (on the numbers); the actionable kernel (favor 50-70 entries) is MEDIUM given n=206 and 7-day-effective sample after nulls.

### 4. "LONG has 11.3% win rate vs SHORT at 7.8% (LONG wins 45% more often)"

**Verdict: DISAGREE**
**Evidence:** True window rates: **LONG 53.5%** (611W/530L, n=1,141) vs **SHORT 53.8%** (394W/339L, n=733). There is no edge — SHORT is marginally higher. The report's "LONG has a real edge, aligns with the philosophy" conclusion is a pure artifact: the top-100-by-PnL% selection is 70% LONG because LONG positions happened to produce the biggest single-trade % spikes in this window, not because LONG wins more often. This is textbook selection-on-outcome bias, and it's the clearest proof that the "corrected" comparison did not actually correct the survivorship bias.
**Confidence: HIGH**

### 5. "market_phase metadata is missing from 97-100% of trades in PostgreSQL"

**Verdict: AGREE (with two important caveats)**
**Evidence:**
- October trades: `market_phase` present in **3 of 211** (1.4% → 98.6% missing). Daily breakdown matches the report (Oct 5: 1/32, Oct 6: 0/12, Oct 7: 0/13, plus my check: Oct 3: 1/34, Oct 4: 1/35).
- Full window: 3/1,874 (0.16%). `btc_score`: **209/209 in October (100%)**, 460 in September — so "btc_score is reliably written" is true for Sept onward (0 before Sept).
- **Caveat 1 — "bug" framing is questionable:** `market_phase` was never in the metadata historically (0% in June/July/Aug/Sept). The 3 October appearances look like a *very recent partial rollout*, not a regression. Calling it "a bug in the metadata writer" asserts a root cause that the data doesn't establish.
- **Caveat 2 — "only btc_score is reliably written" understates what exists:** October metadata also contains `btc_regime` (206/209), `wave_phase` (206/209), `btc_trend_bias`, `btc_linreg_bias` (206/209) — BTC context IS ~98% available under different key names. BTC-phase-adjacent analysis is partially possible today without waiting for a `market_phase` fix.
- Related data-integrity finding: `winner_loser_comparison.btc_phase` is 100% NULL (905/908 losers, 100/100 winners), yet the SQLite `winning_trades.btc_phase` is fully populated (RECOVERY 39, DECLINING 22, NEUTRAL 16, CALM 15, STORMY 8). That column came from an external enrichment that cannot be reconciled with PostgreSQL — so the report's stance "cannot trust BTC phase conclusions" is correct, and I confirm the original BTC-phase findings are unverifiable.
**Confidence: HIGH**

### 6. "The 'winning DNA' is mostly survivorship bias, not a reliable formula"

**Verdict: AGREE (and the problem is worse than the report says)**
**Evidence:**
- The bottom-line warning is correct: the top-100 winners share no reliable formula; leverage 5x (83%) and exit atr_sl_hit (74%) were verified in SQLite and are just defaults.
- But the report's "corrected" analysis **did not fix the bias — it re-labeled it.** The winner set is still selected on outcome magnitude (top-100 by PnL%, min +7.81%, max +47.53%), now compared against all losers over a 7-week window. Signals with fat tails (pump-chain+, ct_hot) get slots in the winner set; high-win-rate signals with modest winners get erased. Example: `bb-squeeze+` has a true 60.9% win rate (42W/27L, n=69) in the window and doesn't appear in the report's signal table at all.
- Concretely false claim in the report: **"No signal has >35% win rate."** True window win rates (n≥20): r2_trend_short 75.0%, bb_bounce_v2_long 74.0%, pump_chain 67.4%, volume-breakout-long+ 66.7%, bb_bounce_short 66.2%, ema300_dip 63.6%, bb-squeeze+ 60.9% … 14 signals exceed 50%.
- Also false: "they're just the ~11% of trades that happened to work out" — the real figure is **~54%**.
- Internal inconsistency: the report's tables total ~897–908 losers, but its header says "81 losers." (Neither matches Oct 1–8, which had ~89–100 actual losers.)
**Confidence: HIGH**

---

## Statistical issues found (beyond the claims)

1. **Window mislabeling (fatal).** "Oct 1–8" claimed; Aug 21 – Oct 8 used. Winners: 8/100 actually from Oct 1–8.
2. **Selection-on-outcome (fatal).** Top-100-by-PnL% winners vs all losers → every per-signal/per-regime/per-direction "win rate" is a truncated ratio, biased in favor of high-variance signals. It cannot estimate any true rate.
3. **NULL-bucketing bug (serious).** 68% of window trades lack `entry_rsi_14`; the RSI "<30" bucket is 93% NULL rows. Any conclusion drawn from that bucket (winners or losers) is void.
4. **Small samples (acknowledged by report, confirmed):** RSI >85 (n=39 total, 5 winners in cut), volume-breakout-long+ (n=24 window), open_skies (n=31 window, true WR 54.8% — report said 22.2%).
5. **Non-independence:** 1,008 comparison rows cover only 90 distinct tokens — heavy same-coin repetition; trades are correlated, so effective sample size is smaller than row counts suggest.
6. **Win rate ≠ profitability (context the report omits):** window expectancy is slightly negative — avg win +3.69% / avg loss −4.01% (payoff ratio ~0.92), total −$8.56 across 1,874 paper trades. The system is a ~54% coin flip with slightly negative payoff, not the ~11% catastrophe the report implies, and not a money printer either.
7. **Headline arithmetic inconsistency:** "81 losers" (header) vs 897/908 (tables) vs ~98 actual Oct 1–8 losers.

## What the report got RIGHT

- The survivorship-bias warning itself (claim 6) — correct, and important.
- The metadata finding (claim 5) — correct numbers.
- Its own data-quality caveats (small samples, 7-day limitation — actually the limitation is 7 *weeks* for the comparison, still short).
- Recommendations 1 and 6 (don't chase winner characteristics; fix/obtain BTC phase data) remain sound advice.
- All SQLite winner-side counts (signal mix, regime mix, LONG 70/SHORT 30, leverage, exit_reason, RSI winners incl. the NULL-contaminated buckets) reproduce exactly — the report faithfully described the pre-computed tables it was handed. The failure is in the tables' construction, not in transcription.

## Bottom line for the CEO

Do **not** act on the report's win-rate numbers, its LONG-bias justification, or its EXTREME-vs-HIGH ranking — all invalid. The defensible residual findings: (a) entries at RSI 50–70 have a real hit-rate edge (~59% vs ~44% below 50, n=206); (b) direction genuinely doesn't matter (53.5% vs 53.8%); (c) volatility regime barely matters (51–55%); (d) `market_phase` is effectively absent from metadata while `btc_regime`/`wave_phase` are ~98% present; (e) the system's true window hit rate is 53.6% with slightly negative expectancy — improving the payoff ratio (avg loss size), not "finding DNA," is where the money is.
