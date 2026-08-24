# Signal Performance Report
**Generated:** 2026-08-24 05:02 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,320 | **WR:** 48.3% | **PnL:** -49.76%
- **Date range:** 2026-07-29 → 2026-08-24

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce+ | LONG | 5 | 80.0% | +2.82 | 5 | 80.0% | +2.82 | ENABLED |
| tl_break_short | SHORT | 6 | 83.3% | +1.11 | 6 | 83.3% | +1.11 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| macd-div+ | LONG | — | —% | — | 5 | 20.0% | -5.00 | ❓ | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| ct-hot- | SHORT | 2 | 50.0% | -1.29 | ❓ | Needs more data |
| hl_copy_trader | LONG | 3 | 33.3% | +1.24 | ❓ | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] macd-div+ LONG** — WR=20.0%, PnL=-5.00% over 5 trades (24h).
2. **[WATCH] ct-hot- SHORT** — WR=50.0%, PnL=-1.29% over 2 trades. Monitor next cycle.
3. **[WATCH] hl_copy_trader LONG** — WR=33.3%, PnL=+1.24% over 3 trades. Monitor next cycle.
4. **[KEEP] 2 winning combos** — bb_bounce+, tl_break_short. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-24 | 7d80a1e | fix: SHORT signals blocked by two filters |
| 2026-08-24 | d8f202e | fix: bb_bounce signal dead — 3 blockers removed |
| 2026-08-24 | 8984c49 | signals: remove macd-div from STANDALONE_BYPASS — no trade d... |
| 2026-08-24 | e67c837 | signals: normalize r2_trend_long slope by price (fixes micro... |
| 2026-08-24 | 2565099 | fix: increase copy signal lookback from 5 to 30 minutes |
| 2026-08-24 | 628459d | fix: enable SHORT copy signals |
| 2026-08-23 | b1400fb | config: tighten trailing distance from 2.0% to 1.0% |
| 2026-08-23 | 467e3ad | signals: kill hzscore- — 37.5% WR, -$0.35/24h, avg loser 2x ... |
| 2026-08-23 | 8229727 | auto_1hr: kill hzscore- signal (7T 43% WR -$0.21/24h) |
| 2026-08-23 | 9bf2370 | CEO: Lower CONF_FILTER_MAX 89→85 (block overconfident trades... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*