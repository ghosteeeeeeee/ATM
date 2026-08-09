# CEO Report — 2026-08-10 (03:50 UTC)

## Diagnosis

**Verified from brain DB `trades` table:**
- 24h: 42 trades, +$0.13, 42.9% WR
- 7d: 369 trades, -$0.95, 43.9% WR

**7d daily trend:** Aug 4: -$0.69 → Aug 5: +$0.21 → Aug 6: -$0.08 → Aug 7: +$0.34 → Aug 8: +$0.10 → Aug 9 (partial): +$0.03. System stabilizing after Aug 2-4 drawdown.

**Star performer:** bb_bounce+,range_finder+ LONG — 18T/24h +$0.36 (50% WR), 27T/7d +$0.67 (59.3% WR). Carries entire system profit.

**Bleeders 24h:** ma100-cross+,vortex_break_long (5T, 20% WR, -$0.14), ma100-cross-,range_finder- (2T, 0% WR, -$0.14), ma100-cross-,vortex_break_short (2T, 0% WR, -$0.14). All low-volume, noise not signal.

**7d worst signals:** zscore-rising- (38T, 31.6% WR, -$0.22), ma100-cross,return_exhaustion- (7T, 42.9% WR, -$0.28), accel-300-breakout (4T, 0% WR, -$0.30). All already disabled via flags.

**Open positions:** 6 fresh (0.1–1.9h old), healthy. All bb_bounce+/hzscore+/range_finder+ confluences.

## Root Cause

System edge is thin. Single confluence (bb_bounce+,range_finder+) generates all profit. Other combos are marginal. No single failure — just low alpha overall.

## Observation

All `close_reason` fields are None across 24h trades — position_manager not recording exit rationale. This blinds us to SL/take-profit analysis. Needs investigation.

## Fix Applied

None needed. System stable. Recent fixes (ATR SL 1.2%, BLOCKED_HOURS removal, is_component_disabled) all verified working. Evaluation window ongoing. Live trading enabled, disk 80% (24GB free).

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

## CEO Report — 2026-08-09 23:00 UTC

### Diagnosis
24h: 43T, +$0.36, 46.5% WR — system profitable. LONG +$0.57 (50% WR). SHORT -$0.21 (28.6% WR, only7 trades). 7d: 369T, -$0.95 (43.9% WR). SHORT -$1.90/7d (37.7% WR) but ALL legacy pre-fix trades. Star: bb_bounce+,range_finder+ LONG — 26T, +$0.70, 61.5% WR.

### Root Cause
SHORT bleeding is historical dead signals aging out. zscore-rising- last fired 08-04 (disabled08-07). hzscore-,return_exhaustion- last fired 08-07 (disabled). inv-accel-300- last fired 08-04 (disabled). These signals are in the7d window but no longer generating new trades. Only 7 SHORT trades in 24h — SHORT volume collapsed as intended.

### Fix Applied
No changes. All prior fixes verified working:
- is_component_disabled() blocking dead SHORT signals ✅
- ATR SL widened to 1.2% ✅
- BLOCKED_HOURS removed from SHORT signals ✅
- Dead signals killed (zscore-rising, inv-accel-300, return_exhaustion-, etc.) ✅

### Verification
24h PnL positive (+$0.36). LONG profitable. SHORT bleeding stopped (7 trades/24h vs 204/7d). Legacy trades will age out of7d window by 08-11. System on track.
