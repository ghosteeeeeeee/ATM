# Signal Performance Report
**Generated:** 2026-09-02 05:08 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (24h):** 61 | **Open:** 3
- **Last 6h:** 27 trades
- **Close reasons (24h):** ATR SL: 44T (25% WR, -$2.18) | Profit Trail: 17T (100% WR, +$1.01)

---

## KILLED (executed this cycle)

None. No signals meet all 3 kill criteria simultaneously:
- `accel-300-v2-short-` — 28.6% WR, $-0.06 PnL, 7T. WR<30% ✓, 5+T ✓, but PnL > -$0.10 ✗. Already in NEVER_REENABLE.
- `accel-300-v2-long` — 25.0% WR, $-0.10 PnL, 4T. Only 4 trades (needs 5+). Already killed by auto_1hr.

---

## BOOSTED

None. No signals meet all boost criteria (WR>55%, PnL>0, 5+T).

---

## LOSERS (watch list — not meeting kill criteria but underperforming)

| Signal | Dir | 24h T | 24h WR | 24h PnL | 6h T | 6h WR | 6h PnL | Status |
|--------|-----|-------|--------|---------|------|-------|--------|--------|
| accel-300-v3-long+ | LONG | 13 | 38.5% | $-0.59 | 13 | 38.5% | $-0.59 | ⚠️ TUNE |
| bb-bounce-long+ | LONG | 17 | 52.9% | $-0.33 | — | — | — | ⚠️ R:R BAD |
| accel-300-v2-short- | SHORT | 7 | 28.6% | $-0.06 | 7 | 28.6% | $-0.06 | DEAD (NEVER_REENABLE) |
| accel-300-v2-long | LONG | 4 | 25.0% | $-0.10 | — | — | — | DEAD (auto_1hr killed) |
| bb-bounce-short | SHORT | 3 | 66.7% | $-0.03 | — | — | — | Needs data |
| r2-trend-long3 | LONG | 4 | 50.0% | $-0.02 | 2 | 50.0% | $0.04 | Needs data |

---

## WINNERS

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|---------|--------|
| profit-monster-trail | — | 17 | 100% | +$1.01 | Exit strategy working |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## KEY FINDINGS

1. **Stop losses dominate losses** — 44/61 trades (72%) hit ATR SL with 25% WR, contributing -$2.18. Only 17 trades hit profit trail (100% WR, +$1.01). The system is bleeding on stops.

2. **accel-300-v3-long+ is the biggest loser** — 13T, 38.5% WR, -$0.59. All recent losses are ATR SL hits. Needs tighter entry filters or wider stops.

3. **bb-bounce-long+ has broken R:R** — 52.9% WR but -$0.33 PnL. Wins avg ~$0.06, losses avg ~$0.10. R:R ~0.6:1. Needs wider TP or tighter SL.

4. **No kills executed this cycle** — existing NEVER_REENABLE flags already cover dead signals. No new kills warranted by criteria.

---

## RECOMMENDATIONS

1. **[TUNE] accel-300-v3-long+** — Raise MIN_PULLBACK or MIN_SLOPE_PCT to filter weak entries. Consider widening ATR SL multiplier.
2. **[TUNE] bb-bounce-long+** — Raise profit target or widen SL. R:R must exceed 1:1 to be viable.
3. **[MONITOR] bb-bounce-short** — Only 3T, too early. Keep enabled, check next cycle.
4. **[MONITOR] r2-trend-long3** — Only 4T. Keep enabled, check next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-02 | 550928b | signals: v3 add MIN_PEAK_DISTANCE filter — block local top e... |
| 2026-09-02 | 746cea8 | signals: v3 fix confidence saturation + lower RSI_MAX to 68 |
| 2026-09-02 | 6127479 | signals: fix v3 short constants — import from hermes_constan... |
| 2026-09-02 | 383057f | signals: disable v2 short, add v3 short to bypass lists |
| 2026-09-02 | 4316a8a | fix: candles_5m stale timer + context gate NAY override |
| 2026-09-02 | 2bd681c | signals: add range_reversion to STANDALONE_BYPASS_SIGNALS |
| 2026-09-02 | 20e77fd | fix: stronger loser filtering |
| 2026-09-02 | 9e3b310 | signals: v3 filter tuning — block overbought chasing entries |
| 2026-09-01 | ac5d65e | signals: accel_300_v3_long — fix own-conclusions audit findi... |
| 2026-09-01 | bac2590 | fix: remove ACE from SHORT_BLACKLIST |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
