=== Signal Performance Report ===
Period: Last 6h | 24h (as of 2026-09-19)

## KILLED (executed):
None — no blanket kills needed.

## REGIME BLOCKS (executed):
| Signal | Dir | Regime | 24h WR | 24h PnL | Action |
|--------|-----|--------|--------|---------|--------|
| grind-trend+ | LONG | NORMAL | 0.0% | -$0.30 | volatility_gate_v2.py: 0.0x multiplier added |
| grind-trend+ | LONG | HIGH | 57.1% | +$0.07 | Unchanged (wins here) |

## BOOSTED (executed):
| Signal | Dir | 24h WR | 24h PnL | Trades | Status |
|--------|-----|--------|---------|--------|--------|
| volume-breakout-long+ | LONG | 77.8% | +$0.80 | 9 | Winner — monitor |
| mover+ | LONG | 80.0% | +$0.12 | 5 | Winner — monitor |

## LOSERS (watch list):
| Signal | Dir | 24h WR | 24h PnL | Trades | Status |
|--------|-----|--------|---------|--------|--------|
| grind-trend+ | LONG | 33.3% | -$0.23 | 12 | NORMAL blocked. HIGH wins (57.1%). Lifetime avg -$0.019/trade |
| pump-chain+ | LONG | 20.0% | -$0.04 | 10 | Tiny losses (-$0.004/trade). Lifetime EXTREME 52% WR (50T). 24h EXTREME bad luck (3T 0%WR) |
| pullback-entry- | SHORT | 0.0% | -$0.35 | 2 | Below threshold (2T). Watch next period |

## WINNERS:
| Signal | Dir | 24h WR | 24h PnL | Trades | Status |
|--------|-----|--------|---------|--------|--------|
| volume-breakout-long+ | LONG | 77.8% | +$0.80 | 9 | Hot |
| mover+ | LONG | 80.0% | +$0.12 | 5 | Hot |

## ISSUES:
- No signal inversions detected
- grind-trend+ NORMAL regime: 0% WR across 5 trades — blocked via volatility_gate_v2.py
- pump-chain+ EXTREME 24h: 0% WR (3T) — likely noise (lifetime EXTREME 52% WR, 50T). No action taken

## FILES CHANGED:
- scripts/volatility_gate_v2.py: Added Grind_Trend NORMAL regime 0.0x multiplier
- scripts/market_phase_gate.py: Added Grind_Trend family to FAMILY_MAP
