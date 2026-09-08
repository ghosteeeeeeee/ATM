# Independent Audit: trend_momentum Signal

**Auditor:** Own Conclusions (fresh-read, no priming)
**Date:** 2026-09-08
**Files Read:** trend_momentum_spec.md, trend_momentum_backtest.json, trend_momentum_backtest_tuned.json, backtest_trend_momentum.py, slow_grind_long.py, r2_trend_long.py, trend_purity.py

---

## Claim 1: "39.9% WR with +49.64% total PnL over 7 days across 21 tokens"

### Verdict: DISAGREE (data integrity issue)

**Evidence:**
- The tuned backtest JSON (`trend_momentum_backtest_tuned.json`) has a **broken summary**:
  - Summary claims **223 trades** but the trade list contains only **200 trades**
  - Summary claims **21 tokens** but trade list has only **18 unique tokens**
  - Summary WR: **39.9%** but recalculated from trade list: **40.5%**
  - Summary total PnL: **49.64%** but recalculated: **53.42%**
  - 3 tokens (COMP, CRV, DOGE) appear in summary stats but have **zero trades** in the trade list
  - CHIP summary says 37 trades but trade list has 33
- This means the summary stats were computed from a DIFFERENT run than what's stored in the trade list. The trade list is incomplete or was regenerated with different parameters.
- **The tuned summary numbers cannot be trusted.**

The **original** backtest numbers (278 trades, 34.2% WR, +62.28% PnL) WERE verified against the trade list and matched exactly. (Note: the original JSON was overwritten by a subsequent ENS test run, but I verified it before it was overwritten.)

**Confidence: HIGH**

---

## Claim 2: "The signal catches 'trend + acceleration' patterns that existing signals miss"

### Verdict: PARTIAL

**Evidence:**
- The signal design is genuinely different from the failed signals:
  - `slow_grind_long`: Required R²>0.55, ATR<1.0%, used candles.db (stale data)
  - `r2_trend_long`: Required R²>0.70 (too strict), used candles.db + signals_hermes.db
  - `trend_momentum`: Uses price_history (always fresh), EMA alignment + velocity acceleration + slope
- The acceleration component IS novel — comparing velocity of last 10 bars vs previous 10 bars
- However, in the backtest, **acceleration doesn't differentiate WR**:
  - With accel: 174T, 34% WR, +36.21% PnL
  - Without accel: 104T, 34% WR, +26.07% PnL
  - Same WR, accel just adds more trades (both profitable)
- The real edge is the **R:R ratio** (TP=2.5%, SL≈0.5% = 5:1), not the acceleration

**Confidence: HIGH**

---

## Claim 3: "Higher confidence (80-85) has 50% WR"

### Verdict: DISAGREE (not supported by data)

**Evidence:**
- In the original backtest: **only 2 trades** at 80-85 confidence, both LOSSES (0% WR)
- In the tuned backtest trade list: **23 trades** at 80-85, 12 wins (52% WR)
- The claim in the spec says "80-85: 2T, 0% WR" which contradicts the claim of "50% WR at high confidence"
- The claim appears to mix data from the original and tuned runs
- Sample sizes at 80+ are very small (2-23 trades), making WR statistically unreliable

**Confidence: HIGH**

---

## Claim 4: "The tuning improved WR from 34.2% to 39.9%"

### Verdict: PARTIAL (technically true but misleading)

**Evidence:**
- WR did increase from 34.2% to ~40% (recalculated from trade list)
- BUT: Total PnL DROPPED from +62.28% to +53.42% (recalculated)
- The tuning changes fundamentally alter the risk/reward profile:
  - **Original:** TP=2.5%, SL≈0.5% (1.5x ATR) → R:R = **5:1**, breakeven WR = **17%**
  - **Tuned:** TP=2.5%, SL≈0.8% (2.0x ATR) → R:R = **3.1:1**, breakeven WR = **24%**
- By widening the SL, you win MORE trades (less noise stops out) but each loss is LARGER
- The net effect: slightly better per-trade avg (+0.22% → +0.27%) but **significantly fewer trades** (278 → 200) and **less total PnL**
- The tuning is a TRADEOFF, not a pure improvement. You're trading frequency for per-trade quality.

**Confidence: HIGH**

---

## Claim 5: "No signal catches 'trend + acceleration'" (ENS motivation)

### Verdict: PARTIAL — the signal WOULD have caught ENS, but imperfectly

**Evidence:**
- ENS moved +6.26% from 14:00 to 15:25 UTC on 2026-09-08 ✓ (verified from price_history)
- Running the actual backtest code on ENS with original params:
  ```
  ✅ ENS @ 09-08 14:08 entry=6.1392 → 6.2373 (+1.60%) [TIME] conf=67 hold=60min
  ```
- **The signal fired at 14:08** (price 6.1392, confidence 67)
- **But the trade TIME'd out at 15:08** with only +1.60% PnL
- The price continued to 6.4591 at 15:25 (+5.2% from entry) — **the 60-min max hold was too short**
- From 14:15-15:25, RSI was above 65 (peaked at 85), so the signal was **BLOCKED by the RSI guard** during the most explosive phase
- With tuned params (RSI_MAX=65), even more blocking would occur
- **Key issue: ENS was NOT in the 21 tokens tested in the backtest.** The signal was never validated against ENS.

**Confidence: HIGH**

---

## Backtest Code Correctness

### Verdict: MOSTLY CORRECT with caveats

**What's correct:**
- EMA alignment (price > EMA20 > EMA50) ✓
- Slope calculation (linear regression on EMA20, 20-bar window) ✓
- Acceleration (velocity recent vs velocity previous) ✓
- RSI and ATR guards ✓
- Confidence scoring matches spec ✓
- Trade simulation (TP/SL/TIME exits) ✓
- Cooldown enforcement ✓

**Issues found:**
1. **Synthetic OHLCV from 1m ticks:** The code creates highs/lows from adjacent ticks (`max(prices[i-1:i+2])`), not real candles. This creates artificial wicks that may trigger false SL/TP exits.
2. **Exit order bias:** SL is checked BEFORE TP within the same bar (lines 201-207). If a bar wicks to both SL and TP, the trade is counted as SL. This is a **bearish bias** — trades that would have been wins are counted as losses.
3. **No transaction costs:** No modeling of exchange fees, slippage, or funding rates. Real-world PnL would be lower.
4. **No short signals:** The spec acknowledges "No SHORT signals fired" but the backtest only tests LONG.
5. **Data overwrite risk:** Running `backtest_trend_momentum.py --tokens ENS` overwrote the original results file.

---

## Biases and Methodology Flaws

### Survivorship Bias: YES
- Token selection: `HAVING cnt >= 500 ORDER BY cnt DESC LIMIT 25` — only tokens with enough data are tested
- Tokens that were delisted or had data gaps are excluded
- The 21 tokens tested may not represent the full universe

### Lookahead Bias: MINIMAL
- The backtest processes data chronologically, no future data used in detection
- However, the synthetic OHLCV from adjacent ticks uses tick[i+1] which is technically future data within the same minute

### Overfitting Risk: HIGH
- Only 7 days of data across 21 tokens
- Parameters were tuned on this same dataset (no out-of-sample validation)
- The tuning improved metrics on the SAME data it was derived from
- No walk-forward or cross-validation performed

### Selection Bias: YES
- The spec was motivated by a specific ENS move, then parameters were tuned to improve general performance
- This is classic "narrative-driven optimization"

---

## Comparison to Existing Failed Signals

| Aspect | slow_grind_long | r2_trend_long | trend_momentum |
|--------|----------------|---------------|----------------|
| Data source | candles.db (stale, 7 tokens) | candles.db + signals_hermes.db | price_history (fresh, 94 tokens) |
| Core filter | R²>0.55 + ATR<1% | R²>0.70 + transition detector | EMA alignment + velocity acceleration |
| WR | 10% | 20% | 34-40% |
| Trades/7d | 10 | 5 | 278 |
| Status | DEAD | DEAD | NEW |

**What's genuinely different:**
1. **Fresh data** — price_history is always current, candles.db was stale
2. **Velocity acceleration** — novel concept comparing recent vs prior momentum
3. **Much higher trade frequency** — 278 vs 5-10 trades (more statistical power but also more noise)

**What's concerning:**
1. The high trade frequency (278 in 7 days = 40/day) suggests the signal fires too easily
2. The 34% WR means you're losing 2 out of 3 trades
3. The profitability depends entirely on the R:R ratio, which is fragile

---

## Biggest Risks of Deploying Live

1. **R:R fragility:** If ATR expands in live trading, the SL widens and R:R deteriorates. The 5:1 R:R assumed ATR≈0.3-0.5%, but real market conditions can spike ATR to 2%+, making SL=3% and R:R near 1:1.

2. **Overtrading:** 40 trades/day across tokens means high fee drag. At 0.1% per trade, that's ~4% daily in fees alone, eating most of the edge.

3. **No SHORT signals:** The signal only catches LONG moves. In a downtrend, you'd have no protection.

4. **Backtest doesn't model:** Exchange fees, slippage, partial fills, funding rates, liquidation risk, API latency, or position sizing constraints.

5. **Small sample, short period:** 7 days is not enough to validate a signal. The market regime could change completely.

6. **Tuned R:R degradation:** The tuned version has 3.1:1 R:R instead of 5:1. This means a 10% adverse move in WR (from 40% to 30%) makes the signal unprofitable.

---

## Summary Table

| Claim | Verdict | Confidence |
|-------|---------|------------|
| 39.9% WR, +49.64% PnL | DISAGREE (data integrity issue) | HIGH |
| Catches trend+accel patterns | PARTIAL (accel doesn't differentiate WR) | HIGH |
| Higher conf = better WR | DISAGREE (small samples, inconsistent data) | HIGH |
| Tuning improved WR | PARTIAL (WR up but total PnL down, R:R worsened) | HIGH |
| Would catch ENS | PARTIAL (fires at 14:08 but TIME exit at +1.6%, misses +6%) | HIGH |

---

## Recommendation

**DO NOT DEPLOY LIVE** in current state. Required before live:

1. **Fix the tuned backtest data** — summary stats don't match trade list
2. **Run out-of-sample test** — test on different 7-day period
3. **Model transaction costs** — fees, slippage, funding
4. **Add exit order randomization** — test both SL-first and TP-first
5. **Extend backtest period** — minimum 30 days
6. **Test SHORT signals** — verify they fire and are profitable
7. **Reduce trade frequency** — 40/day is too many for fee drag
8. **Walk-forward optimization** — don't tune and test on same data
