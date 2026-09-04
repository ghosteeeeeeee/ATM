# Bug Hunter Verification Report — Stale Signal Zombie Loop Fixes

**Date:** 2026-09-04
**Bug:** PRESERVE-APPROVED-UPSERT created APPROVED rows with `CURRENT_TIMESTAMP` every cycle, allowing signals to survive indefinitely through: DB→hotset→preserve→UPSERT→DB→hotset→...

## FIX VERDICT: ✅ PASS

All three fixes are correct, complete, and work together to break the zombie cycle at multiple points. No new bugs introduced.

---

## Fix 1: `created_at` in `get_approved_signals()` (signal_schema.py:2655)

**Correct: YES**
**Complete: YES**
**Side effects: None**

**What was done:** Added `MAX(created_at) as created_at` to the SQL SELECT in `get_approved_signals()`.

**Why it works:**
- Without this, `sig.get('created_at')` in `decider_run.py:2736` returned `None`, making the staleness check at decider_run.py:2734-2753 **dead code** — the `if signal_created_at:` guard always skipped it.
- With it, `created_at` flows through the dict construction at signal_schema.py:2689 (`d = dict(r)`) and is never removed, reaching decider_run.py's staleness check.
- `MAX(created_at)` is the correct aggregation: if even the most recent signal in the group is stale, the entire token+direction pair should be skipped.

**Edge cases verified:**
- `created_at` column has `DEFAULT CURRENT_TIMESTAMP` (signal_schema.py:191), so non-NULL values are always present.
- `MAX(created_at)` is safe with GROUP BY — always returns a string in `%Y-%m-%d %H:%M:%S` format.
- The staleness check at decider_run.py:2740-2743 correctly parses this format with `strptime`.

**Interaction with `cleanup_stale_approved`:** The function at signal_schema.py:2831-2837 uses `created_at <= datetime('now', '-'||?||' hours')` with a 1-hour threshold. This operates on the same `created_at` field and provides a separate safety net for APPROVED signals that somehow evade the 5-minute staleness check.

---

## Fix 2: PRESERVE-APPROVED-UPSERT max age + created_at (signal_compactor.py:2270-2328)

**Correct: YES**
**Complete: YES**
**Side effects: None harmful**

**What was done (two parts):**

### Part A: Age guard (lines 2271-2274)
```python
_pe_age_min = (time.time() - pe.get('entry_origin_ts', time.time())) / 60.0 if pe.get('entry_origin_ts') else 0
_preserve_max_age = 30  # max minutes for preserved entry to get UPSERT
if _pe_age_min > _preserve_max_age:
    # skip UPSERT
```

**Why it works:**
- Blocks UPSERT for preserved entries older than 30 minutes, removing the most dangerous path for zombie loop creation.
- Edge cases verified: when `entry_origin_ts` is `None`/missing, age defaults to `0` (safe — allows UPSERT for entries we can't age).
- When `entry_origin_ts` is a valid float, age is computed correctly (verified round-trip: epoch→string→epoch is lossless).

### Part B: Created_at from entry_origin_ts (lines 2298-2328)
```python
_pe_origin_ts = pe.get('entry_origin_ts')
if _pe_origin_ts:
    _pe_created = _dt.datetime.fromtimestamp(_pe_origin_ts, tz=_dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
else:
    _pe_created = None  # fallback to DB default
```

**Why it works:**
- Uses original `entry_origin_ts` as `created_at` instead of `CURRENT_TIMESTAMP`.
- The staleness check in `decider_run.py:2746` uses `MAX(created_at)` (from Fix 1) — with original timestamps, signals age properly and get blocked when stale.
- **UPDATE path (existing APPROVED row, lines 2287-2296):** Does NOT touch `created_at` — correct, preserves original creation time.

**Edge case — NULL created_at fallback:**
- If `_pe_created` is `None`, SQLite inserts `NULL` (not the column default).
- `NULL created_at` fails `created_at > datetime('now','-10 minutes')` in the compaction query (line 1162), so the signal is excluded from future cycles — effectively self-expiring. This is the correct behavior.
- In practice, `entry_origin_ts` should always exist for preserved entries because `_filter_safe_prev_hotset` ensures it (signal_compactor.py:2990-2994).

**One style note:** `_preserve_max_age = 30` is hardcoded. Per `AGENTS.md` conventions, tunable parameters should go in `hermes_constants.py`. This is not a functional issue, just a style deviation.

---

## Fix 3: entry_origin_ts carry forward (signal_compactor.py:1816-1834)

**Correct: YES**
**Complete: YES**
**Side effects: None**

**What was done:** When `prev_entry` is `None` (entry dropped from hotset, new PENDING signal fires), uses DB signal's `created_at` (row[5]) as `entry_origin_ts` instead of `time.time()`.

```python
else:
    # Try to carry forward from DB signal's created_at
    try:
        _db_created = row[5]  # created_at is at index 5 in the SELECT
        if _db_created:
            import datetime as _dt
            _ts = _dt.datetime.strptime(_db_created, '%Y-%m-%d %H:%M:%S')
            _ts = _ts.replace(tzinfo=_dt.timezone.utc)
            entry_origin_ts = _ts.timestamp()
        else:
            entry_origin_ts = time.time()
    except Exception:
        entry_origin_ts = time.time()
```

**Why it works:**
- Prevents the staleness timer from resetting on re-entry. Before the fix, a signal that dropped from hotset and re-appeared as PENDING would get `entry_origin_ts = time.time()`, resetting staleness to 1.0.
- With the fix, `entry_origin_ts` reflects the original signal creation time, so staleness continues decaying naturally.

**Column index verified:** `row[5]` corresponds to `MAX(created_at) AS created_at` in the SELECT query (signal_compactor.py:1147). The column ordering is:
| Index | Column |
|-------|--------|
| 0 | token |
| 1 | direction |
| 2 | signal_type |
| 3 | confidence |
| 4 | merged_source |
| 5 | created_at |
| 6 | z_score_tier |
| 7 | z_score |
| 8 | rsi_14 |
| 9 | macd_hist |
| 10 | macd_value |
| 11 | macd_signal |
| 12 | momentum_state |
| 13 | compact_rounds |
| 14 | hot_cycle_count |
| 15 | signal_metadata |
| 16 | combo_key |

**Fallback safety:** If `row[5]` is `None`, doesn't parse, or any other exception occurs, falls back to `time.time()`. This means worst case the old behavior persists, but no new bugs are introduced.

**Staleness math verified:** With `entry_origin_ts` from DB's `created_at`:
- `age_from_entry = (now - created_at) / 60` = minutes since original signal creation
- `staleness = max(0, 1 - age * 0.2)` → reaches 0 at 5 minutes
- This correctly reflects the true age of the signal, not the age since re-entry.

---

## Integration Issues: NONE

All three fixes work together correctly:

1. **Fix 3** → Prevents staleness reset at re-entry (entry_origin_ts carries forward)
2. **Fix 2 Part A** → Blocks UPSERT for old preserved entries (>30 min), breaking the DB→hotset→preserve→UPSERT cycle
3. **Fix 2 Part B** → Uses original timestamp as `created_at` in new APPROVED rows, so the staleness check works
4. **Fix 1** → Enables the staleness check in `decider_run.py` (previously dead code)
5. **cleanup_stale_approved** → Final safety net: expires APPROVED signals older than 1 hour

The three fixes form a defense-in-depth strategy. Even if one fix had a gap, the others would catch it.

## New Bugs Introduced: NONE

- All three modified files pass `py_compile` syntax check.
- No existing behavior is broken — the fixes only tighten the staleness filtering.
- The UPDATE path for existing APPROVED rows (lines 2287-2296) correctly preserves `created_at`.
- The conflict loser rescue path (line 2383) correctly sets `entry_origin_ts = time.time()` because the rescued entry is a new hotset entry (it wasn't in the previous hotset, it came from the current cycle's scored signals).

## Minor Observations (not bugs)

1. **Hardcoded constant:** `_preserve_max_age = 30` at line 2272 should ideally be in `hermes_constants.py` per coding conventions. Low priority.
2. **Duplicate price check:** decider_run.py lines 2728-2730 and 2767-2769 both check `if not price:`. This is pre-existing, not introduced by the fixes.
3. **Import inside try block:** Fix 2 and Fix 3 both `import datetime as _dt` inside try blocks. This is functionally correct (Python caches imports) but slightly unusual. It avoids adding a top-level import.

## Recommendations

1. Move `_preserve_max_age = 30` to `hermes_constants.py` as `PRESERVE_UPSERT_MAX_AGE_MIN = 30` for consistency.
2. Consider adding a log line when Fix 3 carries forward `created_at` (for audit trail).
3. The 30-minute UPSERT guard (Fix 2A) and the 5-minute staleness decay (Fix 3) together mean signals will be dropped after ~5 minutes regardless. The 30-minute guard is a belt-and-suspenders measure for the preserve path specifically — worth keeping.
