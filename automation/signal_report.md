# Signal Performance Report
**Generated:** 2026-09-21 23:03 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 2,633 | **WR:** 51.9% | **PnL:** -81.96%
- **Date range:** 2026-07-29 → 2026-09-21

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
| pump-chain+ | LONG | 14 | 35.7% | -5.54 | ❓ | Borderline |
| mover+ | LONG | 2 | 50.0% | -0.53 | ENABLED | Needs more data |
| volume-breakout-long+ | LONG | 2 | 50.0% | +2.93 | ❓ | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] pump-chain+ LONG** — WR=35.7%, PnL=-5.54% over 14 trades. Monitor next cycle.
2. **[WATCH] mover+ LONG** — WR=50.0%, PnL=-0.53% over 2 trades. Monitor next cycle.
3. **[WATCH] volume-breakout-long+ LONG** — WR=50.0%, PnL=+2.93% over 2 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-21 | 09b0d53 | signals: block pump-chain+ LONG in hours 0-4 UTC (0%WR/7d de... |
| 2026-09-21 | ef36d0d | CEO: raise CHASE_GAP_MAX_PCT from 1.0 to 3.0 |
| 2026-09-21 | 9770b3d | daily_orchestrator: 2026-09-21 ~20:30 UTC — NO CONFIG CHANGE |
| 2026-09-21 | 8f7d401 | config: squeeze_breakout cooldown 4h → 20min (2026-09-21) |
| 2026-09-21 | 4f77803 | fix: squeeze_breakout — move all magic numbers to hermes_con... |
| 2026-09-21 | 1ec8df2 | feat: squeeze_breakout signal — consolidation breakout catch... |
| 2026-09-21 | 874094c | Oscillator Matrix: shadow mode implementation |
| 2026-09-21 | 8b63f41 | Fix: BTC_LEVEL constants — remove dead code, add tunable par... |
| 2026-09-21 | ac16c94 | brain_auditor: UNIVERSAL_MAX_HOLD_MINUTES=480 safety net + f... |
| 2026-09-21 | ba0c034 | config: CONF_FILTER_MAX 89→92 (conservative) — 95+ was losin... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*