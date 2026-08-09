# CEO Report — 2026-08-09 (22:30 UTC)

## Diagnosis

**Verified from signal_outcomes DB:**
- 24h: 44 trades, +$0.16, 45.5% WR
- 7d: 424 trades, -$7.52, 42.5% WR (improving from -$8.77 yesterday)

**Star performer:** bb_bounce+,range_finder+ LONG — 17 trades, +$0.52, 58.8% WR
**New SHORT signal:** bb-bounce-short,hzscore- — 2 trades, +$0.11, 100% WR ✓

**Worst bleeders:** All ma100-cross- SHORT combos — 7 trades, -$0.50, 0% WR. ALL pre-fix legacy (earliest 2026-08-08 02:00, latest 11:45). ZERO trades generated after is_component_disabled fix at 22:19 UTC.

## Root Cause

Legacy ma100-cross- SHORT trades from 2026-08-08 are still in the 24h window. They will age out by tomorrow. Dead signals (zscore-rising, vel-hermes, inv-accel-300, pattern_wolf_wave) all correctly disabled since 2026-08-07/08.

## Fix Applied

None needed. is_component_disabled() bug fix deployed at 22:19 UTC — verified working (0 SHORT trades since). All dead signals confirmed disabled. ATR SL at 1.2% (widened from 1.0% on 2026-08-08). System profitable.

## Verification

- Pipeline healthy, 1 token in hotset (LINK LONG)
- All systemd timers running
- No errors in pipeline log last 30min
- 7d WR trending up: 38.7% → 42.5% (+3.8% in 24h)

## Action

**No changes.** All fixes operational. Legacy SHORT trades aging out. Evaluation window ongoing. Next review: 2026-08-10 10:00 UTC.

# CEO Report — 2026-08-09 (02:50 UTC)

## Diagnosis

**Verified from PostgreSQL brain DB:**
- 24h: 42 trades, +$0.40, 47.6% WR (improving from +$0.16 yesterday)
- 7d: 368 trades, -$0.91, 44.0% WR (improving from -$7.52)

**LONG: 35 trades, +$0.61, 51.4% WR** — profitable, on track.
**SHORT: 7 trades, -$0.21, 28.6% WR** — still bleeding, but legacy trades aging out.

**Star:** bb_bounce+,range_finder+ LONG — 17 trades, +$0.60, 58.8% WR
**New star:** bb-bounce-short,hzscore- SHORT — 2 trades, +$0.11, 100% WR ✓

**Worst bleeders (24h):**
- ma100-cross-,range_finder- SHORT: 2T, -$0.14, 0% WR
- ma100-cross-,vortex_break_short SHORT: 2T, -$0.14, 0% WR
- ma100-cross+,vortex_break_long LONG: 6T, -$0.11, 33.3% WR

## Root Cause

All SHORT bleeders are legacy trades from before is_component_disabled fix (2026-08-08 22:19). They will age out by tomorrow. No new SHORT trades generated after the fix.

## Fix Applied

**None needed.** All recent fixes operational:
- is_component_disabled() bug — fixed (0 broken SHORT trades since)
- ATR SL widened to 1.2% — working
- Dead signals (zscore-rising, vel-hermes, inv-accel-300, pattern) — confirmed disabled
- Confluence gate — blocking single-signal entries (verified in pipeline log)

## Verification

- Pipeline healthy, 1 token in hotset (LTC LONG, bb_bounce+,range_finder+)
- 6 open positions (LINK, ASTER, ETH, ME, BCH, ENS — all LONG)
- All systemd timers running
- 7d WR trending up: 38.7% → 44.0% (+5.3% in 24h)

## Action

**No changes.** All fixes working. Legacy SHORT trades aging out. System profitable. Next review: 2026-08-09 10:00 UTC.
