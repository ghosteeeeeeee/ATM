=== Signal Performance Report ===
Period: 2026-09-07 11:10 — 17:10 UTC (6h) / 2026-09-06 17:10 — 2026-09-07 17:10 UTC (24h)
Total 24h: 47 trades, +$0.33 PnL

## KILLED (executed this run)
None — losers already killed:
- `slow-grind+` LONG: killed by ORCHESTRATOR 2026-09-07 (SLOW_GRIND_LONG_ENABLED=False, NEVER_REENABLE). 15T/24h 40% WR -$0.80. Trades after kill are pipeline draining.
- `coil-spring+` LONG: killed 2026-09-06 15:07 UTC (COILED_SPRING_PLUS_ENABLED=False).

## BOOSTED (executed this run)
None — no confidence/hotset changes made.

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Avg PnL | Status |
|--------|-----|-----|-----|--------|---------|--------|
| slow-grind+ | LONG | 40.0% | -$0.80 | 15 | -$0.053 | KILLED (already) |
| open-skies+ | LONG | 50.0% | -$0.23 | 4 | -$0.058 | WATCH (low sample) |
| continuation+ | LONG | 0.0% | -$0.28 | 1 | -$0.280 | WATCH (1 trade only) |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Avg PnL | Status |
|--------|-----|-----|-----|--------|---------|--------|
| pump-chain+ | LONG | 89.5% | $0.64 | 19 | $0.034 | ACTIVE — top performer |
| bb-bounce-v2-long+ | LONG | 77.8% | $0.41 | 9 | $0.046 | ACTIVE — strong, best avg PnL |

## 6h Snapshot (active signals only)
| Signal | Dir | WR | PnL | Trades |
|--------|-----|-----|-----|--------|
| pump-chain+ | LONG | 100% | $0.55 | 7 |
| bb-bounce-v2-long+ | LONG | 60% | $0.21 | 5 |

## ISSUES
- No signal inversions found (24h).
- Total system PnL is +$0.33/24h — **first positive reading since kill cleanup**. Excluding killed signals (slow-grind -$0.80, coil-spring drained), active signals net +$1.13.
- `pump-chain+` at 89.5% WR / 19 trades is the clear leader. 6h showing 100% WR — on a hot streak.
- `bb-bounce-v2-long+` has better avg PnL/trade ($0.046 vs $0.034) despite lower WR — more efficient per trade.
- `open-skies+` at 4 trades is too small to judge. Keep watching.
- No new kills needed — all clear losers already disabled.
