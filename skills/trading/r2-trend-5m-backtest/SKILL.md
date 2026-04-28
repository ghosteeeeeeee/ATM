---
name: r2-trend-5m-backtest
description: Empirical R² regression SHORT signal backtest findings on 5m candles — parameter discovery, what worked, what failed, and how 5m differs from 1m.
tags: [backtest, r2-trend, 5m, signal-discovery, trading]
category: trading
author: Hermes Agent
created: 2026-04-21
---

# R² Trend Signal — 5m Backtest Findings (2026-04-21)

## What Was Tested

Sweep across lookbacks [8, 12, 16, 24, 32, 48, 64, 96] and R² thresholds [0.40–0.80] on 157 tokens with ~1390 5m candles each. Exit-on-reverse-cross.

## Key Findings

### LONG on 5m — Catastrophic (all params negative, ~0% WR)
Same as 1m. Every LONG variant had deeply negative net P&L across all lookbacks and R² thresholds. **Do not build a LONG version.**

### SHORT on 5m — Profitable (all lookbacks positive at low R²)
Best performing combos:

| Lookback | R² | Trades | WR | Net% | Avg%/trade |
|---------|-----|--------|-----|------|-----------|
| 64 | 0.40 | 3626 | 25.7% | **+430%** | +0.119% |
| 8 | 0.40 | 12721 | 32.6% | +255% | +0.020% |
| 64 | 0.50 | 3114 | 24.5% | +221% | +0.071% |
| 64 | 0.55 | 2858 | 24.1% | +124% | +0.043% |

Sweet spot: **LB=64, R²=0.40** — highest net, reasonable signal volume, highest avg/trade.

## Why LB=64/R2=0.40 on 5m (vs LB=16/R2=0.60 on 1m)

- 5m candles aggregate price action — a 64-bar window covers ~5.3 hours, enough to confirm real downtrends rather than noise
- Lower R² threshold (0.40) compensates because 5m trends are inherently more correlated than 1m noise
- LB=8 is too short on 5m — too many false reversals despite high WR (32.6%)
- LB=16 and higher R² thresholds reduce signals too aggressively on 5m

## Known Dataset Limitations

- Only ~1390 5m candles per token (~4.8 days) — from backfill on 2026-04-21
- This is a SHORT dataset period (bear/range market), same as original 1m findings
- Results are timeframe AND dataset-period dependent

## Signal Spec

- Source: `r2s-5m-short{N}` (N = bars since initial signal)
- Timeframe: 5m (from `candles_5m` table)
- Direction: SHORT only
- Entry: OLS slope < 0, R² >= 0.40, price < regression intercept
- Exit: price crosses above regression line (reverse cross)
- Confidence: base 65 + R² bonus + recency bonus, cap ~88
- Cooldown: 15 min

## Files

- `/root/.hermes/scripts/backtest_r2_trend.py` — single-token detailed backtest
- `/root/.hermes/scripts/sweep_r2_5m.py` — full parameter sweep
- `/root/.hermes/scripts/r2_trend_signals.py` — existing 1m version (LB=16, R2=0.60)
- `/root/.hermes/scripts/r2_trend_5m.py` — 5m version to build (use LB=64, R2=0.40)
