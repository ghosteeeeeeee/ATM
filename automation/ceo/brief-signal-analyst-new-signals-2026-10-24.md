# Signal Analyst Brief: New Signals from Shadow Data Mining

**From:** Hermes (CEO agent)
**To:** signal_analyst
**Date:** 2026-10-24 14:30 UTC
**Priority:** HIGH — T urgently needs new signals with positive expectancy

## Context

T's directive: "Urgently needed is new signals that can catch the moves the data is seeing."

Shadow-mode analysis of 17,321 signals reveals the core problem: **entries have negative expectancy**. The signals that pass all gates still lose money on average. We need NEW signals that are profitable BEFORE any filtering.

## Key Findings from Shadow Data

### What Works (Profitable Patterns)

**SHORT signals work best when:**
- Volatility is EXTREME or HIGH (ATR > 1.2%)
- RSI is LOW (27-36) — oversold
- Price is below EMA300 (downtrend)
- Best exit: pump_exit (83.1% WR in HIGH, +0.691 avg)

**LONG signals work best when:**
- Volatility is EXTREME or HIGH (ATR > 1.2%)
- RSI is HIGH (71-81) — overbought (momentum continuation)
- Price is above EMA300 (uptrend)
- Best exit: pm_trail (100% WR in EXTREME, +0.424 avg)

### What Doesn't Work (Losing Patterns)

**Mean-reversion signals lose:**
- LONG at oversold (low RSI) = catching falling knife
- SHORT at overbought (high RSI) = fading momentum
- All RSI bands show negative avg PnL in current signal set

### Top Performing Signals (n≥20, positive avg PnL)

| Signal | Direction | Trades | WR | Avg PnL | Vol Regime | Avg RSI | Avg ATR |
|--------|-----------|--------|-----|---------|------------|---------|---------|
| volume_breakout_short | SHORT | 14 | 100% | +1.70 | EXTREME | 36.0 | 2.25 |
| volume_breakout_short | SHORT | 20 | 100% | +1.63 | HIGH | 28.9 | 1.21 |
| pump-chain-v6 | SHORT | 43 | 100% | +1.61 | EXTREME | 54.3 | 2.83 |
| pump-chain | SHORT | 453 | 100% | +1.05 | EXTREME | 33.3 | 3.42 |
| pump-chain | SHORT | 321 | 100% | +1.02 | HIGH | 30.9 | 1.25 |
| grind_breakout_short | SHORT | 12 | 100% | +1.03 | HIGH | 27.5 | 1.26 |
| hh_hl_breakout_long | LONG | 8 | 100% | +2.05 | EXTREME | 71.0 | 2.65 |
| r2_trend_long | LONG | 11 | 100% | +1.38 | EXTREME | 73.5 | 2.47 |
| pump-chain-v6 | LONG | 137 | 100% | +1.03 | EXTREME | 72.7 | 2.88 |
| pump-chain | LONG | 185 | 100% | +0.96 | EXTREME | 72.8 | 2.41 |

### Exit Engine Performance by Regime

| Regime | Direction | Engine | Trades | WR | Avg PnL |
|--------|-----------|--------|--------|-----|---------|
| HIGH | SHORT | pump_exit | 59 | 83.1% | +0.691 |
| EXTREME | SHORT | pump_exit | 68 | 64.7% | +0.538 |
| EXTREME | LONG | pm_trail | 458 | 100% | +0.424 |
| EXTREME | SHORT | pm_trail | 672 | 100% | +0.410 |
| HIGH | SHORT | pm_trail | 989 | 100% | +0.355 |

## New Signal Recommendations

### Signal 1: Volatility Momentum SHORT

**Thesis:** In high-volatility downtrends, oversold conditions are continuation signals, not reversal signals. Short when momentum is already bearish and volatility confirms.

**Entry conditions:**
- Direction: SHORT
- RSI(14) < 35 (oversold)
- ATR% > 1.5 (EXTREME volatility)
- Price < EMA300 (downtrend confirmation)
- 5m momentum: negative (velocity < 0)

**Exit:**
- pump_exit engine (83.1% WR in HIGH volatility)
- Or: ATR trailing with 1.2% distance

**Expected performance:** Based on shadow data, ~60-80% WR, +0.5 to +1.0 avg PnL

### Signal 2: Volatility Momentum LONG

**Thesis:** In high-volatility uptrends, overbought conditions are continuation signals, not reversal signals. Long when momentum is already bullish and volatility confirms.

**Entry conditions:**
- Direction: LONG
- RSI(14) > 70 (overbought)
- ATR% > 1.5 (EXTREME volatility)
- Price > EMA300 (uptrend confirmation)
- 5m momentum: positive (velocity > 0)

**Exit:**
- pm_trail engine (100% WR in EXTREME volatility)
- Activation: +0.40%, trail: 0.20-1.20% (tiered)

**Expected performance:** Based on shadow data, ~70-100% WR, +0.4 to +1.0 avg PnL

### Signal 3: Volume Breakout Continuation

**Thesis:** Volume breakouts in high-volatility regimes continue. The existing volume_breakout_short is the best performer (+1.7 avg in EXTREME). Build a LONG version.

**Entry conditions:**
- Direction: LONG
- Volume > 2x 20-bar average
- ATR% > 1.5 (EXTREME volatility)
- Price > EMA300 (uptrend confirmation)
- Close > High of previous 3 bars (breakout confirmation)

**Exit:**
- pump_exit or pm_trail engine

**Expected performance:** Based on volume_breakout_short data, ~60-80% WR, +1.0 to +1.7 avg PnL

## Constraints

1. **No new indicators** — use existing RSI, ATR, EMA300, volume, momentum
2. **2-3 conditions max** — more = overfitting
3. **Every condition must be testable** — yes/no, no ambiguity
4. **Include volume confirmation** — price without volume is noise
5. **Test on shadow data** — validate against 17,321 shadow trades before deploying

## Deliverables

1. Signal specification (entry/exit rules)
2. Python implementation in `scripts/signals/`
3. Backtest on shadow data (if possible)
4. Shadow-mode deployment (not live)

## Related Files

- Shadow data: `brain/shadow_trades.db` (17,321 signals)
- Existing signals: `scripts/signals/` (131 files)
- Signal framework: `scripts/signals/__init__.py`
- Constants: `scripts/hermes_constants.py`
- Volatility gate: `scripts/volatility_gate_v2.py`
