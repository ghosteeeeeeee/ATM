=== Signal Performance Report ===
Period: 2026-09-11 | Last 6h + 24h

## 6h Performance
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb-bounce-v2-long+ | LONG | 3 | 33.3% | -$0.21 |
| mover+ | LONG | 3 | 66.7% | -$0.21 |
| pullback-entry- | SHORT | 2 | 0.0% | -$0.19 |
| pump-chain- | SHORT | 3 | 33.3% | -$0.19 |

## 24h Performance
| Signal | Dir | Trades | WR | PnL | Avg PnL |
|--------|-----|--------|-----|-----|---------|
| pump-chain+ | LONG | 7 | 28.6% | -$0.61 | -$0.087 |
| accel-300-v4-short- | SHORT | 2 | 0.0% | -$0.31 | -$0.155 |
| mover+ | LONG | 3 | 66.7% | -$0.21 | -$0.070 |
| bb-bounce-v2-long+ | LONG | 4 | 50.0% | -$0.19 | -$0.048 |
| pullback-entry- | SHORT | 11 | 45.5% | -$0.01 | -$0.001 |
| pump-chain- | SHORT | 20 | 65.0% | +$1.03 | +$0.052 |

**Total 24h:** 50 trades, 50.0% WR, -$0.49 PnL

## KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 28.6% | -$0.61 | 7 | Regime block: 0.0x in HIGH volatility |

**Details:** pump-chain+ LONG wins in EXTREME regime (42.9% WR, +$0.09) but loses badly in HIGH regime (0% WR, -$0.11). Added `Pump_Flow: 0.0` multiplier to `('HIGH', '*')` in `volatility_gate_v2.py` VOL_PHASE_MULTS. SHORT side unaffected (65% WR, +$1.03).

## BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No boost candidates — no signal has WR>55% with 5+ trades AND positive PnL |

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| accel-300-v4-short- | SHORT | 0.0% | -$0.31 | 2 | Watch — insufficient data (2 trades) |
| bb-bounce-v2-long+ | LONG | 50.0% | -$0.19 | 4 | Watch — borderline WR, small losses |
| mover+ | LONG | 66.7% | -$0.21 | 3 | Watch — good WR but negative PnL |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 65.0% | +$1.03 | 20 | Strong performer — keep |

## ISSUES:
- No direction inversions detected (LONG signals not firing SHORT, vice versa)
- Total 24h PnL slightly negative (-$0.49) — 50 trades is a moderate sample
- mover+ has 66.7% WR but negative PnL — winning trades smaller than losing trades (R:R issue)
