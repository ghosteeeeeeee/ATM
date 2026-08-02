# Hot-Set Bug Investigation & Fix Plan

## Status: BUGS FIXED — awaiting live validation

## Root Cause Analysis

The hot-set was showing only 6 tokens (fallback low-quality signals) because of **4 separate bugs** in the signal pipeline:

---

### Bug 1: SQL Syntax Error in `signal_schema.py` (CRITICAL)
**File:** `/root/.hermes/scripts/signal_schema.py`, line 577

**Code:**
```python
""", (f'-{minutes} minutes}',))   # ← stray } in f-string
```

**Fix:**
```python
""", (f'-{minutes} minutes',))
```

**Impact:** The `expire_signals()` function was crashing on EVERY pipeline run, so PENDING signals were never expired. The DB was accumulating thousands of stale PENDING signals. Every new pipeline run competed against this pile.

---

### Bug 2: Indentation Error in `ai_decider.py` (CRITICAL)
**File:** `/root/.hermes/scripts/ai_decider.py`, line 1164

**Code:**
```python
     if not signals:   # 5 spaces — wrong
        conn.close()
```

**Fix:** Changed to 4-space indent.

**Impact:** `ai_decider.py` crashed on startup with `IndentationError`, so it couldn't run LLM compaction at all. Signals piled up unchecked.

---

### Bug 3: Index Out of Range in `ai_decider.py` (CRITICAL)
**File:** `/root/.hermes/scripts/ai_decider.py`, line 1838

**Context:** The `_do_compaction_llm()` SELECT returns 8 columns (indices 0-7):
`token(0), direction(1), signal_type(2), confidence(3), source(4), created_at(5), z_score_tier(6), z_score(7)`

**Code:**
```python
z_val = sig_entry[9] if sig_entry else 0  # ← index 9 doesn't exist!
```

**Fix:** Changed `[9]` to `[7]`.

**Impact:** Even when the LLM correctly ranked signals, the post-LLM loop crashed with `IndexError: tuple index out of range`, preventing any hot-set from being built. The `hot_cycle_count` update also never happened.

---

### Bug 4: 1-Hour Hard Cap Removed
**File:** `/root/.hermes/scripts/signal_schema.py`

Removed the "1-hour hard cap" block that force-expired signals with `review_count>=1` but `compact_rounds=0`. T confirmed signals should be protected indefinitely until compaction succeeds.

---

## Fixes Applied

| File | Bug | Fix |
|------|-----|-----|
| `signal_schema.py:577` | `}` typo in f-string | Removed stray `}` |
| `ai_decider.py:1164` | 5-space indent | Changed to 4 spaces |
| `ai_decider.py:1838` | `sig_entry[9]` OOB | Changed to `sig_entry[7]` |
| `signal_schema.py:579-590` | 1-hour hard cap | Removed per T request |

## Current State

- `signal_schema.py`: Clean (verified with `py_compile`)
- `ai_decider.py`: Clean (verified with `py_compile`)
- LLM rate-limiting is heavy right now (429s on every attempt), but code is syntactically correct

## Validation Steps

1. **Manual test:** `python3 scripts/ai_decider.py` — should complete without IndexError
2. **Check hotset.json:** Should show 5-10 signals (not 4 fallback)
3. **Monitor pipeline.log:** Should show `expire_signals` completing without errors
4. **DB check:** PENDING count should drop over time (compaction + expiry working)

## Open Questions

- LLM rate-limit budget is tight right now — may need to run during off-peak hours
- The 10-min SELECT window may need tuning once system stabilizes
