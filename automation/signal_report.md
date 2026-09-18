=== Signal Performance Report ===
Period: 2026-09-18 17:08 UTC | Last 6h + 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 20.0% | -$0.59 | 5 | Blocked HIGH (0.5→0.0x). NORMAL already blocked (0.0x). Wins only EXTREME (65% WR). |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 75.0% | +$0.89 | 12 | Watch — strong, consistent performer |
| mover+ | LONG | 100.0% | +$0.26 | 3 | Watch — clean wins |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| continuation+ | LONG | 0.0% | -$0.01 | 1 | Single trade, all-time 41.2% WR -$0.71 — needs monitoring |
| btc-pump-rider+ | LONG | 0.0% | $0.00 | 1 | Only 2 lifetime trades, insufficient data |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 75.0% | +$0.89 | 12 | Strong |
| mover+ | LONG | 100.0% | +$0.26 | 3 | Strong |
| warrior-sr-confirm+ | LONG | 100.0% | +$0.04 | 1 | Single trade |
| r2-trend-long8 | LONG | 100.0% | +$0.12 | 1 | Single trade |
| doji-bottom-long | LONG | 100.0% | +$0.13 | 1 | Single trade |

ISSUES:
- pullback-entry- NORMAL trades (0:55 UTC) were placed BEFORE the 05:15 UTC gate fix — NORMAL was at 0.8x at the time. Gate already corrected back to 0.0.
- pullback-entry- HIGH now blocked (0.0x) — was 0.5x, still losing (33% WR -$0.30/24h).
- No signal inversions detected.
- Overall system: 25 trades, 64% WR, +$0.84/24h.

CHANGES:
- scripts/volatility_gate_v2.py: Pullback_Entry HIGH multiplier 0.5→0.0 (blocks SHORT in HIGH regime)
