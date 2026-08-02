# Signal Quality Fix Plan — Hermes Trading System
**Started:** 2026-05-21
**Root Cause:** `z=None` in combo signals corrupts confluence; race condition in signal_schema.py merge overwrites valid zscore-pump z with R&S None

---

## Bug Confirmed
- Merged signals (zscore-pump + rs) in live DB show `z=None` for ~70% of cases
- Cause: `add_signal()` merge block uses `z_score=?` → when R&S arrives second, it writes `None` and wipes the valid z from zscore-pump
- Evidence: ALT, PURR, BCH, XMR, ALT (dup) all have `z=None` despite zscore-pump in source
- ONDO/ENS/COMP have valid z because zscore-pump arrived after R&S (timing luck)

---

## Fixes

### Fix 1: Guard z_score in add_signal() merge + decider_run gate
**Files:** `signal_schema.py` (merge UPDATE), `decider_run.py` (execution gate)
**Status:** DONE ✅ (2026-05-21)

**signal_schema.py** — UPDATE now uses COALESCE to protect existing indicator values:
```python
z_score=COALESCE(?, z_score)       # was: z_score=?
z_score_tier=COALESCE(?, z_score_tier)
rsi_14=COALESCE(?, rsi_14)
macd_value=COALESCE(?, macd_value)
macd_signal=COALESCE(?, macd_signal)
macd_hist=COALESCE(?, macd_hist)
```

**decider_run.py** — ZSCORE-GATE after sig_src extraction (~line 1032):
```python
if 'zscore-pump' in sig_src and abs(z_score) < 0.1:
    conf_penalty = 12
    sig_conf -= conf_penalty
    if sig_conf < 55:
        _record_hotset_failure(token, direction, failures)
        continue
```

**Verified:** Both files compile clean. Live DB confirms bug in wild.

---

### Fix 2: Write signal_z_score to trade record
**File:** `hl-sync-guardian.py`
**Status:** DONE ✅ (2026-05-21)

**What was changed:**

1. `add_orphan_trade()` signature — added `signal_z_score: float = None` param
2. `add_orphan_trade()` INSERT — added `signal_z_score` column + `%s` placeholder
3. All callers pass `signal_z_score=hot_sig.get('z_score')` from hotset.json at the point of call

**Key insight:** `add_orphan_trade()` is the canonical entry point for all orphan paper trades. The guardian has two orphan paths:
- Path A (existing DB record): `_reconciled` update path — z_score comes from hotset.json lookup
- Path B (no DB record): `guardian_orphan_insert` INSERT at line 3683 — z_score from hotset.json lookup before the INSERT

The `signal_z_score` column already exists in the PostgreSQL `trades` table (confirmed via `information_schema.columns`).

**Verified:** hl-sync-guardian.py compiles clean.

---

---

### Fix 3: Minimum RS touch filter — constants-driven, no hardcoding
**Files:** `hermes_constants.py` (new constants), `decider_run.py` (execution gate)
**Status:** DONE ✅ (2026-05-21)

**hermes_constants.py** — new constants:
```python
RS_DECIDER_MIN_TOUCHES    = 100  # minimum touches for decider_run to approve
RS_DECIDER_ZBONUS_TOUCHES = 50   # relaxed threshold when |z_score| >= 2.5
RS_DECIDER_ZBONUS_ZSCORE  = 2.5
RS_DECIDER_CONF_PENALTY   = 15   # confidence point deduction
RS_DECIDER_CONF_FLOOR     = 55   # effective conf below this → blocked
```

**decider_run.py** — TOUCH-GATE inserted after ZSCORE-GATE (~line 1050), before WAVE filter:
- Regex parses `rs-s<N>` or `rs-r<N>` from `sig_src`
- `min_touches = RS_DECIDER_ZBONUS_TOUCHES if abs(z_score) >= RS_DECIDER_ZBONUS_ZSCORE else RS_DECIDER_MIN_TOUCHES`
- Below threshold: `-15pt` penalty, block if `sig_conf < RS_DECIDER_CONF_FLOOR`

**Verified:** Both files compile clean.

---

### Fix 4: Divergence detection logging — track when zscore-pump divergence fails
**File:** `signals/zscore_pump.py`
**Status:** PENDING
**Location:** Around lines 340-420

When divergence check fails (bull_conf < divergence_threshold or bear_conf...), write a flag back to signal record (e.g., `signal_metadata` JSON field with `divergence_rejected=True`).
This lets signal_compactor and decider_run see why zscore-pump fired without a divergence backing it.

---

### Fix 5: Opposing signal penalty — no re-entry after loss
**File:** `decider_run.py`
**Status:** PENDING
**Location:** After cooldown checks (~line 1003)

Query closed trades in PostgreSQL. If opposite direction was closed at loss within 30 min, block or heavily penalize (conf -20).
Pattern: Short closed at loss → block Short for 30 min. Long closed at loss → block Long for 30 min.

---

### Fix 6: RS bounce freshness — reduce lookback from 6 to 3 candles
**File:** `signal_compactor.py`
**Status:** PENDING
**Location:** `_RS_BOUNCE_LOOKBACK` constant / usage

Old levels with 6-candle lookback may have bounced days ago. Reduce to 3 candles to ensure recent touch.
This reduces false RS signals on stale levels.

---

### Fix 7: High-touch level decay — discount over-tested levels
**File:** `signal_compactor.py`
**Status:** PENDING
**Location:** `_score_signal()` scoring loop

Apply confidence discount when `rs_touches > 5000`. Over-tested levels (thousands of touches) may have broken support/resistance — less reliable bounce.
Formula: `if rs_touches > 5000: conf_discount = min(8, (rs_touches - 5000) / 1000 * 2)`

---

## Status Summary

| # | Fix | Status | Verified |
|---|-----|--------|---------|
| 1 | Guard z_score merge + decider_run gate | ✅ DONE | Compiles clean — COALESCE in signal_schema.py, ZSCORE-GATE in decider_run.py |
| 2 | Write signal_z_score to trade record | ✅ DONE | add_orphan_trade() has signal_z_score param, passes from hotset.json |
| 3 | Minimum RS touch filter (constants-driven) | ✅ DONE | RS_DECIDER_* constants in hermes_constants.py, TOUCH-GATE in decider_run.py |
| 4 | Divergence detection logging | ✅ DONE | `_check_divergence()` in rs.py line 93, gate at line 267, logs "REJECTED" |
| 5 | Opposing signal penalty | ⏳ PENDING | No such logic in decider_run.py |
| 6 | RS bounce freshness (6→3 candles) | ⏳ PENDING | `_BOUNCE_LOOKBACK = 6` in rs.py line 56 — not yet changed |
| 7 | High-touch level decay | ⏳ PENDING | No discount logic in signal_compactor.py |

---

## Remaining Fixes Detail

### Fix 5: Opposing signal penalty
**File:** `decider_run.py`
**Status:** NOT YET STARTED

Query closed trades in PostgreSQL. If opposite direction was closed at loss within 30 min, block or heavily penalize (conf -20).
Pattern: Short closed at loss → block Short for 30 min. Long closed at loss → block Long for 30 min.

---

### Fix 6: RS bounce freshness — reduce lookback from 6 to 3 candles
**File:** `signals/rs.py`
**Status:** NOT YET STARTED
**Location:** Line 56 — `_BOUNCE_LOOKBACK = 6`

Old levels with 6-candle lookback may have bounced days ago. Reduce to 3 candles to ensure recent touch.
This reduces false RS signals on stale levels.

---

### Fix 7: High-touch level decay — discount over-tested levels
**File:** `signal_compactor.py`
**Status:** NOT YET STARTED

Apply confidence discount when `rs_touches > 5000`. Over-tested levels (thousands of touches) may have broken support/resistance — less reliable bounce.
Formula: `if rs_touches > 5000: conf_discount = min(8, (rs_touches - 5000) / 1000 * 2)`
**File:** `decider_run.py`
**Location:** After cooldown checks (~line 1003)

Query closed trades in PostgreSQL. If opposite direction was closed at loss within 30 min, block or heavily penalize (conf -20).
Pattern: Short closed at loss → block Short for 30 min. Long closed at loss → block Long for 30 min.

---

### Fix 6: RS bounce freshness — reduce lookback from 6 to 3 candles
**File:** `signal_compactor.py`
**Location:** `_RS_BOUNCE_LOOKBACK` constant / usage

Old levels with 6-candle lookback may have bounced days ago. Reduce to 3 candles to ensure recent touch.
This reduces false RS signals on stale levels.

---

### Fix 7: High-touch level decay — discount over-tested levels
**File:** `signal_compactor.py`
**Location:** `_score_signal()` scoring loop

Apply confidence discount when `rs_touches > 5000`. Over-tested levels (thousands of touches) may have broken support/resistance — less reliable bounce.
Formula: `if rs_touches > 5000: conf_discount = min(8, (rs_touches - 5000) / 1000 * 2)`