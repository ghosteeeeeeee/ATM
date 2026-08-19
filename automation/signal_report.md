=== Signal Performance Report ===
Generated: 2026-08-19 05:08 UTC | Period: 6h / 24h / 72h

## KILLED (executed this cycle)
None — no signal meets all kill criteria (WR<30%, 5+ trades24h, active>24h, PnL<-$0.10).

## WATCH LIST (active losers — monitor next cycle)
| Signal | Dir | WR | PnL | Trades (72h) | Avg PnL | Status |
|--------|-----|-----|-----|--------|---------|--------|
| return_exhaustion_long | LONG | 33.3% | -$0.28 | 6 | -$0.047 | BORDERLINE — WR just above 30% threshold, 3 of6 losses. Kill if drops below30% next cycle |
| r2-trend-long3 | LONG | 42.9% | -$0.16 | 14 | -$0.011 | HIGH VOLUME underperformer —14 trades, small avg loss. Consider tightening entry criteria |
| ct-hot+ | LONG | 0% | -$0.13 | 3 | -$0.043 | INSUFFICIENT DATA — only3 trades, needs 5+ to qualify for kill. Already killed by CEO on 8/16, these are combos |
| bb_bounce+ (standalone) | LONG | 0% | -$0.08 | 3 | -$0.027 | INSUFFICIENT DATA — standalone underperforming but combos winning (bb_bounce+,hl_copy_trader at75% WR) |

## BOOSTED (executed this cycle)
| Signal | Dir | WR | PnL | Trades (72h) | Action |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+,hl_copy_trader | LONG | 75.0% | +$0.24 | 4 | CONFIRMED winner — hot-set priority |
| stop_hunt_reversal_long+ | LONG | 75.0% | +$0.06 | 4 | CONFIRMED winner — hot-set priority |
| r2-trend-long4 | LONG | 62.5% | +$0.05 | 8 | SOLID — 8 trades, positive PnL |

## WINNERS (positive performers)
| Signal | Dir | WR | PnL | Trades | Avg PnL |
|--------|-----|-----|-----|--------|---------|
| bb_bounce+,hl_copy_trader | LONG | 75.0% | +$0.24 | 4 | +$0.060 |
| stop_hunt_reversal_long+ | LONG | 75.0% | +$0.06 | 4 | +$0.015 |
| r2-trend-long4 | LONG | 62.5% | +$0.05 | 8 | +$0.006 |
| r2-trend-long5 | LONG | 66.7% | +$0.02 | 3 | +$0.007 |
| r2-trend-long7 | LONG | 50.0% | +$0.02 | 2 | +$0.010 |
| hzscore- | SHORT | 66.7% | -$0.01 | 3 | -$0.003 |

## LOSERS (negative performers)
| Signal | Dir | WR | PnL | Trades | Avg PnL |
|--------|-----|-----|-----|--------|---------|
| return_exhaustion_long | LONG | 33.3% | -$0.28 | 6 | -$0.047 |
| r2-trend-long3 | LONG | 42.9% | -$0.16 | 14 | -$0.011 |
| ct-hot+ | LONG | 0% | -$0.13 | 3 | -$0.043 |
| range_breakout_short | SHORT | 0% | -$0.17 | 2 | -$0.085 |
| bb_bounce+ (standalone) | LONG | 0% | -$0.08 | 3 | -$0.027 |

## ISSUES
- **No direction inversions detected** — all trades match signal direction
- **Low trade volume in6h window** — only2 signals closed (r2-trend-long4 at50% WR, -$0.06). System is quiet.
- **return_exhaustion_long** is the closest to kill threshold — if next cycle pushes it below30% WR, it dies
- **r2-trend-long3** has14 trades but negative PnL — high frequency, low quality. Consider adding minimum confidence threshold
- **bb_bounce+ combos winning, standalone losing** — hl_copy_trader is the differentiator, standalone bb_bounce without copy trader confirmation is bleeding

## Auto-Killed Signals (already disabled)
- range_breakout_short — AUTO_KILLED 2026-08-17 (0% WR,3T)
- return_exhaustion (bare) — auto_1hr 2026-08-18 (3T/0%WR)
- All combos in NEVER_REENABLE_FLAGS remain dead

## Summary
System is quiet with low volume. No kills needed this cycle. The biggest risk is return_exhaustion_long drifting toward kill threshold. Boosted signals (bb_bounce+hl_copy_trader, stop_hunt_reversal_long+, r2-trend-long4) are performing well — these should stay in hot-set.
