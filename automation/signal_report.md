=== Signal Performance Report ===
Generated: 2026-08-16

## 6h Performance (2+ trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| ct-hot+ | LONG | 9 | 22.2% | -$0.48 |

## 24h Performance (3+ trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| return_exhaustion_long | LONG | 3 | 100.0% | +$0.39 |
| ct-hot+ | LONG | 30 | 46.7% | -$0.29 |
| None | LONG | 4 | 25.0% | -$0.10 |
| ct-hot- | SHORT | 4 | 0.0% | -$0.19 |

## KILLED (executed): None
No signals meet kill criteria (WR <30% with 5+ trades AND PnL <-$0.10 in 24h).

## BOOSTED (executed): None
return_exhaustion_long (100% WR, +$0.39) needs 5+ trades before boost.

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ct-hot+ | LONG | 46.7% | -$0.29 | 30 | KILLED 2026-08-16 (CEO). Re-enable when WR >55% with 20+ trades. |
| ct-hot- | SHORT | 0.0% | -$0.19 | 4 | WATCH — too few trades. |
| continuation+ | LONG | 0.0% | -$0.18 | 2 | KILLED 2026-08-16 per hermes_constants.py. |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| return_exhaustion_long | LONG | 100.0% | +$0.39 | 3 | HOT — needs more volume. All exits via profit-monster. |
| r2-trend-long6 | LONG | 100.0% | +$0.04 | 1 | Low volume. |
| ct-hot+,hl_copy_trader | LONG | 100.0% | +$0.07 | 2 | Low volume. |

## 7d Context (5+ trades, sorted by PnL)
Worst: wave_catcher+ -$0.42, range_breakout+ -$0.41, trend_momentum_near_sma+ -$0.37
Best: bb_bounce+ +$0.25, bb_bounce+,hzscore+ +$0.23, r2-trend-long2 +$0.19

## ISSUES:
- ct-hot+ ATR SL exits: 15/30 trades hit ATR SL = 0% WR avg -$0.07 each. Profit-monster exits: 15/30 = 93% WR. The ATR SL is too tight — consider widening ATR_SL_ATR_MULT or raising ATR_SL_FLOOR.
- No direction inversions found.
- 6h period: ct-hot+ LONG only 22.2% WR — short-term weakness.
