---
name: hermes-pipeline-debug
description: Debug frozen Hermes pipeline — no new trades, stale hot-set, lock contention between ai_decider and decider_run
---

# Hermes Pipeline Debug Skill

## When to Use
When the Hermes pipeline appears frozen: no new trades, hot-set stale, or pipeline steps exiting immediately with "lock held by another process".

## The Diagnostic Framework

### Step 1 — Check What's Actually Running
```bash
ps aux | grep -E "ai_decider|decider_run|pipeline" | grep -v grep
```

### Step 2 — Check Lock Files
```bash
# FileLock-based locks (hotset_json, hotset_last_updated)
ls -la /root/.hermes/locks/

# ai_decider's own fcntl lock (separate from FileLock!)
cat /root/.hermes/locks/ai_decider.lock
```

### Step 3 — Check Staleness
```bash
python3 -c "
import json, time
d = json.load(open('/var/www/hermes/data/hotset.json'))
age = time.time() - d.get('timestamp', 0)
print(f'hotset age: {age:.0f}s ({age/60:.1f}m)')
print(f'cycle: {d.get(\"compaction_cycle\")}')
print(f'hotset size: {len(d.get(\"hotset\", []))}')
for h in d.get('hotset', []):
    print(f'  {h[\"token\"]:10} conf={h.get(\"confidence\",0):.0f}%')
"
```

### Step 4 — Check Pipeline Log
```bash
grep -E "lock held|ai_decider.*exit|hot-set stale|hotset.*stale|Running ai_decider|every_10" \
  /root/.hermes/logs/pipeline.log | tail -20
```

### Step 5 — Check Pipeline Step Timing
The pipeline runs every 1 min via systemd timer. 10-min steps (ai_decider, etc.) should only run at minute % 10 == 0.

Check in `run_pipeline.py`:
```bash
grep -n "every_10\|STEPS_EVERY_10M\|if every_10" /root/.hermes/scripts/run_pipeline.py
```
**Common bug:** The `if every_10:` guard was accidentally removed when adding a process guard, causing 10-min steps to run every minute.

## Known Lock Contention Patterns

### Pattern 1: ai_decider hangs, lock persists after kill
**Symptom:** "🔒 ai_decider lock held by another process. Exiting." every cycle.

**Cause:** `ai_decider`'s `acquire_lock()` (line ~986 in ai_decider.py) uses raw `fcntl.flock` — NOT `FileLock`. It has no stale-lock cleanup. If ai_decider hangs mid-run (LLM rate limit, timeout), the lock file persists after kill.

**Fix:** Add pre-acquisition cleanup to `acquire_lock()`:
```python
def acquire_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.unlink(LOCK_FILE)  # Clean stale lock
    except: pass
    _lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ...
```

### Pattern 2: FileLock race (three-way race on hotset.json)
**Symptom:** hotset.json gets corrupted or overwritten by two processes simultaneously.

**Cause:** `FileLock` was deleting the lock file on `__exit__` only. Between unlock and next process's open(), a third process could race in.

**Fix:** `FileLock.__enter__` deletes stale lock BEFORE acquiring.

### Pattern 3: Pipeline fires 10-min steps every minute
**Symptom:** `ai_decider` running every minute instead of every 10 minutes.

**Cause:** `if every_10:` guard was accidentally removed when adding a process guard to the loop.

**Fix:** Ensure `if every_10:` wraps the `STEPS_EVERY_10M` loop.

### Pattern 4: decider_run blocks all approvals because hotset is stale
**Symptom:** Signals pile up as PENDING, no new trades open, hotset.json is old.

**Cause:** `decider_run` checks if hotset.json is >11 min stale before approving. If `ai_decider` is hung/locked, staleness grows indefinitely.

## Common Failure Chain

```
LLM rate limit / timeout → ai_decider hangs → lock persists after kill
→ next ai_decider run exits immediately (lock held)
→ hotset.json not refreshed → hotset becomes stale (>11 min)
→ decider_run blocks ALL new approvals → no new trades
→ system appears frozen despite pipeline running
```

## Key Files
- `/root/.hermes/scripts/ai_decider.py` — `acquire_lock()` at line ~986
- `/root/.hermes/scripts/decider_run.py` — hot-set staleness check `_check_hotset_fresh()` at line ~1003
- `/root/.hermes/scripts/run_pipeline.py` — `every_10` timing at line ~40
- `/root/.hermes/scripts/hermes_file_lock.py` — `FileLock.__enter__` stale cleanup
- `/root/.hermes/locks/ai_decider.lock` — ai_decider's own fcntl lock file
- `/var/www/hermes/data/hotset.json` — hot-set cache
- `/root/.hermes/logs/pipeline.log` — pipeline execution log
