# Signal Performance Report
**Generated:** 2026-08-16 00:45 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Date range:** 2026-07-29 → 2026-08-16

---

## KILLED (executed)
All underperformers already disabled in previous cycles:
| Signal | Dir | WR | PnL (24h) | Trades | Action |
|--------|-----|----|-----------|--------|--------|
| ct-hot- | SHORT | 0.0% | -$0.19 | 4 | Already killed (COIN_TRACKER_HOT_MINUS_ENABLED=False) |
| range_finder+ | LONG | 33.3% | -$0.14 | 9 | Already killed (RANGE_FINDER_PLUS_ENABLED=False) |
| wave_catcher- | SHORT | 25.0% | -$0.09 | 4 | Already killed (WAVE_CATCHER_MINUS_ENABLED=False) |

**No new kills this cycle.** All losers already disabled.

---

## BOOSTED (executed)
| Signal | Dir | WR | PnL (24h) | Trades | Action |
|--------|-----|----|-----------|--------|--------|
| ct-hot+ | LONG | 57.1% | +$0.19 | 21 | Already boosted (hot-set primary) |
| return_exhaustion_long | LONG | 100.0% | +$0.39 | 3 | Watch — needs 5+ trades to boost |

**No new boosts this cycle.** Winners already promoted.

---

## LOSERS (watch list)
| Signal | Dir | WR | PnL (24h) | Trades | Status |
|--------|-----|----|-----------|--------|--------|
| continuation+ | LONG | 0.0% | -$0.18 | 2 | WATCH — too few trades |
| range_finder- | SHORT | 0.0% | -$0.06 | 1 | WATCH — too few trades |

---

## WINNERS
| Signal | Dir | WR | PnL (24h) | Trades | Status |
|--------|-----|----|-----------|--------|--------|
| return_exhaustion_long | LONG | 100.0% | +$0.39 | 3 | Active — needs 5+ trades for boost |
| ct-hot+ | LONG | 57.1% | +$0.19 | 21 | Active — hot-set primary |
| r2-trend-long6 | LONG | 100.0% | +$0.11 | 2 | Active |
| ct-hot+,hl_copy_trader | LONG | 100.0% | +$0.07 | 2 | Active |

---

## SIGNAL INVERSIONS (24h)
**No inversions found.** All signals respect their direction labels.

---

## ISSUES
- None this cycle. System stable.

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-15 | 011fb51 | config: blacklist 2Z (96h both-direction loser) |
| 2026-08-15 | d6f0a87 | signals: kill ct-hot- (SHORT direction) — 4T 0% WR, all losi... |
| 2026-08-15 | c917915 | CEO: Aug 16 verified run — no changes, eval windows closing ... |
| 2026-08-15 | 0844a0c | config: blacklist 12 both-direction losers (30d analysis) |
| 2026-08-15 | 7d054f6 | scripts: deploy Weather Vane Position Shield (Component 2) |
| 2026-08-15 | 96ab3a3 | CEO: 2026-08-15 23:00 UTC — no changes, eval windows active,... |
| 2026-08-15 | 5538ed0 | CEO: NO CHANGES — eval windows closing tomorrow, R:R 0.68:1 ... |
| 2026-08-15 | 18c9764 | CEO: widened PM_TRAIL_DISTANCE_PCT 0.40%→0.60% — R:R fix |
| 2026-08-15 | 9987e77 | CEO: PM_TRAIL tightened 0.60%→0.40% + NEUTRAL speed override... |
| 2026-08-15 | 387b54b | CEO: LOWERED PM_TRAIL_ACTIVATE_PCT 0.60%→0.40% — R:R fix |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
