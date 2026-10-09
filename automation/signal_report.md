=== Signal Performance Report ===
Period: Last 6h | 24h (generated 2026-10-09 05:12 UTC)

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no kill criteria met |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — pump-chain+ already boosted (1.2 weight, 2026-10-03) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 35.0% (7d) | +$0.11 (7d) | 20 (7d) | watch — WR near floor, PnL still positive; no kill |
| bb-bounce-v3-long+ | LONG | 56.3% (7d) | -$0.37 (7d) | 16 (7d) | watch — WR fine, R:R problem; no 24h trades |
| pump-chain+,pump-chain-v5 | LONG | 0% (24h) | -$0.22 | 2 (24h) | below thresholds, noise |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 57.1% (24h) / 59.1% (7d) | +$0.38 (24h) / +$2.21 (7d) | 7 (24h) / 22 (7d) | top performer, already boosted; 7 trades across 7 tokens |
| bb-squeeze+ | LONG | 65.5% (7d) | +$0.01 (7d) | 58 (7d) | volume leader, break-even; healthy |

ISSUES:
- LOW TRADE VOLUME: only 13 closed trades in 24h (6h window: 0 qualifying groups). All timers active and pipeline running — volume drop is from signal scarcity / gates, not a stalled system. Worth a volume audit if it persists.
- No inversions (long/short direction mismatches): NONE in 24h.
- pump-chain+ trades exclusively in EXTREME regime (10/10 24h trades) — 4W/3L -$0.03 net in regime slice; overall positive due to trade mix. No regime block needed (no regime with 55%+ WR at n>=5, but blanket kill is inappropriate — signal is net positive).
