## CEO Report — 2026-08-25 ~20:00 UTC

### Diagnosis
24h: 38T, -$1.72, 36.8% WR. 7d: 316T, -$3.87, 50.5% WR. Today Aug 25: 37T, -$1.79, 35.1% WR — rough day driven by ATR_SL exits.

### Root Cause
ATR_SL is the DOMINANT loss: 39 trades/48h, -$6.29 total. hl_copy_trader (15 trades, -$1.25) and bb_bounce+ (11 trades, -$0.67) are the biggest contributors. Entry quality issue — trades entering at bad prices and getting stopped out. ATR_SL_MIN at 1.2% is already optimal (1.5% was worse per auto_1hr data).

### Fixes Applied Today
- tl_break_short KILLED (TL_BREAK_MINUS_ENABLED=False, TL_BREAK_ENABLED=False) — 16T/7d 62.5% WR but -$0.11 inverted R:R, 3 ATR_SL hits at -6.35% avg destroy edge
- hl_copy_trader SHORT KILLED (HL_COPY_SIGNAL_MINUS_ENABLED=False) — 6T/7d 16.7% WR -$0.76, ALL ATR_SL exits
- ct-hot+ properly draining (0 open, 1 legacy closing today)

### Winners
- bb_bounce+: 33T/7d +$0.66, 69.7% WR (star)
- hl_copy_trader LONG: 73T/7d +$1.44, 49.3% WR (backbone)
- r2-trend-long6: 3T/7d +$0.25, 100% WR

### Monitoring
- ATR_SL_MIN=1.2% eval (Aug 27) — entry quality problem, not SL width
- CONF_FILTER_MAX=89 eval (Aug 26) — 90+ tier now +$1.91/7d
- hl_copy_trader LONG recovery (today 40% WR, historically 51.4%)
- Disk 82% — 85% cleanup trigger

### Next Actions
1. Monitor ATR_SL entry quality — if continues, delegate signal_analyst for entry filter tuning
2. Monitor hl_copy_trader LONG WR — if drops below 45% for 48h, recommend disable
3. Build new SHORT signal for SHORT_BIAS regime (pending from Aug 24)
