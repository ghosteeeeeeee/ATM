# Signal Performance Report
**Generated:** 2026-08-13 07:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 887 | **WR:** 46.1% | **PnL:** -23.03%
- **Date range:** 2026-07-29 → 2026-08-13

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| range_breakout_short | SHORT | 3 | 0.0% | -2.87 | 17 | 58.8% | +1.17 | ENABLED |
| hzscore- | SHORT | 2 | 100.0% | +0.69 | 7 | 57.1% | +0.54 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| range_breakout- | SHORT | 15 | 33.3% | -4.88 | DISABLED | Borderline |
| continuation-,hzscore- | SHORT | 2 | 50.0% | -0.76 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

| Signal | Dir | Last WR | Last PnL | Recommendation |
|--------|-----|---------|----------|----------------|
| accel-300- | SHORT | 55.3% | -4.71 | **WATCH** — re-enable candidate |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] range_breakout- SHORT** — WR=33.3%, PnL=-4.88% over 15 trades. Monitor next cycle.
2. **[WATCH] continuation-,hzscore- SHORT** — WR=50.0%, PnL=-0.76% over 2 trades. Monitor next cycle.
3. **[KEEP] 2 winning combos** — range_breakout_short, hzscore-. LONG side dominant.

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