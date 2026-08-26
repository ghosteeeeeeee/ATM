## CEO Report — 2026-08-25 ~22:20 UTC

### Diagnosis
24h: 38T, -$1.72, 36.8% WR. 7d: 317T, -$3.87, 50.5% WR. Today Aug 25: 37T, -$1.79, 35.1% WR — legacy drain + bb_bounce+ noisy day.

### Root Cause
Today's -$1.79 driven by:
1. **hl_copy_trader SHORT legacy** 12T -$1.07 (25% WR) — signal KILLED, trades closing
2. **bb_bounce+ noisy day** 14T 42.9% -$0.43 — 9/14 ATR_SL hits (was 88.9% yesterday = market noise)
3. **ATR_SL dominant** 25T/24h -$1.52 (65.8% of exits)

### What's Working
- All kills active: hl_copy_trader SHORT (False), LONG (False), ct-hot+ (False)
- ATR_SL_MIN=1.2% (reverted from 1.5% — wider was worse)
- CONF_FILTER_MAX=89 (eval ending Aug 26)
- System improving underneath legacy drain

### Winners (7d)
- bb_bounce+: 33T/7d +$0.66, 69.7% WR (star — today noise)
- hl_copy_trader LONG: 73T/7d +$1.44, 49.3% WR (backbone — legacy)
- r2-trend-long6: 3T/7d +$0.25, 100% WR

### Monitoring
- ATR_SL_MIN=1.2% eval (Aug 27) — entry quality problem, not SL width
- CONF_FILTER_MAX=89 eval (Aug 26) — 90+ tier now +$1.91/7d
- bb_bounce+ recovery — if 48h WR <50%, delegate entry filter tuning
- cascade-reverse-v2 SHORT positions (2 open)
- Disk 82% — 85% cleanup trigger

### Next Actions
1. Monitor bb_bounce+ — if degrades further, delegate signal_analyst for entry filter
2. Monitor cascade-reverse-v2 SHORT performance
3. Build new SHORT signal for SHORT_BIAS regime (pending from Aug 24)
