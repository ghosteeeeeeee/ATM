=== Signal Performance Report ===
Date: 2026-08-23 05:00 UTC
Period: Last 6h | 24h | 48h | 7d

## VOLUME
- Last 6h: 0 closed trades
- Last 24h: 8 closed trades (system heavily filtered or quiet market)
- Last 48h: 102 closed trades, -$0.83 net
- 7d: 45+ signals, ~3881 total closed trades all-time

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | No kills executed this cycle |

## KILL CANDIDATES (watch)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ct-hot+ | LONG | 31.4% | -$3.28 | 35 (48h) | RESEARCH_FLAGS — T re-enabled 2026-08-22. Cannot kill. Deteriorating. |
| return_exhaustion_long | LONG | 33.3% | -$0.27 | 6 (7d) | Below 5-trade threshold. Watch. |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | No boosts executed this cycle |

## BOOST CANDIDATES (watch)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hl_copy_trader | LONG | 54.4% | +$2.54 | 57 (7d) | Top performer. Already in PROFIT_MONSTER_BYPASS. |
| hzscore- | SHORT | 83.3% | +$0.13 | 6 (7d) | Strong WR, small sample. |
| r2-trend-long3 | LONG | 54.2% | +$0.14 | 24 (7d) | Consistent. |
| r2-trend-long4 | LONG | 71.4% | +$0.22 | 14 (7d) | Strong. |

## WINNERS (7d)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hl_copy_trader | LONG | 54.4% | +$2.54 | 57 | TOP PERFORMER |
| r2-trend-long6 | LONG | 100.0% | +$0.29 | 4 | Small sample |
| r2-trend-long4 | LONG | 71.4% | +$0.22 | 14 | Strong |
| r2-trend-long3 | LONG | 54.2% | +$0.14 | 24 | Consistent |
| hzscore- | SHORT | 83.3% | +$0.13 | 6 | Strong WR |
| bb_bounce+,hl_copy_trader | LONG | 80.0% | +$0.33 | 5 | Confluence winner |
| r2-trend-long5 | LONG | 75.0% | +$0.10 | 4 | Good |
| hl_copy_trader | SHORT | 0.0% | -$0.24 | 2 | Dead — too few trades |

## LOSERS (7d, 5+ trades)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ct-hot+ | LONG | 28.9% | -$3.45 | 38 | WORST — RESEARCH_FLAGS, cannot kill |
| return_exhaustion_long | LONG | 33.3% | -$0.27 | 6 | Below threshold |
| bb_bounce+ | LONG | 25.0% | -$0.03 | 4 | Low sample |
| stop_hunt_reversal_long+ | LONG | 60.0% | -$0.04 | 10 | Already in NEVER_REENABLE_FLAGS |

## ISSUES
- **Signal starvation**: Only 8 trades in 24h. System heavily filtered.
- **ct-hot+ RESEARCH_FLAGS**: Worst performer (-$3.28/48h, 31.4% WR) but locked by RESEARCH_FLAGS (T re-enabled 2026-08-22). Cannot kill without T approval.
- **No signal inversions** found.
- **stop_hunt_reversal_long+**: Already killed (NEVER_REENABLE_FLAGS). Still firing? 10T/7d means it may be executing despite kill switch. Check signal_schema.py guard.

## DECISIONS MADE
1. No kills executed — ct-hot+ is the only candidate meeting kill criteria but is RESEARCH_FLAGS-protected.
2. No boosts executed — top performers already optimized or in research mode.
3. Signal starvation is the primary concern — 8 trades/24h is below viable threshold.
