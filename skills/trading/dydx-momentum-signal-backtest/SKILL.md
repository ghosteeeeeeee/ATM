---
name: dydx-momentum-signal-backtest
description: Backtest methodology and empirical results for DYDX 1m momentum signals (SHORT direction). 14 months of data, Z-score + volume + ROC + MACD composite signals.
---

# DYDX Momentum Signal Backtest — Methodology & Findings

## What This Is
Backtest methodology and empirical results for DYDX 1m momentum signals (SHORT direction).
14 months of 1m candle data (Mar 2025 – Apr 2026, 6,126 candles).

## Data Source
```python
conn = sqlite3.connect('/root/.hermes/data/candles.db')
rows = cur.execute("""
    SELECT ts, open, high, low, close, volume 
    FROM candles_1m WHERE token='DYDX' ORDER BY ts ASC
""").fetchall()
```

## Indicators Used
- **Z-Score(20)**: price vs 20-bar rolling mean / std dev
- **Vol Ratio(20)**: current volume / 20-bar avg volume
- **ROC(3)**: 3-bar rate of change (%)
- **MACD Hist(12,26,9)**: EMA12-EMA26 signal line histogram
- **BB Position**: (price – BB_lower) / (BB_upper – BB_lower)
- **ATR(14)**: 14-bar average true range

## Signal Definitions Tested
```python
def ss_z2(i):     return zscore[i] < -2.0                              # Z only
def ss_zv(i):     return zscore[i] < -2.0 and vol_ratio[i] > 2.5      # Z + volume
def ss_zvr(i):    return zscore[i] < -2.0 and vol_ratio[i] > 2.5 and roc3[i] < -0.2
def ss_full(i):   return zscore[i] < -2.0 and vol_ratio[i] > 2.5 and roc3[i] < -0.2 and macd_hist[i] < 0 and bb_pos[i] < 0.2
def sl_z2(i):     return zscore[i] > 2.0                              # Z only (LONG)
def sl_zv(i):     return zscore[i] > 2.0 and vol_ratio[i] > 2.5      # Z + volume (LONG)
```

## Exit Rules
- **Entry**: close of signal candle
- **SL**: entry ± sl_mult × ATR
- **TP**: entry ± tp_mult × ATR
- **First candle against**: exit immediately if first close is adverse
- **Max hold**: N bars

## Key Findings: DYDX SHORT Signals

| Signal | N | WR% | AvgPnL% | Total% | Best Params |
|--------|---|-----|---------|--------|-------------|
| Z<-2.0 | 161 | 71% | +0.008% | +1.3% | — |
| Z<-2.0 + VR>2.5x | 57 | 74% | +0.046% | +2.6% | — |
| Z<-2.0 + VR>3.0x | 44 | 75% | +0.040% | +1.8% | — |
| FULL 5-cond SHORT | 53 | 75% | +0.060% | +3.2% | — |

### Best Config (param sweep)
```
Hold=8 bars, SL=1.5x ATR, TP=1.0x ATR
→ n=58, WR=69%, AvgPnL=+0.127%, Total=+7.4%, R:R=1.27x
```
- With 10x leverage: ~1.27% per trade gross
- ~57 trades over 14 months

## Key Findings: DYDX LONG Signals

**LONGS DON'T WORK on DYDX in this period.**

- Z>+2.0: WR only 31%, avg +0.030% but R:R = 2.68x (winners big, losers small)
- Every param combination tested was breakeven or losing
- Reason: DYDX bear market (0.72→0.13 over 14 months) — every "extended up" was a dead cat bounce
- WR 16-34% means first-candle reversal kills most longs

## Why "First Candle Against" Rule Hurts SHORTS Less
- SHORTS have 66-79% WR — most shorts continue in the intended direction
- FIRST_OUT exits are ~30-40% of shorts, but avg loss is small (~0.5%)
- The rule saves you from the big reversals that DO happen

## Critical Notes for DYDX
- Token has extremely low absolute price ($0.13-0.14 range during analysis)
- ATR(14) ≈ 0.00025 = 0.18% of price — very tight
- Moves are fast and sharp (crashes happen in 1-3 candles)
- Volume spikes frequently (11.6x avg seen in 1m data)
- The liquidiy grab pattern (wick sweep → reversal) is COMMON

## Reusable Backtest Snippet
```python
def backtest_signal(ss_fn, sl_fn, closes, highs, lows, atr, hold=10, sl_m=1.0, tp_m=2.0):
    """Minimal backtest engine for 1m candle data."""
    n = len(closes)
    shorts, longs = [], []
    i = 50
    while i < n - hold - 2:
        ss_fires = ss_fn(i) if ss_fn else False
        sl_fires = sl_fn(i) if sl_fn else False
        if ss_fires and not sl_fires:
            direction='SHORT'; sl_px=closes[i]+sl_m*atr[i]; tp_px=closes[i]-tp_m*atr[i]
        elif sl_fires and not ss_fires:
            direction='LONG'; sl_px=closes[i]-sl_m*atr[i]; tp_px=closes[i]+tp_m*atr[i]
        else:
            i += 1; continue
        # ... find exit, record pnl
```

## When to Update This
- If DYDX enters a bull market, retest LONG signals
- If token's price range changes significantly, retest Z-score thresholds
- After a governance event or major news, patterns may shift
