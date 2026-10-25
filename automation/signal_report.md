# Signal Performance Report

=== Signal Performance Report ===
Period: Last 6h | 24h — generated 2026-10-25 15:35 UTC

Volume note: thin window — only 3 closed trades in 6h, 12 in 24h. No signal met the 24h kill/boost thresholds (5+ trades).

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no signal met kill criteria (WR<30%, 5+ trades, PnL<-$0.10) |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no signal met boost criteria (WR>55%, 5+ trades) |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades (24h) | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 0.0% | -$0.06 | 2 | WATCH — worst 24h; 7d: 47.1% WR, -$0.46 / 17T. Below 5T kill threshold. |
| r2v2-long3 | LONG | 50.0% | -$0.01 | 2 | WATCH — noise-level losses. |
| pump-chain+ | LONG | 100% | +$0.05 | 1 (winner) | 7d CONTEXT: HIGH 36.8% WR -$0.48, NORMAL 12.5% WR -$0.45, but EXTREME 42.9% +$3.72 / 105T. Regime-blocking candidate for HIGH+NORMAL — NOT a blanket kill. |
| pump-chain-,pump-chain-v6- | SHORT | — | — | 0 in 24h | 7d: 14.3% WR -$0.23 / 7T. EXTREME already gate-blocked (volatility_gate_v2 0.0), HIGH blocked via PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED. NORMAL 58.8% +$0.73 keeps pump-chain- alive. |
| ai-trader-pending | LONG/SHORT | 12.5%/37.5% | -$0.04/-$0.10 | 1 (7d 8T ea) | CEO-driven signal — watch only, do not auto-kill. |

## WINNERS
| Signal | Dir | WR | PnL | Trades (24h) | Status |
|--------|-----|-----|-----|--------|--------|
| continuum+ | LONG | 100% | +$0.20 | 2 | Healthy |
| bb-squeeze+ | LONG | 100% | +$0.06 (1 in 6h) | 2 | Healthy |
| volume-buildup- | SHORT | 100% | +$0.08 | 2 | Healthy — 7d 66.7% +$0.31 / 15T |
| hl_copy_trader | LONG | 100% | +$0.16 | 1 | Healthy |
| ai-trader-pending | LONG | 100% | +$0.12 | 1 | Healthy (24h) |
| pump-chain+ | LONG | 100% | +$0.05 | 1 | Healthy (24h); see watch-list regime notes |

## ISSUES
- **No inversions found** (24h) — all signal direction labels match execution direction.
- **Thin activity**: 12 closed trades / 24h — below threshold for any kill/boost action this cycle.
- **pump-chain+ regime split**: EXTREME is a strong earner (+$3.72 / 105T) while HIGH and NORMAL bleed. If next cycles confirm, add 0.0x multipliers for HIGH+NORMAL in `volatility_gate_v2.py` + FAMILY_MAP entry in `market_phase_gate.py` — do NOT flip PUMP_FLOW_PLUS_ENABLED.
- 6h window had only 2 signals fire (bb-squeeze+, r2v2-long3), both winners.

---
*No flags changed this cycle. Next report: ~6h from now.*
