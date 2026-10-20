# Signal Performance Report
**Generated:** 2026-10-20 | **Period:** Last 6h + 24h

## KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None met kill criteria |

## BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None met boost criteria |

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain-,pump-chain-v6- | SHORT | 20.0% | -$0.06 | 5 (4 tokens) | WATCH — WR<30% but PnL above -$0.10 kill threshold. Lifetime 43.9% WR / -$0.51; wins 60% WR in NORMAL regime → regime block candidate, not blanket kill. |
| pump-chain+ | LONG | 0.0% | -$0.39 | 2 | WATCH — worst PnL 24h but only 2 trades (<5). All-time 39.2% WR / +$2.69 (EXTREME +$3.93). |
| ai-trader-pending | LONG | 0.0% | -$0.07 | 3 | WATCH — CEO pending orders, not auto-killable. |
| ai-trader-manual | LONG | 0.0% | -$0.13 | 2 | WATCH — CEO manual trades. |
| r2v2-long3 | LONG | 50.0% | -$0.06 | 2 | WATCH — small sample. |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 100.0% | +$0.28 | 1 | Positive but n=1, not boostable. |
| r2v2-long5 | LONG | 100.0% | +$0.37 | 1 | Positive but n=1, not boostable. |
| ai-trader-pending | SHORT | 100.0% | +$0.07 | 1 | CEO pending orders. |

## 6h Performance (2+ trades):
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| r2v2-long3 | LONG | 2 | 50.0% | -$0.06 |

## ISSUES:
- **No inversions found** in last 24h — all long/short labels correct.
- **Regime check (pump-chain SHORT):** EXTREME 43.1% WR (-$0.54, n=130), HIGH 46.2% (-$0.42, n=26), NORMAL 60.0% (+$0.43, n=15). Signal is NOT a blanket-kill — it wins in NORMAL. If it crosses kill thresholds, add 0.0x multipliers for HIGH/EXTREME in volatility_gate_v2.py + FAMILY_MAP entry instead of disabling.
- **pump-chain+ LONG:** NORMAL regime 12.5% WR (-$0.45, n=8) vs EXTREME 43.9% (+$3.93, n=98) — NORMAL-regime block candidate if losses continue.
- Low overall volume today (11 closed trades in 24h) — insufficient data for aggressive action.
