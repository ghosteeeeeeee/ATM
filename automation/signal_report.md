# Signal Performance Report
**Generated:** 2026-08-20 05:00 UTC | **Period:** Last 6h + 24h

## Overall Stats (24h)
- **Total trades:** 25 | **Total PnL:** $0.41

---

## KILLED (executed):

None.

---

## BOOSTED (executed):

None.

---

## WINNERS (WR > 55%, 5+ trades, 24h):

| Signal | Dir | WR | PnL | Trades |
|--------|-----|-----|-----|--------|
| r2-trend-long3 | LONG | 100% | $0.17 | 3 |
| r2-trend-long4 | LONG | 75% | $0.12 | 4 |

---

## LOSERS (watch list, 24h):

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| stop_hunt_reversal_long+ | LONG | 50% | -$0.10 | 6 | WATCH — borderline, 6T small sample |
| spike_exhaustion_short- | SHORT | 50% | -$0.06 | 2 | WATCH — too few trades |

---

## MARGINAL:

| Signal | Dir | WR | PnL | Trades |
|--------|-----|-----|-----|--------|
| stop_hunt_reversal_long+ | LONG | 50% | -$0.10 | 6 |

---

## SIGNAL INVERSIONS:

**No inversions found.**

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-19 | f247ff3 | CEO: run 153, verified DB, NO CHANGES — system healthy 72% W... |
| 2026-08-19 | 22871f8 | signals: replace EMA hard filter with score penalty for SHOR... |
| 2026-08-19 | 32ad963 | scripts: add confidence filter (conf>=89) + time block (01-0... |
| 2026-08-19 | 93d8edc | CEO run 143: NO CHANGES — system IMPROVING. 24h 22T +/usr/bi... |
| 2026-08-19 | 3d90495 | CEO run 135: NO CHANGES — system healthy, PM_TRAIL 92.9% WR ... |
| 2026-08-19 | dea5b15 | CEO run 134: RAISED R2_TREND_LONG_MIN_PRE_MOVE 0.2→0.3 |
| 2026-08-19 | a4b55d0 | Daily trading system update (2026-08-19) |
| 2026-08-18 | 37b90e1 | signals: disable return_exhaustion_long (3T/0%WR auto-kill) |
| 2026-08-18 | 15dc023 | CEO run 112: NO CHANGES — system strong, PM_TRAIL carrying, ... |
| 2026-08-18 | b004ff6 | CEO: Run 97 — NO CHANGES, system STRONG. Verified DB 24h 27T... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*