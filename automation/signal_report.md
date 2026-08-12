# Signal Performance Report
**Generated:** 2026-08-12 01:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 770 | **WR:** 45.2% | **PnL:** -12.34%
- **Date range:** 2026-07-29 → 2026-08-12

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce+ | LONG | 14 | 57.1% | +0.73 | 14 | 57.1% | +0.73 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| trend_momentum_near_sma+ | LONG | 2 | 0.0% | -0.46 | 5 | 0.0% | -3.23 | DISABLED | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| hzscore- | SHORT | 4 | 50.0% | -0.23 | ENABLED | Needs more data |
| bb_bounce+,hzscore+ | LONG | 4 | 50.0% | +0.00 | ENABLED | Needs more data |
| hzscore+ | LONG | 8 | 50.0% | +0.39 | ENABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] trend_momentum_near_sma+ LONG** — WR=0.0%, PnL=-3.23% over 5 trades (24h).
2. **[WATCH] hzscore- SHORT** — WR=50.0%, PnL=-0.23% over 4 trades. Monitor next cycle.
3. **[WATCH] bb_bounce+,hzscore+ LONG** — WR=50.0%, PnL=+0.00% over 4 trades. Monitor next cycle.
4. **[WATCH] hzscore+ LONG** — WR=50.0%, PnL=+0.39% over 8 trades. Monitor next cycle.
5. **[KEEP] 1 winning combos** — bb_bounce+. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-12 | 5d7b527 | signals: kill trend_momentum_near_sma PLUS/MINUS flags — bas... |
| 2026-08-12 | 7f9339f | config: increase range_breakout and accel_300 confidence to ... |
| 2026-08-12 | 6986ab4 | post-change: accel-300 re-enable + confidence boost + bug fi... |
| 2026-08-12 | bea53f1 | config: increase accel_300 confidence range to compete with ... |
| 2026-08-12 | 9576091 | config: re-enable accel_300- SHORT + add to bypass |
| 2026-08-12 | 3745fe8 | post-change: kanban + docstring fix for bypass centralizatio... |
| 2026-08-12 | 397f9c7 | config: add continuation_long and continuation_short to STAN... |
| 2026-08-12 | 5de699a | refactor: centralize bypass list into hermes_constants.STAND... |
| 2026-08-11 | de10909 | config: disable trailing cut_loser (CL_TRAIL_ENABLED=False) |
| 2026-08-11 | bc4ade7 | config: widen cut_loser tiers — T1 1-2%, T2 2-5% |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*