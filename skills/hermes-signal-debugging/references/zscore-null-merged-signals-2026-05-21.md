# z_score=None in Merged Combo Signals — Root Cause + Fix

**Date:** 2026-05-21  
**Symptom:** zscore-pump listed in signal source, but z_score=0 in hot-set entries; combo signals with z=None correlated with losses

## Root Cause — signal_schema.py add_signal() merge (line ~697)

When a non-indicator signal (R&S) merges with an existing row that carries z_score from zscore-pump, the UPDATE overwrites z_score with NULL:

```python
# Line 697-710 — all fields written unconditionally
UPDATE signals SET
    z_score=?,      -- NULL when R&S merges (R&S doesn't carry z)
    rsi_14=?,      -- NULL
    macd_value=?, -- NULL
    ...
```

The fix uses COALESCE to preserve existing values when the new signal doesn't provide them:

```python
z_score=COALESCE(?, z_score),   -- only update if new value is not NULL
z_score_tier=COALESCE(?, z_score_tier),
rsi_14=COALESCE(?, rsi_14),
macd_value=COALESCE(?, macd_value),
macd_signal=COALESCE(?, macd_signal),
macd_hist=COALESCE(?, macd_hist),
```

## Secondary Gate — decider_run.py (entry gate, line ~980)

Even with the schema fix, add a runtime gate in the decider entry loop:

```python
sources = hot_sig.get('sources', '')
if 'zscore-pump' in sources and abs(z_score) < 0.1:
    conf_penalty = 12
    confidence -= conf_penalty
    if confidence < 55:
        _record_hotset_failure(token, direction, failures)
        continue
```

## Key Findings

- **Valid z requiring ≥20 candles** — ANIME had 6 candles at 23:14 (z=None), 26 at 18:26 (z=-2.467)
- **Combo signals: only 30% have valid z** vs standalone: 84% — merge is the destroyer
- **z=None on zscore-pump source = signal corruption**, not just absence
- **RS touches predict outcomes** better than z_score alone: winners had 2533, 3415, 498, 294, 490+689 touches; losers had 20, 48, 69, 77, 111, 3071, 16785
- **Low touch count + z=None = likely loss** (counter-trend trap)
- **T's finding**: signals worked well towards end of day, then picked losing moves — zscore-pump candles thinned out as market moved, fewer valid z readings → more merges with z=None → corrupted entries

## Files Affected

- `/root/.hermes/scripts/signal_schema.py` line ~697 (add_signal merge UPDATE)
- `/root/.hermes/scripts/decider_run.py` line ~980 (z-score gate after confidence check)