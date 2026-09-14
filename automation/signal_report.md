# Signal Performance Report
Generated: 2026-09-14 ~17:00 UTC

## System Overview
| Period | Trades | PnL | WR |
|--------|--------|-----|-----|
| 24h | 40 | -$0.97 | 42.5% |
| 7d | 319 | +$0.97 | 53.9% |

No direction inversions detected. No critical bugs.

## KILLED (executed by auto_1hr today)
| Signal | Dir | WR | PnL (7d) | Trades | Action |
|--------|-----|-----|----------|--------|--------|
| pump-chain+ | LONG | 37.5% | -$0.56 | 24 | PUMP_FLOW_PLUS_ENABLED=False (2026-09-14) |

Kill is working — no new pump-chain+ LONG entries after flag set. 1 open position (INJ) entered pre-kill, will close via normal exit logic.

## ALREADY KILLED (pre-existing)
| Signal | Dir | WR | PnL | Status |
|--------|-----|-----|-----|--------|
| trend_purity+ | LONG | 36.4% | -$0.90 | DEAD (TREND_PURITY_PLUS_ENABLED=False) |
| ema300_dip_short | SHORT | 47.1% | -$0.91 | DEAD (EMA300_DIP_SHORT_ENABLED=False) |
| sma20_dip | LONG | 42.1% | -$0.73 | DEAD (SMA20_DIP_PLUS_ENABLED=False) |
| bb_bounce_v2_long | LONG | 45.5% | -$0.68 | DEAD (BB_BOUNCE_V2_LONG_ENABLED=False) |
| pullback-entry+ | LONG | 16.7% | -$0.57 | DEAD (PULLBACK_ENTRY_PLUS_ENABLED=False) |

## WATCH LIST (minor losers, 7d)
| Signal | Dir | WR | PnL (7d) | Trades | Notes |
|--------|-----|-----|----------|--------|-------|
| rr-struct- | SHORT | 42.9% | -$0.42 | 7 | HIGH regime: 25% WR -$0.41. NORMAL: 66.7% WR -$0.01. Consider HIGH block. |
| open-skies+ | LONG | 50.0% | -$0.31 | 6 | EXTREME: 0% WR -$0.49. HIGH: 75% WR +$0.18. Consider EXTREME block. |

## WINNERS (48h)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 62.5% | +$0.98 | 24 | Active, strong |
| rr-struct+ | LONG | 70.0% | +$0.57 | 10 | Active, strong |
| pump-chain- | SHORT | 60.0% | +$0.35 | 10 | Active, strong |

## ISSUES
- None (no inversions, no critical bugs)
- pump-chain+ LONG open trade on INJ ($6.17 entry) — entered before kill, will exit normally
