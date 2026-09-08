=== Signal Performance Report ===
Generated: 2026-09-08 22:40 UTC | 69 trades in 24h | System PnL: -$2.76

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No candidates meet all 3 kill criteria |

TUNING CANDIDATES (blocked):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| ema300-dip-short | SHORT | 38.5% | -$0.96 | 13 | TUNING — 38.5% WR, 13T. BUT CEO_PROTECTED until 2026-09-09 05:00 UTC. Cannot touch. |
| bb-bounce-v2-long+ | LONG | 37.5% | -$0.72 | 8 | WATCH — 37.5% WR, 8T. Below 10-trade tuning threshold. Re-check at 15+ trades. |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 47.1% | -$0.94 | 17 | DETERIORATING — 47.1% WR 24h but 0% WR in last 6h (5T/-$0.78). All 6h trades lost. Wins are small ($0.03-$0.13), losses larger ($0.12-$0.32). 7 wins from profit-monster-trail, 8 losses from atr_sl/cut-loser. |
| sma20-dip+ | LONG | 42.1% | -$0.73 | 19 | ALREADY KILLED — SMA20_DIP_PLUS_ENABLED=False since 2026-09-08 12:10 UTC. Trades are pre-kill. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| open-skies+ | LONG | 50.0% | +$0.48 | 2 | STEADY — low count, positive PnL |
| r2-trend-short3 | SHORT | 100% | +$0.10 | 2 | PERFECT (low count) |

ISSUES:
- **6h window is 0% WR** — all 8 trades lost in last 6 hours (-$1.09). System-wide drawdown.
- **pump-chain+ deteriorating** — 0% WR in 6h with 5 trades. All losses are atr_sl_hit or cut-loser. The signal fires on capital rotation momentum but entries are getting stopped out. Not at kill threshold yet (47.1% WR 24h) but trending badly.
- **ema300-dip-short protected** — 38.5% WR, 13T, -$0.96. Would be a tuning candidate but CEO_PROTECTED until 2026-09-09 05:00 UTC. Review after protection expires.
- **No direction inversions detected.**
- **Loss pattern** — atr_sl_hit and cut-loser-CL-T1 dominate exits. Average loss ~$0.15, average win ~$0.07. R:R imbalance across all signals.
- **bb-bounce-v2-long+** — testing signal since 2026-09-02, 37.5% WR with 8 trades. Close to tuning threshold but needs more data.
