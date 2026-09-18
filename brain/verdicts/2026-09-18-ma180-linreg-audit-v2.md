# Independent Audit v2: LINREG MA180 Filter Analysis (Corrected Run)

**Auditor:** Independent (fresh-read, no prior context)
**Date:** 2026-09-18
**Script:** `scripts/analysis/linreg_ma180_analysis.py`
**Data:** `data/linreg_ma180_analysis.db` (3,988 rows), PostgreSQL brain DB (5,122 closed trades), `data/candles.db` (1m candles)

---

## METHOD

1. Read the analysis script line-by-line for logic bugs
2. Ran independent SQL queries against the analysis DB to verify every claimed number
3. Spot-checked 12 individual trades: pulled entry times/tokens, looked up candles in `candles.db`, manually computed MA180 and linreg slope, compared to stored values
4. Verified alignment logic across all windows and directions
5. Checked temporal distribution: analyzed vs skipped by month
6. Verified PnL matches between PostgreSQL and analysis DB
7. Computed statistical significance (Sharpe-like ratios, 95% confidence intervals)
8. Checked for duplicate candles or data quality issues in the backfill
9. Tested the combined filter claim under different time periods (May-Jul vs Aug-Sep)

---

## CODE REVIEW

### MA180 Calculation — ✅ CORRECT
- `compute_ma()` (line 155): standard rolling average, first valid MA at index `period-1` (179)
- No off-by-one errors. Verified against 12 manual computations.

### Linreg Slope Computation — ✅ CORRECT
- `compute_linreg_slope()` (line 169): filters None values, uses `np.polyfit(indices, vals, 1)`
- Returns slope normalized by mean value as % per candle: `m / mean_val * 100`
- Minimum 10 valid points required
- All 12 spot-checks matched to 6+ decimal places

### Alignment Logic — ✅ CORRECT
- LONG aligned = slope > 0, SHORT aligned = slope < 0 (threshold = 0.0)
- All 3,988 trades have non-NULL slopes for all windows — no classification gaps

### is_win Definition — ⚠️ DESIGN CHOICE (unchanged from v1)
- `is_win = 1 if pnl_usdt > 0 else 0`
- Breakeven trades (pnl_usdt = 0) counted as losses
- This deflates WR by ~2-3 percentage points
- Not a bug, but affects interpretation

### `analysis_summary` Bug — 🐛 BUG (still present)
- Line 515: `trades_skipped` hardcoded to `0` — should be `1134`
- Line 515: `total_trades` parameter set to `len(results)` for both `total_trades` and `trades_analyzed` — the actual total from PG is 5,122
- Does not affect analysis results, only the summary metadata

### Hardcoded Path — ⚠️ MINOR
- Line 27: `CANDLES_DB = '/root/.hermes/data/candles.db'` is hardcoded instead of importing from `paths.py`
- Value matches, so no functional issue, but violates the single-source-of-truth convention

### NULL Handling — ✅ CORRECT
- 0 NULL slopes across all 3,988 trades for all windows
- Minimum candle threshold (190) met by all trades: min candles_available = 213

---

## CLAIM-BY-CLAIM VERDICT

### Claim 1: "3,988 out of 5,119 closed trades were analyzed (1,131 skipped)"
**Verdict: PARTIAL**
- Analyzed: **3,988 ✅**
- Total: **5,122** (not 5,119 — PostgreSQL shows 5,122 closed trades with non-null token/direction/open_time)
- Skipped: **1,134** (not 1,131)
- Minor discrepancies in total/skip counts (off by 3 trades)

### Claim 2: "With full data, alignment edge is POSITIVE at longer windows: 120-candle window shows aligned trades have +3.1% WR"
**Verdict: AGREE ✅ (but misleading)**
- Window 120 overall: Aligned 47.1% WR vs Counter 44.0% WR = **+3.1% WR edge ✅**
- However, this is a COMPOSITE of two opposite effects:
  - **May-Jul: aligned is BETTER** (+5.4% WR, +$6.12 total PnL)
  - **Aug-Sep: aligned is WORSE** (-1.1% WR, -$11.35 total PnL)
- The edge is NOT robust across time periods. See "CRITICAL FINDINGS" below.

### Claim 3: "SHORT alignment helps significantly (+4.1% WR, +$3.54 PnL)"
**Verdict: AGREE ✅ (exact match)**
- SHORT Aligned (120): 1,253T, 581W (46.4%), Total: -$0.63
- SHORT Counter (120): 901T, 381W (42.3%), Total: -$4.17
- WR Edge: **+4.1%** ✅
- Total PnL difference: **+$3.54** ✅
- Avg PnL difference: **+$0.004125/trade** ✅

### Claim 3b: "LONG alignment helps WR (+2.0%) but hurts PnL"
**Verdict: AGREE ✅ (exact match)**
- LONG Aligned (120): 1,054T, 505W (47.9%), Avg: -$0.00835
- LONG Counter (120): 780T, 358W (45.9%), Avg: -$0.00004
- WR Edge: **+2.0%** ✅
- But aligned avg PnL is much worse: -$0.008 vs nearly zero ✅

### Claim 4: "BEST filter: Price near MA (<0.75%) + 120-candle alignment = 49.8% WR, +$1.24 total PnL"
**Verdict: AGREE ✅ (exact match)**
- Combined filter: 1,302T, 648W (**49.8%**), Total PnL: **+$1.24** ✅
- This is the ONLY profitable filter combination in the entire analysis

### Claim 5: "Overextension is still bad: blocking slope >±0.02% improves WR from 45.8% to 46.0%"
**Verdict: AGREE ✅ (exact match, but trivial)**
- Overall WR: 45.8% ✅
- |slope_60| ≤ 0.02%: 3,784T, 46.0% ✅
- Improvement: **+0.2%** — real but essentially noise
- The 204 blocked trades (5.1% of total) have 41.7% WR, so removing them helps slightly

### Claim 6: "The previous 'counter-trend works' finding was an ARTIFACT of the temporal bias"
**Verdict: DISAGREE ❌ (overstated)**
- The previous audit found counter-trend was better in Aug-Sep data. In the corrected run:
  - Aug-Sep: Counter 51.9% WR vs Aligned 50.8% WR — **counter-trend IS still better in the recent period**
  - May-Jul: Aligned 41.9% WR vs Counter 36.5% WR — aligned is better here
- The finding didn't disappear — it was MASKED by adding May-Jul data where the opposite effect dominates
- The temporal bias didn't create a phantom effect; it hid a real regime difference

### Claim 7: "Overall system: 45.8% WR, -$13.63 total PnL across 3,988 trades"
**Verdict: AGREE ✅ (exact match)**
- 3,988T, 1,825W (**45.8%**), Total PnL: **-$13.63** ✅

### Claim 8: "LONG + Slope Flat + Price below MA (-1% to -0.2%): 51% WR, +$3.4, 397 trades"
**Verdict: PARTIAL**
- Actual: **435 trades** (not 397), **51.3% WR**, **+$3.61** (not +$3.4)
- Direction correct, numbers approximate — the sample size changed between runs
- The claimed 397 was from the previous 1,885-trade run; the corrected run has 435

---

## CRITICAL FINDINGS

### 🚨 REGIME FLIP: Alignment Edge Reverses Between Periods

This is the single most important finding. The overall +3.1% WR alignment edge at window 120 is a **composite of two opposite effects**:

| Period | Aligned WR | Counter WR | WR Edge | Total PnL Edge |
|--------|-----------|------------|---------|----------------|
| May-Jul | 41.9% | 36.5% | **+5.4%** | **+$6.71** |
| Aug-Sep | 50.8% | 51.9% | **-1.1%** | **-$11.35** |
| **Overall** | **47.1%** | **44.0%** | **+3.1%** | **-$4.64** |

The "overall +3.1% edge" is driven entirely by May-Jul data, where aligned trades had a large edge. In the more recent Aug-Sep period (which is more representative of current market conditions), **aligned trades are slightly WORSE**.

Month-by-month breakdown (window 120):
- May: Edge -2.6% WR (aligned worse)
- Jun: Edge +6.4% WR (aligned much better) ← drives the overall edge
- Jul: Edge +4.3% WR (aligned better)
- Aug: Edge -1.3% WR (aligned worse)
- Sep: Edge -2.9% WR (aligned worse)

### 🚨 COMBINED FILTER PROFITABILITY IS PERIOD-DEPENDENT

The combined filter (+$1.24 overall) breaks down by period:

| Period | Trades | WR | Total PnL | Avg PnL/trade |
|--------|--------|-----|-----------|---------------|
| May-Jul | 503 | 41.9% | **+$3.04** | +$0.006 |
| Aug-Sep | 799 | 54.7% | **-$1.80** | -$0.002 |
| **Overall** | **1,302** | **49.8%** | **+$1.24** | +$0.001 |

In Aug-Sep (the more recent and presumably more relevant period):
- The combined filter still improves WR (+3.5% vs baseline)
- But the total PnL is **NEGATIVE** (-$1.80)
- The filter reduces losses but does NOT generate profit in the recent period

### 🚨 STATISTICAL SIGNIFICANCE: NONE OF THE CLAIMS PASS 95% CI

| Filter | Avg PnL/trade | Std Dev | SE | 95% CI | Significant? |
|--------|--------------|---------|-----|--------|-------------|
| Combined (all data) | +$0.0010 | $0.0976 | $0.0027 | [-$0.004, +$0.006] | **NO** (includes zero) |
| LONG+Flat+Below MA | +$0.0083 | $0.0987 | $0.0047 | [-$0.001, +$0.018] | **BORDERLINE** |
| Baseline (all trades) | -$0.0034 | ~$0.10 | ~$0.0016 | [-$0.007, -<0.001] | Yes (significant loss) |

The combined filter's positive PnL is **NOT statistically significant at 95% confidence**. The confidence interval includes zero. This means we cannot distinguish the filter's edge from random noise.

Annualized Sharpe-like ratio: ~0.69 (assuming 20 trades/day). This is mediocre — not good enough to be confident in live trading.

### ⚠️ TEMPORAL BIAS: REDUCED BUT NOT RESOLVED

| Month | PG Total | Analyzed | Skipped | % Analyzed |
|-------|----------|----------|---------|------------|
| 2026-05 | 536 | 351 | 185 | 65.5% |
| 2026-06 | 1,551 | 971 | 580 | 62.6% |
| 2026-07 | 703 | 508 | 195 | 72.3% |
| 2026-08 | 1,567 | 1,449 | 118 | 92.5% |
| 2026-09 | 765 | 709 | 56 | 92.7% |
| **TOTAL** | **5,122** | **3,988** | **1,134** | **77.9%** |

The backfill brought candle data from May 20, 2026 onward for most tokens (previously only had Aug+). However:
- May-Jul coverage is only **~65-72%** (not 100%)
- 960 May-Jul trades still skipped (tokens that don't have candle data back to their trade dates)
- The overall skip rate dropped from 54.5% to 22.1% — significant improvement, but not complete

### 🚨 DATA QUALITY: NO ISSUES FOUND
- 0 duplicate candle pairs (token, ts)
- 0 NULL slopes across all 3,988 trades
- All candle data starts from May 20, 2026 or later (no anachronistic data)
- Min candles available: 213 (above the 190 threshold)

---

## SPOT-CHECK RESULTS

### 12 Trades Verified Manually

| Trade ID | Token | Dir | MA180 Match | Slope_120 Match | pvsm Match |
|----------|-------|-----|-------------|-----------------|------------|
| 13471 | DYDX | LONG | ✅ | ✅ | ✅ |
| 14642 | DYDX | LONG | ✅ | ✅ | ✅ |
| 15192 | STX | SHORT | ✅ | ✅ | ✅ |
| 13616 | AVNT | LONG | ✅ | ✅ | ✅ |
| 12697 | PEOPLE | LONG | ✅ | ✅ | ✅ |
| 12847 | UNI | LONG | ✅ | ✅ | ✅ |
| 11853 | ORDI | LONG | ✅ | ✅ | ✅ |
| 12290 | ORDI | SHORT | ✅ | ✅ | ✅ |
| 13158 | ENS | SHORT | ✅ | ✅ | ✅ |
| 15158 | COMP | SHORT | ✅ | ✅ | ✅ |
| 12942 | ORDI | SHORT | ✅ | ✅ | ✅ |
| 12544 | PEOPLE | SHORT | ✅ | ✅ | ✅ |

**All 12 spot-checks passed.** The MA180, slope, and price-vs-MA calculations are mathematically correct.

---

## SUMMARY TABLE

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | 3,988 of 5,119 analyzed | **PARTIAL** (actual: 3,988 of 5,122) | HIGH |
| 2 | Alignment +3.1% WR at 120 window | **AGREE** (but period-dependent — reverses in Aug-Sep) | HIGH |
| 3 | SHORT alignment +4.1% WR, +$3.54 | **AGREE** (exact match) | HIGH |
| 3b | LONG alignment +2.0% WR, hurts PnL | **AGREE** (exact match) | HIGH |
| 4 | Combined filter 49.8% WR, +$1.24 | **AGREE** (exact match) | HIGH |
| 5 | Blocking slope >0.02%: 45.8%→46.0% | **AGREE** (trivial improvement) | HIGH |
| 6 | Counter-trend was artifact | **DISAGREE** (it's a regime difference, not artifact) | HIGH |
| 7 | Overall 45.8% WR, -$13.63 | **AGREE** (exact match) | HIGH |
| 8 | LONG+Flat+BelowMA: 51% WR, +$3.4 | **PARTIAL** (actual: 51.3%, +$3.61, 435T) | HIGH |

---

## BOTTOM LINE

**The script is mathematically correct. The claimed numbers are mostly verified. But the conclusions drawn from them are misleading:**

1. ✅ **Math is solid** — MA180, linreg slopes, alignment flags, PnL all verified against manual computation and PostgreSQL. No bugs in the core analysis.

2. ⚠️ **The overall +3.1% alignment edge is NOT robust** — it flips between periods. In May-Jul, aligned is better. In Aug-Sep (recent), aligned is worse. The "edge" is an artifact of averaging across two regimes, not a universal property.

3. ⚠️ **The combined filter is NOT statistically significant** — 95% confidence interval includes zero. The +$1.24 total could easily be noise.

4. 🚨 **The combined filter is still LOSING MONEY in Aug-Sep** — -$1.80 total across 799 trades. It reduces losses vs baseline but does not generate profit in the recent period.

5. 🚨 **Temporal bias is REDUCED but NOT resolved** — May-Jul coverage is ~65-72%, not 100%. The 960 skipped May-Jul trades could shift results if analyzed.

6. ⚠️ **The "counter-trend is artifact" claim is WRONG** — counter-trend is still better in Aug-Sep. It's the May-Jul period where aligned was better. The finding didn't disappear; it was diluted.

7. ⚠️ **The `analysis_summary` metadata bug persists** — `trades_skipped` is stored as 0 instead of 1,134.

**No filter combination in this analysis provides a statistically significant edge.** The best candidates (combined filter, LONG+Flat+Below MA) have confidence intervals that include zero. The system's overall -$13.63 PnL is statistically significant (it IS losing money), but no filter reliably separates winners from losers.

**Recommendation:** Do NOT use these filters for live trading decisions. The apparent edges are not statistically significant and are period-dependent. The system needs fundamental improvements beyond MA180 slope filtering.
