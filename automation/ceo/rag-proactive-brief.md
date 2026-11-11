# Brief: RAG System Proactivity — Make It Ask Better Questions

## Context

The brain auditor (brain_auditor) runs hourly via opencode, queries the session brain (448K vectors of DSH conversation history), and produces audit recommendations + creative ideas. But T says:

> "we're still grinding in the same place"
> "how can we get the rag to ask more questions like me and prod the system to get better"

The RAG has access to 448K chunks of conversation history but isn't using it to generate the kind of probing, creative questions T asks in sessions. It's producing generic recommendations instead of sharp, specific insights.

## Current State

- **Session brain**: 284 sessions, 448K vectors, sqlite-vec, working
- **Brain auditor**: runs hourly, reads watchdog + trade data + session brain
- **Shadow mode**: 24K+ oscillator entries, 806 contrarian, 289 wyckoff, 1717 floor_admit
- **Auditor prompt**: has "wrong side of trade" philosophy, trend-vs-chop analysis, mandatory verification

## What T Wants

The auditor should ask questions like T does in sessions:
- "Why are we still losing on this signal?"
- "What's the pattern we're missing?"
- "Have we tried X before? What happened?"
- "This looks like Y — what did we learn when we dealt with Y?"

Instead of generic "monitor this signal" or "add RSI filter" recommendations.

## What To Suggest

1. How should the auditor use the session brain more aggressively to generate sharper questions?
2. What prompt changes would make it think more like T (probing, skeptical, creative)?
3. Should it query specific session topics (e.g., "what did we say about bb_bounce losses last month")?
4. How can it cross-reference shadow data with session discussions to find gaps?
5. What would make it stop producing generic recommendations and start producing specific, actionable insights?

## Constraints

- Auditor runs hourly via opencode (600s timeout currently, 1200s configured)
- Must follow the mandatory verification rules (p-values, sample sizes, etc.)
- Cannot modify CEO_PROTECTED_FLAGS
- Session lock protection must remain
