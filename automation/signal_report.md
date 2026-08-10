# Signal Performance Report
**Generated:** 2026-08-10 01:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 667 | **WR:** 45.4% | **PnL:** -8.66%
- **Date range:** 2026-07-29 → 2026-08-10

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce+,hzscore+ | LONG | 7 | 71.4% | +3.72 | 9 | 77.8% | +5.04 | ENABLED |
| bb_bounce+,range_finder+ | LONG | 4 | 75.0% | +0.63 | 23 | 56.5% | +1.65 | ENABLED |
| hzscore+,range_finder+ | LONG | — | —% | — | 5 | 80.0% | +0.23 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| bb-bounce-short,hl_copy_trader | SHORT | 3 | 33.3% | +0.04 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] bb-bounce-short,hl_copy_trader SHORT** — WR=33.3%, PnL=+0.04% over 3 trades. Monitor next cycle.
2. **[KEEP] 3 winning combos** — bb_bounce+,hzscore+, bb_bounce+,range_fin, hzscore+,range_finde. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-09 | 60df870 | config: tune range_breakout params — retest 0.3→0.2, BB peri... |
| 2026-08-09 | b078c58 | CEO 2026-08-09 21:50 review: NO CHANGES - 8th green day, 24h... |
| 2026-08-09 | 33b6670 | signals: add VEL 15m velocity gate to mean-reversion signals |
| 2026-08-09 | 28c6aee | signals: add range_breakout — breakout from tight ranges wit... |
| 2026-08-09 | 14c3b27 | signals: widen profit-monster trail — PM_TRAIL_ACTIVATE 0.25... |
| 2026-08-09 | a95ea3c | config: lower momentum_leaderboard MOVE_MIN 3.0%→1.0% (was t... |
| 2026-08-09 | 3422a08 | config: raise cut-loser T1 threshold to -0.75% (start cuttin... |
| 2026-08-09 | 0b7f3af | config: raise cut-loser T1 threshold to -0.5% (T1 starts lat... |
| 2026-08-09 | 2fcb232 | config: widen cut-loser trailing activation to -0.5% (from -... |
| 2026-08-09 | be9af28 | blacklist: AAVE, SKY, PNUT (worst 7d performers) |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*