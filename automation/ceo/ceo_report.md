## CEO Report — 2026-08-16 (37th run)

### Diagnosis
System -$0.84/24h (34.0% WR, RED). Today 33T -$0.67 at 30.3% WR — worst day, legacy ct-hot+ clearing + Sunday low volume. Real system (excl ct-hot+) 48h: 64T -$0.36 (46.9% WR) — weak but improving. PM_TRAIL 40T 67.5% WR +$1.06/48h carrying system. ATR_SL 37T 2.7% WR -$2.43 is the dominant drag (83% of all losses). 4 open trades flat ($0.01 unrealized).

### Root Cause
Entry quality bottleneck. ATR_SL hits 37/48h with 2.7% WR — 36 of 37 trades hit ATR SL before PM_TRAIL can activate. ATR_SL daily trend improving: Aug12 41→Aug13 28→Aug14 28→Aug15 20→Aug16 15 (SPEED_MIN 40 working). The filter is working but needs full 24h eval. ct-hot+ legacy 33T/48h -$0.42 dominates — all flags False, just aging out.

### Fix Applied
**NO CHANGES this run.** Eval window active:
- SIGNAL_FILTER_SPEED_MIN 40 — ATR_SL hits trending down (41→15), needs 24h eval
- PM_TRAIL 0.15% dist — working (67.5% WR, avg +0.26%)
- ct-hot+ legacy clearing naturally (all flags False, should clear Aug 17-18)
- Stars intact: return_exhaustion_long 100% +$0.43, bb_bounce+ 63.6% +$0.25, r2-trend-long2 64.7% +$0.19
- R:R 0.51:1 (PM_TRAIL +0.26% vs ATR_SL -0.66%) — improving from 0.44:1

### Verification
| Metric | Before (36th) | Current (37th) | Target |
|--------|--------|---------|--------|
| 48h PnL | -$0.77 | -$0.78 | $0 |
| PM_TRAIL WR | 72.0% | 67.5% | >60% |
| ATR_SL hits | 37/48h | 37/48h | <20/48h |
| R:R | 0.51:1 | 0.51:1 | >1:1 |
| Daily trades | 32T | 33T | >20T |
| ATR_SL daily trend | 41→15 | 41→15 | ↓ |

### Next Actions
1. Monitor ATR_SL hit count after SPEED_MIN 40 takes effect (24h)
2. ct-hot+ legacy age-out (Aug 17-18)
3. PM_TRAIL 0.15% dist must hold >60% WR
4. Phantom trades root cause (guardian_orphan — backlog)
5. R:R should improve as ATR_SL hits decline
