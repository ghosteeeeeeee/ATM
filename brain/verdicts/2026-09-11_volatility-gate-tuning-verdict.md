# Verdict: Volatility Gate V2 — Expansion/Compression Tuning (REVISED)

**Auditor:** Independent (fresh eyes, no prior context)
**Date:** 2026-09-11
**Status:** NO-GO — Significant issues remain in revised plan
**Confidence:** HIGH (90%)

---

## Executive Summary

This is the second review after the first was killed for fabricated data. The revised plan uses real trade-level data (300 trades from PostgreSQL at `data/real_trade_backtest.json`), and the statistics mostly check out. However, three critical issues prevent approval:

1. **ATR metric mismatch** — The backtest uses ATR ratio (current/average), but the live system uses ATR% (ATR/close). These are fundamentally different metrics. The plan assumes `atr_ratio > 1.5 = EXPANSION`, but the live system doesn't compute ATR ratio at all.

2. **Statistical insignificance** — The core finding (SHORT in FALLING EXPANSION = 83% WR) is based on only 10 SHORT trades. Z-test shows p=0.065, which is NOT statistically significant at α=0.05. Need n≥30 to reach significance at this effect size.

3. **Implementation complexity** — The plan proposes adding `get_atr_ratio()` and `get_btc_trend()` functions, but these don't exist in the codebase. The "simple 30-line change" is actually a new subsystem (~80-100 lines) that needs its own ATR ratio calculation, BTC trend detection, and integration testing.

**Recommendation:** REVISE. Fix the ATR metric mismatch, collect more data, and simplify the implementation.

---

## 1. Data Verification

### ✅ Data is Real
- **File:** `data/real_trade_backtest.json` (NOT the old `atr_ratio_backtest.json` that was fabricated)
- **Trade count:** 300 (matches plan)
- **Unique tokens:** 71
- **Fields:** token, direction, pnl_pct, regime, atr_ratio, btc_30m, btc_trend, aligned, signal, vol_regime, regime_4h
- **All fields present and populated** (except 2 null vol_regime for BTC trades)
- **ATR ratio ranges are consistent** with regime classification (EXPANSION: 1.51-2.32, NORMAL: 0.70-1.50, COMPRESSION: 0.24-0.70)
- **4 trades with exactly 0.00 PnL** — 2 BTC trades, 1 BANANA, 1 USUAL. These are neutral, not wins or losses.

### ✅ Statistics Mostly Match

| Claim | Plan | Actual | Match? |
|-------|------|--------|--------|
| EXPANSION total WR | 69% | 69.2% (18/26) | ✅ |
| EXPANSION SHORT WR | 80% | 80.0% (12/15) | ✅ |
| EXPANSION FALLING WR | 83% | 83.3% (10/12) | ✅ |
| NORMAL SHORT WR | 59% | 59.0% (69/117) | ✅ |
| NORMAL LONG WR | 51% | 50.9% (58/114) | ✅ |
| COMPRESSION SHORT WR | 69% | 69.2% (9/13) | ✅ |
| COMPRESSION LONG WR | 53% | 53.3% (16/30) | ✅ |
| EXPANSION RISING | 2 trades, 50% | 2 trades, 50% | ✅ |
| NORMAL FALLING | 55% | 54.9% (28/51) | ✅ |
| NORMAL RISING | 41% | 40.9% (18/44) | ✅ |
| NORMAL FLAT | 60% | 59.6% (81/136) | ✅ |

### ⚠️ One Misleading Claim

The plan says: "SHORTs in EXPANSION with BTC falling = 83% WR"

**Reality:** The 83% is for ALL trades (SHORT+LONG) in FALLING EXPANSION (10/12). The SHORT-specific rate is 80% (8/10). Still good, but the plan conflated the numbers. The two losses are SYRUP (-3.71%) and ICP (-7.94%).

---

## 2. Statistical Significance

### ❌ FALLING EXPANSION SHORT is NOT Significant

| Metric | Value |
|--------|-------|
| Target: FALLING EXPANSION SHORT | 8/10 = 80% WR |
| Baseline: All other trades | 162/290 = 55.9% WR |
| Z-statistic | 1.51 |
| p-value (one-tailed) | **0.065** |
| Significant at α=0.05? | **NO** |

### Sample Size Needed for Significance (at 80% WR vs 55.9% baseline)

| n | WR | Z | p-value | Significant? |
|---|-----|------|---------|--------------|
| 10 | 80% | 1.05 | 0.146 | ❌ |
| 20 | 80% | 1.49 | 0.068 | ❌ |
| 30 | 80% | 1.82 | **0.034** | ✅ |
| 50 | 80% | 2.35 | **0.009** | ✅ |
| 100 | 80% | 3.33 | **0.0004** | ✅ |

**Conclusion:** With n=10, you cannot distinguish this from random noise. The edge might be real, but you can't prove it yet. Need at least 30 more FALLING EXPANSION SHORT trades before deploying.

---

## 3. Critical Issue: ATR Metric Mismatch

### ❌ The backtest uses a DIFFERENT ATR metric than the live system

| Metric | Backtest | Live System |
|--------|----------|-------------|
| **What it measures** | ATR ratio = current_ATR / average_ATR | ATR% = ATR(14) / close_price × 100 |
| **Range in data** | 0.24 – 2.32 | 0.3% – 2.3% |
| **EXPANSION threshold** | ATR ratio > 1.5 | ATR% > 1.5 (called EXTREME) |
| **Meaning** | Relative volatility spike (ATR is 1.5x its average) | Absolute volatility level (ATR is 1.5% of price) |

**Why this matters:**
- A token can have EXTREME absolute volatility (high ATR%) but low ATR ratio (stable volatility — ATR is consistently high)
- A token can have NORMAL absolute volatility (moderate ATR%) but high ATR ratio (ATR just spiked from its average)
- These are **completely different signals**. The backtest's "EXPANSION" captures relative spikes, while the live system's EXTREME captures absolute levels.

### The plan assumes `atr_ratio > 1.5 = EXPANSION`

This is correct for the backtest data, but the live system doesn't compute ATR ratio. The plan proposes adding `get_atr_ratio()` — a new function that computes current_ATR / average_ATR. This is fine, but:
1. It's not a "simple 30-line change" — it's a new ATR ratio subsystem
2. It needs its own backtest to verify it captures the same signal as the backtest's ATR ratio
3. The existing volatility gate already uses ATR% (absolute), so adding ATR ratio (relative) creates two different volatility metrics in the same system

---

## 4. Implementation Assessment

### ❌ Plan Underestimates Complexity

The plan says: "Total: ~30 lines extending existing system."

**Reality:**

1. **`get_atr_ratio()`** — New function. Needs to:
   - Compute current ATR(14) from candles.db (reuse existing `get_atr_pct()` logic)
   - Compute average ATR(14) over a lookback period (what period? Plan says 500 candles = ~21 days)
   - Return the ratio (current / average)
   - Handle edge cases (insufficient data, missing candles)
   - **~30 lines by itself**

2. **`get_btc_trend()`** — New function. Needs to:
   - Query momentum_cache for BTC velocity/trend (which column? `velocity` is 30m price change, `momentum_state` is a string)
   - Classify as FALLING/FLAT/RISING (what thresholds? Plan doesn't specify)
   - Handle staleness (momentum_cache can be stale)
   - **~20 lines by itself**

3. **Enhanced `get_combined_multiplier()`** — The plan adds ATR ratio + BTC trend boost AFTER existing multiplier calculation. But:
   - The existing function already has 3 layers (vol_phase, lifecycle, inverse_penalty)
   - Adding a 4th layer makes the multiplier chain more complex
   - The interaction between layers is unclear
   - What happens when ATR ratio says EXPANSION but the regime classification says NORMAL?

4. **Integration testing** — None mentioned beyond "LOG-ONLY (48h)"

### ⚠️ `get_combined_multiplier()` Already Has 3 Layers

```python
def get_combined_multiplier(signal_type, regime, phase):
    mult = 1.0
    # 1. Volatility-phase combined multiplier (VOL_PHASE_MULTS)
    # 2. Lifecycle multiplier (early/concurrent/lagging)
    # 3. Inverse correlation penalty (dominant family vs signal family)
    return max(0.3, min(2.0, mult))
```

Adding a 4th layer (ATR ratio + BTC trend) means:
- 4 independent multiplier sources
- Potential for conflicting signals
- The clamp [0.3, 2.0] may mask important information
- Harder to debug when multipliers interact unexpectedly

---

## 5. Conflict Check

### ⚠️ Potential Conflicts with Existing Layers

1. **vol_phase_mult vs ATR ratio boost**
   - vol_phase_mult uses ATR% (absolute) to classify regime
   - ATR ratio boost uses ATR ratio (relative) to detect expansion
   - These can disagree: a token with stable high ATR% (EXTREME regime) might have low ATR ratio (not expansion)
   - The boost would not fire, even though the backtest suggests it should

2. **BTC trend vs existing BTC chop gate**
   - signal_compactor.py already reads `velocity FROM momentum_cache WHERE token='BTC'` (line 1104)
   - The plan's `get_btc_trend()` would use the same data source
   - But the chop gate uses velocity as a numeric threshold, while the plan classifies it as FALLING/FLAT/RISING
   - These could disagree on edge cases

3. **Signal direction extraction is fragile**
   - The plan uses `get_signal_direction(signal_type)` to extract direction from signal name
   - This function doesn't exist
   - Signal names are inconsistent: `pullback-entry-` vs `pullback_entry+` vs `pump-chain-` vs `pump_chain`
   - Some signals encode direction (`tl_break_long`), most don't (`bb_bounce+` fires for both)
   - The function would need to handle all variants or receive direction as a parameter

---

## 6. Expected Impact

### ❌ Impact Estimate is Optimistic

The plan says: "+$0.20 per 300 trades"

**Reality:**
- 10 trades in FALLING EXPANSION SHORT (not 12 — the plan counted all FALLING EXPANSION)
- Average PnL for FALLING EXPANSION SHORT: +1.82%
- Current WR: 80% (8/10 wins)
- If multiplier boost increases WR to 85% (1 more win), that's +1.82% on 1 trade

But:
- The boost is a multiplier on the confidence score, not a WR guarantee
- A 1.2x multiplier on a winning trade doesn't change whether it wins
- The real impact depends on how the multiplier affects position sizing
- With 10 trades, the expected impact is tiny regardless

**More realistic estimate:** +$0.05-0.10 per 300 trades (if the boost fires on 10 trades and increases avg PnL by 5-10% through better sizing).

---

## 7. What's Good

1. **Real data** — 300 trades from PostgreSQL, not fabricated (the old `atr_ratio_backtest.json` was replaced)
2. **Honest statistics** — All 11 claims verified against raw data, all match within rounding
3. **Conservative approach** — LOG-ONLY testing before live
4. **Modifies existing system** — Doesn't create parallel v2 (the plan code in the markdown shows modifying `get_combined_multiplier` in place)
5. **Reasonable constants** — ATR ratio thresholds (1.5, 0.7) are reasonable

---

## 8. Additional Findings

### Finding 1: EXPANSION LONG underperformance
EXPANSION LONG WR is only 54.5% (6/11). The plan doesn't address whether to penalize LONG in expansion, only whether to boost SHORT. The data suggests LONG in expansion should also be penalized.

### Finding 2: NORMAL misaligned trades outperform
In NORMAL regime, misaligned trades (counter-trend) have 58.3% WR vs 48.8% for aligned trades. The plan notes this but doesn't propose a fix. This suggests the existing directional filters may be too aggressive in NORMAL.

### Finding 3: SHORT bias across all regimes
SHORT outperforms LONG in every regime:
- EXPANSION: 80% vs 54.5%
- NORMAL: 59% vs 50.9%
- COMPRESSION: 69.2% vs 53.3%

The plan mentions this but doesn't propose a systemic fix. This is a structural LONG bias in the system that needs addressing.

---

## 9. Overall Verdict

### **NO-GO** ❌

**Reasons:**
1. **ATR metric mismatch** — Backtest uses ATR ratio (relative), live system uses ATR% (absolute). These are different metrics. The plan assumes they're the same.
2. **Statistical insignificance** — n=10 is too small to prove the edge exists (p=0.065). Need n≥30.
3. **Implementation complexity** — "30 lines" is actually ~80-100 lines with new functions, integration, and testing.
4. **Impact overestimate** — +$0.20 is optimistic; realistic is +$0.05-0.10.
5. **Signal direction extraction** — Fragile, based on string parsing of inconsistent signal names.

### What Needs to Happen Before GO

1. **Collect more data** — Run the backtest query again in 2-4 weeks to get n≥30 FALLING EXPANSION SHORT trades. Until then, the edge is unproven.

2. **Fix the ATR metric** — Either:
   - **Option A:** Use ATR% (absolute) in the backtest to match the live system (preferred — simpler, reuses existing infrastructure)
   - **Option B:** Add ATR ratio (relative) as a new metric and backtest it separately (more complex, but captures the relative spike signal)

3. **Simplify the implementation** — Instead of adding ATR ratio + BTC trend + direction extraction, just add BTC trend to the existing regime classification:
   - Modify `classify_volatility()` to accept an optional `btc_trend` parameter
   - When btc_trend is FALLING, shift the threshold down (e.g., EXTREME starts at 1.2% instead of 1.5%)
   - This avoids the ATR ratio vs ATR% confusion entirely

4. **Add `direction` parameter** — Pass direction explicitly to `get_combined_multiplier()` instead of extracting it from signal names.

5. **Add integration tests** — Verify that the new functions interact correctly with existing layers. Specifically test:
   - ATR ratio > 1.5 but regime = NORMAL (should the boost fire?)
   - BTC trend = FALLING but velocity = 0 (edge case)
   - Multiplier chain: vol_phase (1.5x) × lifecycle (0.5x) × ATR boost (1.2x) = 0.9x (is this correct?)

6. **Document compound effects** — Show how the new multiplier interacts with existing VOL_PHASE_MULTS, lifecycle, and inverse penalties.

---

## 10. Confidence Level

**HIGH (90%)** — Based on:
- Verified all 300 trades against raw data (all 11 statistical claims checked)
- Ran statistical significance tests (Z-test, sample size analysis)
- Checked ATR metric definitions against codebase
- Reviewed existing codebase for implementation details
- Identified concrete issues with data, statistics, and implementation

The data is real, the statistics are mostly correct, but the implementation has fundamental issues that need fixing before deployment.
