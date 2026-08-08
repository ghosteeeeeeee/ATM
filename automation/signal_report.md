# Signal Performance Report
**Period:** 2026-08-08 01:45 UTC | 7d lookback

## Overall
- **7d:** 341 trades | 43.1% WR | -$1.40 PnL
- **24h:** 56 trades | ~48% WR | +$0.24 PnL

## KILLED (executed this run)
None — all known losers already disabled.

## BOOSTED (executed this run)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+,range_finder+ | LONG | 71.4% | +$0.12 | 7 | Added 1.2x confidence |

## EXISTING SUPPRESSIONS (already in signal_compactor.py)
| Signal | Dir | WR | PnL | Trades | Suppression |
|--------|-----|-----|-----|--------|-------------|
| ma100-cross,return_exhaustion- | SHORT | 42.9% | -$0.28 | 7 | 0.5x |
| zscore-rising- | SHORT | 31.6% | -$0.22 | 38 | 0.5x |
| return_exhaustion- | SHORT | 60.0% | -$0.12 | 5 | 0.7x |
| hzscore-,return_exhaustion- | SHORT | 50.0% | -$0.18 | 10 | 0.6x + COSIG-GATE block |

## EXISTING BOOSTS (already in signal_compactor.py)
| Signal | Dir | WR | PnL | Trades | Boost |
|--------|-----|-----|-----|--------|-------|
| bb_bounce,hzscore+ | LONG | 100% | +$0.20 | 5 | 1.3x |
| hzscore+,return_exhaustion_long | LONG | 58.3% | +$0.13 | 12 | 1.2x |
| ma100-cross,return_exhaustion_long | LONG | 66.7% | +$0.12 | 6 | 1.15x |
| ma100-cross,vortex_break_long | LONG | 62.5% | +$0.08 | 8 | 1.1x |

## WATCH LIST (borderline, monitor next cycle)
| Signal | Dir | WR | PnL | Trades | Notes |
|--------|-----|-----|-----|--------|-------|
| vel-hermes- | SHORT | 34.6% | -$0.06 | 52 | High volume, tiny avg loss (-$0.001) |
| bb_bounce,ma100-cross | LONG | 42.9% | -$0.10 | 7 | COSIG-GATE already blocking |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce | LONG | 57.1% | +$0.24 | 14 | Active |
| bb_bounce,hzscore+ | LONG | 100% | +$0.20 | 5 | Active, boosted |
| bb_bounce+,range_finder+ | LONG | 71.4% | +$0.12 | 7 | Active, boosted |
| hzscore+,return_exhaustion_long | LONG | 58.3% | +$0.13 | 12 | Active, boosted |
| ma100-cross,return_exhaustion_long | LONG | 66.7% | +$0.12 | 6 | Active, boosted |
| bb_bounce | SHORT | 46.2% | +$0.09 | 13 | Active |
| ma100-cross,vortex_break_long | LONG | 62.5% | +$0.08 | 8 | Active, boosted |

## ISSUES
- No signal inversions detected.
- Long-bias signals significantly outperform shorts in current regime.
- return_exhaustion- SHORT combos consistently lose despite decent win rates (small avg losses add up).
- `accel-300-,rs-s-broken` SHORT (lifetime top performer: 1025T, +$6.22) hasn't traded since Jul 21 — may be dormant.
