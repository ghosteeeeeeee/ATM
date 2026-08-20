# Signal Performance Report
**Generated:** 2026-08-20 08:00 UTC | **Period:** 48h + 7d

## 48h Performance (2+ trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| return_exhaustion_long | LONG | 2 | 0.0% | -$0.21 |
| stop_hunt_reversal_long+ | LONG | 6 | 50.0% | -$0.10 |
| spike_exhaustion_short- | SHORT | 2 | 50.0% | -$0.06 |
| bb_bounce+,hl_copy_trader | LONG | 2 | 50.0% | +$0.02 |
| r2-trend-long3 | LONG | 7 | 71.4% | +$0.06 |
| r2-trend-long4 | LONG | 6 | 66.7% | +$0.06 |
| r2-trend-long6 | LONG | 2 | 100.0% | +$0.23 |

## 7d Performance (3+ trades, sorted by PnL)
| Signal | Dir | Trades | WR | PnL | Avg PnL |
|--------|-----|--------|-----|-----|---------|
| range_breakout_short | SHORT | 12 | 25.0% | -$0.54 | -$0.045 |
| wave_catcher+ | LONG | 8 | 37.5% | -$0.42 | -$0.053 |
| ct-hot+ | LONG | 33 | 42.4% | -$0.42 | -$0.013 |
| continuation-,hzscore- | SHORT | 3 | 33.3% | -$0.23 | -$0.077 |
| ct-hot- | SHORT | 4 | 0.0% | -$0.19 | -$0.048 |
| hzscore- | SHORT | 19 | 57.9% | -$0.18 | -$0.010 |
| continuation+ | LONG | 5 | 40.0% | -$0.17 | -$0.034 |
| **mover+** | **LONG** | **7** | **28.6%** | **-$0.15** | **-$0.021** |
| range_finder+ | LONG | 9 | 33.3% | -$0.14 | -$0.016 |
| r2-trend-long3 | LONG | 29 | 58.6% | -$0.05 | -$0.002 |
| stop_hunt_reversal_long+ | LONG | 10 | 60.0% | -$0.04 | -$0.004 |
| r2-trend-long1 | LONG | 7 | 57.1% | -$0.02 | -$0.003 |
| bb_bounce+ | LONG | 6 | 50.0% | +$0.01 | +$0.002 |
| r2-trend-long4 | LONG | 15 | 60.0% | +$0.06 | +$0.004 |
| r2-trend-long0 | LONG | 3 | 66.7% | +$0.07 | +$0.023 |
| r2-trend-long5 | LONG | 6 | 66.7% | +$0.08 | +$0.013 |
| return_exhaustion_long | LONG | 9 | 55.6% | +$0.11 | +$0.012 |
| wave_catcher+ | SHORT | 7 | 42.9% | +$0.15 | +$0.021 |
| r2-trend-long2 | LONG | 17 | 64.7% | +$0.19 | +$0.011 |
| bb_bounce+,hl_copy_trader | LONG | 7 | 57.1% | +$0.30 | +$0.043 |
| r2-trend-long6 | LONG | 6 | 100.0% | +$0.43 | +$0.072 |

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| mover+ (MOMENTUM_LEADERBOARD) | LONG | 28.6% | -$0.15 | 7 | Disabled master + SHORT. Added to NEVER_REENABLE_FLAGS. |

## PREVIOUSLY KILLED (confirmed dead, no action needed)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| range_breakout_short | SHORT | 25.0% | -$0.54 | 12 | Already disabled |
| wave_catcher+ | LONG | 37.5% | -$0.42 | 8 | Already disabled |
| ct-hot+ | LONG | 42.4% | -$0.42 | 33 | Already disabled |
| hzscore- | SHORT | 57.9% | -$0.18 | 19 | Already disabled |
| range_finder+ | LONG | 33.3% | -$0.14 | 9 | Already disabled |
| continuation+ | LONG | 40.0% | -$0.17 | 5 | Already disabled |

## BOOSTED (candidates — data supports, no code change needed)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long6 | LONG | 100.0% | +$0.43 | 6 | Already enabled, strong edge |
| r2-trend-long2 | LONG | 64.7% | +$0.19 | 17 | Already enabled, consistent |
| bb_bounce+,hl_copy_trader | LONG | 57.1% | +$0.30 | 7 | Already enabled, solid |
| r2-trend-long5 | LONG | 66.7% | +$0.08 | 6 | Already enabled |

## WATCH LIST (marginal — monitor next cycle)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long3 | LONG | 58.6% | -$0.05 | 29 | High volume, near breakeven. Watch. |
| stop_hunt_reversal_long+ | LONG | 60.0% | -$0.04 | 10 | Good WR, small loss. Watch. |
| bb_bounce+ | LONG | 50.0% | +$0.01 | 6 | Breakeven. Watch. |

## ISSUES
- **No signal inversions** detected in 7d.
- **No trades in last 48h on most signals** — market may be in consolidation or signal pipeline not firing. Check regime scanner and signal compactor health.
- **Null signal trades** (7 trades, 28.6% WR, -$0.07) — trades with no signal label. Investigate source.
