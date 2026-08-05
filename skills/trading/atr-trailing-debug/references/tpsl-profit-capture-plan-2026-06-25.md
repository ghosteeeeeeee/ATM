# TPSL Profit-Capture Plan — 2026-06-25 (canonical spec pointer)

**This file is a pointer to the canonical implementation plan.**
The full spec lives at:

**`/root/.hermes/brain/plans/tpsl-profit-capture-2026-06-25.md`**

The plan contains:
- 24h analysis findings (38 trades, +$0.68 net, 21W/16L)
- 11 prioritized fixes (bug, constant, filter, data) with code refs
- Verification queries for each fix
- Phased implementation order (Phase 1-5)
- Risk assessment per fix
- Expected outcomes by phase (+$0.68 → +$2.00/day target)
- 6 open decision points for T

## Why this lives in a plan file, not a reference

The plan is **the action queue** — it changes as T approves fixes
and we mark them done. A skill reference is supposed to be
relatively stable. When you want to know "what's the current state
of TPSL work?", read the plan. When you want to know "how do I
diagnose a TPSL bug?", read the skill SKILL.md and the other
references.

## When to update the plan

Update `/root/.hermes/brain/plans/tpsl-profit-capture-2026-06-25.md`
when:
- T approves a fix → mark `⏳ PENDING` → `✅ COMPLETE` in the
  Implementation status table
- A fix needs revision → change the row + add a note in the audit
  findings (T's response on the decision questions)
- A new TPSL bug is found → add it as fix #12+ with severity tier
- The 24h window is re-audited → update the expected outcomes
  (Section H) with the new baseline

## Related skill references

- `24h-trade-audit-recipe-2026-06-25.md` — the recipe for running
  the kind of audit that produced the plan
- `2026-06-24-merl-short-lowest-trail-bug.md` — the bug evidence
  that prompted the plan
- `atr-floor-override-subagent-verification.md` — same dead-code
  floor issue observed earlier in May 2026
- `atr-floor-overrides-phase-2026-05-21.md` — first identification
  of the phase-multiplier dead-code pattern
