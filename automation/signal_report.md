# Signal Performance Report
**Generated:** 2026-08-12 19:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 843 | **WR:** 46.0% | **PnL:** -13.59%
- **Date range:** 2026-07-29 → 2026-08-12

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| accel-300- | SHORT | 12 | 83.3% | +4.19 | 15 | 73.3% | +3.59 | ENABLED |
| bb_bounce+ | LONG | — | —% | — | 19 | 57.9% | +1.55 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| range_breakout+ | LONG | — | —% | — | 8 | 25.0% | -4.02 | DISABLED | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| range_breakout- | SHORT | 20 | 50.0% | -1.92 | DISABLED | Borderline |
| hzscore- | SHORT | 14 | 50.0% | -0.58 | ENABLED | Borderline |
| trend_momentum_near_sma+ | LONG | 3 | 33.3% | -0.16 | DISABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] range_breakout+ LONG** — WR=25.0%, PnL=-4.02% over 8 trades (24h).
2. **[WATCH] range_breakout- SHORT** — WR=50.0%, PnL=-1.92% over 20 trades. Monitor next cycle.
3. **[WATCH] hzscore- SHORT** — WR=50.0%, PnL=-0.58% over 14 trades. Monitor next cycle.
4. **[WATCH] trend_momentum_near_sma+ LONG** — WR=33.3%, PnL=-0.16% over 3 trades. Monitor next cycle.
5. **[KEEP] 2 winning combos** — accel-300-, bb_bounce+. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-12 | 8d36599 | CEO: 2026-08-12 18:49 UTC — NO CHANGES. Verified 24h 98T -/u... |
| 2026-08-12 | 7acf1a3 | hermes_constants: fix ATR_K threshold comments (3% → 1.5%) |
| 2026-08-12 | 1534a8b | CEO: widen trailing stop distance 0.60%→0.80%, activation 0.... |
| 2026-08-12 | 1e47094 | CEO: disable RANGE_BREAKOUT_PLUS_ENABLED (8T 25% WR -$0.41 2... |
| 2026-08-12 | de0ff90 | signals: disable RANGE_BREAKOUT_MINUS_ENABLED (SHORT now fro... |
| 2026-08-12 | 124def0 | CEO: restrict hzscore to combo-only (standalone bleeding 36.... |
| 2026-08-12 | 5a72c64 | CEO: Disable range_breakout+ LONG (7T -$0.30 28.6% WR bleed)... |
| 2026-08-12 | f53d4ac | signals: bump RANGE_BREAKOUT_CONF_BASE 65→70 to filter weak ... |
| 2026-08-12 | 446e8ed | signals: fix _sqlite3 NameError in range_breakout_short spik... |
| 2026-08-12 | dcb3090 | signals: add range_breakout_short (SHORT-specific with veloc... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*