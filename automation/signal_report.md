=== Signal Performance Report ===
Period: 2026-09-17 19:45 UTC | Last 6h + 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| open-skies+ | LONG | 20.0% | -$0.42 | 5 | ALREADY KILLED (2026-09-17) — 11T/8d 36%WR/-$0.73, No regime >50% WR. NEVER_REENABLE. Confirmed DISABLED_COMPONENT block in pipeline log at 17:12. |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signals meet boost criteria (5+ trades, >55% WR, >$0.05 PnL) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 33.3% | -$0.30 | 3 | WATCH — Only 3 trades total (all today), all in NORMAL regime, all SL hits. Too few trades to kill. Monitor next 24h. |
| rs-s36,volume-breakout-long+ | LONG | 0.0% | -$0.22 | 1 | WATCH — Combo signal, 1 trade only. Not statistically significant. |
| btc-pump-rider+ | LONG | 0.0% | -$0.09 | 1 | WATCH — 1 trade only. |
| r2-trend-short3 | SHORT | 0.0% | -$0.09 | 1 | WATCH — 1 trade only. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 100.0% | +$0.02 | 1 | OK — 1 trade only, not enough data. |
| grind-breakout+ | LONG | 100.0% | +$0.01 | 1 | OK — 1 trade only, not enough data. |

ISSUES:
- open-skies+ was still firing trades at 17:09-17:11 today despite kill flag being set. DISABLED_COMPONENT block kicked in at 17:12. Trades created at 11:31-14:28 today were from before the kill took effect.
- volume-breakout-long+ has only 3 trades total — all from today. Needs more data before action.
- 5 open trades currently active.
- Low trade volume overall (7 signals, 13 trades in 24h). System is in quiet mode.

SUMMARY:
- No new kills needed. open-skies+ already killed and confirmed blocked.
- No boost candidates — no signals with enough volume and positive performance.
- volume-breakout-long+ is the only signal to watch — needs 7+ more trades before kill threshold.
