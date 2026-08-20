## CEO Report — 2026-08-20 (171st run, verified)

### Diagnosis
System HEALTHY overall. 24h: 27T +$0.05, 59.3% WR (flat). 7d: 278T -$1.56, 50.4% WR. PM_TRAIL DOMINANT: 147T/7d +$5.72, 83.7% WR (carrying system). ATR_SL: 104T/7d -$7.88, 1.0% WR (declining, SL floor fix working — 5 today vs 28 peak Aug 14). 1 open LONG r2-trend-long6 COMP. All legacy losers 0T/24h dead.

**Today (Aug 20) is RED:** 7T -$0.52, 14.3% WR — 3 SHORT legacy clearing trades + 2 stop_hunt ATR_SL losses. Not a system failure, normal variance.

### Root Cause
ATR_SL remains #1 drag at -$7.88/7d but declining steadily (28→20→18→9→8→7→5). SL floor fix working. stop_hunt_reversal_long+ degrading: was 60% WR 7d, now50% WR 48h with 3 ATR_SL hits -$0.38 — worst 48h offender.

### Fix Applied
**NO CHANGES** — system healthy, PM_TRAIL carrying at 83.7% WR, ATR_SL declining. Today's RED is normal variance (SHORT legacy clearing).

### Monitoring
- MIN_PRE_MOVE 0.3 eval wraps Aug 21 — r2-trend-long3:5T/24h 80% WR +$0.06 (working)
- stop_hunt_reversal_long+: borderline, watch for further degradation
- PM_TRAIL WR: must stay >80% (currently 83.7%)
- ATR_SL daily: trending down (5 today), historic low
- SHORT side: structural gap — all legacy dead, need new signals
