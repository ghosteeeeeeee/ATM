# Signal Performance Report
**Generated:** 2026-08-12 13:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 820 | **WR:** 45.2% | **PnL:** -18.68%
- **Date range:** 2026-07-29 → 2026-08-12

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce+ | LONG | — | —% | — | 19 | 57.9% | +1.55 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| range_breakout+ | LONG | 2 | 0.0% | -1.61 | 8 | 25.0% | -4.02 | DISABLED | **DISABLE** |
| trend_momentum_near_sma+ | LONG | — | —% | — | 6 | 16.7% | -2.93 | DISABLED | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| range_breakout- | SHORT | 16 | 50.0% | -1.39 | ENABLED | Borderline |
| hzscore+ | LONG | 12 | 41.7% | -1.09 | ENABLED | Borderline |
| accel-300- | SHORT | 3 | 33.3% | -0.60 | ENABLED | Needs more data |
| hzscore- | SHORT | 16 | 50.0% | -0.39 | ENABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] range_breakout+ LONG** — WR=25.0%, PnL=-4.02% over 8 trades (24h).
2. **[DISABLE] trend_momentum_near_sma+ LONG** — WR=16.7%, PnL=-2.93% over 6 trades (24h).
3. **[WATCH] range_breakout- SHORT** — WR=50.0%, PnL=-1.39% over 16 trades. Monitor next cycle.
4. **[WATCH] hzscore+ LONG** — WR=41.7%, PnL=-1.09% over 12 trades. Monitor next cycle.
5. **[WATCH] accel-300- SHORT** — WR=33.3%, PnL=-0.60% over 3 trades. Monitor next cycle.
6. **[WATCH] hzscore- SHORT** — WR=50.0%, PnL=-0.39% over 16 trades. Monitor next cycle.
7. **[KEEP] 1 winning combos** — bb_bounce+. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-12 | 124def0 | CEO: restrict hzscore to combo-only (standalone bleeding 36.... |
| 2026-08-12 | 5a72c64 | CEO: Disable range_breakout+ LONG (7T -$0.30 28.6% WR bleed)... |
| 2026-08-12 | f53d4ac | signals: bump RANGE_BREAKOUT_CONF_BASE 65→70 to filter weak ... |
| 2026-08-12 | 446e8ed | signals: fix _sqlite3 NameError in range_breakout_short spik... |
| 2026-08-12 | dcb3090 | signals: add range_breakout_short (SHORT-specific with veloc... |
| 2026-08-12 | 7da6787 | signals: remove dead market filter (velocity filter already ... |
| 2026-08-12 | 593e67a | signals: add dead market filter to range_breakout (min 0.2% ... |
| 2026-08-12 | e3010b3 | CEO: NO TRADING CHANGES — 2026-08-14 16:00 UTC |
| 2026-08-12 | ba71af1 | signals: tighten BB_TOUCH_PCT 0.20->0.15, add staleness cons... |
| 2026-08-12 | f8a3ff3 | signals: tighten BB_TOUCH_PCT 0.20->0.15, add staleness cons... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*