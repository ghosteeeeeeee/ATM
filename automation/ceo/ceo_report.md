## CEO Report — 2026-09-24 ~11:00 UTC

### Diagnosis
7d deteriorated: -$2.04 (was -$1.44 at 06:00 UTC). All NEUTRAL. 24h: 36T 33.3%WR -$1.43. 1 open. **pullback-entry- SHORT** is the main drag: 30T/7d 33.3%WR -$2.25. Cold streak vs 30d 52.1%WR +$0.35. **Sep 21-22 were cold** (-$1.12, -$2.21) — dead hours bug was active. Fixes deployed Sep 23-24.

### Fixes Deployed (Sep 24)
1. **CL-T1 fire windows widened (2,3)→(4,6)** ~10:00 UTC (brain_auditor). Trades get 2 extra minutes for mean reversion. Expected +$0.30-0.60/7d.
2. **SHORT_RSI_FLOOR=40 hard block** ~06:00 UTC (CEO). Blocks SHORT entries with RSI<40. 43 trades/7d at RSI<50 lost $2.29.
3. **mover+ killed** by auto_1hr. 14T/7d 42.9%WR -$1.12.
4. **PUMP_CHAIN_LONG_RSI_MAX 75→70** (brain_auditor ~01:30 UTC). Blocks RSI 70-75 dead zone.

### Root Cause
pullback-entry- SHORT cold streak driven by: (1) dead hours trades (pre-fix), (2) oversold SHORT entries (RSI<50, pre-fix), (3) CL-T1 cutting trades too early (pre-fix). All three bugs now fixed. Need48h to measure.

### Regime Memory Updated
Updated signal_regime_memory.json with fresh30d data. Key: pump-chain- SHORT = hidden gem (54.4%WR NEUTRAL, underutilized).

### Next Actions
1. **MONITOR:** CL-T1 fire windows (4,6) — verify avg loss reduces from -3.92% to ~-2.0%
2. **MONITOR:** SHORT_RSI_FLOOR=40 — verify pullback-entry- SHORT improves
3. **REGIME_CONF_MULTIPLIER:** brain_auditor suggested 5th time. EXTREME 1.15x, NORMAL 0.85x. Would help when regime shifts.
4. **DISK:** 85% (95G/118G). Below 90% but watch.
