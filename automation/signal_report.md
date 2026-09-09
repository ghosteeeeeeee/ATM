=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-09-09 17:11 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 50% | -$0.63 | 6 | PUMP_FLOW_MINUS_ENABLED = False — losses 8.8x wins, KAS -$0.42 alone |

ALREADY DISABLED (pre-existing):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pullback-entry+ | LONG | 25% | -$0.34 | 4 | Already False (auto_1hr kill 2026-09-09 15:10 UTC) |
| pump_flow LONG | LONG | 25% | +$0.73 | 8 | Already False (auto_1hr kill 2026-09-09 03:10 UTC) |

BOOSTED (executed):
None — no clear winners above 55% WR with 5+ trades in 24h

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ema300-dip-long | LONG | 33.3% | -$0.15 | 3 | Protected until 2026-09-09 05:00 UTC — cannot kill |
| bb_bounce_v2_long | LONG | 50% | -$0.11 | 2 | Watch: only 2 trades, too early |
| pullback-entry- | SHORT | 100% | +$0.08 | 3 | Winner — keep enabled |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 100% | +$0.08 | 3 | Keep |
| accel-300-v3-short- | SHORT | 50% | +$0.05 | 2 | Protected until 2026-09-09 05:00 UTC |
| mover | SHORT | 100% | +$0.04 | 2 | N/A — 2 trades only |
| open_skies | LONG | 50% | +$0.01 | 2 | N/A — 2 trades only |

ISSUES:
- No signal inversions detected (24h)
- pump-chain- SHORT killed: 6T/50%WR/-$0.63. Losses 8.8x wins (avg loss -$0.237 vs avg win +$0.027). All ATR_SL exits on losers.
- pump_chain LONG: 8T/25%WR/+$0.73 — low WR but profitable (big winners outweigh losses). Keep watching.
- ema300-dip-long under protection until 2026-09-09 05:00 UTC — re-evaluate after protection expires.
- 6h volume moderate: 4 signal combos with 2+ trades.
- 24h total: 41 closed trades.
