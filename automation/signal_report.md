# Signal Performance Report
**Generated:** 2026-10-01 11:03 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 2,740 | **WR:** 51.8% | **PnL:** -112.94%
- **Date range:** 2026-07-29 → 2026-10-01

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
| accel-300- | SHORT | 7 | 42.9% | -2.45 | ENABLED | Borderline |
| pump-chain-v5 | LONG | 6 | 33.3% | -1.84 | DISABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] accel-300- SHORT** — WR=42.9%, PnL=-2.45% over 7 trades. Monitor next cycle.
2. **[WATCH] pump-chain-v5 LONG** — WR=33.3%, PnL=-1.84% over 6 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-01 | 6d2fea2 | signals: kill pump-chain-v5 LONG — 3T 0%WR -$0.20 last hour ... |
| 2026-10-01 | 158e5d6 | scripts: CRITICAL FIX — FAVORITES dict|set crash took pipeli... |
| 2026-10-01 | d403a25 | CEO: PUMP_CHAIN_SHORT_RSI_MIN 25→40 + V5 extend + kanban/rep... |
| 2026-09-30 | 28375e5 | Fix 6 bugs found by bug hunter on dynamic RSI + standalone b... |
| 2026-09-30 | 3294f89 | Raise LONG_RSI_CEILING from 65 to 70 |
| 2026-09-30 | 3e5722a | Remove all time blocks — focus on entry quality filters |
| 2026-09-30 | 8815282 | CRITICAL FIX: CONF_FILTER_MIN blocked ALL signals |
| 2026-09-30 | 6997518 | Brain Audit: 2026-09-30 06:00 UTC — system stable, hotset RS... |
| 2026-09-30 | 5523239 | CEO: pump-chain- SHORT RSI_MIN=25 filter — blocks oversold e... |
| 2026-09-30 | eff23ff | brain-audit: Sep 30 03:35 UTC — LONG RSI>70 leak, hotset con... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*