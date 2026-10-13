# Signal Performance Report
**Generated:** 2026-10-13 11:04 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 3,043 | **WR:** 51.7% | **PnL:** -85.42%
- **Date range:** 2026-07-29 → 2026-10-13

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
| ai-trader+ | LONG | 3 | 33.3% | -1.34 | ❓ | Needs more data |
| hmacd_mtf-+ | LONG | 3 | 33.3% | -1.26 | ❓ | Needs more data |
| hl_copy_trader | LONG | 2 | 50.0% | +0.32 | ❓ | Needs more data |
| pump-chain+ | LONG | 7 | 42.9% | +0.64 | ❓ | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] ai-trader+ LONG** — WR=33.3%, PnL=-1.34% over 3 trades. Monitor next cycle.
2. **[WATCH] hmacd_mtf-+ LONG** — WR=33.3%, PnL=-1.26% over 3 trades. Monitor next cycle.
3. **[WATCH] hl_copy_trader LONG** — WR=50.0%, PnL=+0.32% over 2 trades. Monitor next cycle.
4. **[WATCH] pump-chain+ LONG** — WR=42.9%, PnL=+0.64% over 7 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-13 | 2409c5f | Daily trading system update (2026-10-13) |
| 2026-10-13 | d3b0b35 | brain_auditor: PUMP_CHAIN_LONG_RSI_MAX 75→70 — block overbou... |
| 2026-10-13 | 71f8803 | signal: volume-buildup cooldown 2h→15min — 5m timeframe sign... |
| 2026-10-13 | ab2c065 | signals: disable continuum_score_short — 0 trades all-time, ... |
| 2026-10-13 | 84a3870 | recalibration: CEO-approved 5 changes — disable return_exhau... |
| 2026-10-13 | eea1f59 | fix: pump-chain SHORT RSI_FLOOR also needs 40 variant — bug_... |
| 2026-10-13 | 1ac1c92 | signal: pump-chain SHORT RSI hard floor 45→40 — auditor-appr... |
| 2026-10-13 | 2d6dd55 | config: add ai-trader to PM Trail bypass |
| 2026-10-13 | 2e0e5f0 | config: hard_max_loss -2.50% → -2.80% account PnL |
| 2026-10-13 | 14b1055 | Signals: kill oversold-bounce+ (auto_1hr 2026-10-13 01:15) |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*