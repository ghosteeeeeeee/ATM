# Signal Performance Report
**Generated:** 2026-08-13 13:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 898 | **WR:** 46.3% | **PnL:** -22.95%
- **Date range:** 2026-07-29 → 2026-08-13

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| hzscore- | SHORT | 4 | 50.0% | -0.26 | 6 | 66.7% | +0.43 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| range_breakout- | SHORT | 4 | 50.0% | -0.53 | DISABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

| Signal | Dir | Last WR | Last PnL | Recommendation |
|--------|-----|---------|----------|----------------|
| accel-300- | SHORT | 56.8% | -4.04 | **WATCH** — re-enable candidate |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] range_breakout- SHORT** — WR=50.0%, PnL=-0.53% over 4 trades. Monitor next cycle.
2. **[KEEP] 1 winning combos** — hzscore-. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-13 | 07b84a9 | auto_1hr: disable ACCEL_300_ENABLED — 19T today 36.8% WR, 12... |
| 2026-08-13 | 3469239 | CEO: 2026-08-13 verified, no changes — legacy clearing, stab... |
| 2026-08-13 | 2dbd8e9 | Daily trading system update (2026-08-13) |
| 2026-08-13 | e6a05d0 | CEO: disable ACCEL_300_MINUS_ENABLED (inverted R:R bleeding ... |
| 2026-08-13 | de9add5 | fix: add bb-bounce-short to solo bypass (hyphen/underscore m... |
| 2026-08-13 | cff29ab | signals: disable ATR floor filter — backtest shows ATR overl... |
| 2026-08-13 | ef91324 | signals: accel-300- ATR floor filter (0.02% min, zero winner... |
| 2026-08-13 | 9a9ad46 | CEO: NO TRADING CHANGES — verified DB 24h 107T -/usr/bin/bas... |
| 2026-08-13 | 56c92ba | signals: accel-300- slope filter 0.0005→0.001 (CEO approved) |
| 2026-08-13 | 7e2a49f | Weather Vane v2: velocity tiers + integral long-window catch |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*