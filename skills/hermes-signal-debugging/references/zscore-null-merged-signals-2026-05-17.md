# zscore=None for Merged Signals — ROOT CAUSE + FIX (2026-05-21)

## Root Cause: Merge UPDATE Overwrites Valid Indicator Values with None

**The bug:** In `signal_schema.py` `add_signal()`, when an existing signal row is found (within 5 min) and merged, the UPDATE statement unconditionally writes every indicator field from the NEW signal's parameters:

```python
# BUGGY — unconditionally overwrites with None when new signal omits the field:
UPDATE signals SET
    z_score=?, z_score_tier=?, rsi_14=?,
    macd_value=?, macd_signal=?, macd_hist=?,
    ...
WHERE id=?
```

When `rs.py` calls `add_signal()` it passes ONLY `token, direction, signal_type, source, confidence` — no `z_score`, no `rsi_14`, no `macd_*`. Python defaults these to `None`. The UPDATE writes `None` into every indicator field, destroying whatever the prior signal (e.g., `zscore_pump`) had written.

**Signal generation order** (from `signal_gen.py` scan sequence):
1. `rs.scan_rs_signals()` fires first → INSERT with z_score=NULL
2. `zscore_pump.scan_zscore_pump_signals()` fires ~1 min later → finds existing row → MERGE
3. MERGE UPDATE writes z_score=2.621 (correct — zscore_pump passed real value)
...but then:
4. `rs` fires again (next cycle) → finds same row → MERGE
5. MERGE UPDATE writes z_score=None → overwrites the valid 2.621

If zscore_pump fires AFTER the second RS call, the valid z stays. If RS fires last, z is wiped.

**DB evidence (live, before fix):**
```
  ONDO  SHORT z=-2.814  src=[rs-r268,zscore-pump-]   ← zscore-pump fired LAST (correct)
  ALT   LONG  z=None    src=[rs-s99,zscore-pump+]    ← R&S fired LAST (wiped)
  PURR  SHORT z=None    src=[rs-r32,zscore-pump-]    ← R&S fired LAST (wiped)
  BCH   LONG  z=None    src=[rs-s36,zscore-pump+]    ← R&S fired LAST (wiped)
  XMR   SHORT z=None    src=[rs-r303,zscore-pump-]   ← R&S fired LAST (wiped)
  COMP  LONG  z=2.456   src=[rs-s412,zscore-pump+]   ← zscore-pump fired LAST (correct)
  ENS   LONG  z=3.543   src=[rs-s384,zscore-pump+]   ← zscore-pump fired LAST (correct)
```

## The Fix — signal_schema.py lines 697-714

**Layer 1 (root cause fix):** COALESCE in the merge UPDATE — preserves existing value when new signal passes None:

```python
# FIX (2026-05-21): Only overwrite indicator fields when the new signal
# actually provides a VALID value. COALESCE(?, z_score) preserves the
# existing indicator value when the new signal doesn't carry that field
# (e.g., R&S doesn't pass z_score — without COALESCE it would wipe the
# valid z_score that a prior zscore-pump signal had written).
c.execute('''
    UPDATE signals SET
        confidence=?, source=?, signal_types=?,
        z_score=COALESCE(?, z_score),
        z_score_tier=COALESCE(?, z_score_tier),
        rsi_14=COALESCE(?, rsi_14),
        macd_value=COALESCE(?, macd_value),
        macd_signal=COALESCE(?, macd_signal),
        macd_hist=COALESCE(?, macd_hist),
        combo_key=?,
        updated_at=CURRENT_TIMESTAMP
    WHERE id=?
''', (new_conf, merged_sources, merged_types,
      z_score, z_score_tier, rsi_14,
      macd_value, macd_signal, macd_hist,
      merged_combo_key,
      sig_id))
```

When R&S calls with `z_score=None`: COALESCE(None, existing_z) → returns existing_z (preserved).
When zscore_pump calls with real `z_score=2.621`: COALESCE(2.621, existing_z) → returns 2.621 (replaces).

**Layer 2 (execution gate defense):** decider_run.py lines 1029-1048 — catches any residual edge case:

```python
# ── ZSCORE-PUMP INTEGRITY GATE ─────────────────────────────────────
if 'zscore-pump' in sig_src and abs(z_score) < 0.1:
    conf_penalty = 12
    sig_conf -= conf_penalty
    if sig_conf < 55:
        log(f'  🚫 [ZSCORE-GATE] {token} {direction} BLOCKED: zscore-pump '
            f'failed/invalid (effective conf={sig_conf:.0f}% < 55)')
        _record_hotset_failure(token, direction, failures)
        continue
```

## All Signals That Call add_signal() Without Indicator Params

Any signal that omits `z_score`, `rsi_14`, `macd_*` params is a potential wipe agent. The fix protects against all of them simultaneously.

**Check for future vulnerabilities:**
```bash
grep -n "add_signal(" /root/.hermes/scripts/signals/*.py | grep -v "z_score\|rsi_14\|macd"
```

## Key Files Modified (2026-05-21)

| File | Change | Line |
|------|--------|------|
| `signal_schema.py` | COALESCE in merge UPDATE | ~697-714 |
| `decider_run.py` | zscore-pump integrity gate | ~1029-1048 |

Both compile clean (`python3 -m py_compile` verified).

## Key Lesson

**The merge UPDATE in `add_signal()` is destructive when the caller passes `None` for indicator fields.** Every signal that calls `add_signal()` without carrying all indicator fields (z_score, rsi_14, macd_*) will corrupt prior indicator values on merge unless COALESCE or conditional logic is used.

**Prevention:** Signal modules that only produce one type of indicator (e.g., R&S produces support/resistance levels, not z-scores) should not pass indicator fields at all — the COALESCE fix handles preservation automatically. But the caller must NOT explicitly pass `z_score=None` if the signal doesn't compute it — simply omit the parameter and let Python's default handle it (also None, but the distinction matters for COALESCE correctness in parameterized queries).

Actually: both `add_signal(z_score=None)` and `add_signal()` (omitted) result in `z_score=None` being passed to the SQL — Python function default is `None` either way. The COALESCE fix is the correct solution, not changing call sites.