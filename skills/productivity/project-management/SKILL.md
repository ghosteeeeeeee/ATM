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

## Skill maintenance

If the PM format or file locations change, update this skill immediately. The PM system only works if the files are where this skill says they are.
