# Signal Performance Report
**Generated:** 2026-08-28 05:02 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,575 | **WR:** 49.0% | **PnL:** -80.37%
- **Date range:** 2026-07-29 → 2026-08-28

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| accel-300-v2- | SHORT | 13 | 53.8% | +1.66 | 21 | 57.1% | +2.30 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| accel-300-v2+ | LONG | 6 | 33.3% | -3.68 | DISABLED | Borderline |
| bb-bounce-short | SHORT | 4 | 50.0% | -1.30 | ENABLED | Needs more data |
| engulfing+,r2-trend-long4 | LONG | 2 | 50.0% | -0.99 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] accel-300-v2+ LONG** — WR=33.3%, PnL=-3.68% over 6 trades. Monitor next cycle.
2. **[WATCH] bb-bounce-short SHORT** — WR=50.0%, PnL=-1.30% over 4 trades. Monitor next cycle.
3. **[WATCH] engulfing+,r2-trend-long4 LONG** — WR=50.0%, PnL=-0.99% over 2 trades. Monitor next cycle.
4. **[KEEP] 1 winning combos** — accel-300-v2-. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-28 | 6f938e5 | tune: accel-300-v2 — lower SHORT min gap 1.0% -> 0.5% |
| 2026-08-28 | f77f59d | CEO: monitoring run 278 — verified 24h 69T 49.3% WR -$0.20, ... |
| 2026-08-28 | df57f5b | tune: accel-300-v2 — raise SHORT min gap 0.5% -> 1.0% |
| 2026-08-28 | 1756135 | tune: accel-300-v2 — raise SHORT min gap 0.3% -> 0.5% |
| 2026-08-27 | 0844c77 | signals: kill accel-300-v2+ LONG — 33.3% WR, -$0.16 (48h), 6... |
| 2026-08-27 | e91ac1e | CEO: Fix slow-grind- flag bug (2nd time kill not applied) |
| 2026-08-27 | f50e91b | signals: re-enable slow_grind_short for TESTING |
| 2026-08-27 | d3101a2 | signals: raise slow_grind MAX_DECLINE_FROM_HIGH from 1.0% to... |
| 2026-08-27 | 9393d46 | refactor: move V2 constants to hermes_constants.py + tighten... |
| 2026-08-27 | 0f6639e | signals: kill atr-spike+ (28.6% WR, -$0.15) boost macd-div- ... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*