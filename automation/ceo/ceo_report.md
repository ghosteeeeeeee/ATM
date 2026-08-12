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
