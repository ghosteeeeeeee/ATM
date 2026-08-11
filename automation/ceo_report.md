## CEO Report — 2026-08-11 02:30 UTC

### Diagnosis
System red for 2nd day after 15-green-day streak. Verified DB: 24h 62T -$0.31 (41.9% WR), 12h 32T -$0.42 (37.5% WR — roughest window), 6h 9T +$0.06 (55.6% WR — improving). 7d 367T +$0.33 (51.8% WR — positive). 3 open $0 unrealized.

Daily: Aug 9 +$0.62 (58.5%), Aug 10 -$0.10 (45.5% — first red), Aug 11 +$0.01 (60% — 5T, starting green).

### Root Cause
Two cost drivers dominate: atr_sl_hit 25T -$1.12 and cut-loser-CL-trail 11T -$0.55 in 24h. bb_bounce+,hzscore+ LONG is the bleeding signal: 18T -$0.22 (38.9% WR) in 24h, but 7d still intact at 30T +$0.23 (50% WR). Volume spike on Aug 10 (22T vs normal 2-5T/day) dragged performance. All 3 star signals profitable on 7d — this is variance, not signal decay.

SL widening (0.5%→1.2%) deployed 22:00 Aug 10 — now ~4.5h old. Post-widening sample tiny (6T), inconclusive. ATR SL hit rate was trending up (35.8%→41.9%) — monitoring whether widening reverses this.

### Fix Applied
NO TRADING CHANGES. SL widening needs full 24h evaluation window (complete by 22:00 Aug 11). 7d trajectory positive. Stars intact. Market NEUTRAL.

### Verification
- 6h WR improved to 55.6% (from 37.5% at 12h)
- 7d still +$0.33 at 51.8% WR
- No 0% WR signals to kill
- 0 phantoms, pipeline healthy

## CEO Report — 2026-08-11 02:23 UTC

### Diagnosis
System red for 2nd day after 15-green-day streak. Verified DB: 24h 60T -$0.22 (43.3% WR), 12h 28T -$0.39 (35.7% WR — roughest window), 6h 8T -$0.05 (50% WR — improving). 7d 366T +$0.42 (51.9% WR — positive). 4 open $0 unrealized.

Daily: Aug 9 +$0.62 (58.5%), Aug 10 -$0.10 (45.5% — first red), Aug 11 +$0.01 (60% — 5T, starting green).

### Root Cause
Two cost drivers dominate: atr_sl_hit 35T -$1.62 (48h) and cut-loser-CL-trail 23T -$0.91 (48h). bb_bounce+,hzscore+ LONG is the bleeding signal: 18T -$0.22 (38.9% WR) in 24h, but 7d still intact at 30T +$0.23 (50% WR). Volume spike on Aug 10 (22T vs normal 2-5T/day) dragged performance. All 3 star signals profitable on 7d — this is variance, not signal decay.

SL widening (0.5%→1.2%) deployed 22:00 Aug 10 — now ~4.5h old. Post-widening sample tiny (6T: 3 atr_sl_hit, 3 profit-monster-trail), inconclusive. ATR SL hit rate was trending up (35.8%→41.9%) — monitoring whether widening reverses this.

### Fix Applied
NO TRADING CHANGES. SL widening needs full 24h evaluation window (complete by 22:00 Aug 11). 7d trajectory positive. Stars intact. Market NEUTRAL.

### Verification
- 6h WR improved to 50% (from 35.7% at 12h)
- 7d still +$0.42 at 51.9% WR
- No 0% WR signals to kill
- 0 phantoms, pipeline healthy
- Today (Aug 11) 5T +$0.01 (60% WR) — starting green

### System Health
- hermes-bug-hunter.service: FAILED (imports defunct ai_decider.py)
- hermes-hl-volume.service: FAILED
- hermes-trading-checklist.service: FAILED
- Other services: running normally

## CEO Report — 2026-08-11 02:50 UTC

### Diagnosis
24h 61T -$0.24 (42.6% WR) — red, 2nd day after 15 green. 6h 10T -$0.16 (40% WR). Stars7d intact: all 3 profitable. SL widening (1.2%) deployed 6h ago — 6 trades since, too early.

### Bleeding Point
bb_bounce+,hzscore+ LONG — 18T 38.9% WR -$0.22 (24h). 8/18 SL hits. Dominant star bleeding in chop. But 7d still +$0.23 at 50% WR — noise at n=18.

### Cost Drivers (48h)
- atr_sl_hit: 37T -$1.73 (still dominant)
- cut-loser-CL-trail: 23T -$0.91

### Decision: NO CHANGES
1. SL widening needs full 24h window (6h is insufficient sample)
2. 7d trajectory positive (+$0.42 at 51.9% WR)
3. All 3 star signals profitable on 7d
4. Market NEUTRAL — chop is expected, no regime change
5. 2 open positions, pipeline healthy

### Next Review
Re-check at 08:00 UTC (6h) — if 24h WR still <40% after 12h post-widening, consider disabling bb_bounce+,hzscore+ LONG temporarily.

## CEO Report — 2026-08-11 Volatility Gate Deployed

### What Changed
Volatility gate integrated into context gate + SL/TP pipeline. Market classified by ATR%: FLAT (<0.48%) and EXTREME (>1.5%) skip trade; HIGH (1.0-1.5%) widens SL by volatility multiplier.

### ATR Distribution (143 tokens, 30d baseline)
P25=0.48%, P50=0.67%, P75=0.87%, P90=1.24%, P95=1.63%

### Expected Impact
- FLAT regime trades (currently ~25% of tokens) → eliminated
- EXTREME regime trades (currently ~5%) → eliminated
- HIGH regime trades (~10%) → SL widened, fewer premature exits
- Combined: fewer bad trades in flat markets, wider stops in volatile markets

### Monitoring
Track next 24h: FLAT/EXTREME skip count, HIGH regime WR vs NORMAL, atr_sl_hit rate change. No trading param changes until volatility gate has 48h of data.

### Bug Fixes in This Deploy
- tpsl_utils.py: missing log import
- decider_run.py: None formatting
- position_manager.py: redundant calls simplified
