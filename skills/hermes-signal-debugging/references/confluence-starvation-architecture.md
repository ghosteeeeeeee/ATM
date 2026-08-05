# Confluence Starvation — RS Signals Never Achieve 2+ Unique Types

**Date:** 2026-05-28
**Symptom:** Hot-set stays empty (0 entries). Many signals fire (RS 5–59/hr, mtp_zscore). Almost all EXPIRED via `compaction_stale_5min`. Only 3 signals achieved 2-source confluence in 24h.

**Root Cause Architecture:**

Signal compactor groups by `combo_key` (token+direction+source-set), NOT by token+direction. RS signals fire at multiple levels, each with a different combo_key:
```
AXS SHORT: rs-r12  → combo_key = "AXS:SHORT:rs-r12"  (separate row)
AXS SHORT: rs-r16  → combo_key = "AXS:SHORT:rs-r16"  (separate row)
AXS SHORT: rs-r40  → combo_key = "AXS:SHORT:rs-r40"  (separate row)
```

Even when 3 levels fire simultaneously for the same token+direction, they appear as 3 separate DB rows and are NEVER merged.

**Confluence Normalization Further Collapse:**

`_signal_type_key()` strips trailing digits:
```
rs-r16  → rs-r
rs-r40  → rs-r
rs-r12  → rs-r
```

All normalize to the same type. Even if they somehow got grouped, 3 sources of `rs-r` = 1 unique type → confluence FAILS.

**The Critical Query (signal_compactor.py ~line 430):**
```python
GROUP BY combo_key  # <- This is the bottleneck
```

It should group by token+direction and aggregate sources from all levels.

**The SQL Expiry Gate (line ~391):**
```python
WHERE decision = 'PENDING'
  AND created_at > datetime('now', '-5 minutes')
  AND confidence >= 60
  AND combo_key IS NOT NULL
GROUP BY combo_key
```

5-min window + GROUP BY combo_key = RS multi-level signals can't find each other → expire → 390 EXPIRED in 24h from single-source starvation.

**How to Verify:**
```sql
-- Check combo_keys per token+direction (should be many with RS signals)
SELECT token, direction, COUNT(DISTINCT combo_key) as keys
FROM signals
WHERE signal_type='support_resistance'
  AND created_at >= datetime('now', '-1 hour')
GROUP BY token, direction
HAVING keys > 1;  -- Many hits = multi-level problem
```

**Fix Direction:**
1. Change GROUP BY to `token, direction` (not combo_key)
2. Collapse same-type multi-level sources in post-processing
3. Aggregate all RS levels for same token+direction into one entry with merged source
4. Then confluence check sees rs-s (1 type) but 1 type still fails unless mtp or another signal type also fires

**Note:** The fundamental limit is that RS is a single signal type. Even after fixing the grouping, `rs-s+rs-s` = 1 unique type → still fails confluence. The only real fix is: RS needs to co-fire with a DIFFERENT signal type (mtp, hh_hl, etc.) within the 5-min window. The grouping fix just makes multi-level RS actually count as 1 source properly instead of dying separately.

**Key Numbers:**
- RS signals generating: 5–59/hr (normal rate)
- RS EXPIRED: 390 in 24h (compaction_stale_5min)
- RS multi-source (2+ levels same token+dir): ~60 entries but ALL single-type after normalization
- Confluence passes: 3 in 24h (all mtp+rs cross-type)