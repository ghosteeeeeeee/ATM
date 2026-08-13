# Signal Performance Report
**Generated:** 2026-08-13 14:00 UTC | **Period:** Last 6h + 24h + 7d

## Overall Stats
- **6h:** 11 trades, 63.6% WR, +$0.01 PnL
- **24h:** 80 trades, 56.3% WR, -$0.23 PnL
- **7d:** 439 trades, 50.8% WR, -$0.74 PnL
- **Open trades:** 3 (all range_breakout_short SHORT)

---

## KILLED (executed today or already disabled)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| accel-300- | SHORT | 56.8% | -$0.23 | 37 (24h) | Already killed CEO 2026-08-13 — inverted R:R |
| accel-300 (base) | SHORT | — | — | — | Already killed 2026-08-13 — 36.8% WR |
| range_breakout+ | LONG | 25.0% | -$0.41 | 8 (7d) | Already killed CEO 2026-08-12 |
| trend_momentum_near_sma+ | LONG | 16.7% | -$0.37 | 6 (7d) | Already killed 2026-08-12 |
| hzscore+ | LONG | 41.7% | -$0.12 | 12 (7d) | AUTO-ROTATED 2026-08-13 |

**No new kills needed.** All losers identified in this cycle were already disabled.

---

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+,range_finder+ | LONG | 58.5% | +$0.71 | 53 (7d) | Top performer — hot-set priority |
| bb_bounce+,hzscore+ | LONG | 50.0% | +$0.22 | 34 (7d) | Solid volume + positive PnL |
| bb_bounce+ | LONG | 60.0% | +$0.19 | 20 (7d) | Consistent winner |
| bb-bounce-short,hzscore- | SHORT | 61.1% | +$0.14 | 18 (7d) | Best SHORT combo |
| hzscore+,mover+ | LONG | 80.0% | +$0.17 | 5 (7d) | High WR, boost if volume holds |

---

## LOSERS (watch list — already disabled or borderline)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| range_breakout- | SHORT | 45.0% | -$0.12 | 20 (7d) | DISABLED — use range_breakout_short instead |
| hzscore+ | LONG | 41.7% | -$0.12 | 12 (7d) | AUTO-ROTATED — borderline |
| ma100-cross,return_exhaustion- | SHORT | 40.0% | -$0.22 | 5 (7d) | Low sample, monitor |
| hzscore-,return_exhaustion- | SHORT | 33.3% | -$0.21 | 6 (7d) | Borderline kill — 33% WR but small loss |
| ma100-cross-,range_finder- | SHORT | 40.0% | -$0.19 | 5 (7d) | Low sample, monitor |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+,range_finder+ | LONG | 58.5% | +$0.71 | 53 | ENABLED — top performer |
| bb_bounce+,hzscore+ | LONG | 50.0% | +$0.22 | 34 | ENABLED |
| bb_bounce+ | LONG | 60.0% | +$0.19 | 20 | ENABLED |
| bb-bounce-short,hzscore- | SHORT | 61.1% | +$0.14 | 18 | ENABLED |
| hzscore+,mover+ | LONG | 80.0% | +$0.17 | 5 | ENABLED |
| continuation+,hzscore+ | LONG | 37.5% | +$0.16 | 8 | ENABLED — low WR but positive PnL |
| range_breakout_short | SHORT | 55.0% | +$0.10 | 20 | ENABLED |
| hzscore-,range_breakout- | SHORT | 75.0% | +$0.12 | 4 | ENABLED |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## SYSTEM STATUS

- **LIVE_TRADING_ENABLED:** True
- **Kill switch (runtime):** {"live_trading": true}
- **6h net:** +$0.01 (breakeven)
- **24h net:** -$0.23 (slight loss)
- **7d net:** -$0.74 (slight loss)

**Assessment:** System is running near breakeven. No emergency kills needed. The losers from last week are already disabled. The bb_bounce+ family continues to be the strongest signal group. SHORT side dominated by bb-bounce-short,hzscore- and range_breakout_short.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-13 | 2dbd8e9 | Daily trading system update (2026-08-13) |
| 2026-08-13 | e6a05d0 | CEO: disable ACCEL_300_MINUS_ENABLED (inverted R:R bleeding ... |
| 2026-08-13 | de9add5 | fix: add bb-bounce-short to solo bypass (hyphen/underscore m... |
| 2026-08-13 | cff29ab | signals: disable ATR floor filter — backtest shows ATR overl... |
| 2026-08-13 | ef91324 | signals: accel-300- ATR floor filter (0.02% min, zero winner... |
| 2026-08-13 | 9a9ad46 | CEO: NO TRADING CHANGES — verified DB 24h 107T -/usr/bin/bas... |
| 2026-08-13 | 56c92ba | signals: accel-300- slope filter 0.0005→0.001 (CEO approved) |
| 2026-08-13 | 7e2a49f | Weather Vane v2: velocity tiers + integral long-window catch |
| 2026-08-13 | b2f3893 | CEO: no trading changes, verified flat day |
| 2026-08-13 | dcdf4c1 | feat: Weather Vane v2 — hysteresis + off-course alarm |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
