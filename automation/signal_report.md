# Signal Performance Report
**Generated:** 2026-08-09 13:46 UTC | **Period:** Last 6h + 24h + 7d (for context)

## Overall Stats
- **Total trades (24h):** 64 | **WR:** ~52% | **Net PnL:** ~+$0.30
- **Total trades (7d):** 433 | **WR:** ~44% | **Net PnL:** ~-$5.00 (Aug 2-4 legacy bleeds aging out)

---

## KILLED THIS RUN (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| vortex_break_long (compounds) | LONG | 22.2% (24h) | -$0.18 (24h) | 9 (24h), 25 (7d) | `VORTEX_BREAK_PLUS_ENABLED=False` + added to NEVER_REENABLE_FLAGS |

**Justification:** All three kill criteria met.
- WR < 30% with 5+ trades (24h): 22.2% with 9 trades ✅
- Net PnL < -$0.10 (24h): -$0.18 ✅
- Active > 24h (since 2026-08-06): ✅
- 7d: 25 compounds, 44% WR, -$0.19 confirms the pattern

**Compounds killed** (all 0% WR in 24h):
- ma100-cross+,vortex_break_long: 4T -$0.20
- bb_bounce+,vortex_break_long: 2T -$0.06
- hzscore+,vortex_break_long: 1T -$0.05

---

## BOOSTED THIS RUN (executed)

None. Top performers are already firing at full volume (27 trades/24h).

---

## LOSERS (watch list — needs more data)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| bb-bounce-short,hl_copy_trader | SHORT | 2 | 0.0% | -$0.06 | ENABLED | Sub-threshold; watching |

(No other losers meet the 5+ trades, <30% WR threshold.)

---

## WINNERS (active, performing well)

| Signal | Dir | 24h T | 24h WR | 24h PnL | 7d T | 7d WR | 7d PnL | Status |
|--------|-----|-------|--------|---------|------|-------|--------|--------|
| bb_bounce+,range_finder+ | LONG | 27 | 51.9% | +$0.26 | 39 | 59.0% | +$0.77 | ENABLED — top star |
| bb-bounce-short,hzscore- | SHORT | 9 | 77.8% | +$0.25 | 9 | 77.8% | +$0.25 | ENABLED — strong |
| continuation+,hzscore+ | LONG | 3 | 66.7% | +$0.06 | 3 | 66.7% | +$0.06 | ENABLED — small sample |
| bb_bounce+,hzscore+ | LONG | 4 | 50.0% | +$0.03 | 5 | 100.0% | +$0.20 | ENABLED — positive 7d |

---

## ISSUES

- **No inversions** detected in 24h or 3d window.
- **vortex_break_short** still disabled (per 2026-08-08 CEO action). Raw 2 trades 7d 100% WR but tiny sample. Not re-enabling.
- **7d bleeds** (zscore-rising-, vel-hermes-, pattern_wolf_wave_bear, etc.) all confirmed DISABLED AND DEAD — last fire 2026-08-03 to 2026-08-04. Aging out of 7d window.

---

## RECOMMENDATIONS

1. **[DONE] Killed vortex_break_long** — all kill criteria met, added to NEVER_REENABLE_FLAGS.
2. **[KEEP] bb_bounce+,range_finder+ LONG** — system top earner. Already firing 27 trades/24h.
3. **[KEEP] bb-bounce-short,hzscore- SHORT** — 77.8% WR, SHORT bleeding-stopped hero.
4. **[MONITOR] bb_bounce+,hzscore+ LONG** — 4 trades 24h, 50% WR, +$0.03. 7d is 100% (5T +$0.20) — looks promising but small sample.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-09 | (this run) | signal_reporter: disable VORTEX_BREAK_PLUS — 22.2% WR (9T 24h), -$0.18 |
| 2026-08-09 | 0ed1acf | CEO 2026-08-10: disable MA_100_CROSS_PLUS — losing 5T/24h, 20% WR |
| 2026-08-09 | 56a6fe6 | signals: add engulfing candle signal |
| 2026-08-09 | e50164f | config: tighten PM_TRAIL_ACTIVATE_PCT 0.30→0.25 |
| 2026-08-09 | 2884d93 | CEO: Disabled MA_100_CROSS_MINUS_ENABLED, added regime filter to base ma_100_cross |
| 2026-08-08 | f5aa0d5 | signals: add return_exhaustion_short.py — SHORT-specific percentile exhaustion |
| 2026-08-08 | 8b8e345 | signals: add range_finder_short.py — SHORT-specific range fi... |
| 2026-08-08 | bb61874 | signals: add bb_bounce_short.py — SHORT-specific BB bounce w... |
| 2026-08-08 | 51754e3 | CEO: 24h +$0.13 (50% WR), 7d -$1.23. All fixes verified work... |
| 2026-08-08 | 16900d9 | signals: re-enable hzscore- with RS confluence boost |
| 2026-08-08 | 710c312 | fix: enable MA_100_CROSS_MINUS_ENABLED for new ma_100_cross_... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*