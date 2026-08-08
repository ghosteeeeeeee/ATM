# Transcript Mining Report

**Source**: Ex-NASA dev reveals his Agentic Engineering Workflow
**Date**: 2026-08-08

## TL;DR
- **Program design before coding** — spend 20min up front to save hours of review/fixes
- **Vertical slices** — build end-to-end first, add logic later (testable at each step)
- **Human in the loop** — don't stop reading code entirely; you'll lose the ability to fix hard bugs
- **Measurable outputs** — if you can tell the agent a number to optimize, it will move mountains
- **Context engineering** — smaller/tighter context windows = better results (but don't over-optimize)

## Ideas

### 1. Program Design Before Agent Runs
- **What**: Before letting an agent build something, define: problem, success metrics, architecture, file layout, test plan
- **Why Hermes**: Our signal development could use this — define the signal's edge, backtest criteria, and file structure BEFORE writing code
- **Where**: `add-signal` skill, new signal development workflow
- **Effort**: small (update skill prompt)
- **Priority**: quick win

### 2. Vertical Slices (Tracer Bullets)
- **What**: Build a thin end-to-end slice first (mock API → stub frontend → wire it), then add logic. Don't build all DB, then all services, then all frontend.
- **Why Hermes**: When adding new signals, build the full pipeline first (signal detection → hotset → execution → exit) with minimal logic, then refine. Currently we build signals in isolation.
- **Where**: `scripts/signals/` development pattern
- **Effort**: medium (cultural change)
- **Priority**: worth it

### 3. Measurable Outputs for Agents
- **What**: Give agents a specific number to optimize (conversion rate, PnL, win rate) rather than vague instructions
- **Why Hermes**: Our CEO/automations could use this — "improve win rate by 3% in 24h" is better than "analyze and fix"
- **Where**: `automation/ceo_prompt.md`, `ceo_away_prompt.md`
- **Effort**: trivial (update prompts)
- **Priority**: quick win

### 4. ADRs (Architecture Decision Records)
- **What**: Document key decisions in `/docs/adr/` — pricing, API schema, signal design patterns
- **Why Hermes**: We have LESSONS.md and AGENTS.md but no formal decision log. New signals/changes could reference past decisions.
- **Where**: Create `docs/adr/` directory, update AGENTS.md
- **Effort**: small
- **Priority**: worth it

### 5. Context Window Management ("Dumb Zone")
- **What**: When context gets to ~50-60% full, compact into a doc and start fresh session. Models degrade in the "dumb zone."
- **Why Hermes**: Our opencode sessions might benefit from this — long debugging sessions could be compacted
- **Where**: opencode workflow, handoff skill
- **Effort**: trivial (already have handoff skill)
- **Priority**: skip (already covered)

### 6. Dual-Model Review
- **What**: Use two different frontier models to review code — catches different things
- **Why Hermes**: Our bug_hunter uses one model. Could use opencode command to send to a second model for review.
- **Where**: `bug-hunter` skill, `post-change` workflow
- **Effort**: small
- **Priority**: worth it

### 7. Incident → Agent Pipeline
- **What**: When an alert fires, route it directly to an agent that diagnoses and creates a fix PR
- **Why Hermes**: Our health_monitor already auto-fixes some things. Could expand: error_alerts → agent → fix → kanban
- **Where**: `health_monitor_prompt.md`
- **Effort**: medium
- **Priority**: future

### 8. "What choices were you not confident of?"
- **What**: After an agent makes changes, ask it which decisions it's uncertain about
- **Why Hermes**: Could add this to bug_hunter and post-change workflows — surfaces hidden risks
- **Where**: `bug-hunter` skill, `post-change` skill
- **Effort**: trivial (add to prompt)
- **Priority**: quick win

## Quick Wins (do today)
1. Add "what choices were you uncertain of?" to bug_hunter/post-change prompts
2. Update CEO prompts with measurable output language ("improve X by Y%")
3. Add ADR directory and template for future decisions

## Worth Discussing
1. Vertical slices for signal development
2. Dual-model review for critical changes
3. Incident → agent pipeline expansion

## Skip
- Context window management (already have handoff skill)
- PostHog integration (not relevant for trading system)
- Factory/token optimization (not our bottleneck)
