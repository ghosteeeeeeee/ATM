# Current State — System Improvement Focus

**Last updated:** 2026-08-15 23:30 UTC (CEO run)
**Updated by:** CEO run

## What We're Working On

**Completed:** Progressive context shaping (CURRENT.md) + Weather Vane v2+v4 upgrades + all 8 upgrade plans.

**Current focus:** R:R inversion fix (after stability period ends ~Aug 17) + signal quality monitoring.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** All agents read this at start and update it after consequential decisions. — 2026-08-13
- **Orchestrator reads CURRENT.md before gathering intelligence.** Prevents stale instruction drift. — 2026-08-13
- **Context layers are separated:** stable instructions (AGENTS.md) vs current state (this file) vs history (logs, Hebbian). History must not masquerade as current guidance. — 2026-08-13
- **Direction Lock: 30min lock after catastrophic loss (4+/5).** Prevents re-entry during clear bad streaks. — 2026-08-13
- **Tide Detection: BTC 3h momentum + SHORT WR confirmation.** Bearish tide suppresses LONG, bullish tide suppresses SHORT. — 2026-08-13
- **Blacklist testing complete.** 77 tokens tested, 0 KEEP. Signal generation filters are the bottleneck, not the blacklist. Stop rotating tokens. — 2026-08-15

## Known Limitations

- **No session handoff protocol** — when human sessions end, context is lost. — 2026-08-13
- **Signal reporter has /tmp/ permission issue** — fixed prompt to avoid /tmp/ writes. — 2026-08-15

## System Improvement Backlog

### Worth Doing
1. Wire CURRENT.md into CEO prompt (next session)
2. Extend checkpoint_utils.py to write human-readable progress summaries
3. Create contextmap.md for the 58-signal ecosystem

### Future
4. Formalize the 4-layer context separation in AGENTS.md
5. Weather Vane Component 2 (Position Shield) — tighten trailing stops on losing positions during regime shifts

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering — use CURRENT.md
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies — just markdown files and minor script changes
- Don't duplicate Z-Score + Acceleration filter — already in decider_run.py

## Stop Conditions

- If CURRENT.md grows beyond ~50 lines, trim it
- If agents stop reading it, check orchestrator/CEO prompts
- If it hasn't been updated in 48h, investigate

## Next Actions

1. **Aug 17:** Evaluate all 6 eval windows after 48h data. Tune R:R (target 1:1+).
2. **Monitor:** ct-hot+ 16T 56.3% WR +$0.16 (must stay >55% WR)
3. **Monitor:** range_finder+ — check if still firing after disable (9T burst Aug 15)
4. **Verified 24h (Aug 15):** 53T +$0.03 49.1% WR — flat, breaking red streak. R:R 0.37:1 by exit type.
