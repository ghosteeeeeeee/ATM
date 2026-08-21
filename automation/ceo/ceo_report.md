## CEO Report — 2026-08-21 ~17:00 UTC (216th run)

### Diagnosis
System HEALTHY, CONTINUED GREEN. Verified DB: 24h 35T +$0.39, 57.1% WR (green). 7d: 231T -$0.21, 51.9% WR (break-even — tiny red, legacy losers dragging). 2 open: 1 ct-hot+ LONG, 1 hl_copy_trader LONG. PM_TRAIL carrying: 105T/7d +$4.22, 83.8% WR. ATR_SL: 101T/7d -$4.95, 16.8% WR (only loss source). Today: 30T +$0.40, 56.7% WR. Legacy losers in 7d window: ct-hot+ 45T -$0.90, r2-trend-short2 3T -$0.22, ct-hot- 4T -$0.19, range_breakout_short 2T -$0.17, range_finder+ 9T -$0.14 = -$1.62 total. All legacy age out Aug 22-23 (tomorrow).

### Root Cause
7d slightly red due to legacy losers in window (-$1.62 from 5 dead signals). Without legacy, 7d would be ~+$1.41. PM_TRAIL continues to carry system. ATR_SL count at historic low. Today solid but not peak (+$0.40 vs yesterday's +$1.69).

### Fix Applied
NO CHANGES — system healthy, legacy dying naturally by Aug 22-23. No intervention needed.

### Key Numbers (Verified)
| Metric | 24h | 7d |
|--------|-----|----|
| Trades | 35 | 231 |
| PnL | +$0.39 | -$0.21 |
| WR | 57.1% | 51.9% |

### Exit Breakdown (7d)
- profit-monster-trail: 105T +$4.22, 83.8% WR ✅
- profit-monster-T1: 12T +$0.69, 100% WR ✅
- atr_sl_hit: 101T -$4.95, 16.8% WR (main drag)

### Top Signals (7d)
- r2-trend-long6: 6T +$0.40, 100% WR (best, 0% ATR_SL — bars_since>=6 filter)
- hl_copy_trader: 16T +$0.71, 62.5% WR
- r2-trend-long4: 15T +$0.15, 66.7% WR
- r2-trend-long3: 26T +$0.19, 53.8% WR (MIN_PRE_MOVE 0.3 working — 48h 9T +$0.28, 77.8% WR)

### Monitoring
- MIN_PRE_MOVE 0.3 eval (Aug 25) — 48h improving
- PM_TRAIL WR (>80%) — at 83.8%
- Legacy age out (Aug 22-23) — will clear ~-$1.62 from 7d
- Volume collapse — 82% drop unresolved
- Disk at 81%
- PM_TRAIL WR (>80%)
- ATR_SL daily (<15)
- Volume recovery
- Disk 81% (cleanup at 85%)
