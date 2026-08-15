# Signal Performance Report
**Generated:** 2026-08-15 01:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 994 | **WR:** 47.0% | **PnL:** -33.61%
- **Date range:** 2026-07-29 → 2026-08-15

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| r2-trend-long2 | LONG | 3 | 66.7% | +0.74 | 16 | 62.5% | +1.24 | ❓ |

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| mover+ | LONG | — | —% | — | 7 | 28.6% | -3.06 | ❓ | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| wave_catcher+ | LONG | 8 | 37.5% | -3.27 | DISABLED | Borderline |
| wave_catcher- | SHORT | 4 | 50.0% | -0.86 | DISABLED | Needs more data |
| range_breakout_short | SHORT | 2 | 50.0% | -0.65 | DISABLED | Needs more data |
| r2-trend-long4 | LONG | 2 | 50.0% | -0.42 | ❓ | Needs more data |
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

1. **[DISABLE] mover+ LONG** — WR=28.6%, PnL=-3.06% over 7 trades (24h).
2. **[WATCH] wave_catcher+ LONG** — WR=37.5%, PnL=-3.27% over 8 trades. Monitor next cycle.
3. **[WATCH] wave_catcher- SHORT** — WR=50.0%, PnL=-0.86% over 4 trades. Monitor next cycle.
4. **[WATCH] range_breakout_short SHORT** — WR=50.0%, PnL=-0.65% over 2 trades. Monitor next cycle.
5. **[WATCH] r2-trend-long4 LONG** — WR=50.0%, PnL=-0.42% over 2 trades. Monitor next cycle.
6. **[WATCH] r2-trend-long5 LONG** — WR=50.0%, PnL=-0.23% over 2 trades. Monitor next cycle.
7. **[WATCH] ct-hot+,mover+ LONG** — WR=50.0%, PnL=+0.66% over 2 trades. Monitor next cycle.
8. **[WATCH] wave_catcher+ SHORT** — WR=50.0%, PnL=+0.79% over 6 trades. Monitor next cycle.
9. **[KEEP] 1 winning combos** — r2-trend-long2. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-15 | 7acb03a | signals: kill wave_catcher- SHORT — 25% WR, -/usr/bin/bash.0... |
| 2026-08-15 | c5be3a2 | CEO: DISABLED PM_TRAIL_ENABLED — cuts winners at 0.39% while... |
| 2026-08-14 | ea44ca0 | CEO: PM_TRAIL loosen (0.40%→0.60% activate, 0.15%→0.40% dist... |
| 2026-08-14 | 6b17d79 | fix: add mover+/- to STANDALONE_BYPASS and volatility gate N... |
| 2026-08-14 | 35062dc | config: tighten PM trailing + ATR accel params (CEO locked) |
| 2026-08-14 | 95a9e4c | CEO: DISABLED RANGE_BREAKOUT_SHORT_ENABLED — 13T 48h 23.1% W... |
| 2026-08-14 | b7c8d47 | fix: wave_catcher_short — fix source name, re-enable, update... |
| 2026-08-14 | c7eade8 | signals: rename r2_trend to r2_trend_short, add filters from... |
| 2026-08-14 | 2c7a7c2 | CEO: DISABLED WAVE_CATCHER_ENABLED=False — master flag re-en... |
| 2026-08-14 | 420de56 | signals: add r2_trend- to STANDALONE_BYPASS, source weights,... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*