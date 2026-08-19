# Signal Performance Report
**Generated:** 2026-08-19 ~17:00 UTC | **Period:** 6h + 24h + 7d

## Overall Stats
- **24h:** 17 trades | PnL: -$0.42
- **7d:** 339 trades | PnL: -$2.29
- **Inversions:** None

---

## KILLED (executed)

None. 7d losers already disabled.

---

## BOOSTED (executed)

None. 24h volume too low (17T) to act on.

---

## WINNERS (7d, 3+ trades)

| Signal | Dir | WR | PnL | Trades |
|--------|-----|-----|-----|--------|
| r2-trend-long6 | LONG | 100% | +$0.20 | 4 |
| r2-trend-long2 | LONG | 64.7% | +$0.19 | 17 |
| r2-trend-long0 | LONG | 66.7% | +$0.07 | 3 |
| stop_hunt_reversal_long+ | LONG | 75% | +$0.06 | 4 |
| wave_catcher+ | SHORT | 42.9% | +$0.15 | 7 |
| bb_bounce+ | LONG | 50% | +$0.01 | 6 |

---

## LOSERS (7d, 3+ trades) — ALL ALREADY KILLED

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| range_breakout- | SHORT | 23.1% | -$0.55 | 13 | DISABLED |
| ct-hot+ | LONG | 42.4% | -$0.42 | 33 | DISABLED |
| wave_catcher+ | LONG | 37.5% | -$0.42 | 8 | DISABLED |
| accel-300- | SHORT | 55.3% | -$0.26 | 38 | DISABLED |
| range_breakout_short | SHORT | 46.4% | -$0.21 | 28 | DISABLED |
| mover+ | LONG | 28.6% | -$0.15 | 7 | WATCH |

---

## WATCH LIST

| Signal | Dir | 24h T | 24h WR | 7d WR | 7d PnL | Status |
|--------|-----|-------|--------|-------|--------|--------|
| r2-trend-long4 | LONG | 4 | 50% | 53.8% | -$0.13 | Monitor |
| r2-trend-long3 | LONG | 3 | 33.3% | 52% | -$0.23 | Monitor |
| mover+ | LONG | — | — | 28.6% | -$0.15 | Low WR, needs review |

---

## ISSUES

- **mover+** has 28.6% WR (7d) — borderline kill candidate. Not in hermes_constants.py (composite signal). Needs next cycle data to confirm.
- 24h very quiet (17 trades) — no actionable signal data. Rely on 7d numbers.
- r2-trend-long3 and long4 slightly negative but 7d WR is 52-54% — noise, not edge loss.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-19 | 3d90495 | CEO run 135: NO CHANGES — system healthy, PM_TRAIL 92.9% WR ... |
| 2026-08-19 | dea5b15 | CEO run 134: RAISED R2_TREND_LONG_MIN_PRE_MOVE 0.2→0.3 |
| 2026-08-19 | a4b55d0 | Daily trading system update (2026-08-19) |
| 2026-08-18 | 37b90e1 | signals: disable return_exhaustion_long (3T/0%WR auto-kill) |
| 2026-08-18 | 15dc023 | CEO run 112: NO CHANGES — system strong, PM_TRAIL carrying, ... |
| 2026-08-18 | b004ff6 | CEO: Run 97 — NO CHANGES, system STRONG. Verified DB 24h 27T... |
| 2026-08-18 | 1325eb9 | CEO: Run 96 — NO CHANGES, system STRONG. Verified DB: 24h 27... |
| 2026-08-18 | 342e7b7 | CEO: Run 89 — NO CHANGES, system strong, verified 24h 33T +/... |
| 2026-08-17 | 9a2293a | CEO: 83rd run — NO CHANGES, system STRONG, ct-hot+ CLEARED. ... |
| 2026-08-17 | 22b8e99 | CEO: 74th run — NO CHANGES, system STRONG. 24h 41T +/usr/bin... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*