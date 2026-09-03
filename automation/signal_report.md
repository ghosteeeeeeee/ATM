=== Signal Performance Report ===
Period: 2026-09-03 05:00 UTC | Last 6h + 24h

KILLED (executed this run):
None — no signals met kill threshold (WR<30% with 5+ trades, 24h).
bb-bounce-short SHORT: 50% WR, -$0.27 but only 4T — watch.
r2-trend-long3 LONG: 33.3% WR, -$0.23 but only 3T — already killed (R2_TREND_LONG_ENABLED=False).

BOOSTED (executed this run):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 85% | +$0.74 | 20 | Conf weight 1.0 → 1.3 |
| ema300-dip | LONG | 70% | +$0.29 | 20 | Conf weight 1.0 → 1.2 |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-short | SHORT | 50% | -$0.27 | 4 | Watch — below kill threshold |
| r2-trend-long3 | LONG | 33% | -$0.23 | 3 | Already killed |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 85% | +$0.74 | 20 | Boosted to 1.3 |
| ema300-dip | LONG | 70% | +$0.29 | 20 | Boosted to 1.2 |
| accel-300-v3-long+ | LONG | 54% | $0.00 | 13 | Neutral — breakeven |
| bb-bounce-short | SHORT | 50% | -$0.27 | 4 | Watchlist |

ISSUES:
- None. No signal inversions detected. No critical bugs.
- accel-300-v3-long+ is at exactly breakeven over 24h — monitoring but not acted on (too close to threshold).
- bb-bounce-v2-long+ was at 100% WR in 6h (7T) — exceptional. Watch for regression to mean.
