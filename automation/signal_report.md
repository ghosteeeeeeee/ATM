=== Signal Performance Report ===
Period: Last 6h (0 trades) | 24h (12 trades)

KILLED (executed): None — no signals meet hard-kill criteria (WR<30% + 5+ trades + PnL<-$0.10)

BOOSTED (executed): None — continuum-osc+ LONG 100%WR but only 2T (insufficient sample)

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 57.1% | -$0.46 | 7 | WATCH — loses in EXTREME/HIGH regimes |
| ema300-breakthrough+ | LONG | 0% | -$0.28 | 1 | WATCH — single trade, insufficient data |
| r2-trend-short4 | SHORT | 0% | -$0.21 | 1 | WATCH — single trade, insufficient data |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| continuum-osc+ | LONG | 100% | +$0.10 | 2 | OK — small sample, keep watching |

ISSUES:
- **Volatility gate bug**: pump-chain- SHORT trades still fire in EXTREME (4T/24h) and HIGH (2T/24h) despite Pump_Flow multiplier=0.0 in both regimes (volatility_gate_v2.py lines 247, 272). The gate reduces confidence but doesn't hard-block — trades pass via STANDALONE_BYPASS. All-time: EXTREME 53.6%WR -$0.11, HIGH 48%WR -$0.36. Only NORMAL is profitable (85.7%WR +$0.16). Recommend: add hard regime block in pump_flow_signal.py or signal_compactor.py for EXTREME/HIGH, not just confidence multiplier.
- **Low activity**: Only 12 trades in 24h. System is quiet — normal for current market conditions.
- **No signal inversions** found.
- **pump-chain-,rs-r61 SHORT**: 1 trade, $0.00 PnL — dead money exit, insufficient data.

REGIME BREAKDOWN (pump-chain- SHORT, all-time):
| Regime | Trades | WR | PnL | Avg PnL |
|--------|--------|-----|-----|---------|
| EXTREME | 56 | 53.6% | -$0.11 | -$0.002 |
| HIGH | 25 | 48.0% | -$0.36 | -$0.014 |
| NORMAL | 7 | 85.7% | +$0.16 | +$0.023 |

Generated: 2026-09-25
