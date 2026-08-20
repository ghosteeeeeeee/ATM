# Signal Performance Report
**Generated:** 2026-08-20 23:02 UTC | **Period:** Last 6h + 24h + 7d context

## Overall Stats (24h)
- **Total closed trades:** 19 | **Total PnL:** -$0.53
- **Active signals:** r2-trend-long (multiple variants), bb_bounce+, r2-trend-short2 (re-enabled today)
- **No open trades** at time of report

---

## KILLED (executed)

None. All clear losers already disabled.

---

## BOOSTED (candidates)

| Signal | Dir | 7d WR | 7d PnL | 7d Trades | Status |
|--------|-----|-------|--------|-----------|--------|
| r2-trend-long6 | LONG | 100% | +$0.45 | 7 | Top performer |
| bb_bounce+,hl_copy_trader | LONG | 57.1% | +$0.30 | 7 | Strong combo |
| r2-trend-long2 | LONG | 64.7% | +$0.19 | 17 | Consistent |
| return_exhaustion_long | LONG | 55.6% | +$0.11 | 9 | Consistent |
| r2-trend-long4 | LONG | 64.7% | +$0.10 | 17 | Consistent |

These are already enabled. r2-trend-long6 and r2-trend-long4 have high WR with good sample size.

---

## LOSERS (watch list)

| Signal | Dir | 7d WR | 7d PnL | 7d Trades | Status |
|--------|-----|-------|--------|-----------|--------|
| r2-trend-long3 | LONG | 55.9% | -$0.23 | 34 | R:R problem — wins avg +$0.03, losses avg -$0.09 |
| r2-trend-short2 | SHORT | 0% | -$0.23 | 3 | Re-enabled today, too few trades |

**r2-trend-long3 root cause:** Good win rate (55.9%) but losses are ~3x bigger than wins. The ATR stop loss fires at -$0.10 while profit-monster-trail averages +$0.03. This is a parameter tuning issue, not a signal quality issue.

---

## WINNERS

| Signal | Dir | 7d WR | 7d PnL | 7d Trades | Status |
|--------|-----|-------|--------|-----------|--------|
| r2-trend-long6 | LONG | 100% | +$0.45 | 7 | Enabled |
| bb_bounce+,hl_copy_trader | LONG | 57.1% | +$0.30 | 7 | Enabled |
| r2-trend-long2 | LONG | 64.7% | +$0.19 | 17 | Enabled |
| return_exhaustion_long | LONG | 55.6% | +$0.11 | 9 | Enabled |
| r2-trend-long4 | LONG | 64.7% | +$0.10 | 17 | Enabled |
| r2-trend-long5 | LONG | 66.7% | +$0.08 | 6 | Enabled |
| bb_bounce+ | LONG | 40.0% | +$0.03 | 5 | Enabled |

---

## SIGNAL INVERSIONS

**No inversions found** in 24h or 7d.

---

## ISSUES

1. **r2-trend-long3 R:R imbalance** — 55.9% WR but -$0.23 PnL (34 trades). Avg win +$0.03 vs avg loss -$0.09. Consider tightening ATR stop loss or widening profit target. This is the single biggest active loser.
2. **r2-trend-short2 too early to judge** — 0% WR with only 3 trades. Was re-enabled today with RSI inversion fix + threshold tightening. Monitor next cycle.
3. **Low trade volume** — 19 trades in 24h across all signals. System is conservative by design.

---

## 7d LOBBY (already killed, confirm stays dead)

| Signal | 7d WR | 7d PnL | 7d Trades | Status |
|--------|-------|--------|-----------|--------|
| ct-hot+ | 42.4% | -$0.42 | 33 | DISABLED |
| range_breakout_short | 20.0% | -$0.28 | 5 | DISABLED |
| wave_catcher+ | 40.0% | -$0.27 | 15 | NEVER_REENABLE |
| continuation+ | 40.0% | -$0.17 | 5 | DISABLED |
| mover+ | 28.6% | -$0.15 | 7 | DISABLED |
| range_finder+ | 33.3% | -$0.14 | 9 | DISABLED |

---

## RECOMMENDATIONS

1. **[TUNE] r2-trend-long3** — R:R is broken. Wins +$0.03 avg, losses -$0.09 avg. Tighten ATR_SL or widen profit-monster target. 34 trades is enough data.
2. **[WATCH] r2-trend-short2** — Re-enabled today with fixes. 3 trades only. Give it 48h before judging.
3. **No kills needed** — All clear losers already disabled. System is clean.

---

*Report auto-generated. Next report: ~6h from now.*
