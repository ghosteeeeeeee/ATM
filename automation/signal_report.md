# Signal Performance Report
**Generated:** 2026-10-06 23:03 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 2,903 | **WR:** 52.3% | **PnL:** -112.86%
- **Date range:** 2026-07-29 → 2026-10-06

---

## WINNERS (WR > 55%, PnL > 0)

None found.

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| trend-ride+ | LONG | — | —% | — | 5 | 20.0% | -4.16 | ❓ | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| pump-chain- | SHORT | 3 | 33.3% | -1.45 | ❓ | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] trend-ride+ LONG** — WR=20.0%, PnL=-4.16% over 5 trades (24h).
2. **[WATCH] pump-chain- SHORT** — WR=33.3%, PnL=-1.45% over 3 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-06 | b18891d | CEO: raise SHORT_CONTINUUM_SCORE_MAX 40→60 — every dump is a... |
| 2026-10-06 | dbfe2dd | CEO: T directive — broaden SHORT market (floor 45, HIGH open... |
| 2026-10-06 | 61bec3b | fix: bypass gaps + _is_ride_it over-match (own-conclusions f... |
| 2026-10-06 | 26d3c99 | orchestrator: post-freeze queue 2026-10-06 — FAMILY_MAP unde... |
| 2026-10-06 | bd1728f | signals: kill mtf-regime-trend- SHORT — 0% WR, $-0.53 (24h) ... |
| 2026-10-06 | 5b62627 | Config: add tl-bounce to STANDALONE_BYPASS_SIGNALS |
| 2026-10-06 | 885021c | signals: trend_ride_long — add BB position + momentum filter... |
| 2026-10-06 | 1b6f8f5 | fix: ride_it exit bugs — ATR off-by-one, SL widen, overlay c... |
| 2026-10-05 | 9dde1ca | signals: trend_ride+ mapped to ride_it exit — let trends run |
| 2026-10-05 | 800d5e8 | signals: trend_ride_long tightened — RSI 50-65, ATR>=0.10, 1... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*