# EMA300 Rejection Signal — Independent Backtest Report

**Date:** 2026-09-12
**Auditor:** Independent backtest agent
**Method:** From-scratch Python backtest on `candles.db`

---

## Claim Under Verification

> EMA300 rejection pattern (price approaches EMA300, hits it, bounces) has ~49% WR on 15m candles. Stronger rejections don't perform better. Higher pre-move performs worse.

---

## Methodology

- **EMA300** calculated on 15m and 1h candle closes
- **Rejection candle:** wick touching EMA300, wick/range ratio ≥ 30%
- **Entry:** open of candle after rejection candle
- **Outcome:** close of 4th candle after entry (1 hour for 15m, 4 hours for 1h)
- **Sample:** Top 15 tokens by data availability on each timeframe
- **Total signals:** 62,277 (15m), 19,199 (1h)

---

## Results

### 15m Timeframe (62,277 signals)

| Metric | Value |
|--------|-------|
| Win Rate | **49.9%** (31,099W / 31,178L) |
| Avg PnL | +0.006% (essentially flat) |
| Avg Win | +0.594% |
| Avg Loss | -0.580% |
| Long WR | 49.5% |
| Short WR | 50.4% |

### 1h Timeframe (19,199 signals)

| Metric | Value |
|--------|-------|
| Win Rate | **50.7%** (9,735W / 9,464L) |
| Avg PnL | +0.021% (essentially flat) |
| Avg Win | +1.143% |
| Avg Loss | -1.134% |
| Long WR | 49.1% |
| Short WR | 52.3% |

---

## Claim 1: "~49% WR on 15m candles"

**Verdict: CONFIRMED (slightly generous — actually 49.9%)**

The measured 49.9% WR across 62,277 signals is essentially a coin flip. The claim of "~49%" is directionally correct — the pattern has no edge on its own.

---

## Claim 2: "Stronger rejections don't perform better"

**Verdict: CONFIRMED**

| Wick Ratio | Signals | WR | Avg PnL |
|------------|---------|-----|---------|
| 30-40% | 17,990 | 49.6% | -0.000% |
| 40-50% | 12,782 | 50.5% | +0.004% |
| 50-60% | 12,679 | 49.5% | +0.009% |
| 60-70% | 8,118 | 50.5% | -0.002% |
| 70%+ | 10,708 | 49.9% | +0.022% |

**No meaningful difference across wick ratio buckets.** All WR values cluster between 49.5% and 50.5%. Stronger rejections (70%+ wick) have the same win rate as weaker ones (30-40% wick). The claim is correct — rejection strength provides no additional edge.

---

## Claim 3: "Higher pre-move performs worse"

**Verdict: NOT SUPPORTED (opposite may be true on 1h)**

**15m:**
| Pre-Move | Signals | WR | Avg PnL |
|----------|---------|-----|---------|
| <0.5% | 8,441 | 48.9% | +0.005% |
| 0.5-1% | 8,848 | 49.8% | +0.015% |
| 1-2% | 14,507 | 49.3% | -0.007% |
| 2-5% | 20,796 | 50.6% | +0.004% |
| 5%+ | 8,169 | 50.9% | +0.031% |

**1h:**
| Pre-Move | Signals | WR | Avg PnL |
|----------|---------|-----|---------|
| <0.5% | 1,465 | 47.9% | -0.042% |
| 0.5-1% | 1,516 | 52.0% | +0.063% |
| 1-2% | 2,905 | 48.7% | +0.008% |
| 2-5% | 6,224 | 49.7% | -0.024% |
| 5%+ | 6,810 | **52.8%** | +0.069% |

On 15m, higher pre-move actually performs *slightly better* (not worse). On 1h, the highest pre-move bucket (5%+) has the best WR at 52.8%. The claim appears incorrect — if anything, larger pre-moves may provide a marginal edge, not a penalty.

---

## Can Any Conditions Improve WR Above 55%?

**Verdict: NO**

The best-performing sub-filter was:
- 15m RSI < 30: 52.1% WR (7,763 signals) — still well below 55%
- 1h Flat slope: 54.5% WR (321 signals) — tiny sample, not reliable
- 1h RSI > 70: 52.2% WR (2,068 signals)

No combination of filters (wick ratio + slope, wick ratio + pre-move, RSI extremes) produced a WR above 55% with meaningful sample size. The pattern is fundamentally a coin flip.

---

## EMA Slope Analysis

**15m:** All slope buckets cluster at 49-50% WR. No directional edge from slope.

**1h:** Flat slope shows 54.5% WR but with only 321 signals — too small to be meaningful.

---

## Additional Findings

1. **MFE/MAE nearly symmetric:** On 15m, avg MFE = +0.547%, avg MAE = -0.566%. The pattern has no built-in directional bias.

2. **Profit factor is essentially 1.0:** The ratio of avg win × win count to avg loss × loss count is approximately 1.0 across all timeframes and conditions.

3. **Sample size is robust:** 62,277 signals on 15m and 19,199 on 1h provide high statistical confidence that the ~50% WR is not noise.

4. **1h slightly better than 15m:** 50.7% vs 49.9% WR, but the difference is within normal variation and the avg PnL is still negligible (+0.02%).

---

## === INDEPENDENT VERDICT ===

**Claim:** EMA300 rejection pattern has ~49% WR on 15m candles. Stronger rejections don't perform better. Higher pre-move performs worse.

**Verdict: PARTIAL**

**Evidence:**
- **WR claim: CONFIRMED.** Measured 49.9% WR across 62,277 signals — essentially a coin flip. The "~49%" claim is accurate.
- **Stronger rejections: CONFIRMED.** Wick ratio has zero predictive power. All buckets (30-40% through 70%+) show WR between 49.5-50.5%.
- **Higher pre-move: NOT CONFIRMED.** On 15m, higher pre-move actually performs slightly better (50.9% vs 48.9%). On 1h, 5%+ pre-move has the best WR (52.8%). The claim appears backwards.
- **No conditions improve WR above 55%.** Best sub-filter is 52.1% (15m RSI<30). No actionable edge found.

**Confidence: HIGH**

The backtest used 62,277 signals on 15m and 19,199 on 1h across 15 tokens with 1000+ candles each. Results are statistically robust. The pattern is essentially random with no exploitable edge in isolation.

**Notes:**
- This signal should NOT be deployed as a standalone entry. If implemented, it must be combined with other confluence factors (regime, momentum, volume, etc.) to add value.
- The spec's emphasis on EMA slope and wick ratio as confidence boosters appears unsupported by data — these factors don't improve outcomes.
- The concept's only potential use is as a filter (e.g., "don't enter if rejection at EMA300") rather than as a positive signal.

---

*Backtest script: `/root/.hermes/backtest_ema300_rejection.py`*
*Data source: `/root/.hermes/data/candles.db` (candles_15m, candles_1h)*
*Tokens tested: ETH, IMX, ADA, AIXBT, ALGO, ALT, APT, ARB, ATOM, AVAX, BABY, BANANA, BCH, BIGTIME, BLUR (15m) + AXS, SKY, ASTER, AVNT (1h only)*
