=== Signal Performance Report ===
Period: Last 6h | 24h (generated 2026-10-27)

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No kill candidates |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No boost candidates |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 37.5% | -$0.32 | 8 | WATCH — HIGH regime protects it (all-time 10T 80%WR +$0.42). NORMAL 22T 54.5%WR -$0.13, EXTREME 9T 55.6%WR -$0.04. No blanket kill. 24h loss spread thin across regimes (HIGH -$0.17, NORMAL -$0.13, EXTREME -$0.02). |
| pump-chain+ | LONG | 66.7% | -$0.11 | 9 | WATCH — all 9 trades EXTREME. Wins small (ugb_pt $0.01-$0.19), losses large (BLUR hard_max_loss -$0.31, GRASS hard_sl -$0.10). Classic small-win/large-loss profile. Not a kill (WR > 55%). |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 100% | +$0.25 | 2 | 6h only, sub-sample of 24h set |
| pump-chain+ | LONG | 66.7% | -$0.11 | 9 | 24h — high WR, negative PnL (loss asymmetry) |

ISSUES:
- No direction inversions found (checked long-signal/SHORT and short-signal/LONG last 24h — zero results).
- Low trade volume overall: only 2 signals met the >=2 (6h) / >=3 (24h) trade thresholds. Quiet period.
- volume-buildup- HIGH regime had 4 trades in 24h with -$0.17 despite all-time 80% WR — small sample, not actionable.
