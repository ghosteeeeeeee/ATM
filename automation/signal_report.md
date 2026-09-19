=== Signal Performance Report ===
Generated: 2026-09-19 11:00 UTC

## 6h Performance
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| grind-trend- | SHORT | 3 | 33.3% | -$0.20 |
| grind-trend+ | LONG | 3 | 100.0% | +$0.42 |
| pump-chain+ | LONG | 4 | 100.0% | +$0.44 |

## 24h Performance
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pullback-entry- | SHORT | 3 | 0.0% | -$0.50 |
| grind-trend- | SHORT | 5 | 20.0% | -$0.38 |
| mover+ | LONG | 3 | 33.3% | -$0.19 |
| grind-trend+ | LONG | 18 | 50.0% | +$0.24 |
| pump-chain+ | LONG | 16 | 50.0% | +$1.40 |

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| grind-trend- | SHORT | 20.0% | -$0.38 | 5 | GRIND_TREND_MINUS_ENABLED = False — no winning regime |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 50.0% | +$1.40 | 16 | Strong performer, consistent across regimes |

## WATCH LIST (NOT killed)
| Signal | Dir | WR | PnL | Trades | Reason |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 0.0% | -$0.50 | 3 | Historically profitable (EXTREME 61.9%, HIGH 53.8%). Recent 3 trades bad luck, not broken signal. |
| mover+ | LONG | 33.3% | -$0.19 | 3 | Only 3 trades, too early to judge |

## REGIME ANALYSIS
| Signal | Regime | Trades | WR | PnL |
|--------|--------|--------|-----|-----|
| grind-trend+ | HIGH | 12 | 66.7% | +$0.35 |
| grind-trend+ | NORMAL | 6 | 16.7% | -$0.11 |
| grind-trend- | HIGH | 3 | 33.3% | -$0.16 |
| grind-trend- | NORMAL | 2 | 0.0% | -$0.22 |
| pump-chain+ | EXTREME | 7 | 57.1% | +$0.63 |
| pump-chain+ | HIGH | 8 | 37.5% | +$0.68 |

## ISSUES
- No signal inversions detected (24h)
- grind-trend+ LONG: NORMAL regime (16.7% WR) dragging down overall performance. Already killed by CEO on 2026-09-19.
- pullback-entry- SHORT: 0% WR in 24h window but historically profitable — monitor closely, do NOT blanket kill.
