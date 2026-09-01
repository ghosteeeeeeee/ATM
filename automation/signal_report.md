=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-09-01 ~12:00 UTC

## 6h Performance (min 2 trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb-bounce-long+ | LONG | 10 | 50.0% | -$0.18 |
| bb-bounce-short | SHORT | 3 | 66.7% | -$0.03 |

## 24h Performance (min 3 trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| accel-300-v2-long | LONG | 17 | 29.4% | -$0.64 |
| bb-bounce-long+ | LONG | 17 | 58.8% | -$0.07 |
| bb-bounce-short | SHORT | 5 | 80.0% | +$0.01 |

## KILLED (already executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| accel-300-v2-long | LONG | 29.4% | -$0.64 | 17 | Already killed — NEVER_REENABLE (2026-09-01) |
| bb-bounce-long+ | LONG | 50% | -$0.18 | 10 (6h) | Already killed — NEVER_REENABLE (2026-09-01 AUTO_1HR) |

## BOOSTED (candidates)
None. bb-bounce-short (80% WR, +$0.01) is only 5 trades — insufficient for boost.

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-long+ | LONG | 50% | -$0.18 | 10 (6h) | Killed — watch for resumption after NEVER_REENABLE expires |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-short | SHORT | 80% | +$0.01 | 5 | Healthy but low volume |

## ISSUES
- No direction inversions detected
- Only 3 active signal sources in 24h — signal diversity very low
- bb-bounce-long+ degraded after CEO kill (was 61.5% WR 24h, dropped to 50% in 6h)
- System is signal-starved: only 22 total trades in 24h across all signals

## DECISIONS
No new kills or boosts executed — all candidates already handled by previous reports.
