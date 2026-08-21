# Signal Performance Report
**Generated:** 2026-08-21 11:30 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (7d):** 154 | **Daily avg:** ~22 trades
- **Date range:** 2026-08-14 → 2026-08-21

---

## 6h Performance (min 2 trades)

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| hl_copy_trader | LONG | 6 | 83.3% | +$4.00 |
| ct-hot+ | LONG | 2 | 50.0% | +$0.12 |

## 24h Performance (all signals)

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| hl_copy_trader | LONG | 6 | 83.3% | +$4.00 |
| r2-trend-long3 | LONG | 5 | 60.0% | +$0.23 |
| r2-trend-long4 | LONG | 2 | 100.0% | +$0.04 |
| r2-trend-long13 | LONG | 1 | 100.0% | +$0.03 |
| r2-trend-long16 | LONG | 1 | 100.0% | +$0.02 |
| r2-trend-long11 | LONG | 1 | 100.0% | +$0.04 |
| ct-hot+ | LONG | 2 | 50.0% | +$0.12 |
| r2-trend-long8 | LONG | 1 | 0% | -$0.10 |
| hl_copy_trader | SHORT | 1 | 0% | -$0.11 |

**24h total:** 10 trades, +$4.29 PnL

---

## 7d Performance (min 3 trades)

### Losers

| Signal | Dir | Trades | WR | PnL | Avg PnL |
|--------|-----|--------|-----|-----|---------|
| ct-hot+ | LONG | 35 | 42.9% | -$0.30 | -$0.009 |
| range_breakout_short | SHORT | 3 | 0.0% | -$0.27 | -$0.090 |
| r2-trend-short2 | SHORT | 3 | 0.0% | -$0.22 | -$0.073 |
| ct-hot- | SHORT | 4 | 0.0% | -$0.19 | -$0.048 |
| range_finder+ | LONG | 9 | 33.3% | -$0.14 | -$0.016 |
| wave_catcher- | SHORT | 4 | 25.0% | -$0.10 | -$0.025 |
| wave_catcher+ | SHORT | 3 | 33.3% | -$0.04 | -$0.013 |

### Winners

| Signal | Dir | Trades | WR | PnL | Avg PnL |
|--------|-----|--------|-----|-----|---------|
| r2-trend-long6 | LONG | 6 | 100.0% | +$0.40 | +$0.067 |
| r2-trend-long2 | LONG | 9 | 66.7% | +$0.10 | +$0.011 |
| return_exhaustion_long | LONG | 9 | 55.6% | +$0.12 | +$0.013 |
| r2-trend-long4 | LONG | 15 | 66.7% | +$0.15 | +$0.010 |
| r2-trend-long3 | LONG | 31 | 58.1% | +$0.20 | +$0.006 |

---

## KILLED (executed)
None. 24h volume too low (10 trades) — no signal hits kill threshold.

## BOOSTED (executed)
None. 24h volume too low for boost validation.

## WATCH LIST (7d losers, monitoring)
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| ct-hot+ | LONG | 35 | 42.9% | -$0.30 | Borderline — needs monitoring |
| range_finder+ | LONG | 9 | 33.3% | -$0.14 | Watch |
| range_breakout_short | SHORT | 3 | 0% | -$0.27 | Watch — insufficient sample |
| r2-trend-short2 | SHORT | 3 | 0% | -$0.22 | Watch — insufficient sample |

## WINNERS
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| hl_copy_trader | LONG | 6 | 83.3% | +$4.00 | Dominant |
| r2-trend-long6 | LONG | 6 | 100% | +$0.40 | Perfect |
| r2-trend-long4 | LONG | 15 | 66.7% | +$0.15 | Consistent |
| r2-trend-long3 | LONG | 31 | 58.1% | +$0.20 | Workhorse |

## ISSUES
- **Signal inversions:** None found in 24h
- **SHORT signals are dead:** All 7d SHORT signals have negative PnL (range_breakout_short 0% WR, r2-trend-short2 0% WR, ct-hot- 0% WR, wave_catcher- 25% WR). Consider blocking or retuning SHORT signal sources.
- **Low volume:** Only 10 trades in 24h — system is operating well below capacity. Pipeline may be starved of signals or market is quiet.
- **hl_copy_trader SHORT:** 1T, 0% WR, -$0.11 — but sample too small to act on.
