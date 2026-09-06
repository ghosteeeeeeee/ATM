# Signal Performance Report
Generated: 2026-09-06 11:08 UTC

## Summary
- **Total trades (24h):** 36
- **Total trades (7d):** 258
- **Kill candidates:** 0 (no signals meet ALL kill criteria in 24h window)
- **Boost candidates:** 1 (bb-bounce-v2-long+ — 90.9% WR, $1.15 PnL)
- **Signal inversions:** 0
- **Watchlist:** 1 (open-skies+)

## 24h Performance (by signal+direction)

### Winners (WR > 55%, PnL > $0)
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| bb-bounce-v2-long+ | LONG | 11 | 90.9% | $1.15 | ACTIVE (BB_BOUNCE_V2_LONG_ENABLED=True) |
| coil-spring+ | LONG | 15 | 60.0% | $0.04 | ACTIVE |

### Neutral (WR 40-55%)
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| accel-300-v3-long+ | LONG | 2 | 50.0% | -$0.05 | ACTIVE |

### Losers (WR < 40% OR PnL < -$0.10)
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| open-skies+ | LONG | 6 | 33.3% | -$0.28 | WATCHLIST — active <36h, monitoring |
| ema300-dip-short | SHORT | 1 | 0.0% | -$0.15 | KILLED (EMA300_DIP_SHORT_ENABLED=False) |
| r2-trend-short3 | SHORT | 1 | 0.0% | -$0.20 | KILLED (R2_TREND_SHORT3 - not enough data) |

## 6h Performance
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| coil-spring+ | LONG | 7 | 71.4% | $0.07 |

## Boost Candidates
| Signal | Dir | WR | PnL | Trades | Notes |
|--------|-----|-----|-----|--------|-------|
| bb-bounce-v2-long+ | LONG | 90.9% | $1.15 | 11 | 100% WR on 9/11 tokens. Strong across ALT, AVNT, BLUR, CFX, COMP, DOT, ENA, IMX, SOL. Only loss: KAS (-$0.22). Already enabled. |

## 7-Day Loser Context
Signals already killed in NEVER_REENABLE_FLAGS:
| Signal | 7d WR | 7d PnL | 7d Trades |
|--------|-------|--------|-----------|
| accel-300-v2-long | 28.6% | -$0.74 | 21 |
| accel-300-v3-long+ | 43.2% | -$1.39 | 37 |
| range-reversion-long+ | 16.7% | -$0.62 | 6 |
| macd-div- | 20.0% | -$0.35 | 5 |

## Issues
- **open-skies+** approaching kill threshold (33.3% WR, 6 trades, -$0.28 PnL). Active only ~34h — if still performing this poorly in next report, will be killed.
- **No signal inversions** detected — all trades match expected direction.

## Actions Taken
- None this cycle (no signals met all kill criteria in 24h window)
