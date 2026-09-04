=== Signal Performance Report ===
Period: 2026-09-04 11:08 UTC | 6h + 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| ema300-dip | LONG | 58.8% (24h), 25% (6h) | -$1.13 | 34 | DISABLED — losses 2.7x wins, deteriorating |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 64.3% | $0.14 | 14 | Watch — healthy edge |
| continuation+ | LONG | 100% | $0.30 | 4 | Watch — too few trades to boost |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| accel-300-v3-long+ | LONG | 40.0% | -$0.47 | 5 | Already killed (2026-09-04) |
| accel-300-v3-short- | SHORT | 25.0% | -$0.26 | 4 | Already killed (2026-09-04) |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 64.3% | $0.14 | 14 | Active — 64.3% WR, $0.07 avg win |
| continuation+ | LONG | 100% | $0.30 | 4 | Active — clean, few trades |

ISSUES:
- ema300-dip structural problem: avg loss ($0.15) = 2.7x avg win ($0.05). 58.8% WR can't overcome this.
- 6h ema300-dip: 25% WR, -$1.14 — signal is deteriorating in current market.
- ATR_SL exits dominate losses (8/15 losses). Stop at 1.5% SL_PCT is too tight for current vol.
- No signal inversions detected.
- Total system 24h: 69 trades, 55.1% WR, -$2.03. ema300-dip was the drag.

PREVIOUSLY KILLED (confirmed):
- ACCEL_300_V3_LONG_ENABLED = False (CEO 2026-09-04)
- ACCEL_300_V3_SHORT_ENABLED = False (AUTO_1HR 2026-09-04)
- SLOW_GRIND_SHORT_ENABLED = False (CEO 2026-09-04)
