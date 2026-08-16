# Signal Performance Report
**Generated:** 2026-08-16 17:45 UTC | **Period:** Last 6h + 24h

## Overall Stats (24h)
- **Trades:** 51 | **WR:** 35.3% | **PnL:** -$0.68

---

## KILLS (already executed)

All underperformers already disabled in hermes_constants.py:
- ct-hot+ LONG: 26T 34.6% WR -$0.66 (legacy trades clearing)
- ct-hot- SHORT: 4T 0% WR -$0.19
- wave_catcher: all variants killed 2026-08-14/16
- range_breakout: all variants killed 2026-08-15/16
- trend_momentum_near_sma: killed 2026-08-12

---

## BOOST CANDIDATES

| Signal | Dir | 7d T | 7d WR | 7d PnL | Status |
|--------|-----|------|-------|--------|--------|
| bb_bounce+ | LONG | 22 | 63.6% | $0.25 | Hot-set priority |
| r2-trend-long2 | LONG | 17 | 64.7% | $0.19 | Monitor |
| r2-trend-long3 | LONG | 12 | 66.7% | $0.01 | High WR, low PnL |
| bb_bounce+,hzscore+ | LONG | 31 | 51.6% | $0.23 | Combo stable |

---

## LOSERS (watch list)

| Signal | Dir | 7d T | 7d WR | 7d PnL | Note |
|--------|-----|------|-------|--------|------|
| hzscore- | SHORT | 32 | 53.1% | -$0.21 | R:R inverted (wins small, losses large) |
| accel-300- | SHORT | 40 | 55.0% | -$0.30 | Same R:R issue |

---

## SIGNAL INVERSIONS

**None found.** All signals respect direction labels.

---

## KEY OBSERVATIONS

1. **Legacy ct-hot trades** still clearing — not new signals firing
2. **hzscore- and accel-300-** have decent WR but negative PnL — R:R problem (avg win < avg loss)
3. **bb_bounce+** is the most consistent performer — 63.6% WR with positive PnL
4. **6 trades with NULL signal** — data quality issue, -$0.10 PnL

---

*No new kills executed — all losers already disabled. Monitor hzscore-/accel-300- R:R for potential parameter tuning.*
