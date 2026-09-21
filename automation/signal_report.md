=== Signal Performance Report ===
Period: 2026-09-20 21:00 UTC | 6h + 24h window

KILLED (executed):
None — no kill candidates in 24h window.

BOOST CANDIDATES:
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 57.1% | $1.35 | 14 | Consider compactor weight 1.0→1.2 |
| pullback-entry- | SHORT | 72.7% | $0.62 | 11 | Consider compactor weight 1.0→1.2 |

LOSERS (watch list — 7d, already killed):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| rr-struct-v2+ | LONG | 40.0% | -$0.45 | 10 | KILLED 2026-09-15 (RR_STRUCTURAL_V2_LONG_ENABLED=False) |
| open-skies+ | LONG | 20.0% | -$0.42 | 5 | RE-ENABLED 2026-09-20 CEO 48h test — no trades yet |
| grind-trend- | SHORT | 20.0% | -$0.38 | 5 | KILLED 2026-09-19 (GRIND_TREND_MINUS_ENABLED=False) |
| breakout-long+ | LONG | 25.0% | -$0.35 | 4 | KILLED 2026-09-17 (BREAKOUT_LONG_PLUS_ENABLED=False) |

WINNERS (24h):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 57.1% | $1.35 | 14 | Active, primary earner |
| pullback-entry- | SHORT | 72.7% | $0.62 | 11 | Active, high WR |
| doji-bottom-long | LONG | 100% | $0.30 | 1 | Active, low sample |
| volume-breakout-long+ | LONG | 100% | $0.08 | 1 | Active, low sample |
| continuum- | SHORT | 100% | $0.02 | 1 | Active, low sample |

REGIME GATING (already in place):
- Grind_Trend NORMAL: 0.0x (blocked)
- R2_Structural NORMAL: 0.2x (penalized)
- R2_Structural HIGH: 0.0x (blocked)
- Breakout HIGH: 0.0x (blocked)
- Volume_Breakout HIGH: 0.0x (blocked)

ISSUES:
- open-skies+ re-enabled for CEO 48h test (2026-09-20) — monitor closely, historical 20% WR
- No signal inversions found
- Low trade count in 24h (28 closed) — pipeline may be slower than usual
