# Hermes Signal Debugging — Bug Encyclopedia

## Bugs Caught

### Bug 1: accel-300- SHORT blocked by symmetric gap comparison
**File:** `accel_300.py` line 222-224
**Symptom:** accel-300- (SHORT) never fires in history; 0 signals all-time vs 2862 accel-300+ (LONG).
**Root cause:** `gap_now < MIN_GAP_PCT` (MIN_GAP_PCT = 0.20%) applies symmetrically to both LONG and SHORT directions. For SHORT, `gap_now` is always negative (e.g., -0.05). A negative value is always less than +0.20, so the condition was always True — SHORT was always skipped at Condition 2.
**Fix:**
```python
# WRONG — blocks all SHORT signals:
if gap_now < MIN_GAP_PCT:
    return False

# CORRECT — symmetric check for both directions:
if abs(gap_now) < MIN_GAP_PCT:
    return False
```
**Verified:** After fix — UNI, XMR, ZK SHORT signals fired; DOGE SHORT passed all conditions; 37 LONG + 3 SHORT in next scan.

---

### Bug 2: RS add_signal() missing source/confidence args
**File:** `rs.py` lines 667-671
**Symptom:** RS scan returns 0 signals despite directional flags enabled and tokens clearly in regime.
**Root cause:** `scan_rs_signals()` calls `add_signal(token, direction, signal_type)` omitting required positional args `source` and `confidence`. These exist in the `sig` dict as `sig['source']` and `sig['confidence']`.
**Fix:** Add `source=sig['source'], confidence=sig['confidence']` to the add_signal() call:
```python
# WRONG:
add_signal(token, direction, signal_type)

# CORRECT:
add_signal(token, direction, signal_type, source=sig['source'], confidence=sig['confidence'])
```
**Note:** `add_signal()` signature requires `source` and `confidence` — see `signal_schema.py` line 361.
**Verified:** After fix — RS signals written to DB (BRETT SHORT 86%, BLUR LONG 74.8% at 06:50:08; PURR SHORT, PUMP LONG at 06:51:17).

---

### Bug 3: rows[-1][0] staleness check in rs.py (NOT a bug — confirmed correct)
**File:** `rs.py` line 609
**Symptom:** Confusion about whether `rows[-1][0]` refers to oldest or newest candle.
**Clarification:** The query is `ORDER BY timestamp DESC LIMIT 4700` with outer sort ASC. Therefore:
- `rows[0]` = oldest (first row of ASC sort = most ancient)
- `rows[-1]` = newest (last row of ASC sort = most recent)

The staleness check uses `rows[-1][0]` (newest) which is correct. Do NOT change to `rows[0][0]`.

---

## signal_compactor.py changes this session

Changed requirement from `hhh-` (hh_hl breakout) to `accel-300` at 3 gate locations:
- Line 644-648: verbose skip message
- Line 872-878: HOTSET-FILTER block log
- Line 1320-1324: entry filtering (breakout path)

Both LONG and SHORT now require `accel-300+` / `accel-300-` as the primary directional trigger.

## Key constants
- Staleness threshold: 120s (rs.py line 609)
- MIN_GAP_PCT: 0.20% (accel_300.py)
- ACCEL_300 flags: ACCEL_300_ENABLED=True, ACCEL_300_PLUS_ENABLED=True, ACCEL_300_MINUS_ENABLED=True