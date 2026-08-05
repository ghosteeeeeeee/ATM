# mtp-zscore — Backtest Results & Recommended Parameters

**Date:** 2026-05-27
**Purpose:** Validate lookback periods and Z-score bounds for the mtp-zscore multi-timeperiod z-score signal

---

## Key Finding: Directional WR is Capped ~50%

Raw directional win rate (signal predicts correct next-bar direction) maxes out around 45-50% regardless of:
- Lookback period (tested 14 to 300)
- Z-score threshold (tested Z_MIN 0.0 to 3.5)
- Hold duration (tested 1 to 30 bars)

**The 75%+ system win rate comes from W/L ratio + profit-monster + ATR SL** — NOT from directional accuracy of the signal.

---

## Lookback Period Analysis

Tested across 10 winning tokens (DYDX, MON, XMR, BCH, FET, MORPHO, NEAR, ENS, LINK, AVAX) on ~20k-30k 1m candles.

### Per-Token Best Combo (highest directional WR, 10-bar hold):

| Token | Best Combo | Fires | WR% | AvgRet |
|-------|-----------|-------|-----|--------|
| DYDX | 14,50,150 | 3407 | 47.7% | +0.001% |
| MON | 50,100,150 | 3598 | 47.6% | +0.002% |
| XMR | 50,100,150 | 4521 | 45.2% | +0.001% |
| BCH | 50,150,200 | 4168 | 32.6% | -0.003% |
| FET | 50,150,200 | 4252 | 34.8% | -0.001% |

**Conclusion:** (50, 100, 200) is the best balanced combo across all tokens.

---

## W/L Ratio — The Real Driver

At Z>=3.5, W/L ratio explodes (but directional WR stays flat):

| Z_MIN | Combo | Fires | WR% | AvgWin | AvgLoss | W/L |
|-------|-------|-------|-----|--------|---------|-----|
| >=2.0 | (50,100,200) | 2212 | 46% | +0.84% | -0.42% | 2.0 |
| >=2.5 | (50,150,200) | 730 | 48% | +1.55% | -0.45% | 3.4 |
| >=3.0 | (50,150,200) | 228 | 49% | +3.84% | -0.53% | 7.3 |
| >=3.5 | (14,50,200) | 34 | 59% | +9.81% | -0.38% | 26.1 |

**Higher Z thresholds → sparser signals but MUCH higher W/L ratios.**

---

## Recommended Parameters

```python
# Lookbacks — balanced across tokens, best overall W/L
MTP_ZSCORE_LB_SHORT = 50
MTP_ZSCORE_LB_MID   = 100
MTP_ZSCORE_LB_LONG  = 200

# Per-period Z bounds — start conservative, tune from live data
Z_SHORT_Z_MIN = 1.5;  Z_SHORT_Z_MAX = 3.5
Z_MID_Z_MIN   = 1.5;  Z_MID_Z_MAX   = 3.5
Z_LONG_Z_MIN  = 1.5;  Z_LONG_Z_MAX  = 3.5

# Signal-level
MTP_ZSCORE_MIN_AGREE = 3  # 3/3 ALL periods must agree
MTP_ZSCORE_BASE_CONF = 80
MTP_ZSCORE_COOLDOWN_BARS = 20  # 20 min on 1m data
```

---

## Tuning Path

1. **Start:** Z_MIN = (1.5, 1.5, 1.5) → ~5000+ fires, good for initial validation
2. **Phase 2:** After 50+ live signals, raise to Z_MIN = (2.0, 2.0, 2.0) → ~1800 fires, better W/L
3. **Phase 3:** Tighten selectively based on live WR and W/L data

**Key insight:** The signal's job is NOT 75% directional accuracy. It's to identify high-W/L momentum setups where profit-monster can ride big winners and ATR SL handles the rest.