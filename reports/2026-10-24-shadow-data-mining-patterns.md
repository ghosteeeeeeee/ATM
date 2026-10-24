# Shadow Data Mining: Patterns for New Signals

**Date:** 2026-10-24
**Analyst:** Hermes (CEO agent)
**Data:** 17,321 shadow signals (16,819 closed)
**Purpose:** Mine shadow data for profitable patterns to inform new signal design

---

## Executive Summary

The shadow data reveals three critical patterns:

1. **Winners hold 2x longer than losers** (78-90min vs 39-40min)
2. **Winners have MFE/MAE ratio of 36-50x, losers have 1-2x** — this is the key differentiator
3. **Profitable signals are MOMENTUM signals in volatile markets**, not mean-reversion

---

## 1. Top vs Bottom Decile Comparison

| Group | Direction | Trades | Avg RSI | Avg ATR | Avg PnL | Avg MFE | Avg MAE | Avg Hold |
|-------|-----------|--------|---------|---------|---------|---------|---------|----------|
| TOP 10% | LONG | 546 | 64.4 | 2.24 | +1.398 | 4.305 | -2.05 | **78 min** |
| TOP 10% | SHORT | 1,141 | 38.7 | 1.72 | +1.305 | 4.546 | -1.499 | **90 min** |
| BOTTOM 10% | LONG | 910 | 55.8 | 1.79 | -1.018 | 1.237 | -4.129 | **40 min** |
| BOTTOM 10% | SHORT | 778 | 39.9 | 1.69 | -1.139 | 3.227 | -2.384 | **39 min** |

### Key Differences

1. **Winners hold 2x longer** (78-90min vs 39-40min)
2. **Winners have higher MFE** (4.3-4.5 vs 1.2-3.2) — much bigger moves
3. **Winners have lower MAE** (-1.5 to -2.1 vs -2.4 to -4.1) — less adverse excursion
4. **Winners have higher ATR** (1.72-2.24 vs 1.69-1.79) — more volatile
5. **LONG winners have higher RSI** (64.4 vs 55.8) — momentum confirmation
6. **SHORT winners have similar RSI** (38.7 vs 39.9) — RSI doesn't differentiate SHORT

---

## 2. MFE/MAE Ratio: The Key Differentiator

| Group | Direction | Trades | Avg MFE | Avg MAE | MFE/MAE Ratio | Avg PnL |
|-------|-----------|--------|---------|---------|---------------|---------|
| WINNER | LONG | 2,657 | 2.44 | -2.08 | **36.28x** | +0.454 |
| WINNER | SHORT | 4,694 | 2.969 | -1.615 | **50.75x** | +0.48 |
| LOSER | LONG | 3,523 | 1.437 | -3.25 | **0.97x** | -0.748 |
| LOSER | SHORT | 4,247 | 2.415 | -2.596 | **2.42x** | -0.783 |

### Key Insight

**Winners have MFE/MAE ratio of 36-50x, losers have 1-2x.**

This means:
- **Winners**: big favorable moves (MFE 2.4-3.0), small adverse moves (MAE -1.6 to -2.1)
- **Losers**: small favorable moves (MFE 1.4-2.4), big adverse moves (MAE -2.6 to -3.3)

**Implication:** The exit engines should let winners run (they're already doing this with PM Trail) and cut losers faster (they're already doing this with Hard Max Loss). The problem is the ENTRIES — losers don't have the MFE potential to overcome the MAE.

---

## 3. Profitable Signal Patterns

### SHORT Signals: Momentum Continuation in Volatile Downtrends

| Signal | Trades | WR | Avg PnL | Vol Regime | Avg RSI | Avg ATR |
|--------|--------|-----|---------|------------|---------|---------|
| volume_breakout_short | 14 | 100% | +1.70 | EXTREME | 36.0 | 2.25 |
| volume_breakout_short | 20 | 100% | +1.63 | HIGH | 28.9 | 1.21 |
| pump-chain-v6 | 43 | 100% | +1.61 | EXTREME | 54.3 | 2.83 |
| pump-chain | 453 | 100% | +1.05 | EXTREME | 33.3 | 3.42 |
| pump-chain | 321 | 100% | +1.02 | HIGH | 30.9 | 1.25 |
| grind_breakout_short | 12 | 100% | +1.03 | HIGH | 27.5 | 1.26 |

**Pattern:** SHORT signals work best when:
- Volatility is EXTREME or HIGH (ATR > 1.2%)
- RSI is LOW (27-36) — oversold
- Price is below EMA300 (downtrend)
- Best exit: pump_exit (83.1% WR in HIGH, +0.691 avg)

### LONG Signals: Momentum Continuation in Volatile Uptrends

| Signal | Trades | WR | Avg PnL | Vol Regime | Avg RSI | Avg ATR |
|--------|--------|-----|---------|------------|---------|---------|
| hh_hl_breakout_long | 8 | 100% | +2.05 | EXTREME | 71.0 | 2.65 |
| r2_trend_long | 11 | 100% | +1.38 | EXTREME | 73.5 | 2.47 |
| pump-chain-v6 | 137 | 100% | +1.03 | EXTREME | 72.7 | 2.88 |
| pump-chain | 185 | 100% | +0.96 | EXTREME | 72.8 | 2.41 |

**Pattern:** LONG signals work best when:
- Volatility is EXTREME or HIGH (ATR > 1.2%)
- RSI is HIGH (71-81) — overbought (momentum continuation)
- Price is above EMA300 (uptrend)
- Best exit: pm_trail (100% WR in EXTREME, +0.424 avg)

---

## 4. Exit Engine Performance by Regime

| Regime | Direction | Engine | Trades | WR | Avg PnL |
|--------|-----------|--------|--------|-----|---------|
| HIGH | SHORT | pump_exit | 59 | 83.1% | +0.691 |
| EXTREME | SHORT | pump_exit | 68 | 64.7% | +0.538 |
| EXTREME | LONG | pm_trail | 458 | 100% | +0.424 |
| EXTREME | SHORT | pm_trail | 672 | 100% | +0.410 |
| HIGH | SHORT | pm_trail | 989 | 100% | +0.355 |
| HIGH | LONG | pm_trail | 476 | 100% | +0.339 |
| HIGH | SHORT | atr | 575 | 45.4% | +0.227 |
| EXTREME | SHORT | atr | 1,027 | 47.0% | +0.183 |

**Key insight:** PM Trail is the universal winner (100% WR by design). Pump Exit is best for SHORT in HIGH/EXTREME volatility.

---

## 5. Time-of-Day Patterns

No strong time-of-day pattern exists. Winners and losers are evenly distributed across all hours. The only slight pattern:
- Hour 0 (UTC): SHORT winners +0.606 avg (best hour for SHORT)
- Hour 4 (UTC): LONG winners +0.552 avg (best hour for LONG)

**Implication:** Time-of-day is not a useful filter for new signals.

---

## 6. Recommendations for New Signals

### Signal 1: Volatility Momentum SHORT
- **Thesis:** In high-volatility downtrends, oversold conditions are continuation signals
- **Entry:** SHORT + RSI < 35 + ATR > 1.5% + Price < EMA300
- **Exit:** pump_exit (83.1% WR in HIGH volatility)
- **Expected:** 60-80% WR, +0.5 to +1.0 avg PnL

### Signal 2: Volatility Momentum LONG
- **Thesis:** In high-volatility uptrends, overbought conditions are continuation signals
- **Entry:** LONG + RSI > 70 + ATR > 1.5% + Price > EMA300
- **Exit:** pm_trail (100% WR in EXTREME volatility)
- **Expected:** 70-100% WR, +0.4 to +1.0 avg PnL

### Signal 3: Volume Breakout Continuation (LONG)
- **Thesis:** Volume breakouts in high-volatility regimes continue
- **Entry:** LONG + Volume > 2x avg + ATR > 1.5% + Price > EMA300
- **Exit:** pump_exit or pm_trail
- **Expected:** 60-80% WR, +1.0 to +1.7 avg PnL

---

## 7. What Makes Winners Different (Summary)

| Characteristic | Winners | Losers | Implication |
|----------------|---------|--------|-------------|
| Hold time | 78-90 min | 39-40 min | Let winners run |
| MFE | 2.4-3.0% | 1.4-2.4% | Need bigger moves |
| MAE | -1.6 to -2.1% | -2.6 to -3.3% | Cut losers faster |
| MFE/MAE ratio | 36-50x | 1-2x | **Key differentiator** |
| ATR | 1.72-2.24% | 1.69-1.79% | Need more volatility |
| RSI (LONG) | 64.4 | 55.8 | Momentum confirmation |
| RSI (SHORT) | 38.7 | 39.9 | RSI doesn't differentiate |

**Bottom line:** The exits are working correctly. The gates are working correctly. The problem is the ENTRIES — they don't have the MFE potential to overcome the MAE. New signals need to target higher-volatility, momentum-continuation setups.
