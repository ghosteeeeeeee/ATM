=== Signal Performance Report ===
Date: 2026-08-18 | Period: Last 6h / 24h / 7d

## KILLED (executed this cycle)
None — all obvious losers already killed in prior cycles.

## BOOSTED (executed this cycle)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| return_exhaustion_long | LONG | 71.4% | +$0.32 | 7 (7d) | Top performer — no action needed, already enabled |

## LOSERS (watch list)
| Signal | Dir | WR | PnL (24h) | Trades | Status |
|--------|-----|-----|-----------|--------|--------|
| r2-trend-long3 | LONG | 33.3% | -$0.15 | 6 | Borderline — can't disable individually (R2_TREND_LONG_ENABLED master switch). Monitor. |
| return_exhaustion_long | LONG | 33.3% | -$0.11 | 3 | Bad 24h but 71.4% WR over 7d. Too few trades to judge. |

## WINNERS
| Signal | Dir | WR | PnL (7d) | Trades | Status |
|--------|-----|-----|----------|--------|--------|
| return_exhaustion_long | LONG | 71.4% | +$0.32 | 7 | Strong |
| r2-trend-long2 | LONG | 64.7% | +$0.19 | 17 | Strong |
| bb_bounce+ | LONG | 58.3% | +$0.21 | 24 | Strong |
| bb_bounce+,hl_copy_trader | LONG | 50.0% | +$0.26 | 6 | Good |
| r2-trend-long4 | LONG | 55.6% | $0.00 | 9 | Break-even |

## ISSUES
- No signal inversions detected
- r2-trend-long3 is the worst enabled performer (22T, 54.5% WR, -$0.11 7d) but cannot be individually disabled
- 24h overall: 28 trades, -$0.13 (slight loss, within normal variance)

## RECENTLY KILLED (for reference)
- range_breakout_short: AUTO_KILLED 2026-08-17 — 0% WR, 3T, -$0.17
- wave_catcher+/wave_catcher-: KILLED 2026-08-17 — 37.5% WR, -$0.42
- range_breakout+: KILLED 2026-08-16 — 25% WR, -$0.41
- ct-hot+/ct-hot-: KILLED 2026-08-16 — 42.4% WR, -$0.42
- continuation+: KILLED 2026-08-16 — 40% WR, -$0.17
- trend_momentum_near_sma+: KILLED 2026-08-12 — 16.7% WR, -$0.37
- hzscore-: NEVER_REENABLE — 54.3% WR but -$0.22 (7d)
- accel-300-: NEVER_REENABLE — 55% WR but -$0.30 (7d)
