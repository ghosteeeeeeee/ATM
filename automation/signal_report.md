# Signal Performance Report
**Generated:** 2026-08-15 17:02 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,027 | **WR:** 46.8% | **PnL:** -37.51%
- **Date range:** 2026-07-29 → 2026-08-15

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| r2-trend-long2 | LONG | — | —% | — | 5 | 60.0% | +0.38 | ❓ |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| range_finder+ | LONG | 9 | 33.3% | -2.33 | DISABLED | Borderline |
| wave_catcher- | SHORT | 4 | 50.0% | -0.86 | DISABLED | Needs more data |
| ct-hot- | SHORT | 2 | 50.0% | -0.71 | ❓ | Needs more data |
| wave_catcher+ | LONG | 2 | 50.0% | -0.69 | DISABLED | Needs more data |
| ct-hot+ | LONG | 13 | 46.2% | +0.11 | ❓ | Borderline |
| r2-trend-long3 | LONG | 2 | 50.0% | +0.59 | ❓ | Needs more data |

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
3. **[WATCH] ct-hot- SHORT** — WR=50.0%, PnL=-0.71% over 2 trades. Monitor next cycle.
4. **[WATCH] wave_catcher+ LONG** — WR=50.0%, PnL=-0.69% over 2 trades. Monitor next cycle.
5. **[WATCH] ct-hot+ LONG** — WR=46.2%, PnL=+0.11% over 13 trades. Monitor next cycle.
6. **[WATCH] r2-trend-long3 LONG** — WR=50.0%, PnL=+0.59% over 2 trades. Monitor next cycle.
7. **[KEEP] 1 winning combos** — r2-trend-long2. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-15 | 18c9764 | CEO: widened PM_TRAIL_DISTANCE_PCT 0.40%→0.60% — R:R fix |
| 2026-08-15 | 9987e77 | CEO: PM_TRAIL tightened 0.60%→0.40% + NEUTRAL speed override... |
| 2026-08-15 | 387b54b | CEO: LOWERED PM_TRAIL_ACTIVATE_PCT 0.60%→0.40% — R:R fix |
| 2026-08-15 | da7a56c | CEO: Lower COIN_TRACKER_HOT_MIN_COMPOSITE 50→45 — unblock ct... |
| 2026-08-15 | 59c1f0a | CEO: 3 fixes — trailing activation 0.40%, PM_TRAIL race fix,... |
| 2026-08-15 | d8fb23f | CEO: added range_finder to STANDALONE_BYPASS (volume fix for... |
| 2026-08-15 | 58f2671 | CEO: Remove range_breakout from STANDALONE_BYPASS (25% WR st... |
| 2026-08-15 | c562a8f | CEO: cleaned STANDALONE_BYPASS — removed dead signals (wave_... |
| 2026-08-15 | 0ac3ecd | CEO: FIX SIGNAL STARVATION — lowered SPEED_MIN 45→30 |
| 2026-08-15 | d02de1b | CEO: Added coin_tracker intelligence development — predict m... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*