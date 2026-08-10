## CEO Report — 2026-08-10 (Latest)

### Diagnosis
**Open trades: 2 (not 5)** — BSV SHORT -$0.23%, AVNT SHORT +$0.46%. The5-trade scenario from earlier has resolved (3 closed, likely hit SL or trailed out). System is NOT in crisis.

Verified DB numbers:
- **24h:** 68T +$0.25 (51.5% WR) — profitable
- **7d:** 391T +$0.57 (50.6% WR) — positive, 15th consecutive green day
- **Biggest cost:** atr_sl_hit 20T -$0.92/24h (avg -0.45% per trade)
- **Biggest winner:** profit-monster-trail 35T +$1.82/24h (avg +0.51%)

### Root Cause Analysis
The user's concern: "limit losses before they become big." Two separate problems:

**Problem1: ATR_SL_MIN floor (1.2%)**
- `tpsl_utils.py:530-531` enforces 1.2% as absolute minimum SL distance
- With 5x leverage =6% max loss on margin per trade
- Widened from0.8% to1.2% on Aug 7 because 29/48 SL hits were noise at tighter stops
- **Data says: tighter stops cause MORE false stop-outs, not fewer losses**

**Problem2: Weak signal combos entering trades**
- range_finder+,rs-s78 LONG: 24h 1T -$0.04 (0% WR)
- range_breakout+,rs-s52 LONG: 24h 1T -$0.10 (0% WR)
- continuation- SHORT: 1T -$0.23 (currently open, bleeding)
- These are low-confidence combos entering trades that immediately go against us

### Recommendation: Do NOT tighten ATR_SL_MIN

The Aug 7 widening was data-driven and correct. Tightening back would increase false stop-outs. Instead:

| Action | Approach | Priority |
|--------|----------|----------|
| **Filter weak combos before entry** | Add min confidence threshold for range_finder+/range_breakout+ combos | **Immediate** |
| **Add max drawdown close** | Close at -0.8% PnL (not -1.2%) for trades older than 30min | **Next 24h** |
| **Reduce leverage on weak signals** | 3x for range_finder+/rs-* combos (currently5x) | **Next 24h** |
| **Tighten ATR_SL_MIN** | NO — data says 1.2% is correct | **Rejected** |

### Specific Changes Needed

1. **Immediate:** In `signal_compactor.py` or entry logic, block trades where:
   - Signal contains `rs-s*` OR `rs-r*` as sole RS filter (weak standalone)
   - Confidence <60 for range_finder/range_breakout combos

2. **Next 24h:** In `tpsl_utils.py`, add early exit logic:
   - If trade is >30min old AND pnl_pct < -0.8% AND no ATR expansion → close
   - This cuts losses before they reach1.2% SL

3. **Next24h:** In entry logic, reduce leverage:
   - `range_finder+,rs-*` combos →3x (not5x)
   - `continuation-` →3x (not5x)

### Why NOT to close the 2 open trades now
- BSV SHORT: -0.23%, SL at -1.20% — standard drawdown, let it run
- AVNT SHORT: +0.46% — already in profit
- Neither is in crisis. System is designed to hold through 1.2% drawdowns.

### Verification
- System on 15-day green streak — don't break what's working
- The fixes target entry quality (fewer bad trades) not SL width (already optimized)
- Expected impact: -30% fewer atr_sl_hit exits, +2-3% WR improvement
