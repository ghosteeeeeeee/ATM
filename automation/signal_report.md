# Signal Performance Report
**Generated:** 2026-08-09 13:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 636 | **WR:** 44.5% | **PnL:** -14.15%
- **Date range:** 2026-07-29 → 2026-08-09

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb-bounce-short,hzscore- | SHORT | — | —% | — | 9 | 77.8% | +2.40 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| bb_bounce+,hzscore+ | LONG | 4 | 50.0% | -0.73 | ENABLED | Needs more data |
| hzscore+,range_finder+ | LONG | 2 | 50.0% | -0.61 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] bb_bounce+,hzscore+ LONG** — WR=50.0%, PnL=-0.73% over 4 trades. Monitor next cycle.
2. **[WATCH] hzscore+,range_finder+ LONG** — WR=50.0%, PnL=-0.61% over 2 trades. Monitor next cycle.
3. **[KEEP] 1 winning combos** — bb-bounce-short,hzsc. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-09 | 7aba5df | signals: kill vortex_break_long — 22.2% WR (9T 24h), -$0.18 ... |
| 2026-08-09 | 0ed1acf | CEO 2026-08-10: disable MA_100_CROSS_PLUS — losing 5T/24h, 2... |
| 2026-08-09 | 56a6fe6 | signals: add engulfing candle signal |
| 2026-08-09 | e50164f | config: tighten PM_TRAIL_ACTIVATE_PCT 0.30→0.25 |
| 2026-08-09 | 2884d93 | CEO: Disabled MA_100_CROSS_MINUS_ENABLED, added regime filte... |
| 2026-08-08 | f5aa0d5 | signals: add return_exhaustion_short.py — SHORT-specific per... |
| 2026-08-08 | 8b8e345 | signals: add range_finder_short.py — SHORT-specific range fi... |
| 2026-08-08 | bb61874 | signals: add bb_bounce_short.py — SHORT-specific BB bounce w... |
| 2026-08-08 | 51754e3 | CEO: 24h +$0.13 (50% WR), 7d -$1.23. All fixes verified work... |
| 2026-08-08 | 16900d9 | signals: re-enable hzscore- with RS confluence boost |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*