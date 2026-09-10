# Signal Performance Report
**Period:** Last 6h / 24h | **Generated:** 2026-09-10 17:08 UTC

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | No kill candidates |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 69.2% | +$0.98 | 13 | Hot-set priority candidate |
| pump-chain- | SHORT | 71.4% | +$1.19 | 14 | Hot-set priority candidate |

**Regime breakdown (pullback-entry- SHORT):**
| Regime | Trades | WR | PnL |
|--------|--------|-----|-----|
| EXTREME | 3 | 66.7% | +$0.32 |
| HIGH | 8 | 87.5% | +$0.81 |
| NORMAL | 2 | 0.0% | -$0.15 |

**Regime breakdown (pump-chain- SHORT):**
| Regime | Trades | WR | PnL |
|--------|--------|-----|-----|
| EXTREME | 9 | 77.8% | +$0.98 |
| HIGH | 5 | 60.0% | +$0.21 |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 50.0% | -$0.12 | 2 | Below trade threshold |
| pump-chain- | SHORT | 50.0% | -$0.07 | 4 | Within noise |
| pullback-entry+ | LONG | 0.0% | -$0.23 | 2 | Below trade threshold |

**Long-term concern:** inv_accel_ LONG — 14.3% WR, -$0.31 PnL (77 trades all-time). No regime data. Already disabled.

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 69.2% | +$0.98 | 13 | STRONG — especially HIGH regime |
| pump-chain- | SHORT | 71.4% | +$1.19 | 14 | STRONG — consistent across regimes |
| pump-chain+ | LONG | 50.0% | +$0.33 | 4 | Holding |

## ISSUES
- **No signal inversion bugs detected**
- **pullback-entry- SHORT:** 0% WR in NORMAL regime (2 trades). Consider regime gate if NORMAL regime volume increases.
- **All active signals profitable in 24h window** — no immediate kills needed.

## Recommendations
1. **Add pullback-entry- and pump-chain- to hot-set priority** — both consistently profitable across EXTREME/HIGH regimes
2. **Regime gate consideration:** Add 0.0x multiplier for pullback-entry- SHORT in NORMAL regime if more data confirms the 0% WR pattern
3. **Monitor pump-chain+ LONG** — 50% WR, only 4 trades. Needs more data before action.
