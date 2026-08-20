# Signal Performance Report
**Generated:** 2026-08-20 11:15 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **24h trades:** 28 | **WR:** 60.7% | **PnL:** +$0.23
- **7d trades:** 268 | **WR:** 53.0% | **PnL:** -$1.70
- **Active signals (7d):** 64 distinct types

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | All known losers already disabled |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long6 | LONG | 100.0% | +$0.49 | 7 (7d) | Top performer, carrying system |
| bb_bounce+,hl_copy_trader | LONG | 57.1% | +$0.30 | 7 (7d) | Combo winner |
| return_exhaustion_long | LONG | 66.7% | +$0.21 | 9 (7d) | Consistent edge |
| r2-trend-long4 | LONG | 60.0% | +$0.12 | 15 (7d) | Volume + consistency |
| r2-trend-long2 | LONG | 58.8% | +$0.12 | 17 (7d) | Volume + consistency |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long3 | LONG | 53.3% | -$0.13 | 30 (7d) | Neutral R:R, not bleeding hard |
| r2-trend-short2 | SHORT | 33.3% | -$0.21 | 3 (24h) | Below kill threshold (needs 5+) |
| stop_hunt_reversal_long+ | LONG | 50.0% | -$0.007 | 6 (24h) | Breakeven, watch |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long6 | LONG | 100.0% | +$0.49 | 7 (7d) | Dominant |
| bb_bounce+,hl_copy_trader | LONG | 57.1% | +$0.30 | 7 (7d) | Strong combo |
| return_exhaustion_long | LONG | 66.7% | +$0.21 | 9 (7d) | Reliable |
| r2-trend-long4 | LONG | 60.0% | +$0.12 | 15 (7d) | Workhorse |
| r2-trend-long2 | LONG | 58.8% | +$0.12 | 17 (7d) | Workhorse |
| r2-trend-long0 | LONG | 100.0% | +$0.09 | 3 (7d) | Small sample, perfect |

## ISSUES
- **No direction inversions detected** — signal-to-direction alignment is clean
- **7d system PnL is -$1.70** — dragged by now-killed losers (ct-hot, range_breakout, mover+, wave_catcher+, continuation+, range_finder+). All disabled.
- **SHORT signals underperforming** — most SHORT variants killed. Only r2-trend-short2 still active with 3 trades below kill threshold. Consider monitoring.
- **Low 24h volume (28 trades)** — expected, system filtering well after mass kills.

## Previously Killed (confirmed disabled)
ct-hot+, ct-hot-, range_breakout_short, range_breakout+, mover+, wave_catcher+, wave_catcher-, wave_catcher+, continuation+, range_finder+, hzscore-, r2_trend_short — all set to False in hermes_constants.py.
