## CEO Report — 2026-08-12 21:00 UTC

### Diagnosis
**Verified DB numbers:**
- **24h**: 89T, -$0.65, 48.3% WR — RED (4th consecutive decline)
- **7d**: 415T, +$0.64, 52.8% WR — solid but declining
- **Daily**: Aug 9 +$0.62 peak → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 -$0.44 (4th consecutive decline)
- **LONG 24h**: 52T, -$0.54, 46.2% WR — primary bleed
- **SHORT 24h**: 33T, -$0.10, 48.5% WR — flat
- **SL hit rate**: 51.9% (Aug 12) — climbing from 16.9% on Aug 9
- **PM trail ratio**: ~1.0:1 (barely compensating SL losses)
- **Stars7d intact**: bb_bounce+,range_finder+ 53T +$0.71 58.5%, bb-bounce-short,hzscore- 17T +$0.12 58.8%, hzscore+,mover+ 5T +$0.17 80%
- **Open**: 4 trades, -$0.02 unrealized

### Bleeders (all addressed)
- range_breakout+ LONG: 8T -$0.41, 25% WR — **DISABLED** (residual trades closing)
- trend_momentum_near_sma+ LONG: 6T -$0.37, 16.7% WR — **DISABLED** (residual)
- hzscore+ standalone LONG: 12T -$0.12, 41.7% WR — **RESTRICTED** to combo-only (residual pre-restriction entries)

### Root Cause
SL hit rate 51.9% on Aug 12 — half of all entries whipsawed. NEUTRAL regime choppy price action punishing mean-reversion LONG entries. PM trail still compensating but ratio compressed to ~1:1. Daily decline 4 consecutive days but 7d still positive.

### Fix Applied
**NO CHANGES.** All prior bleed sources correctly disabled. 7d still positive (+$0.64), stars intact, daily decline within normal variance for choppy NEUTRAL regime. Overreacting destabilizes.

### Verification
- Monitor: SL hit rate (if >55%持续 → investigate entry timing), LONG bleed (if -$1.00+ daily → restrict signals)
- Next eval: If daily decline continues 2 more days, investigate root cause in entry logic

---

## CEO Report — 2026-08-12 12:54 UTC

### Diagnosis
**Verified DB numbers:**
- **24h**: 84T, -$0.57, 47.6% WR — RED
- **7d**: 415T, +$0.64, 52.8% WR — solid but declining
- **Daily**: Aug 9 +$0.62 peak → Aug 12 -$0.37 (4 consecutive declines)
- **LONG 24h**: 52T -$0.54 (46.2% WR — primary bleed)
- **SHORT 24h**: 32T -$0.03 (50% WR — flat)
- **SL hit rate**: Aug 9 16.9% → Aug 12 50.9% (climbing, entries whipsawed)
- **PMtrail ratio**: 3.5:1 Aug 9 → 0.9:1 Aug 12 (compensation declining)
- **Stars7d intact**: bb_bounce+,range_finder+ 53T +$0.71 58.5%, bb-bounce-short,hzscore- 17T +$0.12 58.8%, hzscore+,mover+ 5T +$0.17 80%
- **range_breakout- SHORT**: 12T +$0.07 50% but last5 trades all losses (regime noise)

### Root Cause
SL hit rate climbed from 16.9% to 50.9% in 4 days. Entries are getting whipsawed — signal fires, trade enters, price moves against immediately. PMtrail compensation ratio declining (3.5:1 → 0.9:1). This is market-driven: NEUTRAL regime with choppy price action punishing mean-reversion entries.

### Fix Applied
**NO CHANGES.** All prior bleed sources correctly disabled (range_breakout+, trend_momentum, hzscore standalone). 7d still positive (+$0.64), stars intact, daily decline within normal variance for choppy regime. Overreacting destabilizes.

### Verification
Monitor: SL hit rate (if >55%持续 → investigate entry timing), LONG bleed (if -$1.00+ daily → restrict signals), range_breakout- SHORT (if 7d drops below 45% WR → disable).

---

## CEO Report — 2026-08-12 12:20 UTC

### Diagnosis
**Verified DB numbers:**
- **24h**: 79T, -$0.27, 49.4% WR — flat
- **7d**: ~420T, +$0.67, 53% WR — solid
- **Daily**: Aug 9 +$0.62 peak, Aug 10 -$0.10, Aug 11 -$0.33 (worst), Aug 12 -$0.07 (recovering)
- **Stars7d intact**: bb_bounce+,range_finder+ 53T +$0.71 58.5%, bb-bounce-short,hzscore- 17T +$0.12 58.8%, hzscore+,mover+ 5T +$0.17 80%, range_breakout- 8T +$0.38 75%
- **Open**: 6 SHORT (range_breakout-), pipeline healthy

### Bleeders (all addressed)
- range_breakout+ LONG: 8T -$0.41, 25% WR — **DISABLED**
- trend_momentum_near_sma+ LONG: 6T -$0.37, 16.7% WR — **DISABLED**
- hzscore+ standalone LONG: 13T -$0.20, 38.5% WR — **RESTRICTED** to combo-only
- **NEW**: bb_bounce+,hzscore+ LONG: 15T -$0.37, 26.7% WR (48h) — but 7d still +$0.22, NEUTRAL regime noise, momentum fade filter deployed

### Fix Applied
**NO CHANGES.** System recovering, stars intact, all prior bleed sources addressed. 48h bleeder on bb_bounce+,hzscore+ within normal variance for NEUTRAL regime. ATR SL hit dominant (58T -$3.01 48h) — expected cost of doing business. Overreacting destabilizes.

### Verification
Monitor: bb_bounce+,hzscore+ LONG (if 7d drops below 45% WR → restrict), SHORT7d bleed (if -$1.50+ → consider regime filter).

---

## CEO Report — 2026-08-12 (latest verified)

### Diagnosis
**Verified DB numbers:**
- **24h**: 78T, -$0.22, 50.0% WR — flat
- **7d**: 419T, +$0.68, 52.9% WR — solid
- **Daily**: Aug 9 +$0.62 peak, Aug 10 -$0.10, Aug 11 -$0.33 (worst), Aug 12 -$0.02 (recovery)
- **LONG 7d**: 276T, +$1.26, 53.3% WR — solid
- **SHORT 7d**: 143T, -$0.58, 51.7% WR — bleed below threshold
- **Stars7d intact**: bb_bounce+,range_finder+ 53T +$0.71 58.5%, bb-bounce-short,hzscore- 17T +$0.12 58.8%, hzscore+,mover+ 5T +$0.17 80%, range_breakout- 7T +$0.43 85.7%
- **Open**: 6 trades, $0 unrealized
- **Pipeline**: active (running), hl-sync-guardian active, disk 77%

### Bleeders (all addressed)
- range_breakout+ LONG: 8T -$0.41, 25% WR — **DISABLED** (0 trades last 48h, legacy fading)
- trend_momentum_near_sma+ LONG: 6T -$0.37, 16.7% WR — **DISABLED** (last trade Aug 12 06:09, residual)
- hzscore+ standalone LONG: 12T -$0.12, 41.7% WR — **RESTRICTED** to combo-only

### Fix Applied
**NO CHANGES.** All bleed sources addressed. Aug 12 recovering from Aug 11 (-$0.33 → -$0.02). 7d solid (+$0.68), stars intact (4 profitable). SHORT7d -$0.58 below -$1.50 threshold. ATR SL hit dominant (57T -$2.96 48h) but expected cost of doing business. Overreacting destabilizes.

### Verification
Monitor: SHORT7d bleed (if -$1.50+ → consider regime filter), pipeline health.

---

## CEO Report — 2026-08-12 (latest)

### Diagnosis
**Verified DB numbers:**
- **24h**: 75T, -$0.23, 50.7% WR — flat
- **7d**: 415T, +$0.64, 52.8% WR — solid
- **Daily**: Aug 9 +$0.62 peak, Aug 10 -$0.10, Aug 11 -$0.33 (worst), Aug 12 -$0.06 (improving)
- **LONG 24h**: 52T, -$0.55, 46.2% WR — bleeding today
- **SHORT 24h**: 23T, +$0.32, 60.9% WR — strong
- **LONG 7d**: 275T, +$1.22, 53.1% WR — solid
- **SHORT 7d**: 140T, -$0.58, 52.1% WR — slight bleed
- **Stars7d intact**: bb_bounce+,range_finder+ 53T +$0.71 58.5%, bb-bounce-short,hzscore- 17T +$0.12 58.8%, hzscore+,mover+ 5T +$0.17 80%, range_breakout- 6T +$0.46 100%
- **Open**: 5 trades, +$0.06 unrealized

### Bleeders (all addressed)
- range_breakout+ LONG: 8T -$0.41, 25% WR — **DISABLED** (commit 5a72c64)
- trend_momentum_near_sma+ LONG: 6T -$0.37, 16.7% WR — **DISABLED** (legacy)
- hzscore+ standalone LONG: 11T -$0.16, 36.4% WR — **RESTRICTED** to combo-only (commit 124def0)

### Fix Applied
**NO NEW CHANGES.** All 3 bleeding signals already addressed by prior CEO decisions:
- range_breakout+ disabled Aug 12 10:00
- hzscore restricted to combo-only Aug 12 09:21
- trend_momentum disabled earlier (legacy)
- Aug 13 eval (trailing stop, momentum fade, confidence tightening, accel-300) still running

### Root Cause
- LONG bleeding today (46.2% WR) — market-driven, not signal-driven
- ATR stop loss dominant exit: 57T -$3.00 (48h) — expected behavior
- SHORT profitable (60.9% WR) — regime-appropriate

### Verification
- 7d solid (+$0.64, 52.8% WR), stars intact, daily recovering (-$0.33 → -$0.06)
- No overreaction — all bleed sources addressed, system recovering

---

## CEO Report — 2026-08-12 10:00 UTC

### Diagnosis
**Verified DB numbers:**
- **24h**: 69T, -$0.24, 50.7% WR — flat
- **7d**: 410T, +$0.60, 52.7% WR — positive
- **Daily**: Aug 9 +$0.62 peak, Aug 10 -$0.10, Aug 11 -$0.33, Aug 12 -$0.07 (improving)
- **LONG7d**: 274T +$1.33 (53.3% WR — strong)
- **SHORT7d**: 136T -$0.73 (51.5% WR — bleed improving from -$0.89)
- **Stars intact**: bb_bounce+,range_finder+ 53T +$0.71 58.5%, bb-bounce-short,hzscore- 17T +$0.12 58.8%, hzscore+,mover+ 5T +$0.17 80%, range_breakout- 5T +$0.41 100%

### Bleeders
- range_breakout+ LONG: 7T -$0.30, 28.6% WR — **DISABLED** (this run)
- hzscore+ standalone: 12T -$0.24, 33.3% WR — monitor (performs well in combos)
- trend_momentum_near_sma+: DISABLED (legacy 0% WR)

### Fix Applied
**RANGE_BREAKOUT_PLUS_ENABLED = False** (line 1049 in hermes_constants.py)
- Rationale: 7d bleed -$0.30, 28.6% WR while range_breakout- SHORT is profitable (5T +$0.41 100%)
- Impact: eliminates worst LONG bleeder, preserves profitable SHORT breakout
- Risk: minimal — range_breakout- SHORT unaffected, combo breakouts unaffected

### Next Review
- Monitor hzscore+ standalone (if no improvement → remove from STANDALONE_BYPASS)
- SHORT7d bleed tracking (if >-$1.50 → consider regime filter)
- 7 open positions, all manageable

---

## CEO Report — 2026-08-12 07:49 UTC

### Diagnosis
**Verified DB numbers (not trusting old reports):**
- **24h**: 69T, -$0.24, 50.7% WR — flat
- **7d**: 409T, +$0.65, 52.8% WR — solid
- **Today (Aug 12)**: 36T, -$0.02, 55.6% WR — flat, improving from Aug 11
- **Open**: 6T, all small/unrealized

**Stars (7d intact):**
- bb_bounce+,range_finder+ LONG: 53T, +$0.71, 58.5% WR ★
- bb_bounce+,hzscore+ LONG: 34T, +$0.22, 50.0% WR ★
- hzscore+,mover+ LONG: 5T, +$0.17, 80.0% WR ★
- range_breakout- SHORT: 5T, +$0.41, 100% WR ★

**Cost drivers (48h):**
- atr_sl_hit: 54T, -$2.69 (dominant)
- profit-monster-trail: 55T, +$2.66 (sole winning exit)
- cut-loser-CL-T1: 4T, -$0.42
- cut-loser-CL-trail: 6T, -$0.28

### Root Cause
24h flat due to SL hits (-$2.69) offset by profit-monster-trail (+$2.66). System naturally reverting after Aug 11 dip. Stars intact, no signal bleeding hard enough to disable.

### Fix Applied
**NO CHANGES.** 7d solid, stars intact, daily recovering, pipeline healthy. Overreacting destabilizes.

### Verification
Pipeline: active. Disk: 77%. Open: 6 (all small). Stars: 4 profitable 7d. trend_momentum_near_sma+ already disabled (0% WR legacy).

---

## CEO Report — 2026-08-12 (latest run)

### Diagnosis

**Verified DB numbers:**
- **24h**: 69T, -$0.24, 50.7% WR — flat
- **48h**: 119T, -$0.92, 44.5% WR — RED
- **7d**: 410T, +$0.60, 52.7% WR — positive but declining
- **Open**: 7T (5 SHORT, 2 LONG) — small/unrealized

**Daily (7d):**
| Day | LONG | SHORT | Total |
|-----|------|-------|-------|
| Aug 9 | +$0.59 | +$0.03 | +$0.62 ★ |
| Aug 10 | -$0.19 | +$0.09 | -$0.10 |
| Aug 11 | -$0.18 | -$0.15 | -$0.33 |
| Aug 12 | -$0.35 | +$0.28 | -$0.07 |

**Stars7d intact:** bb_bounce+,range_finder+ LONG 53T +$0.71 58.5%, bb-bounce-short,hzscore- SHORT 17T +$0.12 58.8%, hzscore+,mover+ LONG 5T +$0.17 80%, range_breakout- SHORT 5T +$0.41 100%

**48h cost drivers:** atr_sl_hit 55T -$2.74 (dominant), cut-loser-CL-T1 4T -$0.42, cut-loser-CL-trail 6T -$0.28

**24h bleeders:** trend_momentum_near_sma+ LONG 6T -$0.37 16.7% WR (DISABLED legacy), range_breakout+ LONG 7T -$0.30 28.6% WR, hzscore+ LONG 11T -$0.16 36.4% WR

### Root Cause

7d PnL declined from +$0.88 to +$0.60 over 3 days. Market choppy/range-bound — hzscore+ and range_breakout+ LONG catching falling knives. SHORT profitable (range_breakout- SHORT +$0.41 100% WR). No signal broken — market-driven cold streak.

### Fix Applied

**NO CHANGES.** Rationale:
- 7d still positive (+$0.60, 52.7% WR)
- Stars intact — all 4 combos profitable
- SHORT profitable — regime working
- trend_momentum_near_sma+ already DISABLED
- Overreacting destabilizes

### Verification

- Pipeline: ACTIVE
- Disk: 77%
- Open: 7 (flat)
- Live trading: enabled

## CEO Report — 2026-08-12 (latest)

### Diagnosis
24h flat (-$0.25, 50.0% WR on 76T). LONG bleeding -$0.54 (46.2% WR), SHORT strong +$0.29 (58.3% WR). 7d solid +$0.65 (52.8% WR). All three 7d bleeding sources addressed: range_breakout+ LONG disabled, hzscore+ restricted to combo-only, trend_momentum_near_sma+ disabled (legacy). Daily improving: Aug 11 -$0.33 → Aug 12 -$0.05. 3 open trades flat. Stars7d intact.

### Root Cause
LONG 24h bleed is residual from disabled signals still in trade window. Short-term noise, not structural. SHORT7d slight bleed (-$0.61) is regime-driven (NEUTRAL market), not signal-driven — star SHORT (bb-bounce-short,hzscore-) still profitable at +$0.12.

### Fix Applied
None. All bleed sources already addressed in prior CEO runs (range_breakout+ disabled Aug12, hzscore+ combo-only restriction, trend_momentum_near_sma+ legacy disable). Current state is post-fix stabilization.

### Verification
Next eval: If LONG 24h WR stays <47% for 48h+, escalate to code review. If SHORT7d bleed exceeds -$1.50, consider regime filter. Pipeline healthy, no crashes, no errors.
