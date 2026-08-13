# Signal Performance Report
**Generated:** 2026-08-13 01:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 872 | **WR:** 46.3% | **PnL:** -14.92%
- **Date range:** 2026-07-29 → 2026-08-13

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| range_breakout_short | SHORT | 11 | 63.6% | +2.82 | 14 | 71.4% | +4.04 | ENABLED |
| bb_bounce+ | LONG | — | —% | — | 5 | 60.0% | +0.82 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| range_breakout+ | LONG | — | —% | — | 8 | 25.0% | -4.02 | DISABLED | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| range_breakout- | SHORT | 20 | 50.0% | -1.92 | DISABLED | Borderline |
| hzscore- | SHORT | 12 | 50.0% | -0.16 | ENABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] range_breakout+ LONG** — WR=25.0%, PnL=-4.02% over 8 trades (24h).
2. **[WATCH] range_breakout- SHORT** — WR=50.0%, PnL=-1.92% over 20 trades. Monitor next cycle.
3. **[WATCH] hzscore- SHORT** — WR=50.0%, PnL=-0.16% over 12 trades. Monitor next cycle.
4. **[KEEP] 2 winning combos** — range_breakout_short, bb_bounce+. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-13 | dcdf4c1 | feat: Weather Vane v2 — hysteresis + off-course alarm |
| 2026-08-13 | 12cb22f | feat: global spike filter for SHORT entries |
| 2026-08-13 | 16e6abf | CEO: NO TRADING CHANGES — 24h 106T -$0.26 flat, 7d +$0.37 po... |
| 2026-08-12 | c367e1d | CEO: recovery confirmed, 24h +/usr/bin/bash.53 57.6% WR, 7d ... |
| 2026-08-12 | 4586229 | CEO: BLACKLISTED return_exhaustion- SHORT — ALL SL hits loss... |
| 2026-08-12 | a6a5739 | CEO: blacklisted hzscore+ standalone (38.5% WR bleed source) |
| 2026-08-12 | 8d36599 | CEO: 2026-08-12 18:49 UTC — NO CHANGES. Verified 24h 98T -/u... |
| 2026-08-12 | 7acf1a3 | hermes_constants: fix ATR_K threshold comments (3% → 1.5%) |
| 2026-08-12 | 1534a8b | CEO: widen trailing stop distance 0.60%→0.80%, activation 0.... |
| 2026-08-12 | 1e47094 | CEO: disable RANGE_BREAKOUT_PLUS_ENABLED (8T 25% WR -$0.41 2... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*