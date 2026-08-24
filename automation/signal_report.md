=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-08-24 17:10 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| ct-hot+ | LONG | 28.6% | -$0.49 | 14 | DISABLED COIN_TRACKER_HOT_PLUS_ENABLED, added to NEVER_REENABLE_FLAGS |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 92.3% | +$0.95 | 13 | WATCH — consistent winner, consider weight increase |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| confluence-,ct-hot-,macd-div- | SHORT | 0.0% | -$0.32 | 2 | INSUFFICIENT — needs 5+ trades for kill |
| macd-div+ | LONG | 33.3% | -$0.19 | 3 | INSUFFICIENT — needs 5+ trades for kill |
| hl_copy_trader | LONG | 50.0% | -$0.17 | 2 | INSUFFICIENT — needs 5+ trades for kill |
| hl_copy_trader | SHORT | 50.0% | -$0.13 | 2 | INSUFFICIENT — needs 5+ trades for kill |
| bb-bounce-short,confluence- | SHORT | 50.0% | -$0.11 | 2 | INSUFFICIENT — needs 5+ trades for kill |
| confluence-,macd-div- | SHORT | 50.0% | -$0.03 | 2 | INSUFFICIENT — needs 5+ trades for kill |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 92.3% | +$0.95 | 13 | EXCELLENT — 92% WR, consistent |
| tl_break_short | SHORT | 80.0% | +$0.02 | 10 | GOOD WR, low PnL per trade |
| macd-div- | SHORT | 75.0% | +$0.02 | 12 | GOOD WR, low PnL per trade |
| hzscore- | SHORT | 66.7% | +$0.30 | 3 | INSUFFICIENT — needs more trades |
| bb_bounce+ | LONG | 100.0% | +$0.23 | 4 | EXCELLENT — 100% WR (6h) |

ISSUES:
- ct-hot+ LONG killed: 28.6% WR with 14 trades (24h), 0% WR with 4 trades (6h)
- No signal inversions detected
- Multiple signals have insufficient trade count (<5) for kill decisions

SUMMARY:
- Total 24h trades: 88
- Total 24h winners: 51
- Total 24h PnL: -$0.54
- Kill executed: ct-hot+ LONG (28.6% WR, -$0.49)
- Boost candidate: bb_bounce+ LONG (92.3% WR, +$0.95)