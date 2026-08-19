# Signal Performance Report
**Period:** 2026-08-19 ~17:00 UTC | Last 6h / 24h / 7d

---

## EXECUTIVE SUMMARY

- **24h:** 23 trades total (LOW VOLUME — regime flat)
- **7d:** 321 trades total
- **Kill candidates:** NONE (all historical losers already dead/disabled)
- **Boost candidates:** r2-trend-long family, bb_bounce+,hl_copy_trader
- **Inversions:** NONE detected
- **Issues:** Low24h trade volume (23T) — regime-dependent starvation

---

## KILLED (executed this cycle)

None. All historical losers already in NEVER_REENABLE_FLAGS or blacklisted.

---

## BOOSTED (executed this cycle)

None. No new signals crossing boost threshold.

---

## WINNERS (active, sorted by 7d PnL)

| Signal | Dir | Trades | WR% | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| bb_bounce+,hl_copy_trader | LONG | 7 | 57.1% | +$0.30 | ACTIVE — best combo |
| r2-trend-long2 | LONG | 17 | 64.7% | +$0.19 | ACTIVE — core signal |
| return_exhaustion_long | LONG | 9 | 55.6% | +$0.11 | ACTIVE |
| r2-trend-long5 | LONG | 6 | 66.7% | +$0.08 | ACTIVE |
| r2-trend-long4 | LONG | 15 | 60.0% | +$0.06 | ACTIVE — 72.7% WR last 3d |

**3d standout:** `bb_bounce+,hl_copy_trader` 5T 80% WR +$0.33

---

## LOSERS (watch list — 7d, active signals)

| Signal | Dir | Trades | WR% | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| hzscore- | SHORT | 19 | 57.9% | -$0.18 | ACTIVE — positive WR but inverted R:R |
| r2-trend-long3 | LONG | 26 | 53.8% | -$0.21 | ACTIVE — high volume, marginal loss |
| range_breakout_short | SHORT | 27 | 44.4% | -$0.23 | DEAD (range_breakout_short killed 2026-08-17) |

Note: `hzscore-` has good WR but negative PnL — avg loss exceeds avg win. Monitor.

---

## DEAD SIGNALS (verified disabled)

| Signal | Reason | Date Killed |
|--------|--------|-------------|
| wave_catcher+ | NEVER_REENABLE: 37.5% WR -$0.42 | 2026-08-17 |
| ct-hot+ | NEVER_REENABLE: 42.4% WR -$0.42 | 2026-08-17 |
| accel-300- | NEVER_REENABLE: 15% WR -$1.26 | 2026-08-17 |
| range_finder+ | NEVER_REENABLE: 33.3% WR -$0.14 | 2026-08-16 |
| continuation+ | NEVER_REENABLE: 40% WR -$0.17 | 2026-08-16 |

---

## ISSUES

1. **Low24h volume (23T):** Normal for NEUTRAL regime. All filters operational — no action needed.
2. **No signal inversions detected.** All trades match expected direction.
3. **r2-trend-long3:** 26T 53.8% WR but -$0.21 — negative R:R (avg loss > avg win). Monitor for tuning if PnL doesn't improve.
4. **hzscore- SHORT:** 19T 57.9% WR but -$0.18 — inverted R:R pattern. Consider adding to never-reenable if PnL stays negative next cycle.

---

*Report generated: 2026-08-19 ~17:00 UTC*
*Next cycle: ~23:00 UTC*
