# Current State — System Improvement Focus

**Last updated:** 2026-08-16 (CEO run — verified, 3rd run)
**Updated by:** CEO run

## What We're Working On

**Completed:** Progressive context shaping (CURRENT.md) + Weather Vane v2+v4 upgrades + all 8 upgrade plans + eval window (PM_TRAIL, ATR, trailing params).

**Current focus:** R:R inversion fix (PM_TRAIL_ACTIVATE reverted to 0.40%) + SHORT bleed monitoring.

## Active Decisions

- **CURRENT.md is the single source of truth for agent sessions.** All agents read this at start and update it after consequential decisions. — 2026-08-13
- **Orchestrator reads CURRENT.md before gathering intelligence.** Prevents stale instruction drift. — 2026-08-13
- **Context layers are separated:** stable instructions (AGENTS.md) vs current state (this file) vs history (logs, Hebbian). History must not masquerade as current guidance. — 2026-08-13
- **Direction Lock: 30min lock after catastrophic loss (4+/5).** Prevents re-entry during clear bad streaks. — 2026-08-13
- **Tide Detection: BTC 3h momentum + SHORT WR confirmation.** Bearish tide suppresses LONG, bullish tide suppresses SHORT. — 2026-08-13
- **Blacklist testing complete.** 77 tokens tested, 0 KEEP. Signal generation filters are the bottleneck, not the blacklist. Stop rotating tokens. — 2026-08-15
- **PM_TRAIL_ACTIVATE reverted to 0.40%.** Eval showed 0.60% hurt R:R (0.37:1 vs 0.67:1 pre-eval). ATR_SL trades peak 0.94% MFE but trail never activates. — 2026-08-16

## Known Limitations

- **No session handoff protocol** — when human sessions end, context is lost. — 2026-08-13
- **Signal reporter has /tmp/ permission issue** — fixed prompt to avoid /tmp/ writes. — 2026-08-15

## System Improvement Backlog

### Worth Doing
1. Extend checkpoint_utils.py to write human-readable progress summaries
2. Create contextmap.md for the 58-signal ecosystem

### Future
3. Formalize the 4-layer context separation in AGENTS.md
4. Weather Vane Component 2 (Position Shield) — tighten trailing stops on losing positions during regime shifts

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

1. **Monitor PM_TRAIL revert:** atr_sl_hit count should ↓ from 49 (48h), avg exit should ↑ from 0.29%, R:R should ↑ from 0.37:1.
2. **SHORT bleed:** -$0.95/7d — mostly legacy aging out. If still negative in 48h → add regime filter.
3. **Daily trades:** should stay >30T (currently 55T — healthy).
4. **Stars7d:** return_exhaustion_long 3T 100%, bb_bounce+ 22T 63.6%, hzscore+,mover+ 5T 80% — all intact.
