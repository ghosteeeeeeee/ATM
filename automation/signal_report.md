# === Signal Performance Report ===
**Generated:** 2026-08-09 09:45 UTC | **Period:** Last 6h + 24h

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | No signals met kill criteria |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | bb_bounce+,range_finder+ already at 1.2x weight |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ma100-cross+,vortex_break_long | LONG | 33.3% | -$0.11 | 6 | WATCH — needs <30% WR to kill |
| bb_bounce+,hzscore+ | LONG | 33.3% | -$0.01 | 3 | WATCH — insufficient sample (need 5+) |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+,range_finder+ | LONG | 62.5% | +$0.57 | 16 | WINNING — 1.2x weight active |
| bb-bounce-short,hzscore- | SHORT | 100% | +$0.11 | 2 | WINNING — sample too small |

## 6h Performance Detail
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb_bounce+,range_finder+ | LONG | 8 | 50.0% | +$0.17 |
| bb-bounce-short,hzscore- | SHORT | 2 | 100.0% | +$0.11 |
| bb_bounce+,hzscore+ | LONG | 3 | 33.3% | -$0.01 |

## 24h Performance Detail
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb_bounce+,range_finder+ | LONG | 16 | 62.5% | +$0.57 |
| ma100-cross+,vortex_break_long | LONG | 6 | 33.3% | -$0.11 |
| bb_bounce+,hzscore+ | LONG | 3 | 33.3% | -$0.01 |

## ISSUES
- No signal inversions detected
- No signals met kill criteria (WR<30% with 5+ trades)
- Sample sizes small for most combos — re-check in 6h

## ANALYSIS
**No action required.** Current signal landscape is healthy:
- `bb_bounce+,range_finder+` is the clear winner at 62.5% WR, +$0.57 (16 trades)
- Already boosted to 1.2x weight in signal_compactor.py (line 264)
- No bleeding signals meet kill thresholds
- All disabled signals remain in NEVER_REENABLE_FLAGS (no re-enable attempts)
