# 30-Day Trade Analysis — 2026-06-04

## Overall Performance (Last 30 Days)

| Direction | Total | Wins | Losses | WR | Total PnL | Avg PnL% |
|-----------|-------|------|--------|-------|-----------|----------|
| LONG | 533 | 158 | 375 | 29.6% | +$72.38 | -3.48% |
| SHORT | 398 | 168 | 230 | 42.2% | +$131.82 | +6.65% |

System is net profitable on both sides. SHORT is structurally stronger.

## Close Reason Breakdown

| Direction | Reason | N | Avg PnL% | Total PnL |
|-----------|--------|---|----------|-----------|
| LONG | profit-monster | 99 | +2.69 | +$133.21 |
| LONG | atr_sl_hit | 388 | -0.31 | -$59.65 |
| SHORT | profit-monster | 116 | +2.67 | +$154.66 |
| SHORT | atr_sl_hit | 232 | -0.23 | -$26.70 |

**Interpretation**: ATR SL cuts losers fast (small damage). Profit-monster captures winners.
The system exit logic is correct — entries are the problem.

## Signal Family Performance

| Signal | N | WR | Avg PnL% | Total PnL |
|--------|---|---|----------|-----------|
| accel-300+ alone | 30 | 30% | +0.26% | +$3.81 |
| accel-300+,trend_purity+ | 4 | **75%** | **+0.79%** | +$1.57 |
| accel-300+,ema9-sma20+,trend_purity+ | 3 | **67%** | **+1.73%** | +$2.60 |
| accel-300+,hhh-long6 | 17 | 17.6% | -0.10% | -$0.87 |
| accel-300+,hhh-long4 | 8 | 12.5% | -0.04% | -$0.17 |
| accel-300+,hhh-long5 | 7 | 14.3% | +0.11% | +$0.37 |

## Top RS Co-Signal Combinations (accel-300+, n≥3)

| Signal | N | WR | Avg PnL% | Total PnL |
|--------|---|---|----------|-----------|
| accel-300+,rs-s87 | 4 | 50% | +2.24 | +$4.48 |
| accel-300+,rs-s28 | 5 | 60% | +1.14 | +$2.84 |
| accel-300+,rs-s60 | 5 | 60% | +1.02 | +$2.55 |
| accel-300+,rs-s24 | 3 | 33% | +1.10 | +$1.64 |
| accel-300+,rs-s36 | 9 | 44% | +0.19 | +$0.85 |
| accel-300+,rs-s42 | 7 | 29% | +0.25 | +$0.89 |

## hhh Signal Family — All Negative

| Signal | Direction | N | WR | Avg PnL% |
|--------|-----------|---|---|----------|
| accel-300+,hhh-long6 | LONG | 17 | 17.6% | -0.10% |
| accel-300+,hhh-long4 | LONG | 8 | 12.5% | -0.04% |
| accel-300+,hhh-long5 | LONG | 7 | 14.3% | +0.11% |
| accel-300+,hhh-long5,hhh-long6 | LONG | 2 | 0% | -0.43% |

## zscore_pump (with RS co-signal)

Overall (all RS+zscore combos): +$33.95 LONG, +$55.52 SHORT in 30 days.
Pure zscore-pump alone: mixed, no clear edge.

## Duration by Outcome

| Direction | Outcome | N | Avg Duration (min) |
|-----------|---------|---|-------------------|
| SHORT | WIN | 168 | 87.8 |
| SHORT | LOSS | 230 | 35.1 |
| LONG | WIN | 158 | 57.0 |
| LONG | LOSS | 375 | 35.6 |

## Key Constants Tightening Targets (constants-only, no code change)

1. **trend_purity+ weight** — raise in signal_compactor scoring (75% WR vs 30% base)
2. **hhh-long weight = 0** — block for LONG (systematically -100% edge)
3. **ACCEL_300_MIN_CONF** — raise to 85 when trend_purity absent
4. **RS_MIN_TOUCHES_LONG = 60** — filter weaker support levels
5. **RS_MIN_TOUCHES_SHORT = 50** — filter weaker resistance levels
6. **ZSCORE_PUMP threshold** — block solo zscore-pump entries (require RS or accel co-signal)
