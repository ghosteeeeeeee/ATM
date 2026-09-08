=== Signal Performance Report ===
Generated: 2026-09-08 17:10 UTC | 73 trades in 24h

KILLED (executed by auto_1hr):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| ema300-dip-short | SHORT | 47.1% | -$0.91 | 17 | KILLED 2026-09-08 16:10 UTC — 0%WR last hour, 17T/24h, redesign failed |
| sma20-dip+ | LONG | 42.1% | -$0.73 | 19 | KILLED 2026-09-08 12:10 UTC — 0%WR 3T last hour, 47.1%WR all-time |

BOOST CANDIDATES:
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 64.3% | -$0.26 | 14 | MIXED — high WR but bad R:R. 7d: +$0.38/78.8%WR. Keep enabled, monitor. |
| open-skies+ | LONG | 100% | +$1.42 | 2 | STRONG — highest PnL/trade. Low sample, no action needed. |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 44.4% | -$0.57 | 9 | WATCH — 4 cut-loser exits ($0.59), 2 atr_sl ($0.15). Not at kill threshold yet. |
| r2-trend-short5 | SHORT | 0% | -$0.14 | 1 | WATCH — 1 trade, too early. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| open-skies+ | LONG | 100% | +$1.42 | 2 | STRONG |
| r2-trend-short3 | SHORT | 100% | +$0.10 | 2 | PERFECT (low count) |
| r2-trend-short4 | SHORT | 100% | +$0.07 | 2 | PERFECT (low count) |
| continuation+ | LONG | 83.3% | +$0.05 | 6 | STRONG |
| bb-bounce-long+ | LONG | 83.3% | +$0.08 | 6 | STRONG |

ISSUES:
- cut-loser-CL-T1 is the dominant loss exit: 24 trades, -$3.43 total, avg -$0.14 each. This single exit type accounts for more losses than all other exits combined.
- pump-chain+ has high WR (64.3%) but negative PnL — cut-loser losses ($0.62 from 4 trades) exceed profit-monster-trail wins ($0.53 from 8 trades). Risk-reward imbalance.
- No direction inversions detected.
- Both killed signals (ema300-dip-short, sma20-dip+) had their last trades close before the kill time — no post-kill firing detected.
- 7-day picture: ema300-dip (-$0.72, 63.6%WR, 55T), accel-300-v3-long+ (-$1.41, 43.6%WR, 39T), slow-grind+ (-$0.80, 40%WR, 15T) are the biggest 7d losers. slow-grind+ already killed.
