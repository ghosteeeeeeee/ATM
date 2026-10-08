# Independent Verdict: Winning DNA Signal v2

**Date:** 2026-10-08
**Auditor:** Independent verification agent (own-conclusions)
**Plan verified:** `/root/.hermes/plans/winning-dna-signal-v2.md`
**Verdict:** **DISAGREE**

---

## Bottom Line

The "winning DNA" is an artifact of a **time-anchor bug**: both analysis scripts anchor the "2 hours before entry" window at `close_time` instead of `open_time` (`/tmp/analyze_preentry.py` line 129: `analyze_preentry(token, close_time, ...)`; `/tmp/winning_dna_v2.py` line 46: `entry_ts = close_ts - timedelta(hours=1)`). The measured window is therefore the *final 2 hours of the trade*, not the pre-entry period. The top-22 winners held an average of **290 minutes** (median 268m), so for **10 of the 11 analyzed winners the entire "pre-entry" window sits INSIDE the winning move**. Of course it shows +2.93%, rising RSI, and uptrend structure — that is the profit-taking stretch of a trade that already won. Losers held an average of only 100 minutes (median 64m), so their window is a mix of in-trade and genuine pre-entry data. The comparison is structurally rigged.

I re-ran their script verbatim (numbers reproduced exactly: +2.93 vs -0.01, 2.87x vs 1.87x, RSI 62.8 vs 44.8), then recomputed everything anchored at the **actual `open_time`** from PostgreSQL, using both `candles_5m` and `candles_1m`. The DNA disappears.

---

## Claim-by-claim verdicts

### 1. "Winners were already pumping +2.93% over 2h before entry (losers flat -0.01%)"
**Verdict: DISAGREE — Evidence: HIGH**

Correctly anchored at `open_time`:

| Sample | Method | Winners | Losers | Significance |
|---|---|---|---|---|
| 11 winners (5m candles) | THEIR close-anchored | +2.93% | -0.01% | — |
| 11 winners (5m candles) | CORRECT open-anchored | **+0.37%** | **+0.40%** | Welch t=-0.08; MWU z=-0.53 (ns) |
| 22 winners (1m candles) | CORRECT open-anchored | **+1.22% mean, +0.29% median** | +0.40% mean, +0.27% median | Welch t=1.32 (ns); MWU z=0.29 (ns) |

- Medians are virtually identical (+0.29% vs +0.27%). 10/22 winners had **negative** real pre-entry price change (ETH -0.23%, HYPE -1.70%, GRASS -0.58%, NEO -0.31%...). Only 5/22 met the proposed ≥2% threshold.
- Spot-check (CRV 15984, manual): trade opened 2026-10-07 22:17; real pre-entry 2h = **+1.21%**; their "pre-entry" window (23:25–01:20) lies entirely inside the 184-minute trade and shows +2.42%.
- No statistically significant winner/loser difference exists in genuine pre-entry price change.

### 2. "Volume accelerating 2.87x in winners vs 1.87x in losers"
**Verdict: DISAGREE — Evidence: HIGH**

- **47.7% of all rows in `candles_5m` have volume=0.** In 9 of the 11 winner windows the first-30m volume is exactly zero, silently hitting the fallback `else 1.0` in the script.
- The claimed 2.87x winner average is: **9 fallback 1.0s, one 1.02, and one outlier APT=21.58** (a 38-minute trade). Median winner volume trend = **1.00**. One trade drives the entire claim.
- Correct open-anchored: winners 1.53 (median ~1.0) vs losers 1.76 (median 1.03) — losers slightly *higher*, both dominated by zero-volume fallbacks. The metric is unusable with this data.

### 3. "Uptrend structure HH/HL 0.67 vs 0.44"
**Verdict: DISAGREE — Evidence: HIGH**

Correct open-anchored: winners **0.46** vs losers **0.48** — identical. The 0.67 vs 0.44 gap is in-trade structure (the winning move itself), not pre-entry structure.

### 4. "RSI overbought at entry 62.8 vs 44.8"
**Verdict: DISAGREE — Evidence: HIGH**

Correct open-anchored: winners **52.1** vs losers **58.6** — the difference **reverses** (losers higher). Individual winner pre-entry RSI14 ranges wildly from 17 (ETH) to 95 (JUP). There is no coherent pre-entry RSI signature. (Also note: their RSI is a nonstandard simple 14-bar average on 5m closes, not Wilder smoothing — secondary issue.)

### 5. "Higher volatility 0.49% vs 0.30%"
**Verdict: DISAGREE — Evidence: HIGH**

Correct open-anchored: winners **0.27%** vs losers **0.29%** — identical.

### 6. "This is a trend continuation with volume confirmation pattern"
**Verdict: DISAGREE — Evidence: HIGH**

The pattern describes the *in-trade* behavior of long-duration winners (which by definition continued trend-wise after entry), not anything observable before entry.

### 7. "Proposed signal: Trend Continuation+ with thresholds (≥2% 2h, ≥1.5x vol, ≥0.55 trend, RSI≥55, range≥0.35%)"
**Verdict: DISAGREE — Evidence: HIGH**

- Applying all five thresholds to **correct** pre-entry data: **0/11 winners pass. 0/50 losers pass.** The signal would have caught **none** of the top winners it was derived from.
- Even under their own flawed close-anchored numbers: 0/11 winners pass all five conditions (e.g. CRV fails volume by 1.47 vs 1.50). Thresholds were derived from group averages and applied conjunctively — an ecological fallacy.
- n=11 vs 50, no power analysis, no time-matching, mixed directions (2 SHORT winners averaged into a "bullish" DNA), 2 paper trades mixed into the live loser set, AVAX×2 and 7/11 pump-chain+ (signal-confounded sample).

---

## Methodology flaws found (beyond the anchor bug)

1. **Wrong time anchor (fatal).** `close_time` used as entry proxy although `open_time` was available in both the winners DB and PostgreSQL. All six headline metrics are contaminated by in-trade data, asymmetrically (winners' durations 290m avg vs losers' 100m avg; 10/11 winner windows fully in-trade vs 15/50 loser windows).
2. **"Insufficient candle data" was false.** The 11/22 success rate is because `candles_5m` only covers **Sep 8 – Oct 8, 2026** while winners span Aug 21 – Oct 7. `candles_1m` covers all of it (verified 120/120 pre-entry candles for August trades ETH/HYPE). All 22 winners were analyzable; I analyzed all 22 — the conclusion does not change.
3. **Period mismatch.** The "50 most recent losers" actually span only **Oct 4–8** (149 losers exist over 14d; the 50 latest compress into 4.5 days). 7 of the 11 analyzed winners (Sep 9–21) predate the loser window entirely. Regime is uncontrolled.
4. **Asymmetric outcome selection.** Winners = extreme top tail (+20% to +47%, avg ~+26%); losers = typical small losses (avg -3.1%, worst -6.9%). Not comparable populations; amplifies any in-trade measurement.
5. **Direction mixing without sign normalization.** APT/DYDX SHORT winners' pre-entry windows were averaged raw into a "bullish pumping" claim.
6. **Volume data quality ignored.** Near-half of 5m volume fields are zero; silent `else 1.0` fallback masks it; no data-quality flag in the output table.
7. **Winner DB selection itself is valid** (verified: top 100 by pnl_pct are all live, all closed, exactly 22 >20%; atr_sl_hit 74/100 = 74% claim checks out). The bias is entirely in the winner-vs-loser comparison, not the winner list.
8. **Circularity repeat.** v1 was DISAGREE'd for survivorship/circularity; v2 moved the same circular measurement from entry to "pre-entry" by one time-anchor mistake. Same disease, new symptom.

---

## What survives

- Winner/loser DB construction (top-100 live winners, top-22 >20%) — verified correct.
- Exit-reason stats (74% atr_sl_hit over top-100; 82% over top-22) — verified.
- The *intuition* "trade coins already moving with volume" may still be true — but this analysis provides **zero evidence** for it. It must be re-tested from scratch with `open_time` anchoring, matched periods, direction-normalized metrics, and volume-field data-quality filtering. The plan's own Phase 1 (100+/100+ samples) was right to be required; it should be done before any constants are added to `hermes_constants.py`.

## Recommendation

**Do not implement `trend_continuation_long.py`. Do not add the TC_* constants.** Re-run the pre-entry study correctly (open_time anchor, time-matched loser controls, candles_1m for full coverage, exclude zero-volume windows). If a real pre-entry edge exists, it will show up there; based on my corrected 22-vs-50 test (medians +0.29% vs +0.27%, ns), it probably does not exist for price change.

---

## Files produced by this audit

- `/tmp/audit_correct_preentry.py` — corrected open-anchored analysis (reproducible)
- Reproduced original: `python3 /tmp/analyze_preentry.py` (exact match to plan numbers)
