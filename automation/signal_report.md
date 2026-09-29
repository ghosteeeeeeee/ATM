=== Signal Performance Report ===
Period: 2026-09-29 11:00 UTC | Last 6h / 24h

## KILLED (executed)
None — no signal meets kill criteria (5+ trades, WR<30%, PnL<-$0.10 in 24h).

## REGIME ADJUSTMENTS (executed)
| Signal | Regime | Change | Reason |
|--------|--------|--------|--------|
| pump-chain- SHORT | EXTREME | 0.5→1.0 | +$1.70 lifetime (116 trades), 51.7% WR |
| mover- SHORT | EXTREME | 1.0→0.0 | -$1.54 lifetime (32 trades), net negative |
| coin_tracker_hot_short | EXTREME | 1.0→0.0 | Same as mover_short (Mover family) |

## BOOSTED
None — pump-chain- SHORT performing well at full multiplier already.

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| mover- | SHORT | 0% | -$0.68 | 2 | Watch — EXTREME regime blocked, below kill threshold |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 75% | +$0.88 | 8 | Active, EXTREME regime boosted |

## ALL 24h SIGNALS (27 total closed trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pump-chain- | SHORT | 8 | 75.0% | +$0.88 |
| rs-s35 | LONG | 2 | 100% | +$0.09 |
| mover- | SHORT | 2 | 0% | -$0.68 |
| rs-r32 | SHORT | 1 | 100% | +$0.02 |
| rs-r33,rs-r34,rs-r35 | SHORT | 1 | 0% | -$0.20 |
| rs-r68 | SHORT | 1 | 100% | +$0.01 |
| rs-s31 | LONG | 1 | 0% | -$0.20 |
| rs-s36 | LONG | 1 | 100% | +$0.11 |
| rs-s38 | LONG | 1 | 100% | +$0.09 |
| rs-s48 | LONG | 1 | 0% | -$0.04 |
| rs-s52 | LONG | 1 | 0% | -$0.20 |
| rs-s56 | LONG | 1 | 100% | +$0.19 |
| rs-s57 | LONG | 1 | 0% | -$0.21 |
| rs-s82 | LONG | 1 | 0% | -$0.07 |
| bb-bounce-v2-long+ | LONG | 1 | 100% | +$0.02 |
| rs-s94 | LONG | 1 | 100% | +$0.07 |
| doji-bottom-long | LONG | 1 | 100% | +$0.16 |
| r2-trend-short5 | SHORT | 1 | 100% | +$0.01 |

## ISSUES
- Low volume: only 27 closed trades in 24h. Pipeline running but signal output moderate.
- Mover- EXTREME regime blocked. Mover- SHORT lifetime in EXTREME is net negative despite 53% WR (wins smaller than losses).
- pump-chain- EXTREME boosted — proven profitable with 116 lifetime trades.
- No signal inversion bugs detected.
- 9018 signals in DB (may need cleanup — flagged in pipeline health check).
