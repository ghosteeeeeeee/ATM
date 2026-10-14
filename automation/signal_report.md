=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-14 (UTC)

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No kill candidates met all criteria |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No boost candidates met all criteria |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup+ | LONG | 0.0% | -$0.26 | 3 | WATCH — below 5-trade kill threshold; 3x hard_max_loss burst 08:32-08:43; all-time NORMAL regime still +$0.20 (5/9 WR) |
| bb-bounce-v2-long+ | LONG | 40.0% | -$0.03 | 3 | WATCH — 5 trades, tiny loss, not yet tuning-grade |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 100.0% | +$0.41 | 4 | Good — below 5-trade boost threshold |
| pump-chain+ | LONG | 50.0% | +$0.26 | 6 | Positive — WR below boost threshold |
| pump-chain- | SHORT | 33.3% | +$0.26 | 6 | Positive PnL despite low WR |
| r2v2-long3 | LONG | 66.7% | +$0.01 | 3 | Marginal |
| pump-chain+ (6h) | LONG | 66.7% | +$0.26 | 3 | Best 6h performer |

Totals 24h: 38 closed trades, net PnL -$0.04 (breakeven)

ISSUES:
- Zero direction inversions in 24h (checked long/short mismatches) — clean.
- volume-buildup+ LONG: 3 consecutive hard_max_loss within ~10 minutes (08:32-08:43 UTC) — burst of bad entries, possibly correlated positions on same regime shift. Active since 2026-10-12. If it hits 5+ trades with WR still <30% next cycle, kill or regime-gate it.
- All trading on hyperliquid venue only.
- No action taken this cycle — thresholds protect against over-trading on small samples.
