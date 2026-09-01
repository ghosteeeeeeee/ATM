# Signal Performance Report
**Generated:** 2026-09-01 17:03 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,808 | **WR:** 49.9% | **PnL:** -84.72%
- **Date range:** 2026-07-29 → 2026-09-01

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb-bounce-short | SHORT | — | —% | — | 5 | 80.0% | +0.26 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| accel-300-v2-long | LONG | 15 | 33.3% | -5.75 | ENABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] accel-300-v2-long LONG** — WR=33.3%, PnL=-5.75% over 15 trades. Monitor next cycle.
2. **[KEEP] 1 winning combos** — bb-bounce-short. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-01 | 0eb1465 | signals: remove MIN_BB_POS filter from r2_trend_long (was hu... |
| 2026-09-01 | d8781a4 | Config: remove ACE from LONG_BLACKLIST |
| 2026-09-01 | 0edf5ac | signals: re-enable accel_300_v2_long, fix protection flags |
| 2026-09-01 | 35eab5a | auto_1hr: Kill ACCEL_300_V2_LONG_ENABLED (18T/24h 27.8% WR -... |
| 2026-09-01 | 8edbddc | config: re-enable bb_bounce_long for testing |
| 2026-09-01 | 5086268 | CEO: CONF_FILTER_MIN=75 — blocks low-confidence noise (28.6%... |
| 2026-09-01 | 47cf180 | auto_1hr: Kill bb-bounce-long+ (0%WR 5T last hour, -/usr/bin... |
| 2026-09-01 | f675305 | memory: daily orchestrator run 2026-09-01 — accel-300-v2-lon... |
| 2026-09-01 | 375ca5a | signals: kill accel-300-v2-long — 29.4% WR, -$0.64 (24h), 17... |
| 2026-09-01 | a157210 | CEO: Fix range_reversion shadow mode bug + verify accel-300-... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*