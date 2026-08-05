# SHORT Signal Performance — 2026-05-11 Analysis

**Source**: `/var/www/hermes/data/trades.json` (36 closed SHORT trades)

## Overall SHORT Performance

| Metric | Value |
|--------|-------|
| Total SHORT trades | 36 |
| Winners | 8 |
| Win Rate | **22%** |
| Avg PnL% | -0.17% |
| Total PnL | -$6.17 |

**Note**: Much worse than the plan's claimed 48.9% WR. Something has degraded significantly.

## SHORT Signal Breakdown

All 36 shorts are `hzscore+` combos (with RS co-signals):

| Signal | N | Win% | Avg% | Notes |
|--------|---|------|------|-------|
| `hzscore+,rs-r56` (IP) | 1 | 100% | +2.30% | Best SHORT |
| `hzscore+,rs-r842` (SKY) | 1 | 100% | +1.77% | profit-monster exit |
| `hzscore+,rs-r24` (ATOM) | 1 | 100% | +0.99% | |
| `hzscore+,rs-r2116` (GRIFFAIN) | 1 | 100% | +0.49% | |
| `hzscore+,rs-r2524` (ZK) | 1 | 100% | +0.33% | |
| `hzscore+,rs-r40` (S) | 1 | 100% | +0.27% | |
| `hzscore+,rs-r1372` (TRB) | 1 | 100% | +0.18% | |
| `hzscore+,rs-r208,rs-r2431` (UMA) | 1 | 100% | +0.02% | |
| `hzscore+,rs-r8` | 2 | 0% | -0.31% | |
| `hzscore+,rs-r24` | 3 | 33% | -0.04% | rs-r24 fires on XRP, CAKE, ANIME — all losses |

## rs-r Value Analysis (hzscore+ SHORT)

| Metric | Wins (n=8) | Losses (n=24) |
|--------|------------|----------------|
| Avg rs-r | 898 | 1957 |
| Min | 24 | 8 |
| Max | 2524 | 15958 |

**Key finding**: rs-r value has NO predictive power. rs-r 24 produced both a winner (ATOM +0.99%) and multiple losses (CAKE -0.79%, ANIME -0.33%, XRP -0.04%).

## Close Reason Breakdown

| Close Reason | N | WinRate | Avg% |
|-------------|---|---------|------|
| atr_sl_hit | 32 | 18.8% | -0.18% |
| regime_bull_flip | 3 | 33.3% | +0.02% |
| profit-monster | 1 | 100% | +1.77% |

**89% of shorts close via `atr_sl_hit`** — the stop loss is being hit before the trade has room to breathe. The entries are firing but the ATR stop is too tight relative to actual short-term volatility.

## vel-hermes- / pct-hermes- Shorts

Only 2 vel-hermes- trades (both losses), 2 pct-hermes- trades (both losses). These signals barely fire for shorts.

## What Changed vs Historical

The plan (`win-rate-short-long-asymmetry.md`) showed SHORTs at 48.9% WR historically. Current data shows 22% WR. Possible causes:
1. Market regime shifted (strong bullish continuation in May 2026)
2. ATR SL params tightened
3. Signal frequency changed — hzscore+ dominated over other SHORT signals

## Key Action Items

1. **`regime_bull_flip` disabled** — was causing premature exits on shorts that were correctly positioned
2. Investigate why 89% of shorts hit ATR SL — either SL too tight or entries firing at wrong time
3. hzscore+ with rs-r > 2000 has worst performance — high rs-r = ancient levels, price has moved past them
