=== Signal Performance Report ===
Generated: 2026-08-21 22:40 UTC

## Summary
- **Volume too low for kill decisions.** 39 closed trades in 24h, 7 in 6h. Kill criteria require 5+ trades/24h — no signal qualifies.
- **No signal inversions** detected.
- **All previously killed signals remain dead** (checked NEVER_REENABLE_FLAGS).

---

## 6h Performance

| Signal | Dir | Trades | WR | PnL | Avg PnL | Status |
|--------|-----|--------|-----|-----|---------|--------|
| hl_copy_trader | LONG | 6 | 33.3% | -$0.19 | -$0.032 | WATCH |
| ct-hot+ | LONG | 1 | 0.0% | -$0.11 | -$0.110 | — |

## 24h Performance

| Signal | Dir | Trades | WR | PnL | Avg PnL | Status |
|--------|-----|--------|-----|-----|---------|--------|
| hl_copy_trader | LONG | 22 | 54.5% | +$0.53 | +$0.024 | WINNER |
| ct-hot+ | LONG | 15 | 40.0% | +$0.26 | +$0.017 | OK |
| r2-trend-long3 | LONG | 1 | 100% | +$0.28 | +$0.280 | — |
| hl_copy_trader | SHORT | 1 | 0.0% | -$0.11 | -$0.110 | — |

## 48h Performance (>=5 trades)

| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| r2-trend-long3 | LONG | 7 | 57.1% | +$0.13 | OK |
| ct-hot+ | LONG | 15 | 40.0% | +$0.26 | OK |
| hl_copy_trader | LONG | 22 | 54.5% | +$0.53 | WINNER |

## 7d Performance (>=3 trades, sorted by PnL)

| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| r2-trend-short2 | SHORT | 3 | 0.0% | -$0.22 | DEAD (7d) |
| ct-hot- | SHORT | 4 | 0.0% | -$0.19 | DEAD (7d) |
| continuation+ | LONG | 3 | 0.0% | -$0.18 | DEAD (7d) |
| range_breakout_short | SHORT | 3 | 0.0% | -$0.17 | DEAD (7d) |
| hl_copy_trader | SHORT | 3 | 0.0% | -$0.16 | DEAD (7d) |
| range_finder+ | LONG | 9 | 33.3% | -$0.14 | LOSER (7d) |
| wave_catcher- | SHORT | 4 | 25.0% | -$0.10 | DEAD (7d) |
| None | LONG | 7 | 28.6% | -$0.07 | LOSER (7d) |
| ct-hot+ | LONG | 54 | 46.3% | -$0.04 | MARGINAL (7d) |
| stop_hunt_reversal_long+ | LONG | 10 | 60.0% | -$0.04 | MARGINAL (7d) |
| hzscore- | SHORT | 4 | 75.0% | +$0.10 | — |
| return_exhaustion_long | LONG | 9 | 55.6% | +$0.12 | OK |
| r2-trend-long5 | LONG | 6 | 66.7% | +$0.14 | OK |
| r2-trend-long4 | LONG | 15 | 66.7% | +$0.15 | WINNER |
| r2-trend-long3 | LONG | 26 | 53.8% | +$0.19 | WINNER |
| bb_bounce+ | LONG | 21 | 57.1% | +$0.32 | WINNER |
| r2-trend-long6 | LONG | 6 | 100.0% | +$0.40 | WINNER |
| hl_copy_trader | LONG | 24 | 54.2% | +$0.42 | WINNER |

---

## KILLED (executed this cycle)
None — no signal meets kill criteria (5+ trades/24h, WR<30%, PnL<-$0.10).

## BOOSTED (executed this cycle)
None — no signal meets boost criteria with sufficient 24h sample.

## WATCH LIST (trending poorly, need more data)
- **hl_copy_trader SHORT**: 0% WR, -$0.11 (24h) — but only 1 trade. 7d: 0% WR, -$0.16 (3 trades). Monitor.
- **range_finder+**: 33.3% WR, -$0.14 (7d, 9 trades). Negative but not yet in kill zone.
- **ct-hot+**: 40% WR, +$0.26 (24h) is OK, but 46.3% WR, -$0.04 (7d, 54 trades) shows long-term margin compression. Watch for deterioration.

## WINNERS (active, performing)
- **hl_copy_trader LONG**: 54.5% WR, +$0.53 (24h, 22 trades). Consistent across 24h/48h/7d.
- **r2-trend-long3/4/5/6**: All positive. r2-trend-long4 best: 66.7% WR, +$0.15 (7d, 15 trades).
- **bb_bounce+**: 57.1% WR, +$0.32 (7d, 21 trades).

## ISSUES
- **Very low trade volume**: 39 trades in 24h across entire system. Market may be in a quiet period — signal performance data is thin. Re-run in 6h when more data accumulates.
- **No inversions** found — signal direction mapping is clean.
- **Previously dead signals confirmed dead**: wave_catcher, momentum_leaderboard, vel-hermes, accel-300 family, zscore-rising, tl-break (re-enabled 8/16), hzscore+/-, pct-hermes+ all remain in NEVER_REENABLE_FLAGS or set False.
