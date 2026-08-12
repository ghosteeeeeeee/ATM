# Signal Performance Report
Generated: 2026-08-12 15:00 UTC

## 6h Performance (2+ trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| hzscore- | SHORT | 2 | 50.0% | -$0.06 |
| trend_momentum_near_sma+ | LONG | 2 | 0.0% | -$0.05 |
| hzscore+ | LONG | 3 | 33.3% | +$0.03 |
| bb_bounce+ | LONG | 14 | 57.1% | +$0.10 |

## 24h Performance (3+ trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| trend_momentum_near_sma+ | LONG | 5 | 0.0% | -$0.40 |
| hzscore- | SHORT | 4 | 50.0% | -$0.05 |
| bb_bounce+,hzscore+ | LONG | 4 | 50.0% | -$0.01 |
| hzscore+ | LONG | 8 | 50.0% | +$0.02 |
| bb_bounce+ | LONG | 14 | 57.1% | +$0.10 |

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| trend_momentum_near_sma+ | LONG | 0.0% | -$0.40 | 5 | Base already killed 2026-08-12 13:05 UTC. PLUS/MINUS flags now False. |

## BOOSTED (executed): None
No signals met all boost criteria (WR>55%, 5+ trades, PnL>$0.05, consistent across tokens). bb_bounce+ is the closest (57.1% WR, +$0.10) but below trade threshold for boost.

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hzscore- | SHORT | 50.0% | -$0.05 | 4 | Marginal — below kill threshold |
| bb_bounce+,hzscore+ | LONG | 50.0% | -$0.01 | 4 | Breakeven — monitoring |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 57.1% | +$0.10 | 14 | Steady performer |

## Signal Inversions: None found

## Issues
- **trend_momentum_near_sma**: Base flag killed earlier today but PLUS/MINUS flags were still True. Fixed — all three flags now False.
- **Stale open position**: 1 open trend_momentum_near_sma+ LONG from Aug 11 22:14 UTC — may need manual close.

## Full History (all-time winners)
| Signal | Trades | WR | PnL |
|--------|--------|-----|-----|
| accel-300-,rs-s-broken | 1025 | 46.2% | +$6.22 |
| bb_bounce+,range_finder+ | 53 | 58.5% | +$0.71 |
| tl_break_long | 94 | 37.2% | +$0.58 |
| bb_bounce+,hzscore+ | 33 | 48.5% | +$0.20 |
| bb_bounce | 27 | 51.9% | +$0.33 |
| hzscore+,mover+ | 5 | 80.0% | +$0.17 |
| inv-accel-300+,tl_break_long | 8 | 12.5% | +$0.13 |
