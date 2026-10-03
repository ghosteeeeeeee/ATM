=== Signal Performance Report ===
Period: Last 6h | 24h | Generated: 2026-10-02

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None qualified |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — see notes below |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| mtf-regime-trend+ | LONG | 44.4% | -$0.46 | 9 (48h) | 0 trades in 24h window — not currently firing. Monitor next cycle. |
| continuum+ | LONG | 0% | -$0.21 | 1 | Below trade threshold, not actionable |
| bb-squeeze+,rs-s102,rs-s114 | LONG | 0% | -$0.11 | 1 | Combo, below threshold |
| pump-chain-v5 | LONG | 50% | -$0.08 | 2 | Small loss, below threshold |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v3-long+ | LONG | 100% | +$0.12 | 3 | Healthy — below boost trade threshold (5+) |
| bb-squeeze+ | LONG | 66.7% | +$0.10 | 9 | Boost qualified but NOT re-boosted — reverted 2026-10-02 for R:R break (avg win 0.059 vs SL -0.11..-0.27). One good day doesn't undo that fix. |
| pump-chain- | SHORT | 60% | +$0.18 | 5 | Boost qualified — gated and performing well within gates. No weight change needed. |
| pump-chain+ | LONG | 62.5% | +$0.95 | 8 | Boost qualified — highest PnL. Heavily gated (HIGH regime, dead-hours, RSI). Performing well within existing constraints. |

ISSUES:
- No direction inversions in 24h window — clean
- mtf-regime-trend+ has a 44.4% WR / -$0.46 record over 48h but zero trades in the last 24h. If it resumes firing at current quality, it becomes a kill candidate (would need WR<30% + 5+ trades + PnL<-$0.10 in 24h to trigger).
- bb-squeeze+ boost reverted 2026-10-02 remains in effect — do not re-boost without a longer-window R:R check showing the problem is fixed.
