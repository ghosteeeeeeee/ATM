=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-08 22:15 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No kill candidates |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 62.5% (24h) / 59.1% (7d) | +$1.32 (24h) / +$2.21 (7d) | 8 (24h) / 22 (7d) | combo_weights 1.0 → 1.1 |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 0.0% | -$0.23 | 1 (24h) | Watch — 7d 35% WR -$0.14; already suppressed at 0.6 |
| pump-chain+,pump-chain-v5 | LONG | 0.0% | -$0.22 | 2 (24h) | v5 already disabled; residual closes |
| pump-chain-v5 | LONG | 0.0% | -$0.15 | 1 (24h) | Already disabled 2026-10-08 CEO |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 62.5% (6h) | +$0.49 | 6 (6h) | Active; boosted to 1.1 |

ISSUES:
- Low overall trade volume: 12 closed trades in 24h, only one signal group clears sample thresholds.
- No direction inversions detected (0 in 24h).
- self_learner auto-tune threshold (COMBO_BOOST_WR=0.60) sits just above pump-chain+ 7d WR of 59.1% — manual boost applied; self_learner will preserve it (returns None → keeps old weight) until WR crosses 60%.
- 14d window shows same n=22 as 7d (signal_outcomes retention/window), so "active > 24h" confirmed via brain DB (first trade 2026-09-09).
