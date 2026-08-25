# Signal Performance Report
**Generated:** 2026-08-25 17:02 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,425 | **WR:** 48.6% | **PnL:** -72.93%
- **Date range:** 2026-07-29 → 2026-08-25

---

## WINNERS (WR > 55%, PnL > 0)

None found.

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| hl_copy_trader | LONG | 10 | 40.0% | -5.10 | ❓ | Borderline |
| tl_break_short | SHORT | 6 | 50.0% | -1.31 | DISABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] hl_copy_trader LONG** — WR=40.0%, PnL=-5.10% over 10 trades. Monitor next cycle.
2. **[WATCH] tl_break_short SHORT** — WR=50.0%, PnL=-1.31% over 6 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-25 | f187671 | signals: relax atr-spike params for more frequent signals |
| 2026-08-25 | 3276349 | Signals: Fix pump_catcher review findings |
| 2026-08-25 | b621e21 | Signals: Add pump_catcher — momentum breakout signal |
| 2026-08-25 | 67c8abd | signals: mitigate losing streak — kill hl_copy_trader standa... |
| 2026-08-25 | 3890c64 | signals: kill tl_break_short — 28.6% WR, $-0.32 (24h), 7T |
| 2026-08-25 | 1350ec3 | scripts: widen ATR_SL_MIN 1.2%→1.5% — reduce atr_sl_hit domi... |
| 2026-08-25 | 0db8082 | Daily trading system update (2026-08-25) |
| 2026-08-25 | 5ba6408 | auto_1hr: no changes 2026-08-25 04:05 UTC - 2T last hour pro... |
| 2026-08-25 | a10a912 | fix: add bb-bounce-short to standalone bypass list |
| 2026-08-25 | 30f5e90 | fix: raise slope threshold 0.01%→0.05% to unblock SHORT sign... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*