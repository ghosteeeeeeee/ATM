# Kanban Task Corruption Detection Skill

## Purpose
Detect and recover from kanban task corruption or accidental task loss by comparing with recent git versions.

## Trigger
Run automatically when kanban-tasks.json is modified, or as cron every 6 hours.

## Instructions

### Step 1: Get Current Kanban Hash
Read the current kanban-tasks.json and compute a quick hash of the task counts per list:
```
todo_count = len(todo)
in_progress_count = len(in_progress)
done_count = len(done)
blocked_count = len(blocked)
```

### Step 2: Check Last 3 Git Versions
Use `git log` to get the last 3 commits that modified kanban-tasks.json:
```bash
git log --oneline -5 -- kanban-tasks.json
```

For each of the last 3 versions, load and compare:
- Task names in each list
- Total task counts per list

### Step 3: Detect Missing Tasks
For each list (todo, in_progress, done, blocked), check if any tasks exist in previous versions but are missing in current:
- Compare by task name (unique identifier)
- Flag any tasks that were removed

### Step 4: Handle Missing Tasks
If missing tasks found:
1. **Log to taskerrors.md** in /root/.openclaw/workspace/tasks/
2. Add lost tasks back to appropriate list with note: "[RECOVERED] Was in {list} but lost - recovered from git version {commit_hash}"
3. Update taskerrors.md with:
   - Timestamp of detection
   - List(s) affected
   - Task names recovered
   - First detection time (to track if >24h)

### Step 5: Track Persistence
In taskerrors.md, track:
- First occurrence timestamp
- Latest occurrence timestamp
- If latest - first > 24 hours, flag for investigation
- Investigation needed: Check cron logs, other processes that might be corrupting

### Step 6: Investigation Trigger
If corruption persists > 24 hours:
- Log warning in shared_notes/notes.md
- Check for:
  - Concurrent writes to kanban
  - Script errors
  - Git conflicts
  - Memory issues
- Add investigation task to kanban

## Example taskerrors.md Format
```markdown
# Kanban Task Errors

## 2026-02-28
### 13:00 UTC
- **Type:** Lost tasks detected
- **Affected lists:** done
- **Lost tasks:** ["Task name 1", "Task name 2"]
- **Recovered:** Yes
- **First seen:** 2026-02-28 12:00 UTC
- **Investigation needed:** No

### 12:00 UTC
- **Type:** Lost tasks detected  
- **Affected lists:** done
- **Lost tasks:** ["Task name 1"]
- **Recovered:** Yes
- **First seen:** 2026-02-28 12:00 UTC
- **Investigation needed:** YES (>24h)
```

## Cron Example
```
0 */6 * * * cd /root/.openclaw/workspace && node check-kanban-corruption.js
```
