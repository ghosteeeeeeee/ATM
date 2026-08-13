# Signal Performance Report
**Generated:** 2026-08-13 19:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 911 | **WR:** 46.4% | **PnL:** -24.27%
- **Date range:** 2026-07-29 → 2026-08-13

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| hzscore- | SHORT | 8 | 62.5% | +0.72 | 14 | 64.3% | +1.15 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| accel-300- | SHORT | 25 | 44.0% | -8.23 | DISABLED | Borderline |
| continuation-,hzscore- | SHORT | 3 | 33.3% | -2.41 | DISABLED | Needs more data |
| range_breakout_short | SHORT | 20 | 45.0% | -1.75 | ENABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] accel-300- SHORT** — WR=44.0%, PnL=-8.23% over 25 trades. Monitor next cycle.
2. **[WATCH] continuation-,hzscore- SHORT** — WR=33.3%, PnL=-2.41% over 3 trades. Monitor next cycle.
3. **[WATCH] range_breakout_short SHORT** — WR=45.0%, PnL=-1.75% over 20 trades. Monitor next cycle.
4. **[KEEP] 1 winning combos** — hzscore-. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-13 | 687df2e | CEO: NO CHANGES — verified DB, system flat, stability period |
| 2026-08-13 | 669f92a | config: add RANGE_BREAKOUT_SHORT_EMA_PERIOD to hermes_consta... |
| 2026-08-13 | 5aa376a | signals: centralized slope filter + EMA200 trend filter (CEO... |
| 2026-08-13 | 317aba9 | CEO: NO CHANGES — verified DB 24h 79T -$0.24 55.7% WR flat, ... |
| 2026-08-13 | 07b84a9 | auto_1hr: disable ACCEL_300_ENABLED — 19T today 36.8% WR, 12... |
| 2026-08-13 | 3469239 | CEO: 2026-08-13 verified, no changes — legacy clearing, stab... |
| 2026-08-13 | 2dbd8e9 | Daily trading system update (2026-08-13) |
| 2026-08-13 | e6a05d0 | CEO: disable ACCEL_300_MINUS_ENABLED (inverted R:R bleeding ... |
| 2026-08-13 | de9add5 | fix: add bb-bounce-short to solo bypass (hyphen/underscore m... |
| 2026-08-13 | cff29ab | signals: disable ATR floor filter — backtest shows ATR overl... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*