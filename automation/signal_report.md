# Signal Performance Report
**Generated:** 2026-08-23 05:02 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,264 | **WR:** 48.2% | **PnL:** -51.37%
- **Date range:** 2026-07-29 → 2026-08-23

---

## WINNERS (WR > 55%, PnL > 0)

None found.

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| ct-hot+ | LONG | — | —% | — | 10 | 10.0% | -24.64 | ❓ | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| hl_copy_trader | LONG | 24 | 50.0% | +1.29 | ❓ | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] ct-hot+ LONG** — WR=10.0%, PnL=-24.64% over 10 trades (24h).
2. **[WATCH] hl_copy_trader LONG** — WR=50.0%, PnL=+1.29% over 24 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-23 | d46729a | fix: weather integration bugs found by bug_hunter |
| 2026-08-23 | 53e8bc5 | fix: disable copy trader dead hours filter |
| 2026-08-23 | cb20bac | fix: lower cluster min size from 3 to 2 |
| 2026-08-23 | d631a98 | CEO: 237th run — ct-hot+ legacy draining, system recovering.... |
| 2026-08-23 | affb9a9 | Signals: re-enable hzscore, coin_tracker_hot, raise slope th... |
| 2026-08-22 | 0c5c8fd | signals: kill ct-hot+ family — 27.7% WR, -$3.92 PnL (7d, 47 ... |
| 2026-08-22 | 5c3c657 | feat: cluster filter for copy trading signals |
| 2026-08-22 | b21485a | config: add RESEARCH_FLAGS protection category |
| 2026-08-22 | 912d764 | signals: liquidation_hunt — full pipeline integration |
| 2026-08-22 | 5f5568e | signals: add speed and acceleration filters to ct-hot+ |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*