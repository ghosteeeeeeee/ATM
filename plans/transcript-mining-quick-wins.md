# Spec: Transcript Mining Quick Wins

**Source**: Ex-NASA Agentic Engineering Workflow transcript
**Date**: 2026-08-08
**Status**: Ready to implement

---

## Quick Win 1: "What choices were you uncertain of?"

### Problem
Agents make decisions silently. Hidden risks surface later as bugs.

### Solution
Add a mandatory question to bug_hunter and post-change workflows: "What choices did you make that you're not confident of?"

### Changes

**File: `/root/.config/opencode/skills/bug-hunter/SKILL.md`**
Add after the audit section:

```markdown
### Uncertainty Check
After completing the audit, answer:
"What choices did you make during this audit that you're not fully confident of?"
- List any assumptions made
- List any edge cases not verified
- List any fixes that might have side effects
```

**File: `/root/.config/opencode/skills/post-change/SKILL.md`**
Add after Step 1 (bug_hunter):

```markdown
### Uncertainty Check
After bug_hunter completes, ask:
"What choices were made during this fix that you're not confident of?"
- Log uncertainties in the commit message
- If high-confidence issues found, flag for human review
```

### Effort
- trivial: 10 minutes, 2 file edits

### Verification
- Run bug_hunter on a change, verify it outputs uncertainties
- Run post-change, verify it captures uncertainties

---

## Quick Win 2: Measurable Outputs for CEO

### Problem
CEO prompts say "improve performance" — vague, no target.

### Solution
Give the CEO specific numbers to optimize: "improve win rate by 3% in 24h" or "reduce phantom trades to 0".

### Changes

**File: `/root/.hermes/automation/ceo_prompt.md`**
Add a "MEASURABLE GOALS" section after the workflow:

```markdown
## MEASURABLE GOALS (update each run)

Before making changes, set a specific goal:

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| Win rate | X% | X+3% | 24h |
| Phantom trades | X | 0 | 48h |
| SHORT PnL | -$X | $0 | 72h |

After making changes, report:
- What was the metric before?
- What changed?
- What's the expected impact?
```

**File: `/root/.hermes/automation/ceo_away_prompt.md`**
Same addition.

### Effort
- trivial: 15 minutes, 2 file edits

### Verification
- Run CEO, verify it sets measurable goals
- Check kanban for goal tracking

---

## Quick Win 3: ADRs (Architecture Decision Records)

### Problem
Decisions are scattered across LESSONS.md, AGENTS.md, kanban, and commit messages. No single source of truth.

### Solution
Create `/docs/adr/` directory with numbered decision records.

### ADR Template

```markdown
# ADR-001: [Decision Title]

**Date**: YYYY-MM-DD
**Status**: Accepted/Superseded/Deprecated
**Deciders**: [who made the decision]

## Context
What situation forced this decision?

## Decision
What did we decide?

## Consequences
What are the trade-offs?

## Alternatives Considered
What else was evaluated?
```

### Initial ADRs (from existing knowledge)

Create these from existing LESSONS.md and AGENTS.md:

| ADR | Title | Source |
|-----|-------|--------|
| ADR-001 | Use PostgreSQL for brain DB, SQLite for runtime | AGENTS.md |
| ADR-002 | ATR-based SL/TP with trailing | LESSONS.md |
| ADR-003 | Signal confluence required (2+ types) | recent_changes.log |
| ADR-004 | Confluence kill-switches for low-WR combos | hermes_constants.py |
| ADR-005 | Guardian owns HL position reconciliation | hl-sync-guardian.py |
| ADR-006 | Position manager owns ATR SL/TP computation | position_manager.py |
| ADR-007 | Never re-enable killed signals (NEVER_REENABLE_FLAGS) | kanban |
| ADR-008 | Pipeline lock prevents overlapping runs | AGENTS.md |

### Changes

**New directory: `/root/.hermes/docs/adr/`**
- Create `README.md` (explains ADR process)
- Create `001-brain-db.md` through `008-pipeline-lock.md`
- Update `AGENTS.md` to reference ADR directory

**File: `/root/.config/opencode/skills/add-signal/SKILL.md`**
Add step: "Before creating a new signal, check if an ADR covers the pattern."

**File: `/root/.config/opencode/skills/write-trading-skill/SKILL.md`**
Add: "Document key decisions as ADRs."

### Effort
- small: 1-2 hours (create template + 8 initial ADRs)

### Verification
- Check `/root/.hermes/docs/adr/` exists with 8 ADRs
- Run add-skill, verify it references ADRs

---

## Implementation Order

1. **Quick Win 1** (uncertainty check) — 10 min, immediate value
2. **Quick Win 2** (measurable goals) — 15 min, immediate value
3. **Quick Win 3** (ADRs) — 1-2 hours, foundational

## Expected Impact

| Quick Win | Impact | Confidence |
|-----------|--------|------------|
| Uncertainty check | Catches hidden risks before they become bugs | High |
| Measurable goals | CEO makes data-driven decisions, not vibes | High |
| ADRs | Faster onboarding, fewer repeated mistakes | Medium |
