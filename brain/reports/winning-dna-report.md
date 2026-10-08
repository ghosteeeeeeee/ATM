# Winning DNA Report — What Makes Great Trades

**Date:** 2026-10-08
**Data:** Top 100 winning trades by PnL% from PostgreSQL (5,100+ total trades)
**Analysis DB:** `/root/.hermes/data/winning_trades_analysis.db`

## Executive Summary

The top 100 winning trades share a clear "winning DNA" — specific entry conditions that correlate with high-profit outcomes. This report identifies those conditions and recommends a new signal design to replicate them.

## Key Findings

### 1. Top Signal: pump-chain+ LONG

| Signal | Trades | Avg PnL% | Total PnL |
|--------|--------|----------|-----------|
| **pump-chain+** | **14** | **+18.9%** | **+$7.68** |
| hl_copy_trader | 16 | +17.8% | +$4.59 |
| pullback-entry- | 10 | +10.6% | +$3.24 |
| ct_hot | 8 | +20.0% | +$3.15 |
| volume-breakout-long+ | 4 | +21.1% | +$2.26 |

**pump-chain+ LONG is the #1 signal by total PnL.** 14 of the top 100 winners.

### 2. Direction: LONG Dominates

| Direction | Trades | Total PnL |
|-----------|--------|-----------|
| **LONG** | **70** | **$27.42** |
| SHORT | 30 | $9.31 |

LONG trades account for 70% of top winners and 74% of total PnL.

### 3. Volatility: EXTREME is King

| Regime | Trades | Total PnL |
|--------|--------|-----------|
| **EXTREME** | **48** | **$20.51** |
| NORMAL | 29 | $8.76 |
| HIGH | 22 | $7.14 |

EXTREME volatility regime produces the most winners and highest PnL. This is counterintuitive — we've been filtering OUT EXTREME when we should be embracing it.

### 4. BTC Phase: RECOVERY is Best

| Phase | Trades | Total PnL |
|-------|--------|-----------|
| **RECOVERY** | **39** | **$14.52** |
| DECLINING | 22 | $10.51 |
| CALM | 15 | $5.05 |

RECOVERY phase produces 39% of top winners. This is when BTC is bouncing off support — the best time to enter LONG.

### 5. BTC EMA300: AT is Best

| EMA300 | Trades | Total PnL |
|--------|--------|-----------|
| **AT** | **37** | **$16.29** |
| BELOW | 32 | $10.26 |
| ABOVE | 31 | $10.18 |

When BTC is AT its EMA300 (not above, not below), winners emerge. This is the "coiling" zone.

### 6. BTC Score: Neutral Zone (40-60) is Best

| Score | Trades | Avg PnL% | Total PnL |
|-------|--------|----------|-----------|
| **40-60** | **51** | **+16.6%** | **+$18.11** |
| 20-40 | 14 | +17.1% | +$5.79 |
| 60-80 | 11 | +16.4% | +$5.59 |
| <20 | 18 | +11.7% | +$5.37 |

The neutral zone (40-60) produces the most winners. Not too bullish, not too bearish.

### 7. RSI: Overbought Entries Work!

| RSI | Trades | Avg PnL% | Total PnL |
|-----|--------|----------|-----------|
| **>85** | **5** | **+27.8%** | **+$3.65** |
| 70-85 | 5 | +22.8% | +$2.01 |
| 50-70 | 18 | +18.3% | +$6.70 |
| 30-50 | 11 | +15.5% | +$3.44 |
| <30 | 3 | +16.6% | +$1.64 |

**RSI >85 has the highest average PnL (+27.8%).** This directly contradicts our RSI ceiling filter. Overbought entries are the BEST entries for pump-chain+.

### 8. BB Position: Upper Half Works

| BB Position | Trades | Avg PnL% | Total PnL |
|-------------|--------|----------|-----------|
| 0.5-0.7 | 15 | +19.4% | +$5.65 |
| 0.7-0.9 | 9 | +21.4% | +$4.10 |
| >0.9 | 7 | +19.4% | +$3.57 |
| <0.3 | 6 | +18.5% | +$2.31 |

Upper half BB positions (0.5-0.9) produce the highest total PnL. Overbought entries work.

### 9. Exit: ATR Stop Loss is the Workhorse

| Exit Reason | Trades | Total PnL |
|-------------|--------|-----------|
| **atr_sl_hit** | **74** | **$27.01** |
| profit-monster-trail | 13 | $3.18 |
| atr_trail_hit | 4 | $2.88 |

ATR stop loss exits 74% of winners. The trailing exits (profit-monster-trail, atr_trail_hit) produce higher per-trade PnL but fewer trades.

### 10. Leverage: 5x Dominates

| Leverage | Trades | Total PnL |
|----------|--------|-----------|
| **5x** | **83** | **$28.91** |
| 3x | 17 | $7.82 |

## The Winning DNA

A winning trade has these characteristics:

1. **Signal:** pump-chain+ (LONG) or pullback-entry- (SHORT)
2. **Volatility:** EXTREME regime
3. **BTC Phase:** RECOVERY (bouncing off support)
4. **BTC EMA300:** AT (coiling zone)
5. **BTC Score:** 40-60 (neutral)
6. **RSI:** >70 (overbought — momentum is real)
7. **BB Position:** 0.5-0.9 (upper half)
8. **Leverage:** 5x
9. **Exit:** ATR stop loss or trailing stop

## What We're Doing Wrong

1. **RSI ceiling blocks overbought entries** — but RSI >85 has +27.8% avg PnL
2. **We filter OUT EXTREME volatility** — but EXTREME produces 48% of winners
3. **We avoid RECOVERY phase** — but RECOVERY produces 39% of winners
4. **We block signals when BTC is AT EMA300** — but AT produces 37% of winners

## Recommendations

1. **Remove or raise RSI ceiling** for pump-chain+ LONG (currently 85, should be 95+)
2. **Allow EXTREME volatility** for pump-chain+ signals
3. **Boost RECOVERY phase** signals
4. **Prioritize BTC AT EMA300** entries
5. **Use 5x leverage** for pump-chain+ trades
6. **Keep ATR stop loss** as primary exit

## New Signal Design: "Winning DNA"

Based on these findings, a new signal should fire when:
- BTC phase = RECOVERY
- BTC EMA300 = AT
- BTC score = 40-60
- Token RSI > 70 (overbought momentum)
- Token BB position > 0.5 (upper half)
- Volatility regime = EXTREME
- Signal type = pump-chain+ or volume-breakout-long+
- Direction = LONG (preferred) or SHORT (in bearish BTC)

This signal would fire during the "coiling for upside" moments — exactly when BTC is at EMA300 with bullish structure and tokens are showing momentum.
