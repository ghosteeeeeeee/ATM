# Hermes Signal Ideas

> Sourced from: **Volume Momentum Breakout TP and SL** by Vishnu Bajpai (MQL5 #170681)
> https://www.mql5.com/en/market/product/170681 | Published: 27 March 2026 | Version: 1.0 | FREE

---

## Product Overview

Volume Momentum Breakout is a high-precision trading indicator for MetaTrader 5.
Core thesis: "detects powerful breakout moves using a combination of **volume-normalized momentum**
and **structural price behavior**. Identifies when real market participation enters the move —
helping traders avoid false breakouts and low-energy conditions."

**Key Mechanisms (verbatim from product):**
- "Volume-normalized momentum engine to detect real breakout strength"
- "Dual modes: Pivot-based breakout detection and OB/OS momentum crossover"
- "Filters low-quality signals using **volume and price displacement logic**"
- "ATR-based or percentage-based stop loss calculation"
- "Multi-target risk-reward system for structured trade management"
- "Works across Forex, Gold, Indices, and Crypto markets"

---

## Signal Ideas (Prioritized for Hermes)

### 1. Volume-Price Displacement Breakout [HIGHEST PRIORITY]
**Source:** Product's core signal filter — "Filters low-quality signals using volume and price displacement logic"

- **Signal:** LONG when price breaks a structural level (pivot/S&D zone) AND displacement > X%
- **Filter:** Only trigger if volume is elevated OR price displacement exceeds a threshold (e.g., >0.5% body)
- **Why it solves the noise problem:** Instead of generating signals on every RSI cross, only signal when price actually DISPLACES (breaks structure) with conviction. Low displacement = low energy = skip.
- **Hermes integration:** Add displacement threshold check to existing z-score velocity signals

### 2. Multi-Timeframe Momentum Confluence
**Source:** Inspired by product's "dual mode" approach (momentum crossover vs breakout)

- **Signal:** LONG when momentum indicators agree across timeframes
  - Example: RSI(14) < 35 on 1H AND RSI(14) < 45 on 4H (oversold on both TF)
  - Or: Z-score velocity positive on 1H AND positive on 4H
- **Why it solves the noise problem:** A signal confirmed on 4H has much higher probability than 1H-only
- **Hermes integration:** Reuse existing regime detection (4H) + add multi-TF momentum check to signal scoring

### 3. ATR-Adaptive TP/SL Zones
**Source:** Product's "ATR-based or percentage-based stop loss calculation" + "Built-in TP1, TP2, TP3"

- **Signal:** Not a trigger per se, but a position management system
- **Approach:** Use ATR(14) to set dynamic SL/TP distances:
  - SL = entry ± 1.5 * ATR(14)
  - TP1 = entry + 1.5 * ATR (1R)
  - TP2 = entry + 3.0 * ATR (2R)
  - TP3 = entry + 4.5 * ATR (3R)
- **Why it solves the noise problem:** Tokens with different volatility get appropriate stops — avoids getting stopped out on volatile coins or taking tiny profits on calm ones
- **Hermes integration:** Modify trailing stop logic in position_manager.py to use ATR-based levels

### 4. Momentum Crossover Mode (OB/OS)
**Source:** Product's "OB/OS momentum crossover" dual mode

- **Signal:** LONG when RSI crosses above 30 from below (RSI snap-back)
  - SHORT when RSI crosses below 70 from above
- **Why it solves the noise problem:** Pure mean-reversion at extremes — high win rate in ranging conditions
- **Hermes integration:** Add RSI extreme zone snap-back detection to signal_gen.py

### 5. Volume Spike Confirmation
**Source:** Product's "volume-normalized momentum engine" — volume confirmation

- **Signal:** Only allow LONG/SHORT when volume > 2x 20-period average volume (on the breakout candle)
- **Implementation:** Since Hermes may not have per-candle volume, use rate-of-change of volume or price acceleration
- **Why it solves the noise problem:** Price moves without volume are prone to reversal — volume confirmation is a strong filter
- **Hermes integration:** Compute volume ROC from HL data (if available) or use price velocity as a proxy

---

## Lower Priority (Good to Have)

### 6. Dynamic Breakout Zones
- Track "smart money" levels — support/resistance zones that price repeatedly tests
- Breakout signals are higher probability near these zones
- Would require S/R zone detection — moderate complexity

### 7. ADX Trend Strength Filter
- Only allow momentum-following signals when ADX > 25 (trending market)
- When ADX < 20 (ranging), prefer mean-reversion signals instead
- Moderate complexity — requires ADX indicator computation

### 8. Multi-Target RR System
- Instead of single TP, use product's TP1/TP2/TP3 approach (1R/2R/3R)
- Scale out: close 1/3 at TP1, 1/3 at TP2, let 1/3 run with trailing stop
- High impact for managing winners

---

## Priority Stack

| # | Idea | Effort | Impact | Hermes Fit |
|---|------|--------|--------|------------|
| 1 | Volume-Price Displacement Breakout | Medium | HIGH | Solves noise problem directly |
| 2 | Multi-TF Momentum Confluence | Low | HIGH | Reuses existing regime + RSI |
| 3 | ATR-Adaptive TP/SL Zones | Medium | HIGH | Improves position management |
| 4 | Momentum Crossover (OB/OS) | Low | MEDIUM | Quick RSI snap-back logic |
| 5 | Volume Spike Confirmation | Medium | MEDIUM | Needs vol ROC proxy |
| 8 | Multi-Target RR System | Medium | HIGH | Scale-out approach |
