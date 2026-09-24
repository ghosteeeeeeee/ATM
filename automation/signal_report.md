=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-09-24 17:13 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none killed — no signal met blanket-kill criteria) | | | | | |

REGIME BLOCKS (executed):
| Signal | Dir | Regime | WR | PnL | Trades | Action |
|--------|-----|--------|-----|-----|--------|--------|
| pump-chain- | SHORT | EXTREME | 51.9% | -$0.20 | 54 | 0.0x mult (was 1.0x) |
| pump-chain- | SHORT | HIGH | 50.0% | -$0.28 | 24 | 0.0x mult (was 1.0x) |
| pump-chain- | SHORT | NORMAL | 83.3% | +$0.13 | 6 | UNBLOCKED (was 0.0x) |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none — no clear winners in 24h) | | | | | |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| mover+ | LONG | 0.0% | -$0.61 | 3 | Watch — only 3 trades, too few to act |
| accel-300-breakout | SHORT | 20.0% | -$0.07 | 5 | Watch — 1d old, 7 total trades, EXTREME only |
| bb-bounce-v2-long+ | LONG | 33.3% | -$0.16 | 3 | Watch — 1d old, 12 total trades |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| (no signals with 5+ trades and 55%+ WR in 24h) | | | | | |

ISSUES:
- No signal inversions detected
- No clear winners in 24h window — system is in a rough patch
- pump-chain- SHORT had its NORMAL regime UNBLOCKED (was incorrectly blocked by old pump-chain+ LONG data)

ACTIONS TAKEN:
1. Added Pump_Flow 0.0x to EXTREME regime (pump-chain- SHORT 51.9% WR, -$0.20)
2. Added Pump_Flow 0.0x to HIGH regime (pump-chain- SHORT 50% WR, -$0.28)
3. Removed Pump_Flow 0.0x from NORMAL regime (pump-chain- SHORT 83.3% WR, +$0.13 — was incorrectly blocked)
4. Updated comments in volatility_gate_v2.py with evidence dates

NEXT REVIEW: 6 hours
