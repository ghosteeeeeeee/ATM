=== Signal Performance Report ===
Period: 2026-09-10 ~11:09 UTC | Window: 6h / 24h
Total: 5 trades (6h, +$1.71) | 45 trades (24h, +$2.55, 58.9% WR)

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pullback-entry+ | LONG | 0.0% | -$0.61 | 5 | PREVIOUSLY KILLED — 0% WR, 5T/24h, NEVER_REENABLED |

BOOST CANDIDATES (watch):
| Signal | Dir | WR | PnL | Trades | Notes |
|--------|-----|-----|-----|--------|-------|
| pullback-entry- | SHORT | 81.3% | +$1.76 | 16 | DOMINANT — 85.7% WR in EXTREME, 83.3% in HIGH. Consistent across all regimes. |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 60.0% | -$0.50 | 5 | avg_loss 9x avg_win — SL/TP sizing issue, not signal quality |
| open-skies+ | LONG | 0.0% | -$0.23 | 1 | Single trade, too early |
| r2v2-long3 | LONG | 0.0% | -$0.14 | 1 | Single trade, too early |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 81.3% | +$1.76 | 16 | TOP PERFORMER |
| pump-chain+ | LONG | 100.0% | +$0.59 | 1 | Single trade |
| ema300-dip-short | SHORT | 100.0% | +$0.42 | 1 | Single trade |
| accel-300-v4-short- | SHORT | 100.0% | +$0.32 | 1 | Single trade |
| mover+ | LONG | 100.0% | +$0.12 | 1 | Single trade |

KILL DECISIONS:
- pullback-entry+ LONG: ALREADY KILLED (PULLBACK_ENTRY_PLUS_ENABLED=False). 0% WR across 5 trades confirmed. No action needed.
- pump-chain- SHORT: 60% WR with 5 trades — does NOT meet kill criteria (need WR < 30%). But avg_loss ($0.237) is 9x avg_win ($0.027) — SL/TP ratio problem. Flag for signal-quality-tuner review.
- No NEW signals meet ALL kill criteria (WR < 30% + 5+ trades + active > 24h).

ISSUES:
- No signal direction inversions detected
- pump-chain- has severe avg_loss/avg_win imbalance (9:1) — need tighter stops or wider targets

REGIME PERFORMANCE (pullback-entry- SHORT, 24h):
| Regime | Trades | WR | PnL |
|--------|--------|-----|-----|
| NORMAL | 3 | 66.7% | -$0.08 |
| HIGH | 6 | 83.3% | +$0.62 |
| EXTREME | 7 | 85.7% | +$1.22 |

NEXT REVIEW: ~6h (2026-09-10 ~17:09 UTC)
