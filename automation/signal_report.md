# Signal Performance Report
**Generated:** 2026-08-10 13:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 697 | **WR:** 45.5% | **PnL:** -7.56%
- **Date range:** 2026-07-29 → 2026-08-10

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce+,hzscore+ | LONG | 3 | 66.7% | +0.12 | 16 | 68.8% | +5.90 | ENABLED |
| hzscore+,range_finder+ | LONG | — | —% | — | 5 | 80.0% | +0.77 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| bb-bounce-short,hzscore- | SHORT | 6 | 33.3% | -0.72 | ENABLED | Borderline |
| continuation+,hzscore+ | LONG | 3 | 33.3% | +1.67 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] bb-bounce-short,hzscore- SHORT** — WR=33.3%, PnL=-0.72% over 6 trades. Monitor next cycle.
2. **[WATCH] continuation+,hzscore+ LONG** — WR=33.3%, PnL=+1.67% over 3 trades. Monitor next cycle.
3. **[KEEP] 2 winning combos** — bb_bounce+,hzscore+, hzscore+,range_finde. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-10 | 3a0fb69 | Daily trading system update (2026-08-10) |
| 2026-08-10 | 5a2429c | signals: relax SHORT thresholds to balance LONG/SHORT flow |
| 2026-08-10 | dbea2fa | signals: re-enable TL_BREAK and VORTEX_BREAK SHORT signals |
| 2026-08-10 | c4572eb | memory: bug_hunter audit of Hebbian fix + CEO acknowledgment |
| 2026-08-09 | 60df870 | config: tune range_breakout params — retest 0.3→0.2, BB peri... |
| 2026-08-09 | b078c58 | CEO 2026-08-09 21:50 review: NO CHANGES - 8th green day, 24h... |
| 2026-08-09 | 33b6670 | signals: add VEL 15m velocity gate to mean-reversion signals |
| 2026-08-09 | 28c6aee | signals: add range_breakout — breakout from tight ranges wit... |
| 2026-08-09 | 14c3b27 | signals: widen profit-monster trail — PM_TRAIL_ACTIVATE 0.25... |
| 2026-08-09 | a95ea3c | config: lower momentum_leaderboard MOVE_MIN 3.0%→1.0% (was t... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*