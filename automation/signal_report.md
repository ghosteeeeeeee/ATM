# Signal Performance Report — 2026-08-05

## CRITICAL: tl_break Signal Inversions
5 signals fired with swapped directions at 14:28:25-26 UTC. All were profitable
by luck. This is a batch write bug in tl_break signal generation.

## Top Performers (24h)
- tl_break_long LONG: 100% WR, +$11.55 (10 trades)
- tl_break_long SHORT: 100% WR, +$6.06 (4 trades) — INVERTED
- vel-hermes- SHORT: 43.5% WR, +$5.00 (46 trades) — DISABLED but profitable
- zscore-rising- SHORT: 54.8% WR, +$2.69 (31 trades)
- bb_bounce LONG: 85.7% WR, +$2.68 (7 trades)

## Dead Signals
- decider SHORT: 11.1% WR, -$1.59 (9 trades) — should be disabled

## Recommendations
1. FIX tl_break inversion bug (batch write at 14:28)
2. DISABLE decider SHORT (11% WR)
3. RE-ENABLE vel-hermes- SHORT (+$5.00, 46 trades)
4. RE-ENABLE zscore-rising+ LONG (+$2.17, 62.5% WR)
