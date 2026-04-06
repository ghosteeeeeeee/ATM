---
name: project-manager
description: Senior PM review of Hermes trading system PM files (DECISIONS.md, PROJECTS.md, TASKS.md, trading.md). Identifies stale entries, missing decisions, project status conflicts, and priority reordering. Run at end of every session or when PM files need a health check.
author: T
created: 2026-04-06
---

# Project Manager — Hermes PM File Review

Full review of the 4 PM files to identify rot, gaps, and misalignments. Run at end of every session.

## When to Run

- End of every session (after significant work done)
- When TASKS.md hasn't been touched in 2+ sessions
- When PROJECTS.md shows a project as QUEUED but it was actually done
- When DECISIONS.md is missing entries for work that was clearly significant

## PM Files

| File | Purpose | Last Updated |
|------|---------|-------------|
| `/root/.hermes/brain/DECISIONS.md` | Why we made each call, date, revisit, owner | Should be today |
| `/root/.hermes/brain/PROJECTS.md` | Active projects, status, blockers | Should be today |
| `/root/.hermes/brain/TASKS.md` | Current todos, linked to projects | Should be today |
| `/root/.hermes/brain/trading.md` | Live trading log, positions, stats | Should be < 24h old |

## What to Check

### 1. Status conflicts (PROJECTS.md vs actual)
- Is "Cascade Flip Enhancement" marked QUEUED but was actually DONE this session?
- Is "Win Rate Investigation" still marked CRITICAL when the flip test was disabled?
- Any project with "IN PROGRESS" but no activity in days?

### 2. Missing decisions (DECISIONS.md)
- Did you make architectural changes today that aren't logged?
- New thresholds, new features, new data structures
- Fixes to bugs that took significant debugging — log them

### 3. Stale position list (trading.md)
- Does the position table reflect what Hyperliquid actually shows?
- Check with `get_open_hype_positions_curl()` — compare to what's in trading.md

### 4. Blockers that are never actioned
- Tokyo PG asleep for days — escalate or close the project
- Hermes Gateway tokens missing — T needs to action or project should be closed
- WAIT signals stale for 24+ hours — re-review or expire

### 5. T vs Agent responsibility clarity
- Only T can fix: Tokyo wake, Gateway tokens, WR flip test outcome review
- Agent can fix: all PM file updates, signal re-reviews, investigation work

## PM Subagent (run via delegate_task)

Use the `project-manager-senior.md` persona to do the review:

```
Context: Project files + current state (positions, hotset, service status)
Goal: Full PM review — identify stale entries, missing decisions, priority reorder, blockers
Toolsets: terminal, file
```

## Session Wrap Checklist

After every significant session, update:

- [ ] DECISIONS.md — log every significant decision made today
- [ ] PROJECTS.md — close/complete any projects that are done
- [ ] TASKS.md — move done items to [x], add new items as discovered
- [ ] trading.md — refresh position table, hot-set state, service status

## Key Metrics to Track

| Metric | Source | Update frequency |
|--------|--------|-----------------|
| Open positions | `get_open_hype_positions_curl()` | Every session |
| Hot-set tokens | `/var/www/hermes/data/hotset.json` | Every session |
| Service status | `systemctl` or `ps aux` | Every session |
| Win rate | brain DB (closed trades) | Weekly |
| Pipeline last run | `/root/.hermes/logs/pipeline.log` | Every session |

## Common Issues to Watch For

1. **Project marked QUEUED but actually done** — most common rot pattern
2. **Decision not logged** — you made a call but forgot to write it down
3. **Position list stale** — trading.md shows wrong tokens
4. **Blocker never resolved** — Tokyo sleeping for 3+ days, no decision made
5. **WR investigation orphaned** — flip test run but outcome not documented