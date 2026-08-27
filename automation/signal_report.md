# Signal Performance Report
**Generated:** 2026-08-27 17:02 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,531 | **WR:** 48.8% | **PnL:** -78.03%
- **Date range:** 2026-07-29 → 2026-08-27

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| macd-div- | SHORT | 2 | 100.0% | +0.54 | 5 | 80.0% | +2.86 | ❓ |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| pump-catcher+ | LONG | 16 | 31.2% | -4.62 | DISABLED | Borderline |
| bb-bounce-short | SHORT | 3 | 33.3% | -1.47 | ENABLED | Needs more data |
| engulfing+,r2-trend-long4 | LONG | 2 | 50.0% | -0.99 | ENABLED | Needs more data |
| r2-trend-long3 | LONG | 2 | 50.0% | +0.74 | ❓ | Needs more data |
| cascade-reverse-v2-mtf_alignment+ca | LONG | 2 | 50.0% | +1.65 | ❓ | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] pump-catcher+ LONG** — WR=31.2%, PnL=-4.62% over 16 trades. Monitor next cycle.
2. **[WATCH] bb-bounce-short SHORT** — WR=33.3%, PnL=-1.47% over 3 trades. Monitor next cycle.
3. **[WATCH] engulfing+,r2-trend-long4 LONG** — WR=50.0%, PnL=-0.99% over 2 trades. Monitor next cycle.
4. **[WATCH] r2-trend-long3 LONG** — WR=50.0%, PnL=+0.74% over 2 trades. Monitor next cycle.
5. **[WATCH] cascade-reverse-v2-mtf_alignment+cascade_active+macd_exit LONG** — WR=50.0%, PnL=+1.65% over 2 trades. Monitor next cycle.
6. **[KEEP] 1 winning combos** — macd-div-. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-27 | 437b3f0 | ponytail audit Phase 1: delete dead code, prune signal regis... |
| 2026-08-27 | a6e75fb | scripts: Guitar Tuning Phase 0 — regime capture in signal_ou... |
| 2026-08-27 | e8c6d10 | config: Add accel-300-v2 to STANDALONE_BYPASS_SIGNALS |
| 2026-08-27 | dd4ccbe | config: add inv-accel-300-v2 to STANDALONE_BYPASS_SIGNALS |
| 2026-08-27 | 0b729c2 | favorites: remove underperformers, raise demotion threshold |
| 2026-08-27 | 83dde21 | CEO: Kill pump-catcher+ (21T/7d 33.3% WR -$0.39, 76.2% ATR_S... |
| 2026-08-27 | 5542876 | signals: add RSI/BB floor filters to r2_trend_long (blocks f... |
| 2026-08-27 | 85676c1 | CEO: Override auto_1hr bb_bounce+ kill, flag tl_break_short ... |
| 2026-08-27 | ee0e678 | auto_1hr: kill bb_bounce+ (3T/0%WR, re-enabled today) |
| 2026-08-27 | 17021a7 | CEO: Re-enable bb_bounce+ as backbone signal |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*