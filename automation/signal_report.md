=== Signal Performance Report ===
Generated: 2026-09-21 23:09 UTC

Period: Last 6h | 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | No kills — no signal meets kill criteria |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | No boost candidates — no signal with 5+ trades, >55% WR, >$0.05 PnL |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 21.4% | -$0.75 | 14 | WATCH — lifetime profitable ($1.80). 24h bad patch in EXTREME (22%WR -$0.69). NORMAL block already active (0.0x mult). Variance, not structural. |
| doji-bottom-long | LONG | 33.3% | -$0.34 | 3 | WATCH — lifetime 66.7% WR +$0.40. Only 3 trades — insufficient sample. |
| pullback-entry- | SHORT | 0.0% | -$0.32 | 2 | WATCH — lifetime 54.9% WR +$1.89. Only 2 trades — insufficient sample. |
| mover+ | LONG | 50.0% | -$0.24 | 2 | WATCH — lifetime 73.3% WR +$0.10. Only 2 trades. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 50.0% | +$0.57 | 2 | OK |
| accel-300-breakout,rs-r64,rs-r66 | SHORT | 100.0% | +$0.17 | 1 | OK |
| mover- | SHORT | 77.8% | +$0.52 | 9 (7d) | Consistent |

ISSUES:
- **pump-chain+ bad 24h patch**: 21.4% WR -$0.75 in 24h, but lifetime 43.2% WR +$1.80. Losses concentrated in EXTREME regime (22.2% WR -$0.69) where signal normally wins (50% WR +$1.52 over 7d). This is variance, not a structural failure. NORMAL regime block already active (0.0x multiplier).
- **Low trade volume**: Only 27 closed trades in 24h across all signals. Insufficient data for many signals to evaluate.
- **No signal inversions detected**.
- **1 open position**: pump-chain+ LONG on AIXBT (entry $0.02278).

DECISIONS MADE:
- No kills executed — no signal meets kill criteria (WR<30% with 5+ trades in 24h AND PnL<-$0.10 AND active >24h)
- pump-chain+ NORMAL regime block already in place (Pump_Flow = 0.0x in VOL_PHASE_MULTS)
- No regime changes needed
