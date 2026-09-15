# Signal Performance Report
**Generated:** 2026-09-15 11:03 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 2,453 | **WR:** 52.0% | **PnL:** -93.46%
- **Date range:** 2026-07-29 → 2026-09-15

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| pump-chain- | SHORT | — | —% | — | 10 | 60.0% | +2.31 | ❓ |
| rr-struct-v2+ | LONG | — | —% | — | 6 | 66.7% | +0.11 | ❓ |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| pullback-entry- | SHORT | 9 | 44.4% | -2.13 | ENABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] pullback-entry- SHORT** — WR=44.4%, PnL=-2.13% over 9 trades. Monitor next cycle.
2. **[KEEP] 2 winning combos** — pump-chain-, rr-struct-v2+. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-15 | eaca524 | brain_auditor: audit run Sep 15 05:45 UTC — NO CONFIG CHANGE |
| 2026-09-14 | c0fd573 | signals: kill pump-chain- (PUMP_FLOW_MINUS_ENABLED=False) — ... |
| 2026-09-14 | 6bf4d8d | CEO: KILLED rr-struct- (42.9%WR), ATR_SL_MIN 1.3% applied, m... |
| 2026-09-14 | a6ed9bf | brain_auditor: ATR_SL_MIN 1.2%→1.3% (structural fix) |
| 2026-09-14 | 3c42965 | brain_auditor: audit complete ~19:15 UTC Sep 14 — NO CONFIG ... |
| 2026-09-14 | cd4f8de | signals: kill pump-chain+ (PUMP_FLOW_PLUS_ENABLED=False) |
| 2026-09-14 | 0673fa1 | CEO: 2026-09-14 ~10:15 UTC — MONITORING. 24h 46T 43.5%WR -/u... |
| 2026-09-14 | e55cc0a | Daily trading system update (2026-09-14) |
| 2026-09-14 | a5f9d78 | Tune: sniper hysteresis threshold 55→50 (score dropped to 52... |
| 2026-09-14 | 09f6071 | Feature: directional hysteresis — LONG threshold=55, SHORT t... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*