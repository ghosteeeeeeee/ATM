=== Signal Performance Report ===
Generated: 2026-09-15 05:09 UTC
Period: Last 6h (expanded to 8h) | 24h

--- EXECUTIVE SUMMARY ---
24h: 38 trades, 44.7% WR, -$1.12 PnL

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 28.6% | -$0.38 | 7 | REGIME BLOCK: Added Pump_Flow 0.0x to NORMAL regime in volatility_gate_v2.py. Wins in EXTREME (46.7% WR, +$0.22) and HIGH (42.9% WR, -$0.06). 0%WR -$0.44 in NORMAL. |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | No candidates meeting boost criteria |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 42.9% | -$0.48 | 7 | WATCH — Wins in EXTREME (81.8% WR, +$1.74), HIGH (58.1% WR, +$0.56). 24h drawdown is noise. Already regime-blocked in NORMAL via existing Pullback_Entry 0.0x. |
| rr-struct-v2+ | LONG | 57.1% | -$0.16 | 7 | WATCH — Positive WR but negative PnL. R2_Structural already blocked in NORMAL (0.0x) and HIGH (0.0x). Wins in EXTREME. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 46.2% | -$0.04 | 13 | NEUTRAL — Breakeven. No action needed. |
| breakout-long+ | LONG | 100% | +$0.25 | 1 | INSUFFICIENT — Only 1 trade. |
| rr-struct-v2+,rs-s37 | LONG | 100% | +$0.01 | 1 | INSUFFICIENT — Only 1 trade. |

ISSUES:
- No signal inversions detected in 24h window.
- No OpenMemory queries (skipped per instruction).
- 24h overall negative (-$1.12) — market environment is choppy. Regime blocks should help by preventing pump-chain+ LONG from firing in NORMAL (where it goes 0% WR).

ACTIONS TAKEN:
1. Added 'Pump_Flow': 0.0 to VOL_PHASE_MULTS[('NORMAL', '*')] in volatility_gate_v2.py
   - pump-chain+ LONG: 0% WR, -$0.44 in NORMAL (3T lifetime) — wins in EXTREME (+$0.22)
   - Prevents signal from firing in NORMAL regime while preserving EXTREME/HIGH access
