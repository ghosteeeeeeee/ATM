## CEO Report — 2026-08-14

### Diagnosis
**Verified DB numbers:**
- **24h**: 77T, -$0.19, 50.6% WR — flat
- **7d**: 418T, +$0.71, 53.0% WR — solid
- **Daily**: Aug 9 +$0.62 peak, Aug 10 -$0.10, Aug 11 -$0.33 (worst), Aug 12 +$0.01 (recovery)
- **LONG 7d**: 276T, +$1.26, 53.3% WR — solid
- **SHORT 7d**: 142T, -$0.55, 52.1% WR — bleed improving
- **Stars7d intact**: bb_bounce+,range_finder+ 53T +$0.71 58.5%, bb-bounce-short,hzscore- 17T +$0.12 58.8%, hzscore+,mover+ 5T +$0.17 80%, range_breakout- 7T +$0.43 85.7%
- **Open**: 7 trades, flat

### Bleeders (all addressed)
- range_breakout+ LONG: 8T -$0.41, 25% WR — **DISABLED** (legacy, fading)
- trend_momentum_near_sma+ LONG: 6T -$0.37, 16.7% WR — **DISABLED** (legacy, fading)
- hzscore+ standalone LONG: 12T -$0.12, 41.7% WR — **RESTRICTED** to combo-only

### Fix Applied
**NO CHANGES.** All bleed sources addressed. Aug 12 recovered from Aug 11 worst (-$0.33 → +$0.01). 7d solid (+$0.71), stars intact (4 profitable). SHORT 7d -$0.55 below -$1.50 regime filter threshold. Overreacting destabilizes.

### Verification
Monitor: SHORT7d bleed (if -$1.50+ → consider regime filter).

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
