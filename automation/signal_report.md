=== Signal Performance Report ===
Generated: 2026-09-28 23:10 UTC

## Summary
| Period | Trades | PnL | WR |
|--------|--------|-----|-----|
| 6h | 9 | +$0.09 | 50.0% |
| 24h | 14 | +$0.09 | 50.0% |
| 7d | 114 | -$4.30 | 39.5% |

## KILLED (executed this run)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7 (7d) | Added to SIGNAL_SOURCE_BLACKLIST |
| accel-300-v4-short- | SHORT | 20.0% | -$0.26 | 5 (30d) | Added to SIGNAL_SOURCE_BLACKLIST |

**Note:** `accel-300` was already blacklisted (Aug 5) but `validate_source()` does exact match — `accel-300` did NOT match `accel-300-breakout` or `accel-300-v4-short-`. Both slipped through for weeks.

## REGIME BLOCKS (already active — verified)
| Signal | Dir | Blocked Regime | Reason | Status |
|--------|-----|----------------|--------|--------|
| pullback-entry- | SHORT | NORMAL | 0% WR, -$0.62 in NORMAL | ✅ Active since Sep 17 |
| pump-chain+ | LONG | EXTREME | 0.0 mult in EXTREME | ✅ Active since Sep 24 |
| mover+ | LONG | EXTREME | Mover family=0.0 in EXTREME | ✅ Active since Sep 23 |

## BOOSTED
None. No signal with 3+ trades in 7d has WR>55% AND positive PnL.

## LOSERS (watch list — 7d, 3+ trades)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 0.0% | -$1.54 | 6 | Regime-blocked NORMAL; EXTREME/HIGH historically profitable |
| mover+ | LONG | 16.7% | -$0.95 | 6 | EXTREME blocked; HIGH mixed |
| pump-chain+ | LONG | 16.7% | -$0.85 | 6 | EXTREME blocked; HIGH/NORMAL losing |
| pump-chain- | SHORT | 48.6% | -$0.74 | 35 | Near breakeven, watch |
| bb-bounce-v2-long+ | LONG | 42.9% | -$0.18 | 14 | Small loss, watch |
| continuum-osc+ | LONG | 75.0% | -$0.05 | 4 | Great WR, tiny loss — skip |

## WINNERS (7d, 2+ trades)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 50.0% | +$0.05 | 2 | Insufficient sample |

## SIGNAL INVERSIONS
None found in 24h.

## 6h Performance
| Signal | Dir | WR | PnL | Trades |
|--------|-----|-----|-----|--------|
| pump-chain- | SHORT | 100.0% | +$0.19 | 2 |

## ISSUES
1. **Source blacklist gap fixed:** `accel-300-breakout` and `accel-300-v4-short-` were bypassing the `accel-300` blacklist due to exact-match logic in `validate_source()`. Added explicit entries.
2. **7d system-wide underperformance:** 114 trades, -$4.30 PnL, 39.5% WR. Low activity in 24h (14 trades) suggests regime filtering is working but opportunity set is thin.
3. **No boost candidates:** Zero signals with 3+ trades and positive PnL in 7d. System is in a drawdown phase.
