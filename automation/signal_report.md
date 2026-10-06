# Signal Performance Report
**Generated:** 2026-10-06 17:03 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 2,900 | **WR:** 52.3% | **PnL:** -113.67%
- **Date range:** 2026-07-29 → 2026-10-06

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
| trend-ride+ | LONG | 7 | 42.9% | -3.57 | ❓ | Borderline |
| mover+ | LONG | 2 | 50.0% | -0.37 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] trend-ride+ LONG** — WR=42.9%, PnL=-3.57% over 7 trades. Monitor next cycle.
2. **[WATCH] mover+ LONG** — WR=50.0%, PnL=-0.37% over 2 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-06 | 61bec3b | fix: bypass gaps + _is_ride_it over-match (own-conclusions f... |
| 2026-10-06 | 26d3c99 | orchestrator: post-freeze queue 2026-10-06 — FAMILY_MAP unde... |
| 2026-10-06 | bd1728f | signals: kill mtf-regime-trend- SHORT — 0% WR, $-0.53 (24h) ... |
| 2026-10-06 | 5b62627 | Config: add tl-bounce to STANDALONE_BYPASS_SIGNALS |
| 2026-10-06 | 885021c | signals: trend_ride_long — add BB position + momentum filter... |
| 2026-10-06 | 1b6f8f5 | fix: ride_it exit bugs — ATR off-by-one, SL widen, overlay c... |
| 2026-10-05 | 9dde1ca | signals: trend_ride+ mapped to ride_it exit — let trends run |
| 2026-10-05 | 800d5e8 | signals: trend_ride_long tightened — RSI 50-65, ATR>=0.10, 1... |
| 2026-10-05 | c285e79 | signals: trend_ride_long — bypass list bare form + chop over... |
| 2026-10-05 | db536b0 | signals: trend_ride_long LIVE — enable flags + standalone by... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*