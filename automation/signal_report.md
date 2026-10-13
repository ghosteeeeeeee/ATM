=== Signal Performance Report ===
Period: Last 6h | 24h (generated 2026-10-13 05:10 UTC)

Totals: 6h = 5 trades, -$0.45 | 24h = 18 trades, -$0.92

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met kill criteria (WR<30%, 5+ trades, PnL<-$0.10, active>24h) |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met boost criteria (WR>55%, 5+ trades, PnL>$0.05) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 33.3% | -0.40 | 6 | WATCH — near-kill (WR just above 30% threshold). All-time: wins in EXTREME regime (47% WR, +3.25), loses in NORMAL (14% WR, -0.60) and HIGH (36% WR, -0.24). Do NOT blanket-kill; candidate for volatility_gate multipliers on NORMAL/HIGH if 24h trend continues. NORMAL regime n=7 too small to gate yet. |
| oversold-bounce+ | LONG | 0.0% | -0.33 | 3 | WATCH — only 9 all-time trades (first seen 2026-10-06). Sample too small to kill. |
| ai-trader+ | LONG | 0.0% | -0.12 | 2 | WATCH — only 11 all-time trades (first seen 2026-10-09). Sample too small to kill. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hl_copy_trader | LONG | 50.0% | +0.06 | 2 | n too small to boost |
| r2v2-long6 | LONG | 100.0% | +0.02 | 1 | n too small to boost |
| bb-squeeze+ | LONG | 100.0% | +0.01 | 1 | n too small to boost |

ISSUES:
- No direction inversions in last 24h (checked long-signal/SHORT and short-signal/LONG mismatches) — clean.
- Low trade volume overall (18 closed trades / 24h) — most signals have n<5, so neither kills nor boosts are statistically actionable this cycle.
- System is net-negative over 24h (-$0.92) but losses are spread across many small-n signals; no single clear offender.
