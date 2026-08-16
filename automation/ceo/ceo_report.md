## CEO Report — 2026-08-16 (34th run)

### Diagnosis
System flat -$0.71/48h (42.7% WR). Today worst day at 29.0% WR ($0.63 loss) — legacy ct-hot+ clearing + Sunday low volume. Real system (excl legacy+phantoms) healthy: PM_TRAIL 75% WR +$1.76/48h carrying system. ATR_SL 34T 2.8% WR -$2.40 is the dominant drag (84% of all losses).

### Root Cause
Entry quality bottleneck. ATR_SL hits34/48h with 2.8% WR — 35 of 36 trades hit ATR SL before PM_TRAIL can activate. SIGNAL_FILTER_SPEED_MIN raised to 40 last run to filter low-quality entries. Needs 24h to evaluate.

### Fix Applied
**NO CHANGES this run.** Eval window active:
- SIGNAL_FILTER_SPEED_MIN 40 — set last run, monitoring ATR_SL hit reduction
- PM_TRAIL 0.15% dist — working (75% WR, avg +0.331%)
- ct-hot+ legacy clearing naturally (all flags False, should clear Aug 17-18)
- Stars intact: return_exhaustion_long 100%, bb_bounce+ 63.6%, r2-trend-long2 64.7%

### Verification
| Metric | Before | Current | Target |
|--------|--------|---------|--------|
| 48h PnL | -$0.74 | -$0.71 | $0 |
| PM_TRAIL WR | 66.7% | 75.0% | >60% |
| ATR_SL hits | 36/48h | 34/48h | <20/48h |
| R:R | 0.44:1 | 0.74:1 | >1:1 |
| Daily trades | 30T | 31T | >20T |

### Next Actions
1. Monitor ATR_SL hit count after SPEED_MIN 40 takes effect (24h)
2. ct-hot+ legacy age-out (Aug 17-18)
3. PM_TRAIL 0.15% dist must hold >60% WR
4. Phantom trades root cause (guardian_orphan — backlog)
