# Signal Quality Fixes — 2026-05-21

## What Changed

Two root-cause bugs in the Hermes signal pipeline — both verified, both fixed.

---

## Fix 1: z_score Merge Corruption — `signal_schema.py` + `decider_run.py`

**Root cause:** `add_signal()` merge block used direct assignment (`z_score=?`) in the UPDATE.
When R&S calls `add_signal()` with only `token, direction, signal_type, source, confidence`
(no `z_score` param → Python defaults to `None`), the MERGE UPDATE writes `None` into `z_score`,
wiping whatever valid z a prior zscore-pump call had written.

**Evidence — merged signals in live DB before fix:**
```
  ONDO  SHORT z=-2.814  src=[rs-r268,zscore-pump-]   ← zscore-pump fired last (correct)
  ALT   LONG  z=None    src=[rs-s99,zscore-pump+]    ← R&S fired last (wiped)
  PURR  SHORT z=None    src=[rs-r32,zscore-pump-]    ← R&S fired last (wiped)
  BCH   LONG  z=None    src=[rs-s36,zscore-pump+]    ← R&S fired last (wiped)
```

**Fix (signal_schema.py lines 697-714):**
```python
# COALESCE(?, z_score) preserves existing value when new signal passes None.
# Only overwrite when the new signal actually carries a valid value.
UPDATE signals SET
    confidence=?, source=?, signal_types=?,
    z_score=COALESCE(?, z_score),          # was: z_score=?
    z_score_tier=COALESCE(?, z_score_tier),
    rsi_14=COALESCE(?, rsi_14),
    macd_value=COALESCE(?, macd_value),
    macd_signal=COALESCE(?, macd_signal),
    macd_hist=COALESCE(?, macd_hist),
    ...
```

**Fix (decider_run.py lines 1029-1048 — execution gate defense):**
```python
# If zscore-pump claims a slot in sources but z_score is effectively 0,
# treat as RS-only → apply penalty or block.
if 'zscore-pump' in sig_src and abs(z_score) < 0.1:
    conf_penalty = 12
    sig_conf -= conf_penalty
    if sig_conf < 55:
        _record_hotset_failure(token, direction, failures)
        continue
```

**Both files compile clean** (`python3 -m py_compile` verified).

---

## Fix 3: RS Touch Count Gate — `hermes_constants.py` + `decider_run.py`

**Root cause:** Low-touch RS levels (weak support/resistance) correlate with losing trades.
Winners had 2533-3415 touches. Losers had 20-100 touches. No gate enforced minimum touch count.

**New constants in `hermes_constants.py` (no hardcoding):**
```python
RS_DECIDER_MIN_TOUCHES    = 100  # base threshold
RS_DECIDER_ZBONUS_TOUCHES = 50   # relaxed to 50 when |z_score| >= 2.5
RS_DECIDER_ZBONUS_ZSCORE  = 2.5
RS_DECIDER_CONF_PENALTY   = 15   # confidence points deducted
RS_DECIDER_CONF_FLOOR     = 55   # block below this
```

**Fix (decider_run.py — gate after ZSCORE-GATE, before WAVE filter):**
```python
# Parse rs-s<N> or rs-r<N> from sig_src
touch_match = re.search(r'rs-[sr](\d+)', sig_src or '')
if touch_match:
    rs_touches = int(touch_match.group(1))
    min_touches = RS_DECIDER_ZBONUS_TOUCHES if abs(z_score) >= RS_DECIDER_ZBONUS_ZSCORE else RS_DECIDER_MIN_TOUCHES
    if rs_touches < min_touches:
        sig_conf -= RS_DECIDER_CONF_PENALTY
        if sig_conf < RS_DECIDER_CONF_FLOOR:
            _record_hotset_failure(token, direction, failures)
            continue
```

**Why the Z-score bonus?** Strong momentum (|z| >= 2.5) compensates for a weaker level.
Strong pump can create a bounce on a fresh/novel level. The bonus avoids
over-blocking legitimate momentum-driven setups.

---

## What Still Needs Doing (Fixes 2, 4, 5, 6, 7)

See `/root/.hermes/plans/signal-quality-fix-plan.md` — all 7 fixes listed with status.

| Fix | Description | Status |
|-----|-------------|--------|
| 1 | z_score merge COALESCE + decider gate | ✅ DONE |
| 2 | Write signal_z_score to trade record (guardian) | PENDING |
| 3 | RS touch count gate | ✅ DONE |
| 4 | Divergence detection logging (zscore_pump.py) | PENDING |
| 5 | Opposing signal penalty (decider_run) | PENDING |
| 6 | RS bounce freshness — reduce lookback to 3 candles | PENDING |
| 7 | High-touch level decay (>5000 touches → conf discount) | PENDING |

---

## Key Lessons

1. **Merge UPDATE is destructive** when callers omit fields — COALESCE is the right fix, not changing call sites.
2. **Two-layer defense**: schema fix (source of truth) + execution gate (catches residual edge cases).
3. **All RS constants should be in hermes_constants** — Fix 3 put all 5 thresholds there, none hardcoded in decider_run.
4. **Touch count in source string** (`rs-s99`, `rs-r303`) is the parse target — format established by `rs.py` scanner at lines 525/557.