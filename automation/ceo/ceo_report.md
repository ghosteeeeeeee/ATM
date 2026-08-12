## CEO Report — 2026-08-12 01:25 UTC

### Diagnosis
24h: 42T, -$0.16, 47.6% WR (RED but improving from -$0.29)
7d: 383T, +$0.93, 53.0% WR (solid, stable)

Daily: Aug 9 +$0.62 peak → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.15 (5T, 80% WR — strong start)

### Root Cause
- **SHORT bleed persistent**: SHORT 7d 125T -$1.05 (49.6% WR) — regime-driven, not signal-driven. Star SHORT (bb-bounce-short,hzscore-) still profitable 17T +$0.12 58.8%. Top losers: ma100-cross,return_exhaustion- (-$0.28), ma100-cross-,range_finder- (-$0.19), hzscore-,return_exhaustion- (-$0.18). SHORT stopped firing after Aug 12 — system self-correcting.
- **LONG solid**: LONG 7d 258T +$1.98 (54.7% WR) — strong, bb_bounce+ combos dominating
- **Cost drivers 7d**: atr_sl_hit 139T -$7.55 (dominant), profit-monster-trail 143T +$7.00 (sole winning exit net)
- trend_momentum_near_sma+ DISABLED (5T 0% WR -$0.40)

### Stars (7d, all intact)
- bb_bounce+,range_finder+ LONG: 53T +$0.71, 58.5% WR
- bb_bounce+,hzscore+ LONG: 34T +$0.22, 50.0% WR
- bb-bounce-short,hzscore- SHORT: 17T +$0.12, 58.8% WR

### Fix Applied
**NO CHANGES** — 7d solid at +$0.93, stars intact, system idle by design (NEUTRAL/REDUCE). SHORT stopped firing (0 SHORT trades since Aug 12 01:11). Overreacting destabilizes.

### Monitoring
- SHORT7d bleed (if -$1.50+ → consider regime filter for SHORT)
- Disk 85% (WARN threshold — pipeline.log 195M total)
- trend_momentum_near_sma+ residual (will close/age out)
- accel-300 SHORT re-enabled — monitor first trades

### Verification
- Pipeline healthy: 15+ active timers, last run 01:21 UTC
- Live trading: ON
- Open: 7 trades (all LONG, 0 SHORT)
- Hotset: empty (NEUTRAL regime, macro gate REDUCE — correct)
- trend_momentum_near_sma+ DISABLED (0% WR)

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
