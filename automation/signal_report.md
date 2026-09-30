# Signal Performance Report
**Generated:** 2026-09-30 17:03 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 2,720 | **WR:** 51.9% | **PnL:** -106.01%
- **Date range:** 2026-07-29 → 2026-09-30

---

## WINNERS (WR > 55%, PnL > 0)

None found.

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| bb-bounce-v2-long+ | LONG | 2 | 50.0% | +0.26 | ❓ | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] bb-bounce-v2-long+ LONG** — WR=50.0%, PnL=+0.26% over 2 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-30 | 28375e5 | Fix 6 bugs found by bug hunter on dynamic RSI + standalone b... |
| 2026-09-30 | 3294f89 | Raise LONG_RSI_CEILING from 65 to 70 |
| 2026-09-30 | 3e5722a | Remove all time blocks — focus on entry quality filters |
| 2026-09-30 | 8815282 | CRITICAL FIX: CONF_FILTER_MIN blocked ALL signals |
| 2026-09-30 | 6997518 | Brain Audit: 2026-09-30 06:00 UTC — system stable, hotset RS... |
| 2026-09-30 | 5523239 | CEO: pump-chain- SHORT RSI_MIN=25 filter — blocks oversold e... |
| 2026-09-30 | eff23ff | brain-audit: Sep 30 03:35 UTC — LONG RSI>70 leak, hotset con... |
| 2026-09-29 | b76bec7 | fix: bug hunter findings — V5 integration bugs |
| 2026-09-29 | 9265efa | Implement Thesis Validation System (TVS) |
| 2026-09-29 | f9daa25 | fix: pump_chain_v5 not reaching hotset — add to compactor wh... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*