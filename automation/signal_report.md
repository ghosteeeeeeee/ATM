=== Signal Performance Report ===
Period: 2026-09-07 18:00 — 2026-09-08 00:00 UTC (6h) / 2026-09-07 00:00 — 2026-09-08 00:00 UTC (24h)
Total 24h: 59 trades, 61% WR, +$0.19 PnL

## KILLED (executed this run)
None — no active kill candidates. Losers already killed:
- `slow-grind+` LONG: killed by ORCHESTRATOR 2026-09-07 (SLOW_GRIND_LONG_ENABLED=False, NEVER_REENABLE). 12T last 24h 25% WR -$1.22. Trades after kill are pipeline draining.

## BOOSTED (executed this run)
None — no signals meet boost criteria (WR>55% + PnL>$0.05 + 5+ trades). Top performers already enabled.

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| slow-grind+ | LONG | 25.0% | -$1.22 | 12 | KILLED (pipeline drain) |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 83.3% | +$0.48 | 18 | ACTIVE |
| bb-bounce-v2-long+ | LONG | 66.7% | +$0.28 | 9 | ACTIVE |
| ema300-dip-short | SHORT | 75.0% | +$0.05 | 4 | ACTIVE |
| open-skies+ | LONG | 60.0% | +$0.71 | 5 | ACTIVE |

## ISSUES
- No direction inversions detected.
- slow-grind+ trades draining (SLOW_GRIND_LONG_ENABLED=False, NEVER_REENABLE) — trades from before kill completing. Expected.
- 6h window only 3 signals with 2+ trades: pump-chain+ (2T, 50% WR, -$0.10), bb-bounce-v2-long+ (2T, 50% WR, -$0.05), ema300-dip-short (4T, 75% WR, +$0.05). Low volume in 6h window — market may be in NEUTRAL regime or weekend slowdown.

## SYSTEM HEALTH
- Overall 24h WR: 61% (59 trades) — healthy
- No signal flags need changing — all underperformers already killed
- No boost candidates needing weight adjustments
