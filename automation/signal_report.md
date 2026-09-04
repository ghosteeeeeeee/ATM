# Signal Performance Report
**Generated:** 2026-09-04 (auto)

## Period: Last 6h | 24h | 48h | 7d

### System Summary
| Period | Trades | WR | PnL |
|--------|--------|-----|-----|
| 24h | 86 | 59.3% | -$1.00 |
| 7d | 413 | 53.8% | -$3.43 |

> Note: System PnL negative despite good WR — R:R issue (avg loss > avg win), not signal selection.

### KILLED (executed this cycle)
None. All losers already disabled.

### BOOSTED (executed this cycle)
None. Active winners already at full weight.

### ACTIVE WINNERS
| Signal | Dir | WR 24h | PnL 24h | Trades 24h | WR 48h | PnL 48h | Trades 48h | Status |
|--------|-----|--------|---------|------------|--------|---------|------------|--------|
| bb-bounce-v2-long+ | LONG | 71.4% | +$0.51 | 21 | 75.8% | +$0.86 | 33 | ACTIVE |
| ema300-dip | LONG | 69.4% | +$0.11 | 36 | 69.0% | +$0.26 | 42 | ACTIVE |

### LOSERS (all already killed)
| Signal | Dir | WR 24h | PnL 24h | Trades 24h | Status |
|--------|-----|--------|---------|------------|--------|
| accel-300-v3-long+ | LONG | 52.9% | -$0.36 | 17 | DEAD (2026-09-04) |
| accel-300-v3-short- | SHORT | 0.0% | -$0.48 | 3 | DEAD (2026-09-04) |
| bb-bounce-short | SHORT | 0.0% | -$0.39 | 2 | DEAD (2026-09-03) |
| slow-grind- | SHORT | 50.0% | -$0.02 | 2 | TESTING |

### 7d Chronic Losers (all already killed)
| Signal | Dir | Trades | PnL | Status |
|--------|-----|--------|-----|--------|
| accel-300-v3-long+ | LONG | 35 | -$1.34 | DEAD |
| accel-300-v2-long | LONG | 21 | -$0.74 | DEAD |
| range-reversion-long+ | LONG | 6 | -$0.62 | DEAD |
| r2-trend-long3 | LONG | 9 | -$0.46 | DEAD |
| macd-div- | SHORT | 10 | -$0.47 | DEAD |
| confluence-,ichimoku- | SHORT | 7 | -$0.46 | DEAD (ichimoku off) |
| bb-bounce-short | SHORT | 58 | -$0.38 | DEAD |

### Signal Inversions
None detected.

### Token Health (48h)
**ema300-dip:** MNT(+0.18), GMT(+0.10), ME(+0.13), ALT(+0.10), GRASS(-0.20), ICP(-0.13)
**bb-bounce-v2-long+:** KAS(+0.27), DOT(+0.33), GRASS(+0.23), ETC(+0.22), POL(+0.11)

### Issues
- System-wide R:R is the problem, not signal selection. 59.3% WR should be profitable but avg loss exceeds avg win.
- Only 2 signals producing all positive PnL — thin diversification.
- slow-grind- (SHORT) is TESTING with break-even — monitor closely.
