=== Signal Performance Report ===
Period: 2026-09-02 ~13:00 UTC | Last 6h + 24h

KILLED (executed earlier today):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| accel-300-v3-long+ | LONG | 37.5% | -$0.70 | 16 | KILLED ~09:00 UTC (CEO) — ALL ATR_SL in NEUTRAL |
| accel-300-v2-long | LONG | 25.0% | -$0.10 | 4 | KILLED 2026-09-01 (auto_1hr) — NEVER_REENABLE |
| accel-300-v2-short- | SHORT | 28.6% | -$0.06 | 7 | KILLED today (CEO) — replaced by v3 |
| bb-bounce-long+ | LONG | 62.5% | -$0.11 | 8 | KILLED today (CEO) — NEVER_REENABLE |
| range-reversion-long+ | LONG | 0.0% | -$0.67 | 4 | KILLED 12:15 UTC (signal_reporter) — ALL ATR_SL |

BOOSTED: None — no signal has 5+ trades at 55%+ WR in 24h.

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long3 | LONG | 33.3% | -$0.23 | 6 | WATCH — needs 10+ trades to kill. 37.5% WR over7d |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-short | SHORT | 100% | +$0.11 | 3 | GOOD — 60.7% WR over7d. Low sample. |
| r2-trend-short4 | SHORT | 100% | +$0.19 | 2 | GOOD — low sample, monitor |

ISSUES:
- No signal inversions detected (24h)
- All killed signals traded BEFORE their disable times — no stale trades after kills
- r2-trend-long3 is the only active loser — below kill threshold (6T, needs 10+). Will re-evaluate next report.
- Overall24h: 60 closed trades, net PnL negative. Most losses from already-killed signals.

SUMMARY: All bad signals already killed. No new actions needed. System is clean.
