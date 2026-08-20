# Daily Orchestrator Report — 2026-08-20

## Pipeline Status
- **24h:** 23T | 56.5% WR | -$0.40 (quiet day, SHORT legacy clearing)
- **7d:** 271T | 50.6% WR | -$1.57
- **Open:** 0 (clean)
- **Regime:** LONG_BIAS (macro gate)

## Exit Breakdown (24h)
| Exit Type | Trades | WR | PnL |
|-----------|--------|-----|-----|
| profit-monster-trail | 13 | 92.3% | +$0.68 |
| atr_sl_hit | 9 | 0% | -$1.09 |
| regime_bear_flip | 1 | 100% | +$0.01 |

## ATR_SL Daily Trend
| Date | Total | ATR_SL | Ratio | PnL |
|------|-------|--------|-------|-----|
| Aug 14 | 80 | 28 | 35% | -$0.56 |
| Aug 15 | 54 | 20 | 37% | +$0.02 |
| Aug 16 | 43 | 18 | 42% | -$0.49 |
| Aug 17 | 34 | 9 | 26.5% | +$0.37 |
| Aug 18 | 15 | 8 | 53% | -$0.38 |
| Aug 19 | 26 | 7 | 27% | +$0.42 |
| Aug 20 | 15 | 7 | 47% | -$0.61 |

## Signal Performance (24h)
| Signal | Trades | WR | PnL | Notes |
|--------|--------|-----|-----|-------|
| r2-trend-long6 | 3 | 100% | +$0.25 | Best performer |
| stop_hunt_reversal_long+ | 4 | 75% | +$0.13 | Solid |
| r2-trend-long3 | 7 | 71.4% | -$0.02 | Inverted R:R (avg_win $0.04, avg_loss $0.12) |
| r2-trend-short2 | 3 | 0% | -$0.23 | Legacy pre-kill |

## Signal Performance (7d)
| Signal | Trades | WR | PnL | R:R | Status |
|--------|--------|-----|-----|-----|--------|
| r2-trend-long6 | 7 | 100% | +$0.45 | ∞ | STRONG |
| bb_bounce+,hl_copy_trader | 7 | 57% | +$0.30 | 3.0 | STRONG |
| r2-trend-long2 | 17 | 65% | +$0.19 | 0.84 | OK |
| r2-trend-long4 | 17 | 65% | +$0.10 | 0.68 | OK |
| stop_hunt_reversal_long+ | 10 | 60% | -$0.04 | 0.60 | BORDERLINE |
| r2-trend-long3 | 33 | 57.6% | -$0.23 | 0.58 | INVERTED R:R |
| mover+ | 7 | 29% | -$0.15 | — | DEAD |
| ct-hot+ | 33 | 42% | -$0.42 | 0.89 | DEAD |

## Team Activity
- **health_monitor:** All systems nominal, no alerts, 33 timers active, no phantom trades
- **auto_1hr:** No changes needed in last 24h — system within parameters
- **signal_reporter:** Flagged r2-trend-long3 inverted R:R, r2-trend-short2 watching for kill

## Implemented Today
None — system operating within parameters, no changes needed.

## Critical Issues
None.

## Monitoring Items
1. **MIN_PRE_MOVE 0.3 eval** — r2-trend-long3: 48h 8T 75% WR $0.00. Eval extended to Aug 23.
2. **PM_TRAIL edge** — 144T/7d 83.3% WR +$5.43. Must hold >80%.
3. **ATR_SL count** — 7T/day (historic low, 75% reduction from 28 peak). SL floor fix working.
4. **stop_hunt_reversal_long+** — 10T/7d 60% -$0.04 (break-even, R:R 0.60). Watch for degradation.

## Next Actions
1. Monitor MIN_PRE_MOVE 0.3 eval through Aug 23
2. Monitor PM_TRAIL edge — must stay >80% WR
3. Monitor ATR_SL count — should stay <10/day
4. Monitor stop_hunt_reversal_long+ for degradation
