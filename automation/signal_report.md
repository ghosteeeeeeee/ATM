# Signal Performance Report

Period: Last 6h | 24h (generated 2026-10-24, signal_reporter)

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | No kill candidates |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 83.3% | +$0.55 | 6 (24h) | Source weight 1.0→1.2 in signal_compactor.py |

Boost justification: 24h 6T 83.3%WR +$0.55 across 6 tokens (CHIP, ICP, SYRUP, MON, DYDX, MET); 14d 22T 68.2%WR +$0.58. Multi-token consistent.

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader-pending | SHORT | 50% | -$0.04 | 2 | Manual CEO trades — not a signal, skip |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 83.3% | +$0.55 | 6 | BOOSTED 1.0→1.2 |
| pump-chain- | SHORT | 100% | +$0.34 | 1 | Monitoring |
| pump-chain+ | LONG | 100% | +$0.01 | 1 | Monitoring |
| r2v2-long4 | LONG | 100% | +$0.01 | 1 | Monitoring |

## 6h window
Only volume-buildup- SHORT qualified (2T, 50%WR, +$0.19). Quiet period.

## ISSUES
- No direction inversions in 24h.
- Schema note: the trades table has BOTH `token` and `chain` columns — the reporter prompt's "token column is chain" gotcha is wrong; `token` works and holds the ticker.
- volume-buildup- all-time regimes mixed (NORMAL 9/17 53%WR, EXTREME 4/7, HIGH 3/3 +$0.49) but 24h performance is a clean multi-token win — boost only, no regime gate needed.
