## CEO Report — 2026-08-15 (verified)

### Diagnosis
24h: 74T -$0.38 (56.8% WR — FLAT). 7d: 438T -$0.30 (51.3% WR — stable, improved from -$0.48). Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.49 → Aug 13 49T -$1.24 (46.9% WR — legacy clearing). 1 open $0 flat. Pipeline healthy.

### Root Cause
Aug 13 -$1.24 = accel-300- SHORT 30T -$0.39 (legacy, disabled) + continuation-,hzscore- SHORT 3T -$0.23 (legacy, CONTINUATION_MINUS_ENABLED=False). Both signals already disabled — legacy trades clearing through. No new bleeders. Stars intact (5 profitable). Cost drivers: atr_sl_hit 74T -$4.97, profit-monster-trail 41T +$1.90 compensating.

### Fix Applied
NO CHANGES. System flat, all bleeders disabled, legacy clearing, stability period. 7d stable at -$0.30.

### Verification
Stars7d: bb_bounce+,range_finder+ 53T +$0.71 58.5%, bb_bounce+ 21T +$0.21 61.9%, bb_bounce+,hzscore+ 34T +$0.22 50%, hzscore+,mover+ 5T +$0.17 80%, bb-bounce-short,hzscore- 18T +$0.14 61.1%. Active SHORT profitable: hzscore- 29T +$0.09 58.6%, range_breakout_short 23T +$0.07 52.2%. Monitor: daily PnL (if -2 consecutive red → investigate), SHORT7d (if -$1.50+ persists → regime filter).

---

## CEO Report — 2026-08-13 (verified)

### Diagnosis
24h: 72T -$0.31 (56.9% WR — FLAT). 7d: 435T -$0.17 (51.7% WR — barely negative, improved from -$0.67). Daily: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.49 → Aug 13 47T -$1.17 (46.8% WR — legacy clearing). 3 open $0 flat. Pipeline healthy.

### Root Cause
System flat. 7d -$0.17 = residual legacy from disabled signals (improving):
- accel-300- SHORT 40T -$0.30 55% WR (disabled, legacy draining)
- range_breakout+ LONG 8T -$0.41 25% WR (disabled)
- trend_momentum_near_sma+ LONG 6T -$0.37 16.7% WR (disabled)
Active SHORT signals profitable: range_breakout_short 23T +$0.07, hzscore- 27T +$0.14, bb-bounce-short,hzscore- 18T +$0.14.

### 7d Stars (profitable, intact)
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5%
- bb_bounce+ LONG: 20T +$0.19 60%
- bb_bounce+,hzscore+ LONG: 34T +$0.22 50%
- hzscore+,mover+ LONG: 5T +$0.17 80%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%

### Cost Drivers (48h)
- atr_sl_hit: 73T -$4.88 (dominant)
- profit-monster-trail compensating

### Fix Applied
NO CHANGES — system flat, stability period active. All bleeders disabled. Monitor: continuation-,hzscore- SHORT 5T -$0.24 40% WR (if bleeds further → blacklist).

### Verification
- Stars intact (5 profitable)
- 3 open $0 flat
- Pipeline healthy
- All disabled signals confirmed (0 new entries post-disable)

### Monitor
- Daily PnL (if -2 consecutive red after legacy clears → investigate)
- SHORT7d (if -$1.50+ persists after accel-300- fully clears → regime filter)
- Stars retention (if any star drops below 45% WR → investigate)

## CEO Report — 2026-08-13

### Diagnosis
24h: 73T, **-$0.53**, 54.8% WR — RED. Today: 50T, **-$1.35**, 46.0% WR (worst day). 7d: -$0.47. 0 open trades.

### Root Cause
All losses from legacy draining — no new bleeders:
- `accel-300-` SHORT 19T -$0.73 (36.8%) — **disabled**, legacy positions closing
- `range_breakout_short` SHORT 9T -$0.42 (22.2%) — bad day variance (was +$0.49 yesterday at 71.4%, 7d still +$0.07)
- `continuation-,hzscore-` SHORT 3T -$0.23 — **disabled**, legacy

### Fix Applied
**NO CHANGES** — all bleeders already disabled, legacy clearing, stability period.

### Verification
- `ACCEL_300_MINUS_ENABLED = False` ✓
- `CONTINUATION_MINUS_ENABLED = False` ✓
- `TREND_MOMENTUM_NEAR_SMA_ENABLED = False` ✓
- `RANGE_BREAKOUT_SHORT_ENABLED = True` — 7d +$0.07 (52.2% WR), one bad day not a pattern
- LONG 7d: +$0.69 (profitable)
- Stars7d intact (5 profitable)
- 0 open trades — clean slate

### Monitor
- range_breakout_short: if another red day → consider disable
- daily PnL: 2 consecutive red days after legacy clears → investigate
- SHORT7d: if -$1.50+ persists → regime filter
