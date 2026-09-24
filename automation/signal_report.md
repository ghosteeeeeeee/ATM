=== Signal Performance Report ===
Generated: 2026-09-24 ~10:00 UTC

## System Summary
| Period | Trades | PnL | WR |
|--------|--------|-----|-----|
| 6h | 12 | -$0.89 | 33.3% |
| 24h | 36 | -$1.50 | 33.3% |

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7 | Already killed (line 1808). In NEVER_REENABLE. |
| mover+ | LONG | 0.0% | -$0.61 | 3 | Already killed (line 3144). All ATR_SL losses. |

## BOOSTED (executed)
None — no signals meet boost criteria (WR>55%, 5+ trades, positive PnL).

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 25.0% | -$0.19 | 4 | WATCH — but 30d:74% WR +$2.08. Short-term variance. |
| pump-chain- | SHORT | 45.0% | -$0.09 | 20 | OK — 6h shows 60% WR +$0.04. Stabilizing. |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 60.0% | +$0.04 | 5 | 6h winner (short window). |

## ISSUES
- No signal inversions detected.
- System-wide 24h WR is low (33.3%) — broad market headwinds, not signal-specific.
- accel-300-breakout trades in 24h window are from Sep 23 (pre-kill), not new firings.
- mover+ trades from early today (Sep 24) were executed after kill — possible stale signal in queue.
