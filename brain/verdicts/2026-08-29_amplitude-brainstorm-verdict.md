# Independent Verdict: Amplitude-Based Trading System Enhancements

**Auditor:** own-conclusions (fresh eyes, no priming)
**Date:** 2026-08-29
**Files reviewed:** 6 files (2 plans, 1 brain doc, 3 scripts)
**Verification method:** Independent script execution, raw data queries, manual trade analysis

---

## Summary of Findings

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | All 20 tokens are MEDIUM_FREQ_TREND (except WIF = CHAOTIC) | **AGREE** | HIGH |
| 2 | Amplitude is the key differentiator (BTC 1.0% vs ZRO 4.3%) | **AGREE** | HIGH |
| 3 | Dynamic SL based on amplitude would have saved the ZRO SHORT trade | **PARTIAL** | MEDIUM |
| 4 | Position sizing should scale inversely with amplitude | **AGREE** | MEDIUM |
| 5 | Wave position (near peak/trough) can predict trade outcomes | **DISAGREE** | HIGH |

---

## Detailed Analysis

### Claim 1: All 20 tokens are MEDIUM_FREQ_TREND (except WIF)
**Verdict: AGREE**
**Confidence: HIGH**

Independent run of `wave_classifier.py` confirms:
- 19 tokens classified as MEDIUM_FREQ_TREND
- 1 token (WIF) classified as CHAOTIC
- No tokens classified as HIGH_FREQ_OSCILLATOR (post bug fix)

The bug fix (strict `>`/`<` instead of `>=`/`<=`) is verified correct in the code at line 90-97 of `wave_period_detector.py`.

### Claim 2: Amplitude is the key differentiator
**Verdict: AGREE**
**Confidence: HIGH**

My independent amplitude measurements:

| Token | Avg Amp | P95 Amp | Max Amp | Bucket |
|-------|---------|---------|---------|--------|
| BTC | 1.023% | 2.814% | 14.624% | LOW_AMP |
| ETH | 1.140% | 3.007% | 19.830% | LOW_AMP |
| SOL | 1.564% | 4.918% | 12.797% | MED_AMP |
| ZRO | 4.276% | 11.892% | 24.882% | HIGH_AMP |
| TRUMP | 4.012% | 11.015% | 82.450% | HIGH_AMP |
| WIF | 4.363% | 14.022% | 27.895% | HIGH_AMP |

These numbers match the brainstorm's claims exactly. The 4x amplitude difference between BTC and ZRO is real.

**However:** The amplitude sub-bucket boundaries are fragile. HYPE at 2.4775% is 0.02% below the HIGH_AMP threshold (2.5%). A tiny data change could flip its classification. The boundary should be reconsidered.

### Claim 3: Dynamic SL based on amplitude would have saved the ZRO SHORT trade
**Verdict: PARTIAL — technically true, practically dangerous**
**Confidence: MEDIUM**

The math checks out:
- ZRO SHORT at $1.066, stopped out at $1.075 (0.84% price move, -4.22% PnL at ~5x leverage)
- If SL was set at avg_amp (4.28%): SL = $1.1116 — trade would have survived

**But this reasoning has critical flaws:**

1. **Leverage not accounted for.** A 4.28% amplitude SL at 5x leverage = 21.4% max portfolio loss per trade. The brainstorm never mentions this.

2. **The amplitude-based SL is wider than necessary.** The price only moved 0.84% against the position. Setting SL at 4.28% means accepting 5x more adverse movement before stopping out.

3. **Amplitude is non-stationary.** ZRO's amplitude varied from 2.87% (Q1) to 6.45% (Q3) within the same 30-day window. The "average" is misleading.

4. **The trade's actual problem wasn't the SL width.** The SHORT was entered at 1.066 after the price had already declined from 1.117 to 1.074. The entry timing was late in the move, not the SL width.

**Better fix:** Set SL based on recent amplitude (last 5 waves), not the 30-day average.

### Claim 4: Position sizing should scale inversely with amplitude
**Verdict: AGREE (logically sound, numbers need backtesting)**
**Confidence: MEDIUM**

The concept is correct — higher amplitude means higher risk per unit of price movement, so position size should be smaller to maintain equal dollar-risk. The specific multipliers (1.0x LOW, 0.9x MED, 0.7x HIGH, 0.5x CHAOTIC) are reasonable starting points but arbitrary without backtest validation.

**Issues:**
1. The multipliers don't account for leverage. A 0.7x position on ZRO at 5x leverage is still 3.5x effective exposure.
2. Kelly criterion already adjusts for win rate and avg win/loss. Adding amplitude adjustment on top could over-reduce position sizes.
3. The 0.5x for CHAOTIC may be too aggressive — WIF at 50% reduction might never generate meaningful returns.

### Claim 5: Wave position (near peak/trough) can predict trade outcomes
**Verdict: DISAGREE — directly contradicted by trade data**
**Confidence: HIGH**

This is the most critical finding. The brainstorm's wave_position logic is contradicted by the actual ZRO trade data:

| Trade | Wave Position | Alignment | PnL |
|-------|--------------|-----------|-----|
| SHORT @ 1.066 | post_peak_declining | ✓ ALIGNED | **-4.22%** |
| SHORT @ 1.1267 | near_trough | ✗ AGAINST | **+16.06%** |
| SHORT @ 1.1727 | near_peak | ✓ ALIGNED | **+1.11%** |

**Key findings:**
1. The losing trade (-4.22%) was classified as "ALIGNED" (post_peak_declining), not "near_trough" as the brainstorm claims.
2. The best trade (+16.06%) was classified as "AGAINST" the wave (near_trough).
3. The brainstorm incorrectly states "The losing ZRO SHORT at $1.066 would have been filtered (entered near trough = low score)." This is factually wrong — the trade was post_peak_declining.
4. Wave-aligned trades averaged -1.55% PnL vs +16.06% for against-wave trades.
5. **Sample size of 3 is far too small to draw conclusions**, but the data certainly doesn't support the claim.

**The wave position scoring logic needs fundamental rethinking.** The current implementation in `wave_trade_context.py` may be flawed:
- It compares time-since-peak vs time-since-trough, but this doesn't capture the actual price trajectory.
- A "post_peak_declining" position is actually GOOD for a SHORT — the issue is that the wave might reverse.
- The scoring doesn't account for how far along the decline/rise you are.

---

## Code Quality Assessment

### `wave_period_detector.py`
- ✅ Bug fix is correct (strict `>`/`<` on lines 90-97)
- ✅ Data gap filtering is implemented (48h max gap)
- ⚠️ `calculate_wave_periods` uses close prices only — should also consider high/low for extrema
- ⚠️ No handling of zero-price candles (could cause division by zero in amplitude calc)
- ⚠️ The `analyze_wave_periods` function calls `get_candles` twice in the pretty-print path (lines 408, 502)

### `wave_classifier.py`
- ✅ Clean implementation, correct logic
- ⚠️ Classification thresholds (60% dominance) are hardcoded — should be in `hermes_constants.py`
- ⚠️ No handling for tokens with insufficient data

### `wave_trade_context.py`
- ⚠️ Duplicate `find_peaks_troughs` and `get_candles` functions (should import from `wave_period_detector`)
- ⚠️ Wave position logic may be flawed (see Claim 5 analysis above)
- ⚠️ Hardcoded `token = 'ZRO'` in `analyze_trade_in_wave_context` default parameter

---

## Missing Ideas (Not in Brainstorm)

### 1. Leverage-Aware Stop Loss (CRITICAL)
The brainstorm calculates SL as a percentage of price but never accounts for leverage. A 4.28% SL at 5x = 21.4% portfolio loss. Every SL suggestion should be expressed in both price% and portfolio% terms. This is a fundamental omission.

### 2. Amplitude Regime Detection
Amplitude is non-stationary. ZRO's amplitude ranged from 2.87% (Q1) to 6.45% (Q3). TRUMP went from 2.26% to 8.42%. The brainstorm treats amplitude as a static property. We need:
- Rolling amplitude windows (not 30-day averages)
- Regime detection (is amplitude expanding or compressing?)
- Adaptive SL that responds to amplitude changes within a trade

### 3. Amplitude Mean-Reversion Strategy
After high-amplitude periods, does amplitude tend to compress? If so, we could:
- Enter trades when amplitude is at historical highs (expecting compression)
- Use this as a vol-selling strategy
- The data suggests amplitude has autocorrelation — test this

### 4. Multi-Timeframe Amplitude Analysis
The brainstorm only uses 1h candles. Amplitude on 4h or daily might be:
- More stable (less noise)
- Better for SL/TP setting
- Different classification results

### 5. Amplitude-Winrate Correlation Backtest
Has anyone actually tested whether high-amplitude tokens have lower win rates? The brainstorm assumes amplitude is bad, but:
- High amplitude also means bigger wins when trades work
- The net effect (win rate * avg win - loss rate * avg loss) might favor HIGH_AMP tokens
- This needs empirical validation before adjusting anything

### 6. Time-of-Day Amplitude Effects
Some tokens might have different amplitude profiles at different hours. If ZRO is more volatile during Asian session, we should avoid trading it then. No one has checked this.

### 7. Amplitude Clustering (Volatility Regimes)
Do amplitude regimes persist? If ZRO enters a high-amplitude phase, does it stay there for days/weeks? This would inform:
- How often to update the amplitude cache
- Whether to pause trading when amplitude spikes
- Position sizing responsiveness

### 8. Amplitude-Adjusted Take Profit with Partial Exits
Instead of a single TP at avg_amplitude, consider:
- Take 50% at 0.5x amplitude (lock in partial profit)
- Trail the remaining 50% with a tighter stop
- This captures more of the wave while limiting downside

### 9. Cross-Token Amplitude Correlation
When multiple HIGH_AMP tokens (ZRO, TRUMP, SUI) are all expanding amplitude simultaneously, it might signal a market-wide volatility event. This could be used as a portfolio-level risk signal.

### 10. Amplitude-Based Signal Filtering (Not Just Scoring)
The brainstorm multiplies signal confidence by amplitude factor. But a better approach might be:
- Hard filter: Don't take any signal on CHAOTIC tokens below a confidence threshold
- Soft filter: Reduce size for HIGH_AMP tokens
- These are different mechanisms with different risk profiles

---

## Specific Code Issues Found

1. **HYPE classification fragility:** HYPE at 2.4775% is 0.02% below the HIGH_AMP threshold. One more candle could flip it. Consider wider buckets or hysteresis.

2. **BTC CV anomaly:** BTC has CV=8.87 (extremely high) but is classified MEDIUM_FREQ_TREND. The classification logic uses fast/med/slow percentages, which are robust, but the CV metric is misleading for tokens with data gaps.

3. **TRUMP max amplitude 82.45%:** This is an extreme outlier that skews all statistics. Should be filtered or winsorized before computing averages.

4. **Zero-amplitude waves:** ZRO has waves with 0.00% amplitude (min=0.0000%). These are flat-price candles that should be filtered out before amplitude calculation.

5. **Duplicate code:** `wave_trade_context.py` duplicates `find_peaks_troughs` and `get_candles` instead of importing from `wave_period_detector.py`. This is a maintenance risk.

---

## Recommendations

1. **Don't implement wave-position entry filter (Idea 2) yet.** The data contradicts the hypothesis, and the sample size is too small. Need 50+ trades per token before this is actionable.

2. **Implement amplitude cache (Idea 4) with rolling windows, not TTL.** Use the last 100 waves (not 1-hour TTL) to compute amplitude. This adapts to regime changes.

3. **Add leverage to all SL/TP calculations.** Every suggestion should show: price%, portfolio%, and maximum acceptable loss.

4. **Backtest amplitude-based position sizing before implementing.** The 0.7x/0.5x multipliers are guesses. Run the backtest first.

5. **Fix the duplicate code in wave_trade_context.py.** Import from wave_period_detector instead of duplicating functions.

6. **Filter extreme outliers before computing amplitude statistics.** Remove waves with >30% amplitude (likely data errors or black swan events) before computing averages.

7. **Test multi-timeframe amplitude.** Run the same analysis on 4h candles and compare with 1h results.

---

## Bottom Line

The core insight is correct: amplitude is the key differentiator, not frequency. The amplitude numbers are accurate. The position sizing concept is sound. But several specific claims are contradicted by data (wave position prediction), the SL suggestions ignore leverage, and amplitude is treated as static when it's clearly dynamic. The brainstorm is a good starting point but needs significant refinement before implementation.
