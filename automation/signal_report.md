# Signal Performance Report
**Generated:** 2026-09-24 23:03 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 2,677 | **WR:** 51.8% | **PnL:** -119.48%
- **Date range:** 2026-07-29 → 2026-09-24

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
| pump-chain- | SHORT | 18 | 38.9% | -7.43 | ❓ | Borderline |
| continuum-osc+ | LONG | 2 | 50.0% | -0.89 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] pump-chain- SHORT** — WR=38.9%, PnL=-7.43% over 18 trades. Monitor next cycle.
2. **[WATCH] continuum-osc+ LONG** — WR=50.0%, PnL=-0.89% over 2 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-24 | 64e2c7a | CEO: REGIME_CONF_MULTIPLIER deployed — EXTREME +15%, NORMAL ... |
| 2026-09-24 | 76ffdba | signals: add pump-chain- SHORT dead hours [2,3] — 14d 0%WR -... |
| 2026-09-24 | 02581c8 | CEO: DISABLE CL-T1 — 25T/14d 0%WR -$3.11 pure loss machine |
| 2026-09-24 | 9441fe6 | CEO: RAISE SHORT_RSI_FLOOR 40→50 — blocks RSI <50 SHORT blee... |
| 2026-09-24 | b6e8426 | brain_auditor: CL-T1 fire windows (2,3)->(4,6), audit update |
| 2026-09-24 | cb1739e | signals: KILL mover+ LONG — 3T 0%WR -$0.44 24h, 13T -$0.67 7... |
| 2026-09-24 | f143248 | CEO: Fix SHORT_RSI_FLOOR soft penalty → hard block |
| 2026-09-24 | c0975ff | CEO: widen CL-T1 range -2.0→-3.0, fix 0%WR loss machine |
| 2026-09-24 | 0c91d2f | brain-auditor: PUMP_CHAIN_LONG_RSI_MAX 75→70 + audit |
| 2026-09-23 | 29aa478 | signals: kill accel-300-breakout, block Mover EXTREME |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*