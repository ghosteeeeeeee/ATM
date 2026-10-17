# Signal Performance Report
**Generated:** 2026-10-17 14:13 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 3,183 | **WR:** 50.9% | **PnL:** -108.74%
- **Date range:** 2026-07-29 → 2026-10-17

---

## WINNERS (WR > 55%, PnL > 0)

None found.

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| doji-bottom-long | LONG | — | —% | — | 7 | 28.6% | -3.63 | ❓ | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| ai-trader+ | LONG | 3 | 33.3% | -1.53 | ❓ | Needs more data |
| ai-trader-manual | SHORT | 2 | 50.0% | -0.41 | ❓ | Needs more data |
| ai-trader-manual | LONG | 3 | 33.3% | -0.39 | ❓ | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] doji-bottom-long LONG** — WR=28.6%, PnL=-3.63% over 7 trades (24h).
2. **[WATCH] ai-trader+ LONG** — WR=33.3%, PnL=-1.53% over 3 trades. Monitor next cycle.
3. **[WATCH] ai-trader-manual SHORT** — WR=50.0%, PnL=-0.41% over 2 trades. Monitor next cycle.
4. **[WATCH] ai-trader-manual LONG** — WR=33.3%, PnL=-0.39% over 3 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-17 | 209c5ae | brain_auditor: trail-arm-timeout candle OOS (all 4 cohorts) ... |
| 2026-10-17 | b01d329 | brain_auditor: captain run Oct 17 06:45 — 0 changes, verify+... |
| 2026-10-17 | 75b2af2 | brain_auditor: REGIME_CONF_EXTREME_MULT 1.15→0.85 — stale Se... |
| 2026-10-17 | ece01f3 | scripts: MFE-CUT shadow collector (T=45m, zero behavior) + a... |
| 2026-10-17 | 70f45e4 | brain_auditor: ai-trader RSI drift guard + MFE exit-ladder a... |
| 2026-10-17 | 5a95263 | signals: pump-chain+ LONG dead-gap falling-knife block (gap<... |
| 2026-10-17 | 66716f2 | scripts: extend trail-arm-timeout SHADOW to ai-trader+ LONG ... |
| 2026-10-17 | 02f6d4e | config: ATR_SL_MIN 1.3% → 1.5% |
| 2026-10-16 | 70ff616 | scripts: bb-bounce-v2 trail-arm-timeout SHADOW collector T=5... |
| 2026-10-16 | ccf804e | brain_auditor: LONG_RSI_SWEET_SPOT_MIN 40→55 — boost only si... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*