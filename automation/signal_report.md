# Signal Performance Report
**Generated:** 2026-08-12 18:00 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 820 | **WR:** 45.2% | **PnL:** -18.68%
- **Date range:** 2026-07-29 → 2026-08-12

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| accel-300- | SHORT | 12 | 83.3% | +0.43 | 15 | 73.3% | +0.36 | ENABLED |
| bb_bounce+ | LONG | — | —% | — | 19 | 57.9% | +0.16 | ENABLED |
| range_breakout_short | SHORT | 3 | 100% | +0.11 | 3 | 100% | +0.11 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -0.10)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| range_breakout+ | LONG | — | —% | — | 8 | 25.0% | -0.41 | DISABLED | Already killed |
| hzscore+ | LONG | — | —% | — | 7 | 28.6% | -0.11 | DISABLED | Already killed |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| range_breakout- | SHORT | 20 | 45.0% | -0.12 | ENABLED | Borderline — near breakeven |
| hzscore- | SHORT | 14 | 50.0% | -0.05 | ENABLED | Near breakeven |
| trend_momentum_near_sma+ | LONG | 3 | 33.3% | -0.02 | ENABLED | Insufficient data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None. Top performers already active.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[NO ACTION] range_breakout+ LONG** — Already disabled. 25% WR, -$0.41 (24h).
2. **[NO ACTION] hzscore+ LONG** — Already disabled. 28.6% WR, -$0.11 (24h).
3. **[WATCH] range_breakout- SHORT** — 45% WR, -$0.12 over 20 trades. Near breakeven — keep enabled but monitor.
4. **[KEEP] accel-300- SHORT** — Strong performer: 73.3% WR, +$0.36 (24h). Keep enabled.
5. **[KEEP] bb_bounce+ LONG** — Solid: 57.9% WR, +$0.16 over 19 trades. Keep enabled.
6. **[KEEP] range_breakout_short SHORT** — 100% WR (3 trades). Too small sample but promising.

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
