# Current State — System Improvement Focus

**Last updated:** 2026-08-13
**Updated by:** Human (initial version)

## What We're Working On

Implementing **progressive context shaping** — giving Hermes agents structured state between sessions so they don't drift on stale context. This is a meta-improvement to how the system improves itself.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** All agents (CEO, orchestrator, human) read this at start and update it after consequential decisions. — 2026-08-13
- **Orchestrator reads CURRENT.md before gathering intelligence.** Prevents stale instruction drift. — 2026-08-13
- **Signal deprecation reasons are recorded, not just state transitions.** Carry the lesson, not the noise. — 2026-08-13
- **Context layers are separated:** stable instructions (AGENTS.md) vs current state (this file) vs map (contextmap.md) vs history (logs, Hebbian, checkpoints). History must not masquerade as current guidance. — 2026-08-13

## Known Limitations / Failed Approaches

- **Monolithic orchestrator prompt** becomes a graveyard of stale rules over time. Fix: progressive context shaping via CURRENT.md. — 2026-08-13
- **Editing constants.py or AGENTS.md for temporary steering** is too heavy — those are permanent. CURRENT.md is the ephemeral steering layer. — 2026-08-13
- **No session handoff protocol** — when human sessions end, context is lost. CEO sometimes repeats work or misses decisions from the last session. — 2026-08-13

## System Improvement Backlog

### Quick Wins (do first)
1. Wire CURRENT.md into orchestrator prompt (Phase 0 read, Phase 5 write)
2. Wire CURRENT.md into CEO prompt (read at start, update on decisions)
3. Add deprecation reason to signal_lifecycle.py state transitions

### Worth Doing
4. Extend checkpoint_utils.py to write human-readable progress summaries
5. Create contextmap.md for the 58-signal ecosystem
6. Session handoff protocol: when session_lock releases, write handoff to CURRENT.md

### Future
7. Formalize the 4-layer context separation in AGENTS.md (structural refactor)
8. Progress file as portable memory between CEO sessions

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering — use CURRENT.md
- Don't edit AGENTS.md for ephemeral state — that's stable instructions only
- Don't add session persistence to the pipeline — it's stateless by design (correct)
- Don't add new dependencies — just markdown files and minor script changes

## Stop Conditions

- If CURRENT.md grows beyond ~50 lines, it's become a graveyard. Trim it.
- If agents stop reading it, the wiring is broken. Check orchestrator/CEO prompts.
- If it hasn't been updated in 48h, the system isn't using it. Investigate.

## Next Actions

1. **CEO**: Review the spec at `plans/2026-08-13_progressive-context-shaping-spec.md` and give feedback
2. **Human**: Approve spec or adjust scope
3. **Implementation**: Wire CURRENT.md into orchestrator + CEO (smallest change first)
