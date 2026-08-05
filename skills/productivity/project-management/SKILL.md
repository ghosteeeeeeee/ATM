---
name: project-management
description: Manage Hermes project tracking across sessions via brain/PROJECTS.md, brain/DECISIONS.md, and brain/TASKS.md
triggers:
  - project management
  - update projects
  - log decision
  - track tasks
  - end of session wrap
---

# project-management

## What this skill does

Manages the Hermes project management system — three Markdown files in `brain/` that track everything across sessions. These are the agent's long-term memory for projects, decisions, and tasks.

**Files:**
- `brain/PROJECTS.md` — active projects, status, owner, blockers
- `brain/DECISIONS.md` — why we made each call, date, revisit date, alternatives
- `brain/TASKS.md` — current todos linked to projects

---

## When to update

**At the START of every session:**
```bash
grep -n "Status:\|Owner:\|## \|### " brain/PROJECTS.md | head -40
grep -n "2026\|decision\|revisit\|## " brain/DECISIONS.md | tail -20
grep -n "\- \[ \]\|\- \[P\]\|\- \[!\]" brain/TASKS.md
```

**At the END of every session:**
1. Update project statuses in PROJECTS.md
2. Log new decisions in DECISIONS.md
3. Move completed tasks to "Completed" section in TASKS.md
4. Update TASKS.md with new tasks discovered during the session
5. **After any TASKS.md write: run kanban sync**
   ```
   python3 /root/.hermes/scripts/sync_kanban_tasks.py tasks→kanban
   ```

---

## Format rules

### PROJECTS.md
```
## Project Name | Status | Owner | Last updated
```
- Status: 🚧 IN PROGRESS | ✅ COMPLETE | ⚠️ DEFERRED | ❌ CLOSED
- Include: blockers, sub-items table, key decisions link

### DECISIONS.md
```
## YYYY-MM-DD | Short title

**Decision:** What was decided
**Rationale:** Why this approach
**Evidence:** Data or observations that led to the decision
**Alternatives considered:** Other options that were rejected
**Revisit condition:** When to re-evaluate this decision
**Owner:** Who owns this decision
```
- Append new decisions below the header, above the "Prior Decisions" section
- Most recent first (reverse chronological)

### TASKS.md
```
- [STATUS] Task description (Project) — owner
```
- Status: `[ ]` queued | `[P]` in progress | `[!]` urgent | `[x]` done
- Priority: Most urgent at top
- Completed tasks: Move to "Completed (this session)" section at bottom

---

## Quick reference commands

```bash
# Read current project state
grep -n "Status:\|Owner:\|## \|### " brain/PROJECTS.md | head -40

# Read decisions
grep -n "2026\|decision\|revisit\|## " brain/DECISIONS.md | tail -20

# Read tasks
grep -n "\- \[ \]\|\- \[P\]\|\- \[!\]" brain/TASKS.md

# Full files
cat brain/PROJECTS.md
cat brain/DECISIONS.md
cat brain/TASKS.md
```

---

## Task → Project linking

Every task in TASKS.md should link to a project in PROJECTS.md using the `**Project:**` field. This makes it easy to see which project a task belongs to.

```
### [ ] Build feature X (Project: Signal Quality Improvement)
```

---

## Decision logging checklist

When logging a decision, include:
1. **What** — the specific change or choice made
2. **Why** — the reasoning (market context, data, T's feedback)
3. **Evidence** — actual data points, backtest results, observations
4. **Alternatives** — what else was considered
5. **Revisit** — under what conditions to re-evaluate
6. **Owner** — who is responsible for this area

---

## Project status update checklist

When updating a project's status, check:
1. Are all sub-items complete?
2. Are there blockers? Are they still valid?
3. Has the status changed? (IN PROGRESS → COMPLETE → CLOSED)
4. Are there new next steps to add?

---

## Session End Review — PM Health Check

Run at the end of every significant session to catch rot, gaps, and misalignments across all 4 PM files. Different from the inline check-lists above — this is a *full audit* of all four files together.

### When to Run

- End of every session (after significant work done)
- When `TASKS.md` hasn't been touched in 2+ sessions
- When `PROJECTS.md` shows a project as QUEUED but it was actually done
- When `DECISIONS.md` is missing entries for work that was clearly significant

### The Four PM Files

| File | Purpose | When Updated |
|------|---------|--------------|
| `brain/DECISIONS.md` | Why we made each call, date, revisit, owner | Every significant session |
| `brain/PROJECTS.md` | Active projects, status, blockers | Every significant session |
| `brain/TASKS.md` | Current todos, linked to projects | Every significant session |
| `brain/trading.md` | Live trading log, positions, stats | < 24h old |

### What to Check (Five Common Rot Patterns)

1. **Status conflicts (PROJECTS.md vs actual)** — Is "Cascade Flip Enhancement" marked QUEUED but was actually DONE this session? Any project with "IN PROGRESS" but no activity in days?
2. **Missing decisions (DECISIONS.md)** — Did you make architectural changes today that aren't logged? New thresholds, new features, new data structures? Bug fixes that took significant debugging?
3. **Stale position list (trading.md)** — Does the position table reflect what Hyperliquid actually shows? Check with `get_open_hype_positions_curl()` and compare to `trading.md`.
4. **Blockers that are never actioned** — Tokyo PG asleep for days (escalate or close), Hermes Gateway tokens missing (T needs to action or close), WAIT signals stale for 24+ hours (re-review or expire).
5. **T vs Agent responsibility clarity** — Only T can fix: Tokyo wake, Gateway tokens, WR flip test outcome review. Agent can fix: all PM file updates, signal re-reviews, investigation work.

### PM Subagent (run via delegate_task)

Use the `project-manager-senior.md` persona to do the review:

```
Context: Project files + current state (positions, hotset, service status)
Goal: Full PM review — identify stale entries, missing decisions, priority reorder, blockers
Toolsets: terminal, file
```

### Session Wrap Checklist (after every significant session)

- [ ] `DECISIONS.md` — log every significant decision made today
- [ ] `PROJECTS.md` — close/complete any projects that are done
- [ ] `TASKS.md` — move done items to `[x]`, add new items as discovered
- [ ] `trading.md` — refresh position table, hot-set state, service status

### Key Metrics to Track

| Metric | Source | Update frequency |
|--------|--------|-------------------|
| Open positions | `get_open_hype_positions_curl()` | Every session |
| Hot-set tokens | `/var/www/hermes/data/hotset.json` | Every session |
| Service status | `systemctl` or `ps aux` | Every session |
| Win rate | brain DB (closed trades) | Weekly |
| Pipeline last run | `/root/.hermes/logs/pipeline.log` | Every session |

### Common Issues

1. **Project marked QUEUED but actually done** — most common rot pattern
2. **Decision not logged** — you made a call but forgot to write it down
3. **Position list stale** — `trading.md` shows wrong tokens
4. **Blocker never resolved** — Tokyo sleeping for 3+ days, no decision made
5. **WR investigation orphaned** — flip test run but outcome not documented

## Skill maintenance

If the PM format or file locations change, update this skill immediately. The PM system only works if the files are where this skill says they are.
