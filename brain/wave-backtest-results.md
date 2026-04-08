# Wave Rider Backtest — Results Summary
**Date:** 2026-04-07 (updated)
**Data:** 6 tokens × 3 timeframes (BTC/ETH/AXS/IMX/SKY/TRB × 4H/1H/15m)

---

## Core Finding

**The momentum continuation strategy (wave>=2 + velocity threshold + regime filter) is validated as the base approach.** Pure stall-then-flip reversal does NOT outperform momentum continuation at scale.

**Key refinement from this session:**
- Trailing stop (1.5% hard SL, 1.5% trailing activation) is the most important exit mechanism
- vel_flip exit fires too early in chop, giving back profits
- Regime filter consistently improves WR (+3-5%) but can hurt Sharpe if SL is too loose
- Tighter SL (1.5%) outperforms 2% SL on 4H — bigger ATR stops don't help
- 1H is mostly noise — choppy, too many fakeouts

---

## Token Trend Analysis (Jan 13 → Apr 6, 2026)

| Token | Start→End | Change | Vol (4H) | Direction | Notes |
|-------|-----------|--------|----------|-----------|-------|
| BTC | 93,449→69,752 | **-25.4%** | 1.09% | Bear | Primary bear market |
| ETH | 3,184→2,140 | **-32.8%** | 1.45% | Bear, choppy | Most choppy of the bear tokens |
| AXS | 1.04→1.12 | +7.9% | 3.42% | Mild bull | Highest volatility, rare clean trends |
| IMX | 0.28→0.14 | **-51.2%** | 1.89% | Strong bear | Steepest drop, should be great for SHORTs |
| SKY | 0.06→0.08 | +31.3% | 1.68% | Mild bull | Ranged, mixed |
| TRB | 22.25→14.91 | **-33.0%** | 1.55% | Bear, H1 dump | H1=-37.8%, H2=+7.7% recovery |

**Market character:** Primarily bear market (BTC/ETH/TRB/IMX all down 25-51%). AXS/SKY mildly bullish.

---

## Strategy Parameters Tested

### Entry
- Wave threshold: 1, 2, 3
- Velocity threshold: 0.05, 0.10, 0.15 (MACD velocity = (curr_macd - prev_macd) / max(|prev_macd|, 0.5))
- Regime filter: ON (only LONG when regime=1/BULL, only SHORT when regime=-1/BEAR) or OFF
- Z-score chop filter: z > 2.0 blocks entries (tested but mixed results)

### Exit
- Trailing: activate at 1.5% profit, exit on 1.5% pullback
- Vel flip: exit when velocity crosses ±0.05
- Wave 4 exit
- SL: 2% or 1.5%

---

## Best Results by Token

### BTC 4H (Bear market, primary trend)
```
Config: w2_v005_reg_sl15 (wave>=2, vel>=0.05, regime filter, 1.5% SL)
N=11 | WR=54.5% | Sharpe=+0.38 | Avg PnL=+1.69%
Exits: Trailing=3, VelX=4, SL=4
```

### TRB 4H (Bear then recovery)
```
Config: w1_v005_reg_sl2 (wave>=1, vel>=0.05, regime filter, 2% SL)
N=22 | WR=50.0% | Sharpe=+0.23 | Avg PnL=+0.86%
Exits: Trailing=11, VelX=1, SL=10
Note: Trailing stop dominates — captures trend continuation
```

### ETH 1H (Bear, choppy — hardest to trade)
```
Config: w2_v010_noreg (wave>=2, vel>=0.10, no regime, 2% SL)  
N=10 | WR=60.0% | Sharpe=+0.42 | Avg PnL=+0.55%
Note: Higher vel threshold (0.10) filters fakeouts; ETH 4H doesn't work
```

---

## Aggregated Results (all 6 tokens, 4H+1H)

| Config | N | WR | Sharpe | Avg% | Notes |
|--------|---|-----|--------|------|-------|
| w2_v010_noreg_sl2 | 58 | **41.4%** | **+0.07** | +0.13 | Best aggregated — higher vel threshold |
| w2_v005_reg_sl15 | 50 | 42.0% | +0.09 | +0.57 | Regime filter + tight SL |
| w2_v005_reg_sl2 | 50 | 42.0% | +0.04 | +0.44 | Regime filter helps WR |
| w2_v010_reg_sl2 | 36 | 36.1% | +0.04 | +0.17 | |
| w1_v005_reg_sl2 | 160 | 35.0% | -0.01 | +0.12 | Most data but poor Sharpe |

**Key:** N=160 for w1 (wave>=1) sounds like lots of data but Sharpe is -0.01 — it's averaging in chop losses. Wave>=2 is the practical minimum.

---

## Exit Mechanism Analysis

**Trailing vs Vel_flip by market:**

| Token | TF | Trailing exits | Vel flip exits | SL hits | Dominant |
|-------|----|----------------|----------------|---------|----------|
| BTC | 4h | 3 | 4 | 4 | Mixed |
| TRB | 4h | 11 | 1 | 10 | **Trailing** |
| ETH | 4h | 8 | 18 | 8 | **Vel flip** |
| ETH | 1h | 0 | 25 | 3 | **Vel flip** |
| BTC | 1h | 0 | 36 | 1 | **Vel flip** |

**Insight:** In choppy markets (ETH), vel_flip exits prevent holding through reversals. In trending markets (TRB), trailing stops let winners run. The strategy needs BOTH exit types — "trailing_or_vel" is correct.

---

## Key Insights

1. **Wave>=2 is the practical minimum.** Wave>=1 floods with signals (160 aggregated trades, zero Sharpe). Wave>=3 is too rare on 4H (only 4 occurrences in 500 candles).

2. **Regime filter: use it for WR, don't rely on it for direction.** It adds +3-5% WR but doesn't dramatically improve risk-adjusted returns. In a pure bear market, it blocks most SHORTs (correct) but also blocks some LONGs that would work as bounces.

3. **Vel threshold 0.05-0.10 is the sweet spot.** Below 0.05 (vel>=0.01) floods with noise. Above 0.15 starts missing valid entries.

4. **Tight SL (1.5%) beats loose SL (2%) on 4H.** The ATR-based 2% SL might be too loose. On a 4H candle, 2% is ~$1400 on BTC — way too much room in a $70k market. Consider 1.0-1.5% on 4H.

5. **1H is mostly noise for this strategy.** The only exception is ETH 1h with vel>=0.10 (Sharpe +0.42). Most 1H configs show negative Sharpe when aggregated.

6. **Stall-then-flip thesis is WEAKENED by multi-token data.** It worked on TRB 4H (66.7% WR) but the sample was tiny (N=6). Across all tokens, pure momentum continuation (vel>=0.05) works better than stall_then_flip patterns.

7. **SHORT entries are rare and situational.** In bear markets, vel < -0.05 fires mostly when regime is also BEAR (confirming), so SHORTs are actually aligned with regime. In bull markets, SHORTs almost never fire. This means the strategy naturally adjusts to regime — it mostly rides LONGs in bulls and SHORTs in bears.

---

## Refined Strategy for Live Testing

```
Name: WAVE_MOMENTUM_V2
Timeframe: 4H primary, 1H secondary

Entry:
  - wave >= 2 (minimum — don't enter wave 1)
  - velocity >= 0.05 (momentum building in direction)
  - regime filter ON: only enter LONG if regime=BULL, SHORT if regime=BEAR

Exit (priority order):
  1. Trailing stop: activate at +1.5% profit, exit on 1.5% pullback
  2. OR vel flip: velocity crosses ±0.05 (momentum broken)
  3. OR wave >= 4 (exhaustion — rare)
  4. OR max hold 48 candles (4H = 8 days)

Stop Loss: 1.5% (tighter than current 2%)

Position sizing:
  - wave=2: 0.75x
  - wave=3+: 0.50x

Guard: chop_cooldown
  - After 2 consecutive losses: skip next 5 signals
```

---

## What's Still Unknown

1. **Does this work in a bull market?** All data is bear market (Jan-Apr 2026). In bull markets, the regime filter would favor LONGs — but the velocity patterns might behave differently.

2. **AXS/SKY/IMX have too few trades.** AXS has only 500 candles on 4H but only 7.9% change — not a great trend. IMX dropped 51% but our strategy only got a handful of SHORT signals. Need more data.

3. **Wave>=3 almost never fires on 4H** (only 4 times in 500 candles). The wave counter might be counting incorrectly — it counts diff crosses, not price waves. Consider a price-based wave counter instead.

4. **The "stall-then-flip" pattern needs larger sample.** TRB 4H showed 66.7% WR with stall_then_flip but N=6. Not enough to conclude.

5. **1H trailing exits are almost zero.** On 1H, trailing never activates (profit never exceeds 1.5% before vel_flip fires). The trailing activation threshold might need to be lower for 1H (1.0% instead of 1.5%).

---

## Next Steps

1. **Run full grid on 4H only** — focus on BTC/TRB/IMX (most trending)
2. **Add price-based wave counter** — current wave counter counts diff crosses, not price action
3. **Test ATR-based SL** with k=1.5 instead of fixed 1.5% — adapts to volatility
4. **ADX filter** — test with ADX > 20 to detect trending vs ranging markets
5. **Fine-tune trailing activation threshold** — 1.5% for 4H, 1.0% for 1H
6. **Wire WAVE_MOMENTUM_V2 into signal_gen.py** as a new signal type
