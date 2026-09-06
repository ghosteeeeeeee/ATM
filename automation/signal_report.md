# Signal Performance Report
Generated: 2026-09-06

## Summary
- **Total trades (24h):** 34
- **Total trades (all-time):** 4,642
- **Kill candidates:** 0 (no signals meet ALL kill criteria)
- **Boost candidates:** 1 (bb-bounce-v2-long+ already enabled)
- **Signal inversions:** 0

## 24h Performance (by signal+direction)

### Winners (WR > 55%, PnL > $0)
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| bb-bounce-v2-long+ | LONG | 11 | 90.9% | $1.29 | ACTIVE (BB_BOUNCE_V2_LONG_ENABLED=True) |

### Neutral (WR 40-55%)
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| coil-spring+ | LONG | 8 | 50.0% | -$0.03 | ACTIVE |
| open-skies+ | LONG | 8 | 50.0% | -$0.19 | ACTIVE |

### Losers (WR < 40% OR PnL < -$0.10)
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| ema300-dip-short | SHORT | 3 | 0.0% | -$0.42 | KILLED (EMA300_DIP_SHORT_ENABLED=False, NEVER_REENABLE) |

## 6h Performance
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb-bounce-v2-long+ | LONG | 2 | 100.0% | $0.34 |
| coil-spring+ | LONG | 5 | 60.0% | $0.04 |

## Kill Analysis
**No signals meet ALL kill criteria:**
- WR < 30% with 5+ trades (24h)
- Net PnL < -$0.10 (24h)
- Signal active > 24h

**Note:** ema300-dip-short has 0% WR but only 3 trades (needs 5+). Already killed by CEO on 2026-09-05.

## Boost Analysis
**bb-bounce-v2-long+ qualifies:**
- WR: 90.9% (> 55%)
- PnL: $1.29 (> $0.05)
- Trades: 11 (> 5)
- Already enabled (BB_BOUNCE_V2_LONG_ENABLED=True)

## Signal Inversions
No direction mismatches found in 24h period.

## Actions Taken
None — no kills or boosts required. Current state is optimal.

## System Health
- Live trading: ENABLED
- All filters active (context gate, regime, speed, etc.)
- No anomalies detected
