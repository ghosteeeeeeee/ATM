=== Signal Performance Report ===
Period: 2026-09-12 05:00 UTC | 6h + 24h

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 16.7% | -$0.38 | 6 | Already killed 2026-09-11 15:10 |

No new kills this cycle. bb-bounce-v2-long+ (25% WR, -$0.47) has only 4 trades — below 5+ threshold for blanket kill. Will monitor next cycle.

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|

No boosts this cycle. mover+ (83.3% WR) and mover- (100% WR) already performing well — no tuning needed.

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 25.0% | -$0.47 | 4 | WATCH — below kill threshold, 2+ days active |
| accel-300-v4-short- | SHORT | 0.0% | -$0.27 | 2 | LOW VOLUME — too few trades to act |
| ema300-dip-long | LONG | 0.0% | -$0.25 | 1 | LOW VOLUME |
| pump-chain- | SHORT | 62.5% | -$0.17 | 16 | R:R ISSUE — good WR, bad risk/reward |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| mover- | SHORT | 100.0% | +$0.46 | 3 | EXCELLENT |
| mover+ | LONG | 83.3% | +$0.15 | 6 | STRONG |
| open-skies+ | LONG | 66.7% | +$0.16 | 3 | GOOD |
| pullback-entry- | SHORT | 60.0% | +$0.07 | 5 | GOOD |
| trend_purity+ | LONG | 75.0% | +$0.02 | 4 | GOOD |
| rr-struct+ | LONG | 100.0% | +$0.09 | 2 | EXCELLENT (low vol) |

## ISSUES
- No signal inversions detected
- pump-chain- SHORT: 62.5% WR but -$0.17 PnL — winning trades are small, losing trades are large. Needs R:R tuning or SL adjustment. Historical regime data shows all regimes profitable — recent 24h underperformance may be temporary.
- bb-bounce-v2-long+ has been active 2+ days with 25% WR. If next cycle shows 5+ trades, will kill.

## 6h Performance (for reference)
| Signal | Dir | WR | PnL | Trades |
|--------|-----|-----|-----|--------|
| trend_purity+ | LONG | 75.0% | +$0.02 | 4 |
| rr-struct+ | LONG | 100.0% | +$0.09 | 2 |

## Summary
No actions taken. All kill candidates either already killed (pump-chain+) or below threshold (bb-bounce-v2-long+ at 4 trades). System performing well — 59 closed trades in 24h, 5 signals with >55% WR and positive PnL.
