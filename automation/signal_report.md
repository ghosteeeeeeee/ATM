# Signal Performance Report
**Generated:** 2026-08-09 19:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 649 | **WR:** 44.7% | **PnL:** -14.09%
- **Date range:** 2026-07-29 → 2026-08-09

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb-bounce-short,hzscore- | SHORT | 3 | 0.0% | -0.97 | 12 | 58.3% | +1.43 | ENABLED |
| bb_bounce+,hzscore+ | LONG | — | —% | — | 5 | 60.0% | +0.25 | ENABLED |
| hzscore+,range_finder+ | LONG | 3 | 100.0% | +0.85 | 5 | 80.0% | +0.24 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

None found.

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[KEEP] 3 winning combos** — bb-bounce-short,hzsc, bb_bounce+,hzscore+, hzscore+,range_finde. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-09 | 28c6aee | signals: add range_breakout — breakout from tight ranges wit... |
| 2026-08-09 | 14c3b27 | signals: widen profit-monster trail — PM_TRAIL_ACTIVATE 0.25... |
| 2026-08-09 | a95ea3c | config: lower momentum_leaderboard MOVE_MIN 3.0%→1.0% (was t... |
| 2026-08-09 | 3422a08 | config: raise cut-loser T1 threshold to -0.75% (start cuttin... |
| 2026-08-09 | 0b7f3af | config: raise cut-loser T1 threshold to -0.5% (T1 starts lat... |
| 2026-08-09 | 2fcb232 | config: widen cut-loser trailing activation to -0.5% (from -... |
| 2026-08-09 | be9af28 | blacklist: AAVE, SKY, PNUT (worst 7d performers) |
| 2026-08-09 | 7aba5df | signals: kill vortex_break_long — 22.2% WR (9T 24h), -$0.18 ... |
| 2026-08-09 | 0ed1acf | CEO 2026-08-10: disable MA_100_CROSS_PLUS — losing 5T/24h, 2... |
| 2026-08-09 | 56a6fe6 | signals: add engulfing candle signal |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*