# Signal Performance Report
**Generated:** 2026-08-08 19:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 583 | **WR:** 43.4% | **PnL:** -18.39%
- **Date range:** 2026-07-29 → 2026-08-08

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce+,range_finder+ | LONG | 3 | 66.7% | -0.82 | 11 | 81.8% | +4.72 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| ma100-cross+,vortex_break_long | LONG | 5 | 40.0% | -0.44 | ❓ | Borderline |
| bb_bounce+,ma100-cross+ | LONG | 2 | 50.0% | +0.29 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] ma100-cross+,vortex_break_long LONG** — WR=40.0%, PnL=-0.44% over 5 trades. Monitor next cycle.
2. **[WATCH] bb_bounce+,ma100-cross+ LONG** — WR=50.0%, PnL=+0.29% over 2 trades. Monitor next cycle.
3. **[KEEP] 1 winning combos** — bb_bounce+,range_fin. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-08 | 16900d9 | signals: re-enable hzscore- with RS confluence boost |
| 2026-08-08 | 710c312 | fix: enable MA_100_CROSS_MINUS_ENABLED for new ma_100_cross_... |
| 2026-08-08 | f16ee66 | fix: disable old ma_100_cross to prevent duplicate signals |
| 2026-08-08 | 47c14db | fix: widen trend filter threshold to allow SHORT in weak BUL... |
| 2026-08-08 | 57d1eb5 | scripts: cut_loser v2 — two-tier loss cutting + trailing los... |
| 2026-08-08 | 1fe611f | signals: kill range_finder- and vortex_break_short SHORT — 4... |
| 2026-08-08 | 1f4e2ba | config: add TRUMP to long/short blacklists |
| 2026-08-08 | 125546f | CEO: Disable MA_100_CROSS_MINUS — worst SHORT signal (40% WR... |
| 2026-08-08 | ac33b43 | CEO: Disable return_exhaustion- SHORT, update report |
| 2026-08-08 | c3daf6a | CEO: widen ATR SL from 1.0% to 1.2% |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*