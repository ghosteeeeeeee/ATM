# Trading System Improvement Plan

## Goal: Increase winrate and make every trade profitable

## Critical Bugs Fixed (Session 5)

### Bug 1: close_paper_position returns None not False
**File:** position_manager.py:1049-1050
**Fix:** Added `return False` instead of bare `return`

### Bug 2: Context gate FLIP fires AFTER signal inversion
**File:** decider_run.py:2476 vs 2536
**Fix:** Moved signal inversion BEFORE context gate
**Impact:** When SIGNAL_INVERSION_ENABLED is re-enabled, FLIP decisions will be based on correct direction

### Bug 3: _get_1h_trend direction inverted for LONG
**File:** signals/inverse_accel_300.py:163-166
**Fix:** LONG reversion now blocks when price FALLS (catching falling knife)
**Impact:** Was blocking good reversion LONGs when price was recovering

## Pending Fixes

### Bug 4: TP_MAX (1.5%) < SL_MAX (2.0%) — broken risk-reward
**File:** hermes_constants.py:325-328
**Issue:** Max R:R = 1.5/2.0 = 0.75:1. Need >57% WR to be profitable.
**Fix:** Set ATR_TP_MAX = 0.025 (2.5%)
**Impact:** HIGH — this is the single biggest structural reason the system loses money

### Bug 5: FLIP threshold too aggressive (z > 0.5)
**File:** decider_run.py:803,806
**Issue:** z > 0.5 is only half a standard deviation — well within normal market noise
**Fix:** Change threshold from 0.5 to 1.0
**Impact:** MEDIUM — reduces false flips in normal markets

### Bug 6: Dead hours not blocking most signals
**File:** hermes_constants.py:930
**Issue:** DEAD_HOURS_DEFAULT=False means only 4 signal prefixes are blocked
**Fix:** Set DEAD_HOURS_DEFAULT=True (block ALL) with allowlist for proven signals
**Impact:** MEDIUM — dead hours have 16% WR

### Bug 7: Speed=0 cliff edge
**File:** decider_run.py:2393
**Issue:** Only blocks speed exactly 0%, but speed=1% is equally stale
**Fix:** Change to speed < 5%
**Impact:** MEDIUM — prevents stale token trades

### Bug 8: Signal inversion disabled
**File:** hermes_constants.py:943
**Issue:** SIGNAL_INVERSION_ENABLED=False
**Fix:** Set to True when ready
**Impact:** MEDIUM — can flip 77+ losing trades

### Bug 9: Soft trigger 1h → 2h
**File:** position_manager.py:2654-2655
**Issue:** 1h soft trigger kills trades that haven't developed
**Fix:** Change to 2h, 0.5% trail
**Impact:** LOW — fewer premature exits

### Bug 10: Cascade flip arm -10% → -5%
**File:** position_manager.py:104-106
**Issue:** Trade losing 10% before arming is already deeply underwater
**Fix:** Tighten to -5% arm, -8% trigger
**Impact:** LOW — earlier protection

## Winrate Improvement Opportunities

1. **Increase ATR_TP_MAX to 2.5%** — changes R:R from 0.75:1 to 1.25:1
2. **Enable signal inversion** — flip 77+ losing trades
3. **Block all dead hours signals** — +20% WR during dead hours
4. **Context gate FLIP threshold z > 1.0** — reduces false flips
5. **Soft trigger 2h** — fewer premature exits

## Priority Order

1. Bug 4 (TP_MAX) — biggest structural issue
2. Bug 5 (FLIP threshold) — reduces false flips
3. Bug 6 (Dead hours) — blocks low-WR trades
4. Bug 8 (Signal inversion) — flips losing trades
5. Bug 7 (Speed cliff) — prevents stale trades
6. Bug 9 (Soft trigger) — fewer premature exits
7. Bug 10 (Cascade flip) — earlier protection
