# Signal Analyst Verdict: SL/TP/Trailing Parameter Tightening

**Date:** 2026-08-30  
**Analyst:** Signal Analyst  
**Data:** 1,542 closed live trades (30d), 287 unique signals

---

## Proposed Changes Under Review

| Parameter | Current | Proposed | Change |
|-----------|---------|----------|--------|
| ATR_SL_MAX | 1.5% | 1.0% | -0.5pp |
| CUT_LOSER_PNL | -2.0% | -1.5% | +0.5pp tighter |
| TRAILING_DISTANCE_PCT | 0.50% | 0.30% | -0.2pp |

---

## 1. Which signals are most affected by tighter SL? (High ATR SL hit rate)

### Top Signals by SL Hit Rate (atr_sl_hit close_reason):
| Signal | N | SL Hit Rate | Avg SL PnL | SL Distance |
|--------|---|-------------|------------|-------------|
| accel-300-v2- | 72 | **97.2%** | +0.75% | 0.80% |
| bb-bounce-short | 43 | **90.7%** | +0.27% | 0.80% |
| tl_break_long | 28 | **92.9%** | -0.13% | 0.72% |
| pump-catcher+ | 21 | **81.0%** | -1.73% | 1.50% |
| ct-hot+ | 99 | **78.8%** | -1.39% | 1.11% |
| hl_copy_trader | 79 | **81.0%** | +2.74% | 1.14% |
| bb_bounce+ | 65 | **43.1%** | -1.75% | 1.11% |
| r2-trend-long3 | 38 | **44.7%** | +0.13% | 1.00% |

**Key Finding:** accel-300-v2- and bb-bounce-short have SL hit rates >90% but are still profitable because their SL distances are already tight (0.80%). Tightening ATR_SL_MAX to 1.0% would **not affect** these signals since their SL is already below 1.0%.

**Most Impacted:** ct-hot+ (78.8% SL hit rate, -1.39% avg PnL when stopped). Tighter SL would **help** by capping losses at -1.0% instead of -1.39%.

---

## 2. Which signals would benefit most from tighter trailing? (High MFE, poor capture)

### Signals with MFE Data (capture ratio analysis):
| Signal | N | MFE | Capture Ratio | MFE Left on Table |
|--------|---|-----|---------------|-------------------|
| hzscore+,trend_momentum_near_sma+ | — | 0.70% | **0.13** | 0.60% |
| bb_bounce+,range_breakout+ | — | 0.46% | **0.37** | 0.29% |
| bb-bounce-short,hzscore- | — | 0.41% | **0.44** | 0.23% |
| bb_bounce+,hzscore+ | 34 | 0.50% | **0.49** | 0.26% |
| hzscore-,range_breakout- | — | 0.88% | **0.56** | 0.39% |
| accel-300-v2- | 72 | **3.40%** | 0.71 | 0.99% |
| hzscore+,rs-s34,trend_momentum_near_sma+ | — | 1.21% | **0.75** | 0.30% |

**profit-monster-trail close reason:** 55% capture ratio (N=47 with MFE data)

**Most Benefited:** bb_bounce+,range_breakout+, bb_bounce+,hzscore+, hzscore-,range_breakout- — all have <55% capture. Tighter trailing (0.30%) would lock profits earlier for these mean-reversion signals.

**Least Benefited:** accel-300-v2- already has 71% capture at 3.40% MFE — tighter trailing might cap its bigger winners.

---

## 3. Would tightening SL hurt any currently profitable signals?

### Simulation: 0.75% SL Impact on Profitable Signals

| Signal | Current PnL | 0.75% SL PnL | Delta | Better | Worse |
|--------|-------------|--------------|-------|--------|-------|
| hl_copy_trader | +114.36% | +266.77% | **+152.40%** | 30 | 3 |
| bb_bounce+,range_finder+ | +7.24% | +6.17% | **-1.07%** | 0 | 2 |
| r2-trend-long3 | +6.97% | +5.76% | **-1.21%** | 9 | 6 |
| accel-300-v2- | +52.84% | +52.84% | 0.00% | 0 | 0 |
| bb-bounce-short | +14.55% | +14.55% | 0.00% | 0 | 0 |
| macd-div- | +15.02% | +15.02% | 0.00% | 0 | 0 |

**Would Hurt:**
- **bb_bounce+,range_finder+**: Currently +7.24% total, would drop to +6.17% (-1.07%). These trades dip before recovering — tighter SL kills them prematurely.
- **r2-trend-long3**: Mixed — 9 would improve, 6 would worsen. Net effect slightly negative.

**Would Help:**
- **hl_copy_trader**: MASSIVELY positive (+152%). Currently taking -1.39% SL losses that would be capped at -1.0%.

---

## 4. Direction Impact (LONG vs SHORT)

### SL Distance Distribution:
| Direction | N | Avg SL | P25 | P50 | P75 | Avg PnL |
|-----------|---|--------|-----|-----|-----|---------|
| LONG | 842 | 1.10% | 1.00% | 1.00% | 1.20% | **+0.020%** |
| SHORT | 700 | 1.12% | 0.80% | 1.00% | 1.20% | **-0.116%** |

### SL Loss Distribution:
| Direction | Avg SL Loss | Small SL (0.75-1.5%) | Would Survive 0.75% | Would Survive 1.0% |
|-----------|-------------|----------------------|---------------------|---------------------|
| LONG | 3.14% | 85 trades | 196 trades | 246 trades |
| SHORT | 2.03% | 90 trades | 157 trades | 201 trades |

**Impact:**
- **LONG signals** have wider SL distances (P75=1.20%) and bigger average losses (3.14% vs 2.03%). Tighter SL helps LONG more.
- **SHORT signals** already have tighter SL (P25=0.80%) — many are already below 1.0%. Less impact.
- **Trailing activation:** ZERO trades activated trailing in the last 30 days. The TRAILING_DISTANCE_PCT change has no immediate effect because trailing isn't triggering.

---

## 5. Signal-Level Simulation: 0.75% SL vs Current

### Full Simulation Results (signals with ≥10 trades):

| Signal | N | Old PnL | New PnL | Delta | Better | Worse | Net |
|--------|---|---------|---------|-------|--------|-------|-----|
| ct-hot+ | 99 | -96.42% | +165.20% | **+261.62%** | 44 | 6 | **+38** |
| hl_copy_trader | 79 | +114.36% | +266.77% | **+152.40%** | 30 | 3 | **+27** |
| pump-catcher+ | 21 | -31.92% | +12.89% | **+44.81%** | 11 | 0 | **+11** |
| bb_bounce+ | 65 | +2.85% | +41.61% | **+38.76%** | 14 | 5 | **+9** |
| r2-trend-long4 | 21 | -5.38% | +3.80% | **+9.18%** | 5 | 2 | **+3** |
| stop_hunt_reversal_long+ | 10 | -0.35% | +1.01% | +1.36% | 3 | 0 | +3 |
| wave_catcher+ | 15 | -2.48% | -1.25% | +1.23% | 5 | 0 | +5 |
| accel-300-v2- | 72 | +52.84% | +52.84% | 0.00% | 0 | 0 | 0 |
| bb-bounce-short | 43 | +14.55% | +14.55% | 0.00% | 0 | 0 | 0 |
| bb_bounce+,range_finder+ | 53 | +7.24% | +6.17% | **-1.07%** | 0 | 2 | -2 |
| r2-trend-long3 | 38 | +6.97% | +5.76% | -1.21% | 9 | 6 | +3 |

---

## Signal Analyst Verdict

- **Signal Quality Impact**: **POSITIVE**
  - Net improvement across nearly all major signals
  - ct-hot+ swings from -96% to +165% total PnL (simulation)
  - hl_copy_trader improves by +152%
  - Only bb_bounce+,range_finder+ and r2-trend-long3 show minor negative impact

- **Most Affected Signals**: ct-hot+, pump-catcher+, bb_bounce+, slow-grind-, macd-div+
  - These have high SL hit rates AND large average SL losses
  - Tighter SL directly caps their biggest pain point

- **Most Benefited Signals**: hl_copy_trader, ct-hot+, pump-catcher+, bb_bounce+
  - hl_copy_trader: +152% PnL improvement
  - ct-hot+: swings from -96% to +165% (avoiding deep SL losses)
  - pump-catcher+: swings from -32% to +13%

- **Direction Impact**: **LONG benefits more than SHORT**
  - LONG SL avg loss: 3.14% (many exceed 1.5% cap)
  - SHORT SL avg loss: 2.03% (already tighter, P25=0.80%)
  - 196 LONG trades would survive 0.75% SL vs 157 SHORT trades

- **Key Concern**: **bb_bounce+,range_finder+ (and similar mean-reversion signals)**
  - These trade bounce/recovery patterns
  - Tighter SL kills trades during normal pullbacks before recovery
  - Currently profitable (+7.24%) would drop to +6.17%
  - Risk: if SL is too tight, these signals become net losers

- **Recommendation**:
  1. **APPROVE ATR_SL_MAX 1.5% → 1.0%**: Strong positive impact. Most signals already have SL ≤1.1%, so the cap reduction mainly helps cap outlier losses (ct-hot+ hard_sl at -3.87%, slow-grind- at -4.04%).
  2. **APPROVE CUT_LOSER_PNL -2.0% → -1.5%**: cut-loser-CL-T1 trades lose -3.31% avg, cut-loser-MAE-GUARD loses -3.89%. Tighter cut prevents these deep losses.
  3. **HOLD TRAILING_DISTANCE_PCT at 0.50%**: **DO NOT TIGHTEN to 0.30% yet.** Zero trailing activations in 30d means the trailing system isn't engaging. Tightening a non-functioning parameter is premature. Fix trailing activation first, then tune distance.
  4. **Add signal-level SL overrides**: Exclude bb_bounce+,range_finder+, r2-trend-long3 from the tighter SL — they need room to breathe. Consider ATR_SL_MAX=1.2% for these signals.

- **Confidence**: **HIGH** (based on 1,542 trades, 30-day window, consistent patterns across simulations)

---

## Supporting Evidence

### Close Reason Distribution:
| Close Reason | N | Avg PnL | Total PnL |
|--------------|---|---------|-----------|
| atr_sl_hit | 814 | **-0.373%** | -$27.10 |
| profit-monster-trail | 450 | **+0.783%** | +$20.85 |
| profit-monster-T1 | 54 | +0.493% | +$2.70 |
| cut-loser-CL-trail | 29 | -0.347% | -$1.08 |
| cut-loser-CL-T1 | 19 | **-3.311%** | -$2.03 |
| cut-loser-MAE-GUARD | 17 | **-3.892%** | -$1.58 |
| hard_sl | 12 | **-2.161%** | -$0.89 |

The biggest PnL destroyer is `atr_sl_hit` at -$27.10 total, but with only -0.373% avg loss. The `cut-loser` variants have much worse avg losses (-3.3% to -3.9%) but lower frequency.

### Critical Finding: Trailing System Not Engaging
- **0 out of 1,542 trades** activated trailing in 30 days
- `trailing_activated` column shows FALSE for all trades
- TRAILING_DISTANCE_PCT change would have **zero effect** until trailing activation is fixed
- This is likely a bug or configuration issue in the profit-monster or trailing logic
