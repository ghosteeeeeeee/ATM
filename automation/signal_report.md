# Signal Performance Report
**Generated:** 2026-08-09 01:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 600 | **WR:** 43.5% | **PnL:** -17.88%
- **Date range:** 2026-07-29 → 2026-08-09

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce+,range_finder+ | LONG | 8 | 50.0% | +1.66 | 16 | 62.5% | +4.83 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| bb_bounce+,hzscore+ | LONG | 3 | 33.3% | -1.07 | ENABLED | Needs more data |
| ma100-cross+,vortex_break_long | LONG | 6 | 33.3% | -0.78 | ❓ | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] bb_bounce+,hzscore+ LONG** — WR=33.3%, PnL=-1.07% over 3 trades. Monitor next cycle.
2. **[WATCH] ma100-cross+,vortex_break_long LONG** — WR=33.3%, PnL=-0.78% over 6 trades. Monitor next cycle.
3. **[KEEP] 1 winning combos** — bb_bounce+,range_fin. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-08 | f5aa0d5 | signals: add return_exhaustion_short.py — SHORT-specific per... |
| 2026-08-08 | 8b8e345 | signals: add range_finder_short.py — SHORT-specific range fi... |
| 2026-08-08 | bb61874 | signals: add bb_bounce_short.py — SHORT-specific BB bounce w... |
| 2026-08-08 | 51754e3 | CEO: 24h +$0.13 (50% WR), 7d -$1.23. All fixes verified work... |
| 2026-08-08 | 16900d9 | signals: re-enable hzscore- with RS confluence boost |
| 2026-08-08 | 710c312 | fix: enable MA_100_CROSS_MINUS_ENABLED for new ma_100_cross_... |
| 2026-08-08 | f16ee66 | fix: disable old ma_100_cross to prevent duplicate signals |
| 2026-08-08 | 47c14db | fix: widen trend filter threshold to allow SHORT in weak BUL... |
| 2026-08-08 | 57d1eb5 | scripts: cut_loser v2 — two-tier loss cutting + trailing los... |
| 2026-08-08 | 1fe611f | signals: kill range_finder- and vortex_break_short SHORT — 4... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*