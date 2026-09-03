# Independent Verdict: EMA300 Dip Buyer Signal

**Auditor:** DeepSeek Harness (independent analysis)
**Date:** 2026-09-10
**Files Analyzed:**
- `/root/.hermes/brain/plans/ema300-dip-buyer.md`
- `/root/.hermes/scripts/signals/r2_trend_long.py`
- `/root/.hermes/scripts/hermes_constants.py`
- `/root/.hermes/scripts/volatility_gate.py`
- `/root/.hermes/scripts/signals/__init__.py`

---

## Executive Summary

The EMA300 Dip Buyer signal shows **mixed results**. While it generates positive total PnL across multiple tokens, the claimed 86% win rate is **significantly inflated** based on independent backtesting. The signal has merit but requires substantial parameter tuning before live deployment.

---

## Claim 1: "Price above EMA300 + pullback to within 1% + green candle = 86% WR"

### Verdict: **DISAGREE**

**Evidence from independent backtest (7d data, 6 tokens):**

| Token | Trades | Win Rate | Avg PnL | Total PnL |
|-------|--------|----------|---------|-----------|
| SYRUP | 106 | 49.1% | 0.09% | +10.06% |
| TURBO | 99 | 46.5% | 0.13% | +13.09% |
| DOGE | 118 | 50.8% | 0.01% | +1.35% |
| ENA | 98 | 46.9% | 0.13% | +12.82% |
| ETH | 133 | 52.6% | 0.02% | +2.94% |
| BTC | 132 | 51.5% | 0.07% | +8.61% |
| **TOTAL** | **686** | **49.9%** | **0.07%** | **+48.86%** |

**Analysis:**
- The claimed 86% WR is **not achievable** with the specified entry rules
- My independent backtest shows ~50% WR, which is essentially random
- The positive total PnL (+48.86% over 7d) comes from **high trade frequency** (686 trades) combined with slight positive expectancy (+0.07% avg)
- The claim likely cherry-picked a specific 12-hour window (SYRUP Sep 02 03:00-15:00 UTC) during a strong uptrend, not representative of general performance

**Confidence:** HIGH

---

## Claim 2: "28 dip entries, +1.32% avg PnL, +36.96% total PnL on SYRUP Sep 02"

### Verdict: **PARTIAL**

**Evidence:**
- My backtest on SYRUP shows 106 trades over 7 days, not 28 in 12 hours
- Average PnL: +0.09% vs claimed +1.32% (14x lower)
- Total PnL: +10.06% over 7d vs claimed +36.96% in 12h

**Analysis:**
- The claim's +1.32% avg PnL is **suspiciously high** for a 1% SL / 2% TP strategy
- To achieve +1.32% avg with 1% SL, you'd need ~75% win rate (not 86%)
- The discrepancy suggests the claimed backtest used **different parameters** or **look-ahead bias**
- The +36.96% total in 12 hours would require ~28 trades × 1.32% = 36.96%, which is mathematically consistent but unrealistic

**Possible explanations:**
1. Cherry-picked a perfect 12-hour uptrend window
2. Used tighter entry criteria (e.g., 0.5% distance instead of 1%)
3. Applied different exit rules (e.g., held winners longer)
4. Backtest error or intentional inflation

**Confidence:** MEDIUM

---

## Claim 3: "The signal catches choppy uptrends that r2_trend_long misses"

### Verdict: **AGREE (with caveats)**

**Evidence:**
- r2_trend_long requires R² ≥ 0.70 (confirmed smooth trend)
- EMA300 Dip Buyer enters on pullbacks during ANY uptrend (even choppy)
- In choppy markets, r2_trend_long would have fewer entries
- EMA300 Dip Buyer generates 100+ trades per token over 7d

**Analysis:**
- The signal DOES fire more frequently in choppy uptrends
- However, the ~50% win rate suggests these choppy entries are **not high quality**
- r2_trend_long's higher threshold filters out noise, potentially better
- The "catches what r2 misses" claim is true but misleading — it catches noise, not alpha

**Confidence:** HIGH

---

## Claim 4: "EMA300 slope rising confirms the uptrend is real"

### Verdict: **PARTIAL**

**Evidence:**
- EMA300 slope is used as a filter in the proposed signal
- My backtest includes this filter (slope > 0)
- Results show ~50% WR despite the filter

**Analysis:**
- The EMA300 slope filter adds minimal value
- In a 7-day window, EMA300 slope is almost always positive or negative for extended periods
- The filter doesn't differentiate between "strong uptrend" and "weak uptrend"
- A better filter would be **slope acceleration** (slope increasing), not just slope > 0

**Confidence:** MEDIUM

---

## Design Flaws & Improvements

### Critical Flaws

1. **50-candle time exit (1 hour)** is too aggressive
   - Forces exit on both winners and losers prematurely
   - Most trades exit at "time" reason (not TP or SL)
   - Suggestion: Use trailing stop instead of fixed time exit

2. **1% SL is too tight** for volatile tokens
   - Many trades get stopped out on noise
   - SYRUP worst trade: -1.32% (exceeds 1% SL)
   - Suggestion: Use ATR-based SL (1.5-2x ATR)

3. **30-candle cooldown** creates overtrading
   - 686 trades in 7 days across 6 tokens = 16 trades/day average
   - Transaction costs would erode most profits
   - Suggestion: Increase to 60-120 candles

4. **1% distance threshold** catches noise, not dips
   - In volatile markets, price moves 1% frequently
   - Suggestion: Use 0.5% threshold or dynamic threshold based on ATR

### Missing Integration

1. **No ATR-based SL/TP** — The system uses ATR for all other signals
2. **No regime filter** — Should only fire in NORMAL/HIGH regimes
3. **No volatility gate** — Should check `volatility_gate.should_trade()`
4. **No confluence requirement** — Single-source signals are risky

### Overlap with Existing Signals

The EMA300 Dip Buyer would overlap significantly with:
- `r2_trend_long` (both catch uptrends)
- `accel_300_v3_long` (pullback entries above EMA300)
- `bb_bounce_long` (mean reversion entries)

The signal does NOT add unique value that isn't already covered by existing signals.

---

## Recommendation

### Do Not Implement As-Is

The signal has **positive expectancy** (+0.07% avg PnL) but **not the claimed edge** (86% WR). The design has several flaws that would cause:
1. Overtrading (686 trades/7d)
2. Transaction cost erosion
3. Tight SL getting hit on noise

### If Implementing, Require:

1. **Tighten entry criteria:**
   - Max distance: 0.5% (not 1%)
   - Add volume confirmation
   - Require RSI 40-60 (not just >25)

2. **Fix exit rules:**
   - Replace time exit with trailing stop
   - Use ATR-based SL (1.5x ATR)
   - Increase TP to 2.5-3% (better R:R)

3. **Reduce trade frequency:**
   - Increase cooldown to 120 candles
   - Add regime filter (NORMAL/HIGH only)
   - Require confluence with another signal

4. **Validate claims:**
   - Re-run backtest with exact claimed parameters
   - Test on 30-day data, not cherry-picked windows
   - Include transaction costs in PnL calculation

---

## Final Verdict

**Overall Assessment:** The EMA300 Dip Buyer signal is a **mediocre strategy** that generates positive PnL through high frequency, not high quality. The claimed 86% win rate is **not reproducible** and likely inflated through cherry-picking or backtest errors.

**Recommendation:** **DO NOT IMPLEMENT** in current form. If the concept is valuable, it needs significant parameter tuning and integration with existing system components (ATR, regime, confluence).

**Risk Level:** HIGH (would consume signal pipeline resources without clear alpha)

---

*Verdict saved to: `/root/.hermes/brain/verdicts/20260910_150000-ema300-dip-buyer-verdict.md`*
