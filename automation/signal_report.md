=== Signal Performance Report ===
Period: Last 6h | 24h (generated 2026-10-11)

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met kill criteria |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met boost criteria (min 5 trades) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| continuum_engine | LONG | 0.0% | -$0.01 | 7 | Watch — all exits NOT_HOTSET/ORPHAN_PAPER (paper fills, not real losses) |
| ai-trader+ | LONG | 33.3% | -$0.13 | 3 | Watch — below trade threshold for kill (needs 5+) |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| doji-bottom-long | LONG | 100.0% | +$0.37 | 3 | Watch — strong but below boost threshold (needs 5+) |

ISSUES:
- No direction inversions in last 24h.
- continuum_engine trades are all on BTC with near-zero size and paper/orphan close reasons — not representative of real signal performance; monitor for real hotset trades.
- No regime-null volatility_regime values present on these trades (all NULL).
