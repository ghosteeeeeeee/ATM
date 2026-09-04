# Signal Performance Report
**Generated:** 2026-09-04 11:09 UTC | **Period:** 6h + 24h

---

## KILLED (executed today — pre-report)
| Signal | Dir | WR | PnL | Trades | Action | Notes |
|--------|-----|-----|-----|--------|--------|-------|
| accel-300-v3-long+ | LONG | 53.3% | -$0.16 | 15 | KILLED by CEO 2026-09-04 | All trades from Sep 3 (before kill). Kill confirmed working. |
| accel-300-v3-short- | SHORT | 25.0% | -$0.26 | 4 | KILLED by AUTO_1HR 2026-09-04 | 3/4 ATR_SL hits. Kill confirmed working. |
| slow-grind-short | SHORT | 33.3% | -$0.81 | 15 (30d) | KILLED by CEO 2026-09-04 | ALL losers. NEVER_REENABLE. |
| bb-bounce-short | SHORT | 0.0% | -$0.39 | 2 | KILLED by AUTO_1HR 2026-09-03 | 2 consecutive losses. |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action | Notes |
|--------|-----|-----|-----|--------|--------|-------|
| bb-bounce-v2-long+ | LONG | 76.2% | +$0.68 | 21 | MONITOR — strong performer | 16W/5L, avg win +$0.11, avg loss -$0.11. R:R balanced. Distributed across 17 tokens. |
| ema300-dip | LONG | 68.8% | +$0.11 | 32 | MONITOR — consistent winner | 22W/10L. 100% WR on ALT(3T), POL(2T). Losers are small (-$0.10 to -$0.18). |
| continuation+ | LONG | 100% | +$0.18 | 2 | INSUFFICIENT — too few trades | 2W/0L. Need 5+ trades to evaluate. |

## LOSERS (watch list — enabled signals with negative PnL)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-short+ | SHORT | 0.0% | -$0.10 | 2 | INSUFFICIENT — 2 trades only. Below kill threshold. Watch. |

## WINNERS (enabled signals with positive PnL)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 76.2% | +$0.68 | 21 | Active, consistent |
| ema300-dip | LONG | 68.8% | +$0.11 | 32 | Active, high volume |
| continuation+ | LONG | 100% | +$0.18 | 2 | Insufficient sample |

## ISSUES
- **No signal inversions found** — all signals match expected directions.
- **accel-300-v3-long+ was still showing 15 trades in 24h** — investigation confirms ALL trades are from Sep 3 (before kill at Sep 4). Kill is working correctly, no new trades firing.
- **bb-bounce-v2-long+ has 5 small losers** (WLD, MON, SAND, FIL, SOL) — all -0.01 to -0.15. These are normal noise, not a pattern. 16 winners compensate.
- **ema300-dip losers are slightly larger** than winners (avg loss ~$0.14 vs avg win ~$0.07). Not critical at 68.8% WR but monitor R:R.
- **Most SHORT signals are dead or disabled** — system is running almost entirely LONG-biased. This is expected given the current market regime.

## ACTION TAKEN
- No new kills needed — all losers were already killed today.
- No new boosts needed — winners are already enabled and performing.
- Report generated for CEO kanban update.
