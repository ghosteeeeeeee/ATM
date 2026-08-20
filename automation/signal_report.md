# Signal Performance Report
**Generated:** 2026-08-20 19:00 UTC | **Period:** Last 6h + 24h

---

## 6h Performance (min 2 trades)

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| r2-trend-long3 | LONG | 3 | 66.7% | -$0.06 |
| r2-trend-long4 | LONG | 2 | 100% | +$0.04 |

## 24h Performance (min 3 trades)

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| r2-trend-long3 | LONG | 7 | 71.4% | -$0.02 |
| stop_hunt_reversal_long+ | LONG | 5 | 60.0% | +$0.01 |
| r2-trend-long6 | LONG | 3 | 100% | +$0.25 |
| r2-trend-short2 | SHORT | 3 | 0.0% | -$0.23 |

---

## KILLED (executed)

None — no signals meet kill threshold (5+ trades, WR < 30%, PnL < -$0.10 over 24h).

## BOOSTED (executed)

None — no signals meet boost threshold (5+ trades, WR > 55%, PnL > $0.05) with enough trade volume.

## LOSERS (watch list)

| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| r2-trend-short2 | SHORT | 3 | 0.0% | -$0.23 | WATCH — 0% WR, 3 trades. Kill if 5+ trades stay 0%. |

## WINNERS

| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| r2-trend-long6 | LONG | 3 | 100% | +$0.25 | Strong — monitor for consistency |
| r2-trend-long4 | LONG | 2 | 100% | +$0.04 | Early winner — needs more trades |
| r2-trend-long3 | LONG | 7 | 71.4% | -$0.02 | INVERTED R:R — avg_win=$0.042, avg_loss=$0.115 (2.7:1 against). Tighten stops. |
| stop_hunt_reversal_long+ | LONG | 5 | 60.0% | +$0.01 | Positive, meeting criteria |

## SIGNAL INVERSIONS

None found.

## NOTES

- Overall volume is low this period — 24 total closed trades across all signals.
- r2-trend-short2 is the only clear loser but needs 5+ trades before kill.
- r2-trend-long3 has 71.4% WR but -$0.02 PnL — winners are small, losers are big. Worth investigating avg win vs avg loss.
- No bugs or anomalies detected.
