# Signal Performance Report
**Generated:** 2026-08-08 01:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 557 | **WR:** 43.3% | **PnL:** -18.84%
- **Date range:** 2026-07-29 → 2026-08-08

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce+,range_finder+ | LONG | 3 | 100.0% | +1.55 | 7 | 85.7% | +1.46 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| bb_bounce,ma100-cross | LONG | 7 | 42.9% | -1.33 | ENABLED | Borderline |
| ma100-cross,range_finder | SHORT | 3 | 33.3% | -0.31 | ❓ | Needs more data |
| ma100-cross,vortex_break_long | LONG | 2 | 50.0% | -0.13 | ❓ | Needs more data |
| ma100-cross-,vortex_break_short | SHORT | 2 | 50.0% | -0.10 | ❓ | Needs more data |
| bb_bounce,range_finder | LONG | 7 | 42.9% | -0.00 | ENABLED | Borderline |
| bb_bounce+,ma100-cross+ | LONG | 2 | 50.0% | +0.07 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] bb_bounce,ma100-cross LONG** — WR=42.9%, PnL=-1.33% over 7 trades. Monitor next cycle.
2. **[WATCH] ma100-cross,range_finder SHORT** — WR=33.3%, PnL=-0.31% over 3 trades. Monitor next cycle.
3. **[WATCH] ma100-cross,vortex_break_long LONG** — WR=50.0%, PnL=-0.13% over 2 trades. Monitor next cycle.
4. **[WATCH] ma100-cross-,vortex_break_short SHORT** — WR=50.0%, PnL=-0.10% over 2 trades. Monitor next cycle.
5. **[WATCH] bb_bounce,range_finder LONG** — WR=42.9%, PnL=-0.00% over 7 trades. Monitor next cycle.
6. **[WATCH] bb_bounce+,ma100-cross+ LONG** — WR=50.0%, PnL=+0.07% over 2 trades. Monitor next cycle.
7. **[KEEP] 1 winning combos** — bb_bounce+,range_fin. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-08 | cdeeeb7 | signals: add continuation — re-entry after profitable close |
| 2026-08-08 | 2960004 | fix: momentum_leaderboard thresholds too loose — picking up ... |
| 2026-08-07 | e55b6c4 | signals: self_learner auto-tunes combo weights |
| 2026-08-07 | 757c5c3 | signals: boost winning combos, suppress losers (7d data) |
| 2026-08-07 | 566a2f9 | Daily Orchestrator: disable bb_bounce SHORT, investigate hot... |
| 2026-08-07 | 159c43c | signals: CEO kills TL_BREAK, ZSCORE_RISING, HZSCORE_MINUS pe... |
| 2026-08-07 | b708d45 | signals: momentum_leaderboard overextended→fade + all params... |
| 2026-08-07 | 76be66a | signals: enable momentum_leaderboard for paper testing |
| 2026-08-07 | bc5f076 | signals: add momentum_leaderboard — top movers signal |
| 2026-08-07 | 2d684fd | signals: add +/- kill-switch variants to all signals missing... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*