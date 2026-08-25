# Signal Performance Report
**Generated:** 2026-08-25 23:02 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,431 | **WR:** 48.6% | **PnL:** -76.40%
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
| hl_copy_trader | LONG | 11 | 36.4% | -6.44 | ❓ | Borderline |
| bb_bounce+ | LONG | 15 | 46.7% | -4.53 | ENABLED | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] hl_copy_trader LONG** — WR=36.4%, PnL=-6.44% over 11 trades. Monitor next cycle.
2. **[WATCH] bb_bounce+ LONG** — WR=46.7%, PnL=-4.53% over 15 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-25 | 4845662 | signals: slow_grind_short + signal starvation fixes (post-ch... |
| 2026-08-25 | c62afc0 | auto_1hr: Kill hl_copy_trader signal (12T/25%WR/-$1.13/24h).... |
| 2026-08-25 | c9f55aa | CEO: REVERT ATR_SL_MIN 1.5%→1.2% — wider SL worsened hit rat... |
| 2026-08-25 | 397a940 | orchestrator: kill ct-hot+ (-.65/7d), fix signal reporter SQ... |
| 2026-08-25 | f187671 | signals: relax atr-spike params for more frequent signals |
| 2026-08-25 | 3276349 | Signals: Fix pump_catcher review findings |
| 2026-08-25 | b621e21 | Signals: Add pump_catcher — momentum breakout signal |
| 2026-08-25 | 67c8abd | signals: mitigate losing streak — kill hl_copy_trader standa... |
| 2026-08-25 | 3890c64 | signals: kill tl_break_short — 28.6% WR, $-0.32 (24h), 7T |
| 2026-08-25 | 1350ec3 | scripts: widen ATR_SL_MIN 1.2%→1.5% — reduce atr_sl_hit domi... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*