# Plan: Hot-Set Redesign — LLM Only Ranks, Execution is Separate

**Date:** 2026-04-12
**Focus:** Perfect `.hermes/prompt/main-prompt.md` only

---

## Goal

Redesign the LLM's role: **it only ranks and compacts signals into the hot-set**. It never opens or closes trades. Execution is a separate system with its own ATR TP/SL logic.

---

## Clarified Architecture

```
SIGNAL PIPELINE (every 10 min purge)
    │
    ▼
signal_gen.py → signals DB (500+/hr)
    │
    ▼
LLM COMPACTION (replace _do_compaction_llm)
    │  Input: pending signals (last 30 min)
    │  Output: hot-set.json — top ~20 survivors
    │  LLM does NOT execute anything
    │
    ▼
hot-set.json (survivors, rounds count, confidence)
    │
    ▼
EXECUTION LAYER (decider_run.py + position_manager)
    │  Reads hot-set.json
    │  ATR-based TP/SL (separate logic)
    │  Opens/closes trades autonomously
    │
    ▼
guardian.py (independent safety monitor)
```

---

## Key Clarifications

1. **Hot-set = ranked priority list, not execution trigger**
   - It's a "watch list" of the most promising coins right now
   - The LLM compacts 500+ signals/hr into ~20 survivors
   - Surviving multiple cycles = higher rank, not automatic execution

2. **LLM never opens or closes trades**
   - Open trades are fed to LLM for **context only** — to inform which signals are already working, so the LLM doesn't contradict itself
   - OPEN action should be REMOVED from the prompt
   - Trade execution is entirely in the execution layer

3. **Execution layer is separate from LLM**
   - decider_run.py reads hot-set.json + executes based on ATR TP/SL
   - position_manager handles open trade monitoring (trailing stops, SL violations)
   - This is NOT driven by the LLM

4. **Compaction cycle = pipeline purge cycle**
   - Every 10 min: signal_gen purges old signals
   - Every 10 min: LLM re-compacts survivors into hot-set.json
   - Survivors track rounds (how many cycles they survived)

---

## Open Questions (for T)

1. **Execution trigger:** If the LLM doesn't execute, what triggers a trade entry? Is it:
   - (a) Auto-enter all hot-set survivors up to MAX_OPEN?
   - (b) Some separate signal scanner triggers entries?
   - (c) Manual T decision?

2. **Hot-set output format:** Should `hotset.json` just be a list of `TOKEN|DIRECTION|conf|signal_count|rounds`? Or does it need more detail for the execution layer?

3. **Hot-set size:** Still cap at 20? Or adaptive based on open slots?

4. **Survival rounds:** Keep `survival_round` counter? Does rounds count affect anything beyond ranking priority?

5. **Counter-signals:** If a token is in the hot-set as LONG but `ai_decide()` detects a SHORT signal forming, does the hot-set entry get demoted? Or does the LLM compaction just re-rank from scratch each cycle?

---

## Proposed Prompt Changes (for `.hermes/prompt/main-prompt.md`)

### REMOVE
- Section 1 (Open Trades monitoring) — LLM should not be told to close trades
- OPEN action from response format
- EXECUTE action from response format
- References to "decide" / "approve" for trades

### KEEP / REVISE
- Section 2: Hot-Set Survivors — LLM re-ranks, outputs APPROVED/SKIP/REJECTED
- Section 3: Market Context — still useful for ranking context
- Section 4: New Pending Signals — LLM ranks these into hot-set
- Hard Rules — pre-filter awareness

### ADD (maybe)
- Instruction clarifying LLM's role: "You are a ranking engine. You do not open or close trades. Your output determines which signals survive into the hot-set."

---

## Files to Change

1. `.hermes/prompt/main-prompt.md` — rewrite per above
2. `ai_decider.py` — refactor `_do_compaction_llm()` → `compact_signals()` (no trade execution)
3. `decider_run.py` — untangle from ai_decider, execution layer stands alone
4. `hotset.json` — confirm schema still makes sense

---

## Risks

- If execution is truly separate, there may be a gap where hot-set survivors never get traded — need to confirm the execution trigger
- T needs to answer the open questions before the prompt can be finalized
