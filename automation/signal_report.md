=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-08 05:10 UTC
Source: PostgreSQL brain.trades (queried live, not cached)

## 6h Performance (close_time > now-6h, closed, n>=2)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pump-chain+ | LONG | 1 | 100% | +$0.94 |

No other signal had >=2 closed trades in 6h.

## 24h Performance (close_time > now-24h, closed)
| Signal | Dir | Trades | WR | PnL | Regime mix (all-time) |
|--------|-----|--------|-----|-----|------------------------|
| pump-chain- | SHORT | 6 | 0.0% | -$0.38 | EXTREME 50% (110T), HIGH 42.9% (28T), NORMAL 64.3% (14T) |
| pump-chain+ | LONG | 5 | 40.0% | +$0.74 | EXTREME 48.4% (62T), HIGH 39.3% (28T), NORMAL 20% (5T) |
| pump-chain-v5 | LONG | 1 | 0.0% | -$0.06 | EXTREME 50% (8T) |

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 0.0% | -$0.38 | 6 | SURFACE kill criteria met (WR<30%, n>=5, PnL<-$0.10, active>24h) — NOT killed. Regime check: NORMAL all-time 64.3% WR +$0.22 (wins). Losing regimes already gated: EXTREME mult=0.5 (volatility_gate_v2.py:310,325 — brain_auditor 2026-10-08), HIGH hard-block PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED=True, NORMAL boosted 1.2. 24h bleed was 100% EXTREME (5T -$0.32). CEO philosophy: every dump is a SHORT — dampen, don't kill. |
| pump-chain+ | LONG | 40.0% | +$0.74 | 5 | Not kill (positive PnL). Not tune (n=5 < 10). Not boost (WR<55%). Watch. All-time 44.2% WR +$2.78 (95T) — profitable but soft WR. |
| pump-chain-v5 | LONG | 0.0% | -$0.06 | 1 | Not kill (n=1 < 5). All-time 11T 36.4% WR -$0.27 — weak, low sample. Watch. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 100% | +$0.94 | 1 (6h) | Only 6h closer. Single trade, not a boost signal. |

ISSUES:
- No direction inversions in 24h (long/short mismatch query: clean).
- No code changes this run. Regime path for pump-chain- already implemented and verified in volatility_gate_v2.py + hermes_constants.py flags.
- 6h window nearly empty (1 closed trade total) — low activity, not a signal-quality signal.
- pump-chain-v5 all-time 36.4% WR -$0.27 on 11T — under observation, not yet at kill threshold (needs 5+ trades in a 24h window with the full kill criteria).

VERIFICATION CHECKS RUN:
- Live PostgreSQL query (not cached report)
- Regime cross-tab for all three active pump-chain signals
- Flag reads: PUMP_CHAIN_SHORT_EXTREME_BLOCK_ENABLED=False (CEO revert 2026-10-07), PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED=True, PUMP_CHAIN_LONG_HIGH_BLOCK_ENABLED=False, PUMP_CHAIN_V4_ENABLED=False
- Gate multipliers confirmed present for EXTREME/NORMAL/HIGH × pump_chain± / pump-chain±
- FAMILY_MAP Pump_Flow includes pump-chain+/pump-chain-/pump-chain-v5 (market_phase_gate.py:60-62)
