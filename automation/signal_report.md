# Signal Performance Report
**Generated:** 2026-08-15 11:02 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,018 | **WR:** 46.9% | **PnL:** -35.14%
- **Date range:** 2026-07-29 → 2026-08-15

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| ct-hot+ | LONG | 7 | 57.1% | +1.92 | 7 | 57.1% | +1.92 | ❓ |
| r2-trend-long2 | LONG | — | —% | — | 9 | 55.6% | +0.67 | ❓ |
| r2-trend-long3 | LONG | — | —% | — | 7 | 71.4% | +0.65 | ❓ |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| range_finder+ | LONG | 9 | 33.3% | -2.33 | DISABLED | Borderline |
| wave_catcher- | SHORT | 4 | 50.0% | -0.86 | DISABLED | Needs more data |
| wave_catcher+ | LONG | 2 | 50.0% | -0.69 | DISABLED | Needs more data |
| wave_catcher+ | SHORT | 3 | 33.3% | +0.02 | DISABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] range_finder+ LONG** — WR=33.3%, PnL=-2.33% over 9 trades. Monitor next cycle.
2. **[WATCH] wave_catcher- SHORT** — WR=50.0%, PnL=-0.86% over 4 trades. Monitor next cycle.
3. **[WATCH] wave_catcher+ LONG** — WR=50.0%, PnL=-0.69% over 2 trades. Monitor next cycle.
4. **[WATCH] wave_catcher+ SHORT** — WR=33.3%, PnL=+0.02% over 3 trades. Monitor next cycle.
5. **[KEEP] 3 winning combos** — ct-hot+, r2-trend-long2, r2-trend-long3. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-15 | 59c1f0a | CEO: 3 fixes — trailing activation 0.40%, PM_TRAIL race fix,... |
| 2026-08-15 | d8fb23f | CEO: added range_finder to STANDALONE_BYPASS (volume fix for... |
| 2026-08-15 | 58f2671 | CEO: Remove range_breakout from STANDALONE_BYPASS (25% WR st... |
| 2026-08-15 | c562a8f | CEO: cleaned STANDALONE_BYPASS — removed dead signals (wave_... |
| 2026-08-15 | 0ac3ecd | CEO: FIX SIGNAL STARVATION — lowered SPEED_MIN 45→30 |
| 2026-08-15 | d02de1b | CEO: Added coin_tracker intelligence development — predict m... |
| 2026-08-15 | e62c8db | CEO: Updated prompt — added active winrate improvement and s... |
| 2026-08-15 | 505c742 | CEO: WIDENED PM_TRAIL_DISTANCE_PCT 0.40%→0.60% — R:R inverte... |
| 2026-08-15 | 8e923cb | Daily trading system update (2026-08-15) |
| 2026-08-15 | c095ba1 | CEO: ATR_TP_K_MULT 2.0→2.5 — fix inverted R:R (0.60:1→0.75:1... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*