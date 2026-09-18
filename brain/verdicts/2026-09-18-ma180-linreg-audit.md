# Independent Audit: LINREG MA180 Filter Analysis

**Auditor:** Independent (fresh-read, no prior context)
**Date:** 2026-09-18
**Script:** `scripts/analysis/linreg_ma180_analysis.py`
**Data:** `data/linreg_ma180_analysis.db` (1,885 rows), PostgreSQL brain DB (5,118 closed trades), `data/candles.db` (1m candles)

---

## METHOD

1. Read the analysis script line-by-line for logic bugs
2. Ran independent SQL queries against the analysis DB to verify every claimed number
3. Spot-checked 11 individual trades: pulled entry times/tokens, looked up candles in `candles.db`, manually computed MA180 and linreg slope, compared to stored values
4. Verified alignment logic exhaustively (every combination of direction × slope sign × aligned flag)
5. Checked for temporal bias in which trades were analyzed vs skipped
6. Verified PnL matches between PostgreSQL and analysis DB
7. Tested edge cases: NULL slopes, minimum candle counts, breakeven trades

---

## CODE REVIEW

### MA180 Calculation — ✅ CORRECT
- `compute_ma()` at line 155: standard rolling average, first valid MA at index `period-1` (179), which is correct for period=180
- No off-by-one errors. The MA at the last position correctly represents the MA at entry time.
- Uses `sum(values[i-period+1:i+1]) / period` — this is the standard SMA formula

### Linreg Slope Computation — ✅ CORRECT
- `compute_linreg_slope()` at line 169: filters None values, uses `np.polyfit(indices, vals, 1)` for linear regression
- Returns slope normalized by mean value as % per candle: `m / mean_val * 100`
- Minimum 10 valid points required — reasonable guard
- Verified against manual computation for 11 trades: all matched to 10+ decimal places

### Alignment Logic — ✅ CORRECT
- LONG aligned = slope > 0 (threshold 0.0), SHORT aligned = slope < 0
- Exhaustive verification: 0 misclassifications found across all 1,885 trades
  - LONG + slope>0 + aligned=1: 706 ✓
  - LONG + slope<0 + aligned=0: 428 ✓
  - SHORT + slope>0 + aligned=0: 294 ✓
  - SHORT + slope<0 + aligned=1: 457 ✓
  - No slope = 0 exists in the dataset

### is_win Definition — ⚠️ DESIGN CHOICE
- Line 238: `is_win = 1 if pnl_usdt > 0 else 0`
- 69 breakeven trades (pnl_usdt = 0) are counted as losses
- This deflates WR by ~3.7 percentage points (69 out of 1,885 trades)
- Not a bug, but affects interpretation: 52.1% WR becomes ~54.6% if breakeven excluded

### analysis_summary Bug — 🐛 BUG
- Line 515: `trades_skipped` is hardcoded to `0` in the INSERT statement
- The actual skipped count is 3,233 (5,118 - 1,885)
- Does not affect analysis results, only the summary metadata

### Minimum Candle Threshold — ⚠️ TOO LENIENT
- Line 212: requires `len(candles) < MA_PERIOD + 10 = 190`
- For `slope_120`, the linreg window needs 120 MA values, which requires 180+120=300 candles
- With only 190 candles, there are only 12 valid MA values — enough for the minimum 10-point linreg check, but the slope is computed from a very short series
- In practice: 95.3% of analyzed trades have 351 candles (maximum), so this affects only 89 trades (4.7%)

### NULL Handling — ✅ CORRECT
- 0 NULL slopes in the analysis results (all 1,885 trades have valid slopes for all windows)
- The script properly returns None for insufficient data and filters them in queries

---

## CLAIM-BY-CLAIM VERDICT

### Claim 1: "1,885 out of 5,117 closed trades were analyzed"
**Verdict: PARTIAL**
- Analyzed count: **1,885 ✅**
- Total count: **5,118** (not 5,117 — off by 1, likely a new trade added between runs)
- Skip reason: **CONFIRMED** — no 1m candle data. The candle DB only has data from ~August 2026 onward. All May/June/July trades (2,790 total) had zero candle data.

### Claim 2: "MA180 slope alignment has NEGATIVE edge"
**Verdict: AGREE ✅**
- Confirmed across ALL windows:
  | Window | Aligned WR | Counter WR | Edge |
  |--------|-----------|------------|------|
  | 30     | 50.2%     | 55.4%     | -5.2% |
  | 60     | 50.6%     | 54.6%     | -4.0% |
  | 90     | 50.7%     | 54.6%     | -3.9% |
  | 120    | 51.0%     | 54.3%     | -3.3% |
- Aligned trades also have worse avg PnL in every window

### Claim 3: "Counter-trend trades have 56.1% WR vs aligned trades at 50.4%"
**Verdict: PARTIAL**
- The direction is correct: counter-trend WR > aligned WR
- But the exact numbers don't match any single window:
  - Window 30: counter 55.4% vs aligned 50.2%
  - Window 60: counter 54.6% vs aligned 50.6%
  - Window 90: counter 54.6% vs aligned 50.7%
  - Window 120: counter 54.3% vs aligned 51.0%
- The closest to "56.1%" is SHORT counter-trend at window 30 (56.7%), but the claim says "overall"
- The claim's numbers appear to be approximations or from a different analysis run

### Claim 4: "slope >0.03%: aligned 31.4% WR vs counter 80.0% WR"
**Verdict: AGREE (with clarification) ✅**
- "slope > 0.03%" means **absolute** slope > 0.03% (the claim is ambiguous but the numbers match only with absolute value)
- Aligned |slope|>0.03%: 51 trades, 16 wins = **31.4% WR ✅**
- Counter |slope|>0.03%: 5 trades, 4 wins = **80.0% WR ✅**
- **⚠️ CAVEAT:** The counter-trend bucket has only 5 trades — far too small for statistical significance. The 80% WR is from 4 wins out of 5 trades, which is not reliable.

### Claim 5: "Blocking trades where |price vs MA180| > 0.75% improves WR from 52.1% to 54.7% and PnL by +$6.94"
**Verdict: PARTIAL**
- WR improvement: **52.1% → 54.7% ✅** (exact match)
- Total PnL without filter: **-$11.78**
- Total PnL with filter: **-$2.42**
- **Actual PnL improvement: +$9.36** (not +$6.94 as claimed)
- Average PnL improvement: +$0.0042/trade × 1,164 filtered trades = +$4.85
- No calculation yields +$6.94 — the claimed number appears incorrect

### Claim 6: "Combined filter (both price position and slope) gives 54.6% WR"
**Verdict: DISAGREE ❌**
- No combination of filters produces exactly 54.6% WR:
  - |pvsm|≤0.75 alone: **54.7%** (1,164 trades)
  - |pvsm|≤0.75 + counter-trend_60: **55.7%** (517 trades)
  - |pvsm|≤0.75 + aligned_60: **53.9%** (647 trades)
  - |pvsm|≤0.75 + counter-trend_30: **55.8%** (525 trades)
- The closest is the price filter alone at 54.7%, but that's not a "combined" filter
- The claimed 54.6% may come from a different parameter combination or analysis run

### Claim 7: "LONG + Slope UP + Price extended above MA180 = 39% WR (162 trades)"
**Verdict: DISAGREE ❌**
- No combination produces 39% WR or 162 trades:
  - LONG + aligned_60 + pvsm>0.75: 292 trades, **43.5% WR**
  - LONG + aligned_60 + pvsm>0.5: 349 trades, **46.4% WR**
  - LONG + aligned_60 + pvsm>1.0: 255 trades, **41.6% WR**
  - LONG + aligned_30 + pvsm>0.75: 312 trades, **43.3% WR**
  - LONG + aligned_120 + pvsm>0.75: 273 trades, **41.8% WR**
- The closest is window 120 with pvsm>1.0 at 41.8% WR, but still not 39%
- The claimed numbers appear fabricated or from a different analysis

### Claim 8: "SHORT + slope UP = 66.7% WR"
**Verdict: DISAGREE ❌**
- No window produces 66.7% WR for SHORT counter-trend:
  - SHORT + slope_30>0: 275 trades, **56.7% WR**
  - SHORT + slope_60>0: 294 trades, **55.4% WR**
  - SHORT + slope_90>0: 292 trades, **56.2% WR**
  - SHORT + slope_120>0: 277 trades, **55.2% WR**
- The best is window 30 at 56.7% — far from 66.7%
- The claimed number appears incorrect

---

## CRITICAL FINDINGS

### 🚨 SEVERE TEMPORAL BIAS
This is the most important finding of the audit.

| Month    | Analyzed | Skipped | % Analyzed |
|----------|----------|---------|------------|
| 2026-05  | 0        | 536     | **0.0%**   |
| 2026-06  | 0        | 1,551   | **0.0%**   |
| 2026-07  | 0        | 703     | **0.0%**   |
| 2026-08  | 1,178    | 389     | 75.2%      |
| 2026-09  | 707      | 54      | 92.9%      |

- **100% of May, June, and July trades were skipped** (2,790 trades, 54.5% of all trades)
- The analysis only covers August 5 — September 18 (~6 weeks)
- The 1m candle data simply doesn't exist before early August
- **All conclusions are only valid for the recent period, not the full trading history**

### 🚨 ANALYZED PERIOD IS THE WORST PERFORMING
- All analyzed trades (Aug-Sep): total PnL = **-$11.78**
- Skipped trades (May-Jul): total PnL = **+$0.81** (profitable!)
- The analysis is exclusively looking at the worst-performing period of the trading system
- The "counter-trend has edge" finding may be specific to this losing period, not a general truth

### 🚨 STATISTICAL POWER ISSUES
- 1,885 trades is decent for overall WR, but sub-group analysis has thin samples:
  - Counter-trend with steep slopes: only 5 trades (Claim 4)
  - Various price/direction/slope buckets: 1-50 trades each
- The "biggest losing bucket" claims (e.g., Claim 7 with 162 trades) are based on combinations I cannot reproduce — the actual numbers differ significantly

### 🐛 SUMMARY TABLE BUG
- `trades_skipped` is hardcoded to 0 in the INSERT (line 515)
- Should be `skipped` variable (which is computed but never stored)

---

## SPOT-CHECK RESULTS

### 11 Trades Verified Manually

| Trade ID | Token | Dir | MA180 Match | Slope Match |
|----------|-------|-----|-------------|-------------|
| 14757    | ARB   | LONG | ✅ (0.109788) | ✅ (0.008111) |
| 13756    | MON   | SHORT | ✅ (0.021830) | ✅ (0.001194) |
| 14968    | CAKE  | LONG | ✅ (2.246994) | ✅ (-0.004224) |
| 13912    | PUMP  | LONG | ✅ (0.002815) | ✅ (0.003638) |
| 14558    | BANANA| SHORT | ✅ (3.849712) | ✅ (0.001567) |
| 13838    | ENA   | LONG | ✅ (0.085093) | ✅ (-0.005015) |
| 14249    | PURR  | SHORT | ✅ (0.134852) | ✅ (-0.008901) |
| 14396    | CASHCAT| LONG | ✅ (0.217592) | ✅ (0.104772) |
| 13738    | GMT   | SHORT | ✅ (0.006551) | ✅ (-0.002047) |
| 14149    | PUMP  | LONG | ✅ (0.004843) | ✅ (0.016067) |
| 13602    | MEGA  | LONG | ✅ (0.036461) | ✅ (-0.003257) |

**All 11 spot-checks passed.** The MA180 and slope calculations are correct.

### PnL Verification
- PostgreSQL total for 1,885 analyzed trades: **-$11.78**
- Analysis DB total: **-$11.780000000000001**
- 50 random trades checked individually: **0 mismatches**

---

## SUMMARY TABLE

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | 1,885 of 5,117 analyzed | **PARTIAL** (5,118 not 5,117) | HIGH |
| 2 | Alignment has NEGATIVE edge | **AGREE** | HIGH |
| 3 | Counter 56.1% WR vs aligned 50.4% | **PARTIAL** (direction correct, numbers off) | HIGH |
| 4 | slope >0.03%: aligned 31.4% vs counter 80% | **AGREE** (with absolute value interpretation; counter n=5) | MEDIUM |
| 5 | Price filter improves WR to 54.7% and PnL by +$6.94 | **PARTIAL** (WR correct, PnL is +$9.36 not +$6.94) | HIGH |
| 6 | Combined filter gives 54.6% WR | **DISAGREE** (no combination matches) | HIGH |
| 7 | LONG+slope UP+extended = 39% WR (162 trades) | **DISAGREE** (cannot reproduce) | HIGH |
| 8 | SHORT+slope UP = 66.7% WR | **DISAGREE** (actual is 55-57%) | HIGH |

---

## BOTTOM LINE

**The core findings are directionally valid but the specifics are unreliable:**

1. ✅ The MA180 calculation and linreg slope computation are **technically correct** — no bugs in the math
2. ✅ The finding that trend alignment has negative edge is **real and consistent** across all windows
3. ⚠️ The specific numbers in Claims 3, 5, 6, 7, and 8 are **inaccurate or unverifiable** — they don't match the data in the analysis DB
4. 🚨 The **temporal bias is severe** — 54.5% of all trades were excluded because candle data doesn't exist before August 2026. All conclusions apply only to the recent 6-week period, which happens to be the worst-performing period
5. 🚨 The "counter-trend works" finding should be treated with extreme caution — it's based on a period where the system was losing money overall, and the steep-slope counter-trend sample is only 5 trades

**Recommendation:** Do NOT use these claims as a basis for trading decisions without addressing the temporal bias. Re-run the analysis when 1m candle data covers a longer period, or at minimum clearly state that conclusions are limited to Aug-Sep 2026 market conditions.
