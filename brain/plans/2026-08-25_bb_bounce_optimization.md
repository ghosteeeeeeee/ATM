# bb_bounce Signal Optimization Plan
**Date:** 2026-08-25
**Status:** PENDING
**Author:** CEO / Hermes Agent

---

## Executive Summary

Analysis of 232+ bb_bounce trades identified two root causes of losses:
1. **Stale velocity data** — `_get_15m_velocity()` used `price_history` (2 entries/min) with `LIMIT 15`, covering only 7.5 minutes instead of 15. FIXED.
2. **Missing execution-time staleness gate** — Constants `SIGNAL_STALENESS_MAX_AGE_MIN=3` and `SIGNAL_STALENESS_PRICE_PCT=0.25` were defined but never wired into the execution path.

---

## Changes Already Completed

### 1. Fix velocity data source (bb_bounce.py)
**File:** `scripts/signals/bb_bounce.py`
**Status:** ✅ DONE

Changed `_get_15m_velocity()` and spike exhaustion filter to read from `candles.db/candles_1m` instead of `signals_hermes.db/price_history`.

**Backtest results (250 trades):**
- Allowed WR: 63.8% → 66.8% (+3.0%)
- +22 winners recovered, +11 losers caught
- Net: +21 winners, -3 losers

**Verification:** ✅ Independent agent confirmed fix is correct and improves accuracy.

### 2. Add bb_bounce to profit_monster bypass
**File:** `scripts/hermes_constants.py`
**Status:** ✅ DONE, then REVERTED per user instruction

---

## Changes Pending

### 3. Wire up signal staleness gate in decider_run.py
**File:** `scripts/decider_run.py`
**Status:** PENDING
**Priority:** HIGH

**Problem:** `SIGNAL_STALENESS_MAX_AGE_MIN=3` and `SIGNAL_STALENESS_PRICE_PCT=0.25` are defined in `hermes_constants.py` (lines 1492-1493) but never imported or used. No staleness check exists at execution time.

**Implementation:**
Add two checks in `decider_run.py` in the per-signal execution loop, BEFORE the context gate:

```python
from hermes_constants import SIGNAL_STALENESS_MAX_AGE_MIN, SIGNAL_STALENESS_PRICE_PCT

# --- Signal staleness gate ---
signal_created_ts = signal.get('created_at_ts')  # Unix timestamp from signal
signal_price = signal.get('price')
current_price = prices.get(token, {}).get('price')

# Age check
if signal_created_ts:
    signal_age_min = (time.time() - signal_created_ts) / 60
    if signal_age_min > SIGNAL_STALENESS_MAX_AGE_MIN:
        log(f'  🚫 [STALE] {token} {direction}: signal {signal_age_min:.1f}min old (max {SIGNAL_STALENESS_MAX_AGE_MIN}min)')
        mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
        skipped += 1
        continue

# Price drift check
if signal_price and current_price and signal_price > 0:
    price_delta_pct = abs(current_price - signal_price) / signal_price * 100
    if price_delta_pct > SIGNAL_STALENESS_PRICE_PCT:
        log(f'  🚫 [DRIFT] {token}: price moved {price_delta_pct:.2f}% since signal (max {SIGNAL_STALENESS_PRICE_PCT}%)')
        mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
        skipped += 1
        continue
```

**Notes:**
- Need to verify how `created_at_ts` and `price` are available in the signal dict passed to execution
- May need to add these fields to the signal loading query if not already present
- Log clearly so we can tune thresholds from production data

### 4. Fix range_finder.py and range_finder_short.py velocity data source
**Files:** `scripts/signals/range_finder.py`, `scripts/signals/range_finder_short.py`
**Status:** PENDING
**Priority:** MEDIUM

Both files have identical `_get_15m_velocity()` reading from `price_history` with the same 7.5-minute window bug. Apply the same `candles_1m` fix as bb_bounce.py.

### 5. Clean up dead code
**Status:** PENDING
**Priority:** LOW

- Remove `expire_pending_signals()` from `signal_schema.py` (dead function, never called)
- Remove import/call from `signal_gen.py` (defunct file)
- Remove `hermes_constants.py.bak` if it exists

---

## Backtest Validation Plan

Before deploying changes 3-4, run backtest validation:

1. Pull all bb_bounce trades from `signal_outcomes`
2. For each trade, compute what the staleness gate WOULD have blocked
3. Measure: winners killed, losers caught, net PnL impact
4. Verify no regression on existing winning trades

---

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Velocity data source fix | LOW | Already verified by independent agent |
| Staleness gate | MEDIUM | New filter — monitor first week closely |
| range_finder fix | LOW | Same pattern as bb_bounce fix |
| Dead code cleanup | LOW | Functions are never called |

---

## Monitoring After Deployment

1. Watch pipeline logs for `STALE` and `DRIFT` skip messages
2. Track skip rate — if >20% of signals are being skipped, thresholds may be too tight
3. Monitor bb_bounce WR weekly — should improve or stay flat
4. Check for false positives (winners being skipped)

---

## Files Changed

| File | Change | Status |
|------|--------|--------|
| `scripts/signals/bb_bounce.py` | Velocity data source fix | ✅ DONE |
| `scripts/hermes_constants.py` | bb_bounce bypass (reverted) | ✅ REVERTED |
| `scripts/decider_run.py` | Staleness gate | PENDING |
| `scripts/signals/range_finder.py` | Velocity data source fix | PENDING |
| `scripts/signals/range_finder_short.py` | Velocity data source fix | PENDING |
| `scripts/signal_schema.py` | Dead code cleanup | PENDING |
