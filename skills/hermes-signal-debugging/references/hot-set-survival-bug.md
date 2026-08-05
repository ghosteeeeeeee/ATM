---
name: hot-set-survival-bug
description: Fix for hot-set signal survival bug — compaction excluding signals older than 90 minutes even when they had hot_cycle_count>=1
version: 1.0.0
author: Hermes Agent
created: 2026-04-14
tags: [signals, compaction, hot-set, bug-fix]
metadata:
  hermes:
    files: [/root/.hermes/scripts/ai_decider.py, /var/www/hermes/data/hotset.json]
    symptom: survival_score=0.0 for all entries, compact_rounds always=1, signals never accumulate survival rounds
---

# Hot-Set Compaction Survival Bug

## Symptom
- All entries in `hotset.json` have `survival_score=0.0` and `compact_rounds=1`
- Signals that should survive multiple compaction cycles are lost
- `survival_round` never increments past 1 or 2
- Confirmed via: `cat /var/www/hermes/data/hotset.json`

## Root Cause
In `_do_compaction_llm()` (ai_decider.py, line ~1140), the SQL query filtered:
```sql
WHERE decision IN ('PENDING', 'WAIT')
  AND executed = 0
  AND created_at > datetime('now', '-90 minutes')  -- BUG: age limit
  AND token NOT LIKE '@%'
```

This excluded signals older than 90 minutes — even signals with `hot_cycle_count >= 1` (pipeline-approved survivors). The signal that survived from cycle 1 gets REJECTED in cycle 2 because it's no longer in the 90-min query window.

Compare with `_load_hot_rounds()` (line ~460), which correctly handles this:
```sql
WHERE (
    created_at > datetime('now', '-3 hours')  -- new signals: must be <3h old
    OR hot_cycle_count >= 1                   -- pipeline-approved signals: no age limit
)
```

## Fix Applied
**ai_decider.py line ~1143** — changed WHERE clause to:
```sql
WHERE decision IN ('PENDING', 'WAIT')
  AND executed = 0
  AND (
      created_at > datetime('now', '-90 minutes')  -- new signals: must be <90m old
      OR hot_cycle_count >= 1                       -- pipeline-approved signals: no age limit
  )
  AND token NOT LIKE '@%'
```

This mirrors the correct pattern from `_load_hot_rounds()`.

## Verification
After fix, `survival_round` values should increment (2, 3, etc.) instead of all being 1:
```bash
cat /var/www/hermes/data/hotset.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
for e in d['hotset']:
    print(f'{e[\"token\"]:8} sr={e.get(\"survival_round\",\"?\")} survival={e.get(\"survival_score\",\"?\")} rounds={e.get(\"compact_rounds\",\"?\")}')"
```

## Related Bugs Fixed in Same Session
- FileLock PID fd leak in hermes_file_lock.py — `open(self.lockfile, 'w').write()` leaked fd; fixed to use `os.write(self.fd, ...)` with lseek+ftruncate
- Phantom positions in DB not closing — `_close_paper_trade_db()` silently skipped when `exit_price <= 0`; fixed with explicit ValueError validation
