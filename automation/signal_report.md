# Signal Performance Report
**Generated:** 2026-08-11 07:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 731 | **WR:** 44.9% | **PnL:** -11.79%
- **Date range:** 2026-07-29 → 2026-08-11

---

## WINNERS (WR > 55%, PnL > 0)

None found.

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| bb_bounce+,hzscore+ | LONG | — | —% | — | 14 | 28.6% | -2.54 | ENABLED | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| bb_bounce+,range_finder+ | LONG | 7 | 42.9% | -0.79 | ENABLED | Borderline |
| hl_copy_trader,range_breakout- | SHORT | 2 | 50.0% | -0.20 | ❓ | Needs more data |
| range_breakout-,vortex_break_short | SHORT | 2 | 50.0% | +0.12 | ENABLED | Needs more data |
| hzscore-,vortex_break_short | SHORT | 2 | 50.0% | +0.74 | ENABLED | Needs more data |
| continuation+,hzscore+ | LONG | 3 | 33.3% | +1.65 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] bb_bounce+,hzscore+ LONG** — WR=28.6%, PnL=-2.54% over 14 trades (24h).
2. **[WATCH] bb_bounce+,range_finder+ LONG** — WR=42.9%, PnL=-0.79% over 7 trades. Monitor next cycle.
3. **[WATCH] hl_copy_trader,range_breakout- SHORT** — WR=50.0%, PnL=-0.20% over 2 trades. Monitor next cycle.
4. **[WATCH] range_breakout-,vortex_break_short SHORT** — WR=50.0%, PnL=+0.12% over 2 trades. Monitor next cycle.
5. **[WATCH] hzscore-,vortex_break_short SHORT** — WR=50.0%, PnL=+0.74% over 2 trades. Monitor next cycle.
6. **[WATCH] continuation+,hzscore+ LONG** — WR=33.3%, PnL=+1.65% over 3 trades. Monitor next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-11 | 7daf7fe | CEO: review 2026-08-11 08:00 UTC — NO CHANGES, SL revert mon... |
| 2026-08-11 | f7a3152 | CEO: Revert SL to 1.2% — 0.5% SL caused 64.7% SL hit rate (w... |
| 2026-08-11 | bcea2be | CEO: Revert SL widening — 0.5% SL was working, 1.2% caused 4... |
| 2026-08-11 | 9eab58b | signals: fix hardcoded numbers in both new signals |
| 2026-08-11 | ad5a63e | signals: add spike_exhaustion_short — fade violent spikes |
| 2026-08-11 | ab14c8d | signals: tune stop_hunt_reversal_long threshold |
| 2026-08-11 | 8285da0 | signals: add stop_hunt_reversal_long — catch violent long af... |
| 2026-08-11 | 3fcc5d7 | CEO: ack spec items #1/#3 implemented, bug fixes verified |
| 2026-08-10 | 5b6e89d | signals: trend_momentum_near_sma — full add-signal complianc... |
| 2026-08-10 | a4c2def | signals: add trend_momentum_near_sma signal |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*