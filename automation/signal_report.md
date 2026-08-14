# Signal Performance Report
**Generated:** 2026-08-14 01:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 918 | **WR:** 46.3% | **PnL:** -27.53%
- **Date range:** 2026-07-29 → 2026-08-14

---

## WINNERS (WR > 55%, PnL > 0)

None found.

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| range_breakout_short | SHORT | — | —% | — | 10 | 20.0% | -5.05 | DISABLED | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| accel-300- | SHORT | 9 | 44.4% | -3.33 | DISABLED | Borderline |
| continuation-,hzscore- | SHORT | 3 | 33.3% | -2.41 | DISABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

| Signal | Dir | Last WR | Last PnL | Recommendation |
|--------|-----|---------|----------|----------------|
| hzscore- | SHORT | 56.2% | -0.77 | **WATCH** — re-enable candidate |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] range_breakout_short SHORT** — WR=20.0%, PnL=-5.05% over 10 trades (24h).
2. **[WATCH] accel-300- SHORT** — WR=44.4%, PnL=-3.33% over 9 trades. Monitor next cycle.
3. **[WATCH] continuation-,hzscore- SHORT** — WR=33.3%, PnL=-2.41% over 3 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-13 | e0e2bd2 | config: relax slope filter 0.001→0.0005 (signal starvation) |
| 2026-08-13 | add0d9f | CEO: Disabled hzscore- standalone SHORT (inverted R:R) |
| 2026-08-13 | 5224237 | fix: profit_monster bug fixes from bug_hunter audit |
| 2026-08-13 | 1781f45 | CEO: DISABLED RANGE_BREAKOUT_SHORT — 24h 20% WR flip, -/usr/... |
| 2026-08-13 | a9a1696 | CEO: verified run 2026-08-13 21:49 UTC — NO CHANGES, flat sy... |
| 2026-08-13 | 473b4ed | feat: r2_trend_long tuning — filters for stale/overbought/ex... |
| 2026-08-13 | eab7960 | fix: add both r2-trend-long and r2l-long to STANDALONE_BYPAS... |
| 2026-08-13 | 3dde6ff | fix: r2_trend_long source string mismatch with STANDALONE_BY... |
| 2026-08-13 | 81cc8b5 | config: add r2_trend_long to STANDALONE_BYPASS_SIGNALS |
| 2026-08-13 | 4601d78 | signals: add r2_trend_long — R² trend confirmation for LONG ... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*