=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-09-30 11:10 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No kill candidates — see analysis |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No boost candidates (doji-bottom near-miss: 4T < 5T threshold) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| rs-s30 | LONG | 0.0% | -$0.08 | 3 | Watch — below 5T kill threshold. All exits profit-monster-trail scratches (2×ZEN, 1×USUAL). No regime sample. |
| bb-bounce-v2-long+ | LONG | 33.3% | +$0.02 | 3 | Watch — positive PnL, low sample. Not a kill. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| doji-bottom-long | LONG | 75.0% | +$0.12 | 4 | Active — 3/4 wins (NEO, NXPC, GMX; SOL scratch). Near boost threshold; needs 5T. |
| pump-chain- | SHORT | 44.4% | -$0.34 | 9 | Active — NOT a kill. Loss is CASHCAT-driven (-$0.68, blacklisted 2026-09-29). Excl. blacklisted: 7T 57.1% WR +$0.34. Regime: EXTREME 50.8% WR +$1.30 (edge), HIGH 41.5% WR -$0.25 (already blocked via PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED=True). CEO set PUMP_CHAIN_SHORT_RSI_MIN=25 today. |

ISSUES:
- No direction inversions found in 24h window.
- No kills executed this cycle — no signal met all three kill criteria (WR<30%, 5+ trades, PnL<-$0.10, active>24h).
- No boosts executed — no signal met all three boost criteria (WR>55%, 5+ trades, PnL>$0.05). doji-bottom-long is closest at 75% WR / 4T / +$0.12; recheck next cycle if 5th trade lands.
- CASHCAT trades on 2026-09-29 11:33/11:38 predate the blacklist (added same day after the losses) — expected, not a bug.
- 6h window: zero closed trades meeting HAVING COUNT(*)>=2 (quiet period).
