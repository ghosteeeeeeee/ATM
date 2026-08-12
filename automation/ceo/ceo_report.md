## CEO Report — 2026-08-13 18:00 UTC

### Diagnosis
24h: 41T, -$0.29, 43.9% WR (RED)
7d: 383T, +$0.93, 52.7% WR (improved from +$0.91, solid)

Daily: Aug 9 +$0.62 peak → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.14 (2T)

### Root Cause
- **SHORT bleed persistent**: SHORT 7d — many combos negative but star SHORT profitable. Regime-driven, not signal-driven.
- **LONG solid**: LONG 7d profitable, bb_bounce+ combos dominating
- **cost drivers 48h**: atr_sl_hit 42T -$1.81 (dominant), cut-loser-CL-trail 12T -$0.60
- **sole winning exit**: profit-monster-trail
- trend_momentum_near_sma+ DISABLED (5T 0% WR -$0.40, 1 residual open)

### Stars (7d, all intact)
- bb_bounce+,range_finder+ LONG: 53T +$0.71, 58.5% WR
- bb_bounce+,hzscore+ LONG: 34T +$0.22, 50.0% WR
- bb-bounce-short,hzscore- SHORT: 17T +$0.12, 58.8% WR

### Fix Applied
**NO CHANGES** — 7d improved to +$0.93, stars intact, system idle by design (NEUTRAL/REDUCE). Hotset populated with 8 tokens post-compaction (accel-300- NEO SHORT first entry). Overreacting destabilizes.

### Monitoring
- SHORT7d bleed (if -$1.50+ → consider regime filter for SHORT)
- Disk 85% (at WARN threshold — pipeline.log 195M total)
- trend_momentum_near_sma+ residual open trade (will close/age out)
- Hotset: 8 tokens, accel-300- first firing since re-enable

### Verification
- Pipeline healthy: 15+ active timers
- Live trading: ON
- Open: 7 trades (5 LONG +$0.06, 1 SHORT +$0.04, 1 paper)
- Hotset: 8 tokens (NEO SHORT accel-300-, KAS SHORT hzscore-, SYRUP LONG bb_bounce+, ZRO LONG bb_bounce+, JUP SHORT hzscore-, HBAR LONG hzscore+, AVNT LONG hzscore+, WLFI SHORT hzscore-)
- trend_momentum_near_sma+ DISABLED (0% WR, 1 residual open)

---

## CEO Report — 2026-08-11 23:45 UTC

### Diagnosis
24h: 41T, -$0.33, 43.9% WR (RED)
7d: 384T, +$0.70, 52.1% WR (positive, solid)

Daily: Aug 9 +$0.62 peak → Aug 10 -$0.10 → Aug 11 -$0.33 (declining, worst day since Aug 4)

### Root Cause
- **SHORT bleed persistent**: SHORT 7d 125T -$1.02 (49.6% WR) — regime-driven, star SHORT still profitable. Top losers: ma100-cross,return_exhaustion- (-$0.28), ma100-cross-,range_finder- (-$0.19), hzscore-,return_exhaustion- (-$0.18)
- **LONG declining**: LONG 7d 259T +$1.72 (53.3% WR) — solid but daily declining (Aug 9 +$0.59 → Aug 11 -$0.18)
- **cost drivers 48h**: atr_sl_hit 42T -$1.81 (dominant), cut-loser-CL-trail 13T -$0.65, cut-loser-CL-T1 4T -$0.42
- **regime data NULL**: 366/384 trades have NULL regime (brain.py INSERT missing column — data quality debt)

### Stars (7d, all intact)
- bb_bounce+,range_finder+ LONG: 53T +$0.71, 58.5% WR
- bb_bounce+,hzscore+ LONG: 34T +$0.22, 50.0% WR
- bb-bounce-short,hzscore- SHORT: 17T +$0.12, 58.8% WR

### Fix Applied
**NO CHANGES** — 7d positive (+$0.70), stars intact, system idle by design (NEUTRAL/REDUCE). Momentum fade filter deployed Aug 13 — too early to evaluate. Overreacting destabilizes.

### Monitoring
- SHORT7d bleed (if -$1.50+ → consider regime filter for SHORT)
- Daily declining trend (if Aug 12 negative → investigate)
- cut-loser-CL-T1 (4T -$0.42, 0% WR — watch for pattern)
- Disk 84% (1% from WARN)

### Verification
- Pipeline healthy: 15+ active timers, no crashes
- Live trading: ON (kill switch enabled)
- Open: 7 trades (5 LONG, 1 SHORT, 1 paper)
- Hotset: EMPTY (NEUTRAL regime, correct)
- trend_momentum_near_sma+ DISABLED (0% WR, 1 open trade)
