# Current State — System Improvement Focus

**Last updated:** 2026-08-15
**Updated by:** Daily Orchestrator

## What We're Working On

**Completed:** Progressive context shaping (CURRENT.md) + Weather Vane v2+v4 upgrades.

**Current focus:** R:R inversion fix (after stability period ends ~Aug 17) + signal quality monitoring.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** All agents (CEO, orchestrator, human) read this at start and update it after consequential decisions. — 2026-08-13
- **Orchestrator reads CURRENT.md before gathering intelligence.** Prevents stale instruction drift. — 2026-08-13
- **Signal deprecation reasons are recorded, not just state transitions.** Carry the lesson, not the noise. — 2026-08-13
- **Context layers are separated:** stable instructions (AGENTS.md) vs current state (this file) vs map (contextmap.md) vs history (logs, Hebbian, checkpoints). History must not masquerade as current guidance. — 2026-08-13
- **Direction Lock: 30min lock after catastrophic loss (4+/5).** Prevents re-entry during clear bad streaks. — 2026-08-13
- **Tide Detection: BTC 3h momentum + SHORT WR confirmation.** Bearish tide suppresses LONG, bullish tide suppresses SHORT. — 2026-08-13

## Known Limitations / Failed Approaches

- **Monolithic orchestrator prompt** becomes a graveyard of stale rules over time. Fix: progressive context shaping via CURRENT.md. — 2026-08-13
- **Editing constants.py or AGENTS.md for temporary steering** is too heavy — those are permanent. CURRENT.md is the ephemeral steering layer. — 2026-08-13
- **No session handoff protocol** — when human sessions end, context is lost. CEO sometimes repeats work or misses decisions from the last session. — 2026-08-13
- **Z-Score + Acceleration filter** — spec proposed soft penalty in signal_compactor, but hard block already exists in decider_run.py. No duplicate needed. — 2026-08-13

## System Improvement Backlog

### Quick Wins (do first)
1. ~~Wire CURRENT.md into orchestrator prompt~~ ✅ Done 2026-08-15
2. Wire CURRENT.md into CEO prompt (next session)
3. ~~Add deprecation reason to signal_lifecycle.py~~ ✅ Already exists (line 164-182)

### Worth Doing
4. Extend checkpoint_utils.py to write human-readable progress summaries
5. Create contextmap.md for the 58-signal ecosystem
6. Session handoff protocol: when session_lock releases, write handoff to CURRENT.md

### Future
7. Formalize the 4-layer context separation in AGENTS.md (structural refactor)
8. Progress file as portable memory between CEO sessions
9. Weather Vane Component 2 (Position Shield) — tighten trailing stops on losing positions during regime shifts

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering — use CURRENT.md
- Don't edit AGENTS.md for ephemeral state — that's stable instructions only
- Don't add session persistence to the pipeline — it's stateless by design (correct)
- Don't add new dependencies — just markdown files and minor script changes
- Don't duplicate Z-Score + Acceleration filter — already in decider_run.py as hard block

## Stop Conditions

- If CURRENT.md grows beyond ~50 lines, it's become a graveyard. Trim it.
- If agents stop reading it, the wiring is broken. Check orchestrator/CEO prompts.
- If it hasn't been updated in 48h, the system isn't using it. Investigate.

## Next Actions

1. **After stability period (~Aug 17):** Tune TRAILING_ACTIVATION_PCT to fix R:R inversion (0.21:1 → target 0.75:1)
2. **CEO:** Review range_finder+ re-enable results (9 trades, 33.3% WR — on watch list)
3. **Monitor:** r2-trend family performance (best performers at 60-67% WR)
