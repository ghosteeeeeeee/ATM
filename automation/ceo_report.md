## CEO Report — 2026-08-08 (14:00 UTC)

### Diagnosis (Verified Numbers — DB queried directly)

| Period | Trades | PnL | WR |
|--------|--------|-----|-----|
| Last 24h | 49 | +$0.27 | 59.2% |
| Last 7d | 406 | -$8.70 | 38.7% |

**Daily trend (7d):**
- Aug 1: 8t, -$0.60, 12.5% WR
- Aug 2: 46t, -$3.87, 8.7% WR
- Aug 3: 32t, -$3.07, 6.3% WR
- Aug 4: 32t, -$3.50, 3.1% WR
- Aug 5: 139t, +$2.32, 44.6% WR ← turning point
- Aug 6: 82t, -$0.54, 56.1% WR
- Aug 7: 56t, +$0.40, 62.5% WR
- Aug 8: 11t, +$0.15, 54.5% WR (partial)

**Direction breakdown (7d):**
- LONG: 162t, -$1.38, 48.1% WR
- SHORT: 244t, -$7.33, 32.4% WR ← hemorrhaging

**Worst SHORT signals (7d, 3+ trades):**
- inv-accel-300-: 30t, -2.06, 16.7% WR (disabled, historical)
- zscore-rising-: 44t, -1.37, 25.0% WR (disabled, historical)
- vel-hermes-: 58t, -1.14, 31.0% WR (disabled, historical)
- pattern_wolf_wave_bear: 9t, -0.79, 11.1% WR (disabled)
- bb_bounce: 10t, -0.56, 30.0% WR (combo trades from before kill)

**Best signals (7d, 5+ trades):**
- tl_break_long: 20t, +1.17, 70.0% WR
- bb_bounce+,range_finder+: 9t, +0.38, 88.9% WR
- bb_bounce,hzscore+: 5t, +0.22, 100% WR

### Root Cause

7d SHORT bleed (-$7.33) is mostly historical trades from dead signals (inv-accel-300-, zscore-rising-, vel-hermes-) that were already killed. Current SHORT signals (last 24h) are -$0.46 on14 trades — small sample, not alarming. ATR SL widened 1.0%→1.2% today, need 24h to assess.

### Fix Applied

No new changes — today's ATR SL widening (1.0%→1.2%) + RETURN_EXHAUSTION_MINUS kill are fresh. Monitor before adding more kills.

### Verification

- Target: SHORT PnL ≥ $0 within 48h (after dead signal trades age out)
- Watch: bb_bounce combos (range_finder+, ma100-cross+) — currently profitable, keep enabled
- ATR SL 1.2% impact: check if SL hits decrease tomorrow
- pipeline.log at 1.6GB — needs log rotation (not blocking, logged as tech debt)
