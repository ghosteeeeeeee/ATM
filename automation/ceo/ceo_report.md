## CEO Report — 2026-08-26 ~00:25 UTC (259th run)

### Diagnosis
24h: 34T, -$1.35, 41.2% WR. 7d: 317T, -$3.95, 50.5% WR. Today Aug 26: 2T, +$0.04 (just started). 5 open trades (2 cascade-reverse-v2 SHORT, 2 continuation- SHORT, 1 r2-trend-long14 LONG).

### Root Cause
7d -$3.95 dominated by:
1. **ct-hot+** 66T/7d 36.4% WR -$3.65 (DOMINANT — CEO_PROTECTED, draining)
2. **hl_copy_trader SHORT** 6T/7d 16.7% WR -$0.76 (KILLED, legacy closing)
3. **ATR_SL** 175T/7d -$5.41 (55% of all exits — structural)
4. **cut-loser-MAE-GUARD** 17T/7d -$1.58 (legacy, signal killed)

### SHORT vs LONG
- SHORT 7d: 88T 47.7% WR -$2.85 (bleeding — hzscore- 50% WR inverted R:R, cascade-reverse-v2 new)
- LONG 7d: 229T 51.5% WR -$1.10 (improving — bb_bounce+ star, hl_copy_trader backbone)

### What's Working
- bb_bounce+: 33T/7d 69.7% WR +$0.66 (star — today degraded to 41.7%, small sample)
- hl_copy_trader LONG: 73T/7d 49.3% WR +$1.44 (backbone)
- r2-trend-long6: 3T/7d 100% WR +$0.25
- All kills active (hl_copy_trader SHORT/LONG, ct-hot+)
- ATR_SL_MIN=1.2% (reverted from 1.5% — wider was worse)
- CONF_FILTER_MAX=89 (eval ending Aug 26)
- Pipeline active, timers firing, disk 82%

### Monitoring
- **CONF_FILTER_MAX=89 eval (Aug 26)** — 48h window closing
- **MIN_PRE_MOVE=0.3 eval (Aug 25)** — check if filter producing results
- **bb_bounce+ recovery** — 41.7% today vs 69.7% 7d, small sample but watch
- **cascade-reverse-v2 SHORT** — 3 open, 0 closed, new signal evaluating
- **continuation- SHORT** — 2 open, 1 closed (-$0.14), re-enabled Aug 25
- **Phantom trade ALT SHORT #14327** — flagged, likely stale

### DECISION: 30s Price Interval

**A — Split Architecture.** System at 39.4% WR / -$1.36 — no time for risky full migration. Split keeps 30s exit freshness while signals revert to calibrated 60s bars. One line change, zero signal rewrites.

### Next Actions
1. **Monitor CONF_FILTER_MAX=89** — eval window closes Aug 26
2. **Monitor MIN_PRE_MOVE=0.3** — check filter impact today
3. **Build new SHORT signal** — SHORT side structural issue, pending from Aug 24
4. **Monitor bb_bounce+** — if 48h WR <50%, delegate signal_analyst
