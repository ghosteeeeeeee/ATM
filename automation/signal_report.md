# Signal Performance Report
**Generated:** 2026-08-15 05:02 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,007 | **WR:** 46.8% | **PnL:** -36.71%
- **Date range:** 2026-07-29 → 2026-08-15

---

## WINNERS (WR > 55%, PnL > 0)

None found.

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| mover+ | LONG | — | —% | — | 6 | 16.7% | -3.40 | ❓ | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| wave_catcher+ | LONG | 8 | 37.5% | -3.27 | DISABLED | Borderline |
| range_finder+ | LONG | 9 | 33.3% | -2.33 | ENABLED | Borderline |
| r2-trend-long4 | LONG | 3 | 33.3% | -1.16 | ❓ | Needs more data |
| wave_catcher- | SHORT | 4 | 50.0% | -0.86 | DISABLED | Needs more data |
| r2-trend-long5 | LONG | 2 | 50.0% | -0.23 | ❓ | Needs more data |
| ct-hot+,mover+ | LONG | 2 | 50.0% | +0.66 | ❓ | Needs more data |
| wave_catcher+ | SHORT | 6 | 50.0% | +0.79 | DISABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] mover+ LONG** — WR=16.7%, PnL=-3.40% over 6 trades (24h).
2. **[WATCH] wave_catcher+ LONG** — WR=37.5%, PnL=-3.27% over 8 trades. Monitor next cycle.
3. **[WATCH] range_finder+ LONG** — WR=33.3%, PnL=-2.33% over 9 trades. Monitor next cycle.
4. **[WATCH] r2-trend-long4 LONG** — WR=33.3%, PnL=-1.16% over 3 trades. Monitor next cycle.
5. **[WATCH] wave_catcher- SHORT** — WR=50.0%, PnL=-0.86% over 4 trades. Monitor next cycle.
6. **[WATCH] r2-trend-long5 LONG** — WR=50.0%, PnL=-0.23% over 2 trades. Monitor next cycle.
7. **[WATCH] ct-hot+,mover+ LONG** — WR=50.0%, PnL=+0.66% over 2 trades. Monitor next cycle.
8. **[WATCH] wave_catcher+ SHORT** — WR=50.0%, PnL=+0.79% over 6 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-15 | 505c742 | CEO: WIDENED PM_TRAIL_DISTANCE_PCT 0.40%→0.60% — R:R inverte... |
| 2026-08-15 | 8e923cb | Daily trading system update (2026-08-15) |
| 2026-08-15 | c095ba1 | CEO: ATR_TP_K_MULT 2.0→2.5 — fix inverted R:R (0.60:1→0.75:1... |
| 2026-08-15 | 12b7e58 | config: enable range_finder +/- for testing |
| 2026-08-15 | 8da5f4a | CEO: LOWERED TRAILING_ACTIVATION_PCT 0.80%→0.60% — fix inver... |
| 2026-08-15 | 7acb03a | signals: kill wave_catcher- SHORT — 25% WR, -/usr/bin/bash.0... |
| 2026-08-15 | c5be3a2 | CEO: DISABLED PM_TRAIL_ENABLED — cuts winners at 0.39% while... |
| 2026-08-14 | ea44ca0 | CEO: PM_TRAIL loosen (0.40%→0.60% activate, 0.15%→0.40% dist... |
| 2026-08-14 | 6b17d79 | fix: add mover+/- to STANDALONE_BYPASS and volatility gate N... |
| 2026-08-14 | 35062dc | config: tighten PM trailing + ATR accel params (CEO locked) |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*