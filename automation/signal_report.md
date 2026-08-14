# Signal Performance Report
**Generated:** 2026-08-14 19:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 983 | **WR:** 46.9% | **PnL:** -32.99%
- **Date range:** 2026-07-29 → 2026-08-14

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| r2-trend-long2 | LONG | 3 | 66.7% | +0.03 | 13 | 61.5% | +0.51 | ❓ |

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| mover+ | LONG | — | —% | — | 7 | 28.6% | -3.06 | ❓ | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| wave_catcher+ | LONG | 6 | 33.3% | -2.58 | DISABLED | Borderline |
| range_breakout_short | SHORT | 3 | 33.3% | -1.12 | ENABLED | Needs more data |
| r2-trend-long4 | LONG | 2 | 50.0% | -0.42 | ❓ | Needs more data |
| ct-hot+,mover+ | LONG | 2 | 50.0% | +0.66 | ❓ | Needs more data |
| wave_catcher+ | SHORT | 6 | 50.0% | +0.79 | DISABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] mover+ LONG** — WR=28.6%, PnL=-3.06% over 7 trades (24h).
2. **[WATCH] wave_catcher+ LONG** — WR=33.3%, PnL=-2.58% over 6 trades. Monitor next cycle.
3. **[WATCH] range_breakout_short SHORT** — WR=33.3%, PnL=-1.12% over 3 trades. Monitor next cycle.
4. **[WATCH] r2-trend-long4 LONG** — WR=50.0%, PnL=-0.42% over 2 trades. Monitor next cycle.
5. **[WATCH] ct-hot+,mover+ LONG** — WR=50.0%, PnL=+0.66% over 2 trades. Monitor next cycle.
6. **[WATCH] wave_catcher+ SHORT** — WR=50.0%, PnL=+0.79% over 6 trades. Monitor next cycle.
7. **[KEEP] 1 winning combos** — r2-trend-long2. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-14 | 8161d34 | signals: kill wave_catcher+, mover+, range_breakout+ LONG — ... |
| 2026-08-14 | 5be3229 | signals: re-enable wave_catcher+ and range_breakout+ LONG pe... |
| 2026-08-14 | 5aba5dc | CEO: PM_TRAIL_ACTIVATE_PCT 0.30→0.60 — fix inverted R:R (0.4... |
| 2026-08-14 | 804a0b5 | CEO: verified run 2026-08-15 — NO CHANGES, ATR 2.0 eval acti... |
| 2026-08-14 | 3069a9e | CEO: 2026-08-15 verified run — NO CHANGES, ATR 2.0 eval acti... |
| 2026-08-14 | 822ddad | trailing SL tuning: ACTIVATION 0.40→0.80%, DISTANCE 0.80→2.0... |
| 2026-08-14 | 4a95822 | coin_tracker_hot: Tune thresholds for fast-moving coins |
| 2026-08-14 | 0011ec7 | CEO: no changes — ATR 2.0 eval window active, 76T -$0.83 RED |
| 2026-08-14 | 4d0056d | coin_tracker_hot: Raise thresholds to reduce noise |
| 2026-08-14 | 2010160 | Revert "fix: add ct-hot to standalone bypass to unblock coin... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*