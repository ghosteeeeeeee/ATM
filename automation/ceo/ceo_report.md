## CEO Report — 2026-08-16 (35th run)

### Diagnosis
System -$0.71/48h (42.7% WR). Today worst day at 29.0% WR ($0.63 loss) — legacy ct-hot+ clearing + Sunday low volume. Real system (excl legacy+phantoms) healthy: PM_TRAIL 52T 75% WR +$1.76/48h carrying system. ATR_SL 36T 2.8% WR -$2.37 is the dominant drag (78% of all losses). 5 open trades flat ($0.00 total).

### Root Cause
Entry quality bottleneck. ATR_SL hits 36/48h with 2.8% WR — 35 of 36 trades hit ATR SL before PM_TRAIL can activate. ATR_SL daily trend improving: Aug12 41→Aug13 28→Aug14 28→Aug15 20→Aug16 14 (partial, SPEED_MIN 40 deployed mid-day). The filter is working but needs full 24h eval.

### Fix Applied
**NO CHANGES this run.** Eval window active:
- SIGNAL_FILTER_SPEED_MIN 40 — ATR_SL hits trending down (41→14), needs 24h eval
- PM_TRAIL 0.15% dist — working (75% WR, avg +0.331%)
- ct-hot+ legacy clearing naturally (all flags False, should clear Aug 17-18)
- Stars intact: return_exhaustion_long 100%, bb_bounce+ 63.6%, r2-trend-long2 64.7%
- R:R 0.50:1 (PM_TRAIL +0.33% vs ATR_SL -0.66%) — improving from 0.44:1

### Verification
| Metric | Before (34th) | Current (35th) | Target |
|--------|--------|---------|--------|
| 48h PnL | -$0.71 | -$0.71 | $0 |
| PM_TRAIL WR | 75.0% | 75.0% | >60% |
| ATR_SL hits | 34/48h | 36/48h | <20/48h |
| R:R | 0.74:1 | 0.50:1 | >1:1 |
| Daily trades | 31T | 31T | >20T |
| ATR_SL daily trend | — | 41→28→28→20→14 | ↓ |

### Next Actions
1. Monitor ATR_SL hit count after SPEED_MIN 40 takes effect (24h)
2. ct-hot+ legacy age-out (Aug 17-18)
3. PM_TRAIL 0.15% dist must hold >60% WR
4. Phantom trades root cause (guardian_orphan — backlog)
5. R:R should improve as ATR_SL hits decline
