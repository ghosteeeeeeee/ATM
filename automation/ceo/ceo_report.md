## CEO Report — 2026-08-20 (172nd run, ~11:00 UTC, verified)

### Diagnosis
System HEALTHY. 24h: 28T +$0.07, 60.7% WR (9th consecutive green day). 7d: 279T -$1.54, 50.5% WR. 0 open positions (clean). PM_TRAIL DOMINANT: 148T/7d +$5.74, 83.8% WR (carrying system — avg win +0.49%). ATR_SL: 104T/7d -$7.88, 1.0% WR (historic low, ~9/day, avg loss -0.77%). All legacy losers 0T/24h confirmed dead. SHORT legacy clearing as expected (r2-trend-short killed Aug 20).

**stop_hunt_reversal_long+ degrading:** 48h: 4 ATR_SL -$0.51, 3 PM_TRAIL +$0.28 — net -$0.23. Worst 48h ATR_SL offender. 7d still 60% WR -$0.04 (break-even) but trajectory is down.

### Root Cause
PM_TRAIL R:R positive (0.49% avg win vs -0.77% avg loss = 1:1.57). System profitable despite 50.5% WR because PM_TRAIL winners are bigger than ATR_SL losers. stop_hunt degrading because ATR_SL hits increasing while PM_TRAIL captures shrinking.

### Fix Applied
**NO CHANGES** — system healthy, 9th green day, PM_TRAIL 83.8% WR carrying. stop_hunt not at kill threshold yet (60% 7d WR, break-even PnL).

### Monitoring
- stop_hunt_reversal_long+: borderline, 4 ATR_SL hits in 48h. Kill if 7d WR drops below 55% or PnL goes negative.
- MIN_PRE_MOVE 0.3 eval wraps Aug 21 — r2-trend-long3: 1T today -$0.12 (first loss after 4T/100% +$0.18 yesterday)
- PM_TRAIL WR: must stay >80% (currently 83.8%)
- ATR_SL daily: ~9 today, historic low from 28 peak
- SHORT side: structural gap — all legacy dead, need new signals
