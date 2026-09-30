=== Signal Performance Report ===
Period: 2026-09-30 22:40 UTC | Last 6h + 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met kill criteria (WR 40% > 30% threshold) |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met boost criteria |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 40.0% | -$0.30 | 5 (24h) | BLOCKED in EXTREME/HIGH via regime gate (bug fixed). Allowed in NORMAL (85.7% WR). Historical: 109T 55% WR +$0.12. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 100% | +$0.94 | 1 (24h) | Strong historical: 20T 70% WR +$2.48. EXTREME 75% WR. |
| pump-chain-v5,rs-s32 | LONG | 100% | +$0.23 | 1 (24h) | New combo, too few trades to evaluate. |
| r2-trend-short3 | SHORT | 100% | +$0.07 | 1 (24h) | R2 trend SHORT family working. |
| pump-chain-v5 | LONG | 50% | +$0.04 | 2 (24h) | V5 LONG variant — positive but thin sample. |

ISSUES:
- **✅ FIXED: Gate bypass bug** — `SIGNAL_TYPE_OVERRIDES[('EXTREME', 'pump-chain-')] = 1.0` was bypassing the family-level `Pump_Flow: 0.0` block in `volatility_gate_v2.py`. Per-signal override has highest priority in `get_combined_multiplier()`. Changed both `pump_chain-` and `pump-chain-` EXTREME overrides from 1.0 to 0.0. Verified: pump-chain- now returns 0.0 multiplier in EXTREME/HIGH, 1.0 in NORMAL.
- Low trade volume: only 13 closed trades in 24h (system normally higher). Could be regime filters working correctly or market quiet.
- No direction inversions detected in 24h.
- No OpenMemory queries performed (per instructions — tenant_mismatch errors).

REGIME BREAKDOWN (pump-chain- all-time):
| Regime | Trades | WR | PnL | Gate Status |
|--------|--------|-----|-----|-------------|
| EXTREME | 77 | 54.5% | +$0.32 | BLOCKED (bug fixed 2026-09-30) |
| HIGH | 25 | 48.0% | -$0.36 | BLOCKED |
| NORMAL | 7 | 85.7% | +$0.16 | ALLOWED |

Actions taken:
1. Fixed gate bypass bug in `volatility_gate_v2.py` (lines 303, 318)
2. Verified fix: get_combined_multiplier returns 0.0 for EXTREME/HIGH, 1.0 for NORMAL
3. No kills, no boosts (criteria not met)
