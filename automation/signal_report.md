=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-18 (signal_reporter)

6h closed trades: 0 — quiet period, no action.
24h closed trades: 13.

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signal met kill criteria (no signal had 5+ trades in 24h) |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signal met boost criteria (no signal had 5+ trades in 24h) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 0.0% | -0.18 | 2 | WATCH — 7d 31.3% WR -$0.61 (16T). EXTREME already 0.0-blocked (10-16). NORMAL sliding: 7d 6T 33% -$0.18 vs lifetime 46.2% +$0.15. HIGH still 55.6% lifetime — keep alive, re-check next run |
| pump-chain+ | LONG | 33.3% | -0.07 | 3 | WATCH — 7d 30.3% WR but +$0.31 net. NORMAL already 0.5-dampened (lifetime 11.1% WR -$0.63, 9T). HIGH 0.5. EXTREME carries PnL (+$0.41 7d). No change |
| hl_copy_trader | SHORT | 0.0% | -0.06 | 1 | noise (1 trade) |
| ai-trader- | SHORT | 0.0% | -0.05 | 1 | noise (1 trade) |
| hl_copy_trader | LONG | 0.0% | -0.05 | 1 | noise — 7d LONG 50% WR +$0.12 |
| volume-buildup- | SHORT | 0.0% | -0.03 | 1 | noise — 7d 77.8% WR +$0.35 (9T) |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain-,pump-chain-v6- | SHORT | 100% | +0.54 | 2 | healthy |
| ai-trader+ | LONG | 100% | +0.05 | 1 | healthy |
| ai-trader-manual | LONG | 100% | +0.03 | 1 | healthy |

ISSUES:
- None. 0 direction inversions in 24h. No bugs or anomalies detected.
- Signal volume is very low (13 trades/24h, 0 trades/6h) — insufficient data for kill/boost decisions this cycle. Existing regime gates (bb-bounce-v2-long+ EXTREME=0.0, pump-chain+ NORMAL/HIGH=0.5) remain appropriate.
