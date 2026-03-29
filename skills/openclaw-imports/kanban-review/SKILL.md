# Kanban Review Skill

## Purpose
Daily review of kanban tasks to identify items that need verification, follow-up, or a fresh perspective. Moves stale items back to todo and cleans up lists.

## Trigger
Run as cron daily at 2pm UTC or manually when needed.

## Instructions

### Step 1: Read Current Kanban
Read the current kanban-tasks.json to see all lists (todo, in_progress, done, blocked).

### Step 2: Review Done Items
For each item in "done", consider:
- **Re-verification needed?** Has it been >2 weeks since completion? Does it need a retest?
- **Follow-up needed?** Are there pending results or next steps not captured?
- **Better version?** Can the approach be improved with new learnings?

If yes to any, move back to "todo" with updated notes.

### Step 3: Review Blocked Items
For each item in "blocked", consider:
- **Still blocked?** Can the blocker be resolved now?
- **Needs new approach?** Is there a different way to tackle this?
- **Should unblock?** If Tokyo is back online or dependencies resolved, move to todo

If blocker resolved, move to "todo".

### Step 4: Sync with Shared Notes
Add a summary to /root/shared_notes/notes.md with:
- Items moved from done→todo
- Items moved from blocked→todo
- Current kanban status (counts)

### Step 5: Commit Changes
Git commit the updated kanban.

## Example Items to Move Back
- Hyperopt results (re-run with more epochs)
- Trading strategies (test with new market data)
- Verify working
- Re setups still-test theories from conversation logs

## Cron Setup
```
0 14 * * * cd /root/.openclaw/workspace && node -e "
const fs = require('fs');
const kanban = JSON.parse(fs.readFileSync('kanban-tasks.json'));

// Review done items - move stale ones back to todo
const stale = kanban.done.filter(t => 
  t.name.includes('hyperopt') || 
  t.name.includes('verify') ||
  t.name.includes('setup') && Date.now() > Date.parse('2026-03-01')
);

if (stale.length > 0) {
  stale.forEach(t => {
    t.status = 'todo';
    t.notes = '[REVIEWED] ' + t.notes;
  });
  kanban.todo = [...kanban.todo, ...stale];
  kanban.done = kanban.done.filter(t => !stale.includes(t));
  fs.writeFileSync('kanban-tasks.json', JSON.stringify(kanban, null, 2));
  console.log('Moved', stale.length, 'items back to todo');
}
"
```

## Notes
- Focus on items that can be improved with fresh perspective
- Don't move everything back - only items with clear verification/follow-up need
- Keep done list clean but not empty - some items are truly complete
