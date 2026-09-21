# Ride-It Exit System — Bug Hunter V2 Report

**Auditor:** Bug Hunter Subagent  
**Date:** 2026-09-19  
**Files Audited:**
- `scripts/ride_it_exit.py` (399 lines — the FIXED exit module)
- `scripts/position_manager.py` (lines 2695-2730 — ride_it integration)
- `scripts/hermes_constants.py` (lines 1450-1470 — SIGNAL_EXIT_CONFIG)

**Severity Scale:** CRITICAL = money-losing / system-breaking, HIGH = logic error affecting trades, MEDIUM = code quality / edge case, LOW = cosmetic

---

## Previous Bug Verification

### Bug #1 — CRITICAL: Phase 2 Dead Code (Datetime Object vs String)
**Status: ✅ FIXED**

The new `_parse_hold_time()` function (line 242-271) correctly handles datetime objects:
```python
if isinstance(open_time_val, datetime):
    entry_dt = open_time_val
    if entry_dt.tzinfo is None:
        entry_dt = entry_dt.replace(tzinfo=timezone.utc)
```
Phase 2 now properly activates after 2h hold. Max hold time check works. The `manage_ride_it_exit` function now receives `current_price` correctly from position_manager.py (line 2502: `cur = float(pos.get("current_price") or 0)` → passed as 3rd arg at line 2711).

### Bug #2 — CRITICAL: SHORT Phase 2 Trail Comparison Inverted
**Status: ✅ FIXED**

Phase 2 trail (line 392):
```python
should_update = new_sl < current_sl  # SHORT: lower SL = tighter ✓
```
Both LONG and SHORT paths correctly update the trail SL.

### Bug #3 — CRITICAL: SHORT Volume Spike Trail Comparison Inverted
**Status: ✅ FIXED**

Spike override (line 329):
```python
should_update = new_sl < current_sl  # SHORT: lower SL = tighter ✓
```

### Bug #4 — HIGH: Momentum Exit Direction-Unaware
**Status: ✅ FIXED**

New `_get_pos_candle_count()` function (lines 184-219) correctly counts consecutive positive candles (price rising). Momentum exit (lines 369-372) now uses:
- LONG → `_get_neg_candle_count` (price dropping = adverse)
- SHORT → `_get_pos_candle_count` (price rising = adverse)

### Bug #5 — HIGH: Connection Leak in `_persist_sl`
**Status: ✅ FIXED**

`_persist_sl()` (lines 222-239) now has proper `finally` block with connection cleanup.

### Bug #6 — HIGH: SQLite Connections Not in Finally
**Status: ✅ FIXED**

All four SQLite helpers (`_get_atr`, `_get_volume_ratio`, `_get_momentum_velocity`, `_get_neg_candle_count`) now have `finally` blocks with `conn.close()` wrapped in try/except.

### Bug #7 — HIGH: DB Credential Mismatch
**Status: ✅ FIXED**

`_persist_sl()` now imports and uses `BRAIN_DB_DICT` (lines 227-228):
```python
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
```

---

## NEW Bugs Introduced During Fix

### Bug #15 — MEDIUM: No-Op String Replace in `_parse_hold_time`

**Location:** `ride_it_exit.py:257`  
**Severity:** MEDIUM

**Description:**  
The string path in `_parse_hold_time` has a no-op replace:
```python
entry_dt = datetime.fromisoformat(open_time_val.replace('+00:00', '+00:00'))
```
This replaces `'+00:00'` with `'+00:00'` — the same string. The developer clearly intended to handle 'Z' suffix (e.g., `"2026-09-17T12:00:00Z"`), which would need:
```python
entry_dt = datetime.fromisoformat(open_time_val.replace('Z', '+00:00'))
```

**Impact:** LOW-MEDIUM in practice. The primary path (datetime object from psycopg2) is correctly handled at line 249. The string fallback is only triggered if `open_time` is somehow stored as a string. If that string has a 'Z' suffix, `fromisoformat` will raise ValueError (Python <3.11), fall through to strptime, fail again, and default to `hold_hours = 0`. This would cause Phase 2 to never activate for that trade.

**Fix:**
```python
entry_dt = datetime.fromisoformat(open_time_val.replace('Z', '+00:00'))
```

---

## Pre-Existing Bugs Still Present (Not Fixed in This Round)

### Bug #9 — MEDIUM: `volume-breakout` Bare Variant Missing from SIGNAL_EXIT_CONFIG

**Location:** `hermes_constants.py:1457-1460`  
**Severity:** MEDIUM  
**Status:** UNCHANGED (was in original report, not in scope of this fix)

**Description:**  
`mover` has a bare variant (`'mover': 'ride_it'`), `pump_chain` has a bare variant (`'pump_chain': 'pump_exit'`), but `volume-breakout` does NOT have a bare variant. Only `volume-breakout+`, `volume-breakout-`, `volume_breakout+`, `volume_breakout-` are mapped.

```python
'volume-breakout+': 'ride_it',
'volume-breakout-': 'ride_it',
'volume_breakout+': 'ride_it',
'volume_breakout-': 'ride_it',
# Missing: 'volume-breakout': 'ride_it'
# Missing: 'volume_breakout': 'ride_it'
```

**Impact:** If a signal fires with source `volume-breakout` (no +/- suffix), the trade falls through to default exit behavior (ATR TP/SL only). The ride_it 2-phase system is not applied.

**Fix:** Add bare variants:
```python
'volume-breakout': 'ride_it',    # bare variant
'volume_breakout': 'ride_it',    # bare variant
```

### Bug #16 — HIGH: pump_exit Dead Money Time Check Still Broken

**Location:** `position_manager.py:2673`  
**Severity:** HIGH  
**Status:** UNCHANGED (was flagged in original Bug #1 note, not fixed in this round)

**Description:**  
The pump_exit section at line 2673 has the SAME datetime object bug that was the root cause of Bug #1:
```python
open_time_str = pos.get('open_time')
entry_dt = datetime.fromisoformat(open_time_str.replace('+00:00', ''))
```
`open_time_str` is a datetime object from psycopg2. Calling `.replace('+00:00', '')` on a datetime raises `TypeError: 'str' object cannot be interpreted as an integer`, caught by `except Exception: pass` at line 2692.

**Impact:** The pump_exit "dead money" time exit never fires. Trades that are flat for 6+ hours (below `PUMP_EXIT_TIME_THRESHOLD` profit) with fading velocity are not auto-closed. They remain open until ATR SL/TP or other exit mechanisms trigger.

**Fix:** Same pattern as ride_it_fix:
```python
open_time_val = pos.get('open_time')
if open_time_val:
    try:
        if isinstance(open_time_val, datetime):
            entry_dt = open_time_val
            if entry_dt.tzinfo is None:
                entry_dt = entry_dt.replace(tzinfo=timezone.utc)
        else:
            entry_dt = datetime.fromisoformat(str(open_time_val).replace('Z', '+00:00'))
        hold_hours = (datetime.now(timezone.utc) - entry_dt).total_seconds() / 3600
```

### Bug #10 — MEDIUM: `RIDE_IT_TP_PHASE1_MULT` Defined But Never Used

**Location:** `hermes_constants.py:3491`  
**Severity:** MEDIUM  
**Status:** UNCHANGED

**Description:** `RIDE_IT_TP_PHASE1_MULT = 3.0` is defined but never imported or used in `ride_it_exit.py`. The import block (lines 31-40) includes it but the function never references it.

**Impact:** No functional impact, but suggests a planned Phase 1 TP that was never implemented. Misleading for future developers.

### Bug #11 — MEDIUM: Duplicate Signal Parsing 3x Per Position Per Cycle

**Location:** `position_manager.py:2699-2701, 2731-2733`  
**Severity:** MEDIUM  
**Status:** UNCHANGED

**Description:** Signal parsing (`signal.split(',')` + `SIGNAL_EXIT_CONFIG` lookup) happens independently in the ride_it block and the rr_engine block, with identical code.

**Impact:** Performance waste — 900+ unnecessary string operations per minute with 10 positions. Also a maintenance risk: if signal parsing changes, both blocks must be updated.

---

## Summary Table

| # | Severity | Location | Status | Bug |
|---|----------|----------|--------|-----|
| 1 | CRITICAL | `ride_it_exit.py:242-271` | ✅ FIXED | Phase 2 datetime parsing |
| 2 | CRITICAL | `ride_it_exit.py:392` | ✅ FIXED | SHORT Phase 2 trail comparison |
| 3 | CRITICAL | `ride_it_exit.py:329` | ✅ FIXED | SHORT spike trail comparison |
| 4 | HIGH | `ride_it_exit.py:369-372` | ✅ FIXED | Momentum exit direction |
| 5 | HIGH | `ride_it_exit.py:222-239` | ✅ FIXED | `_persist_sl` connection leak |
| 6 | HIGH | `ride_it_exit.py:72-77` etc | ✅ FIXED | SQLite connection leaks |
| 7 | HIGH | `ride_it_exit.py:227-228` | ✅ FIXED | DB credential mismatch |
| 15 | **MEDIUM** | `ride_it_exit.py:257` | **NEW** | No-op string replace in `_parse_hold_time` |
| 16 | **HIGH** | `position_manager.py:2673` | UNFIXED | pump_exit datetime bug (related to Bug #1) |
| 9 | MEDIUM | `hermes_constants.py:1457` | UNFIXED | `volume-breakout` bare variant missing |

---

## Net Assessment

**All 7 previously reported critical and high bugs are FIXED.** The ride_it_exit system now:
- ✅ Phase 2 activates correctly (datetime handled)
- ✅ SHORT trailing works (correct comparisons)
- ✅ Momentum exit is direction-aware (SHORT exits on rising price)
- ✅ Connections are properly cleaned up (finally blocks everywhere)
- ✅ DB credentials match (BRAIN_DB_DICT)

**1 new bug introduced:** A no-op string replace in `_parse_hold_time` (Bug #15, MEDIUM). This is low-impact because the primary datetime path is correct.

**1 critical related bug remains unfixed:** pump_exit dead money time check at `position_manager.py:2673` (Bug #16, HIGH) — same root cause as Bug #1 but in a different code path. This should be fixed using the same `_parse_hold_time` pattern.

**Recommended next steps:**
1. Fix Bug #15: Change `.replace('+00:00', '+00:00')` to `.replace('Z', '+00:00')` in ride_it_exit.py:257
2. Fix Bug #16: Apply the same datetime handling fix to position_manager.py:2673 (pump_exit)
3. Fix Bug #9: Add bare `volume-breakout` variants to SIGNAL_EXIT_CONFIG
