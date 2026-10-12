# Signal Performance Report

Period: 2026-10-12 ~10:00 UTC | Last 6h + 24h

## Activity
- 6h: 6 closed trades, net PnL ≈ -$0.09
- 24h: 22 closed trades, net PnL ≈ +$0.64
- No direction inversions found.

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no signal met kill criteria |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no signal met boost criteria |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 25.0% | -$0.31 | 4 | WATCH — 4 trades < 5 kill threshold. Historical EXTREME regime: 194T 48.5%WR +$3.58 (profitable). Not a kill. |
| ai-trader+ | LONG | 33.3% | -$0.13 | 3 | WATCH — 3 trades < 5 kill threshold. All-time: 9T 66.7% +$0.05. Active ~3d. Not a kill. |
| hmacd_mtf-- | SHORT | 0% | -$0.12 | 1 | WATCH — single trade, insufficient data. |
| oversold-bounce+ | LONG | 0% | -$0.07 | 2 | WATCH — small sample. |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2v2-long3 | LONG | 100% | +$0.59 | 1 | healthy, small sample |
| ai-trader-manual | LONG | 100% | +$0.57 | 1 | healthy |
| hl_copy_trader | LONG | 100% | +$0.09 | 1 | healthy |
| bb-bounce-v2-long+ | LONG | 100% | +$0.06 | 1 | healthy |
| volume-buildup+ | LONG | 50% | +$0.05 | 2 | healthy |
| bb-squeeze+ | LONG | 100% | +$0.01 | 1 | healthy |

## ISSUES
- Quiet trading window — only 6 trades closed in 6h. No action warranted on such thin samples.
- pump-chain+ LONG losers were all EXTREME-regime (hard_max_loss exits); regime gate already routes this signal and historical EXTREME data is positive. No flag changes needed.
