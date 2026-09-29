=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-09-29 13:00 UTC

KILLED (executed):
(none — no signals meet blanket-kill criteria)

BOOSTED (executed):
(none — no signals meet boost criteria with sufficient trade volume)

REGIME-BLOCKED (executed):
| Signal | Dir | Regime | WR | PnL | Trades | Action |
|--------|-----|--------|-----|-----|--------|--------|
| mover- | SHORT | EXTREME | 0% | -$0.68 | 2 | BLOCKED via volatility_gate_v2.py — added 0.0x override |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| rs-s30 | LONG | 0% | -$0.08 | 3 (all-time) | NEW — only 3 trades today, insufficient data. Monitor. |
| mover- | SHORT | 0% | -$0.68 | 2 (24h) | EXTREME regime blocked. 58.3% all-time WR — signal works, regime context was wrong. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 57.1% | +$0.54 | 14 (24h) | ✅ Performing well |
| doji-bottom-long | LONG | 80% | +$0.28 | 5 (24h) | ✅ Performing well |
| bb-bounce-v2-long+ | LONG | 50% | +$0.04 | 4 (24h) | ⚠️ Neutral — watching |

ISSUES:
- No signal inversions detected.
- rs-s30 is brand new (first trade 2026-09-29 11:40). All 3 trades lost. Too early to kill — needs 10+ trades for statistical significance. Monitor closely.
- mover- losses are EXTREME-regime specific. All-time WR is 58.3% (12 trades). Regime block applied, signal left enabled.
