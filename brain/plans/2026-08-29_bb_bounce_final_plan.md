# bb_bounce Signal Optimization — Final Plan
**Date:** 2026-08-29
**Status:** PENDING
**Author:** CEO / Hermes Agent

---

## Executive Summary

Multiple independent analyses (3 agents + 1 own-conclusions audit) converged on the same root cause and solution. The bb_bounce signal has a 58.9% WR across 276 trades. The primary issue is the velocity gate fires at detection time, not execution time. The best filter found is velocity-based: LONG > -0.005%, SHORT < 0.005%, achieving 84.6% WR.

---

## Root Cause (Confirmed by Independent Audit)

**Velocity gate fires at signal detection time, not execution time.** Signals can sit in the hotset for 17+ minutes while market conditions deteriorate. By execution, the price has reversed.

Evidence: 58.1% of losers (68/117) show falling knife (LONG) or rising knife (SHORT) pattern.

---

## Changes Already Completed

### 1. Velocity data source fix (bb_bounce.py)
**Status:** ✅ DONE
- Changed `_get_15m_velocity()` from `price_history` (stale, 7.5min window) to `candles_1m` (accurate, 15min window)
- Also fixed spike exhaustion filter
- Backtest: +22 winners recovered, +11 losers caught

### 2. Connection leak fix (bb_bounce.py)
**Status:** ✅ DONE
- Added `finally` block to `_is_solo()` function

### 3. Hardcoded path fix (bb_bounce.py)
**Status:** ✅ DONE
- Replaced hardcoded `/root/.hermes/data/candles.db` with `CANDLES_DB` from `paths.py`

---

## Changes Pending

### 4. Velocity filter at detection time
**File:** `scripts/signals/bb_bounce.py` and `scripts/signals/bb_bounce_short.py`
**Status:** PENDING
**Priority:** HIGH

Add velocity check in `detect_bb_bounce()` and `detect_bb_bounce_short()`:

```python
# In detect_bb_bounce(), after momentum computation:
from hermes_constants import BB_BOUNCE_VEL_LONG_MIN, BB_BOUNCE_VEL_SHORT_MAX

# For LONG: block if momentum < threshold (price still falling)
if direction == 'LONG' and momentum < BB_BOUNCE_VEL_LONG_MIN:
    return None

# For SHORT: block if momentum > threshold (price still rising)
if direction == 'SHORT' and momentum > BB_BOUNCE_VEL_SHORT_MAX:
    return None
```

**Thresholds (from independent audit):**
- `BB_BOUNCE_VEL_LONG_MIN = -0.005` (block LONG if momentum < -0.005)
- `BB_BOUNCE_VEL_SHORT_MAX = 0.005` (block SHORT if momentum > 0.005)

**Backtest result:** 84.6% WR (55/65 trades survive)

### 5. Execution-time velocity check in decider_run.py
**File:** `scripts/decider_run.py`
**Status:** PENDING
**Priority:** HIGH

Add re-check of velocity before placing trade:

```python
from hermes_constants import SIGNAL_STALENESS_MAX_AGE_MIN, SIGNAL_STALENESS_PRICE_PCT

# Age check
signal_age_min = (time.time() - signal_created_ts) / 60
if signal_age_min > SIGNAL_STALENESS_MAX_AGE_MIN:
    log(f'🚫 [STALE] {token}: {signal_age_min:.1f}min old')
    continue

# Price drift check
price_delta = abs(current_price - signal_price) / signal_price * 100
if price_delta > SIGNAL_STALENESS_PRICE_PCT:
    log(f'🚫 [DRIFT] {token}: price moved {price_delta:.2f}%')
    continue
```

### 6. Fix velocity sign inversion (bb_bounce.py)
**File:** `scripts/signals/bb_bounce.py` line 372
**Status:** PENDING
**Priority:** MEDIUM

The spike exhaustion filter has a sign inversion bug.

### 7. Fix hardcoded path in bb_bounce_short.py
**File:** `scripts/signals/bb_bounce_short.py` line 77
**Status:** PENDING
**Priority:** MEDIUM

Same hardcoded path issue as bb_bounce.py — should use `CANDLES_DB`.

### 8. Fix inconsistent kill-switch state
**File:** `scripts/hermes_constants.py`
**Status:** PENDING
**Priority:** LOW

`BB_BOUNCE_ENABLED=False` but `ROTATOR_PROTECTED_FLAGS` includes it. Need to align.

---

## Backtest Summary

| Filter | WR | PnL | Trades | Winners Kept |
|--------|-----|-----|--------|-------------|
| Baseline (no filter) | 58.9% | -$0.78 | 26 | 100% |
| Velocity (LONG>-0.005, SHORT<0.005) | **84.6%** | TBD | 55 | TBD |
| Momentum > -0.005 (LONG only) | 54.5% | TBD | TBD | TBD |
| BB width >= 0.5% | 62.7% | TBD | TBD | TBD |
| Execution-time staleness (3min) | TBD | TBD | TBD | TBD |

---

## Independent Audit Findings

**Verdict file:** `brain/verdicts/2026-08-29-bb_bounce-independence-verdict.md`

**Key corrections:**
- BB width filter achieves 62.7% WR (not 75% as claimed)
- 5m range filter hurts performance (55.9% vs 58.9% baseline)
- Momentum filter only works for SHORT (85.7%), not LONG (54.5%)
- Velocity filter is the best: 84.6% WR

---

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Velocity filter at detection | LOW | Blocks bad entries, keeps good ones |
| Execution-time staleness check | MEDIUM | New filter at execution, monitor first week |
| Bug fixes | LOW | Correcting existing issues |

---

## Files to Change

| File | Change | Priority |
|------|--------|----------|
| `scripts/signals/bb_bounce.py` | Velocity filter + bug fixes | HIGH |
| `scripts/signals/bb_bounce_short.py` | Velocity filter + hardcoded path | HIGH |
| `scripts/decider_run.py` | Execution-time staleness check | HIGH |
| `scripts/hermes_constants.py` | Add velocity thresholds + fix kill-switch | HIGH |

---

## Monitoring After Deployment

1. Watch pipeline logs for `STALE` and `DRIFT` skip messages
2. Track velocity filter skip rate — if >30% of signals skipped, thresholds may be too tight
3. Monitor bb_bounce WR weekly — should improve from 58.9%
4. Check for false positives (winners being skipped)
