# SPEC: Single LLM Call Per Pipeline Cycle

**Date:** 2026-04-12
**Problem:** 2-3 LLM calls per cycle. `_do_compaction_llm()` for ranking + `ai_decide_batch()` for non-hot decisions + `ai_decide()` per hot signal. Wasteful, slow, and the LLM doesn't have full context simultaneously.
**Principle:** ONE LLM call per cycle. Full stop.

---

## Current Flow (Before)

```
get_pending_signals()                          ← entry point
  └─ _do_compaction_llm()                    ← LLM Call #1: rank signals, build hotset.json
      • SELECT PENDING/WAIT signals (last 30 min)
      • LLM ranks top 20
      • WRITE hotset.json (survival_round)
      • UPDATE DB (APPROVED/REJECTED)
      • DB updated, hot_rounds loaded

__main__ loop
  └─ ai_decide_batch(non_hot_signals)        ← LLM Call #2: decide on non-hot signals + monitor open trades
      • get_open_trade_details()              ← fetched again (also fetched inside ai_decide_batch)
  └─ ai_decide() per hot signal              ← LLM Call #3: one at a time
      • get_open_trade_details()              ← fetched yet again

= 2-3 calls per cycle, open trades monitored redundantly
```

---

## New Flow (After)

```
ONE entry point: decide_all()

Inputs gathered ONCE:
  • open_trades         ← get_open_trade_details()
  • pending_signals    ← PENDING/WAIT signals (last 30 min, from DB)
  • hot_set_survivors  ← hotset.json entries (proven by LLM in previous cycles)

Pre-LLM filtering (hard rules, no LLM needed):
  • HOTSET_BLOCKLIST tokens → skip
  • SHORT_BLACKLIST / LONG_BLACKLIST → skip direction
  • Already-open positions → skip
  • Counter-signals (opposite to open position) → SKIP immediately
  • TTL expired → EXPIRE immediately
  • MAX_OPEN reached → SKIP remaining

LLM Call #1 (Sole call):
  • Prompt contains: open_trades + pending_signals + hot_set_survivors + market_context
  • Single JSON-able response: trade actions + signal decisions
  • Response includes: what to CLOSE, what to APPROVE, what to WAIT/REJECT

Post-LLM (no more LLM calls):
  • Parse response
  • Execute trade closes (guardian handles HL mirror)
  • Execute trade entries via brain.py
  • Write hotset.json (updated survival_round for any APPROVED signals that survived)
  • Update signal decisions in DB (APPROVED/WAIT/SKIPPED)
  • De-escalation: APPROVED but not executed after N cycles → PENDING
  • Purge: survival_round > threshold without execution → EXPIRE

= 1 call per cycle, all decisions made with full cross-context
```

---

## Prompt Design

### Section 1: Open Trades (for monitoring)
```
=== OPEN TRADES ===
{n} open trades. For each:
  - TOKEN DIRECTION ENTRY=$.CURRENT=$..SL=$..PnL=±.%
  - Distance to SL: .%

  Instructions: FLAG if PnL < -1% or distance_to_SL < 0.5%.
  Output: CLOSE:token:reason for any trades to exit now.
```

### Section 2: Hot-Set Survivors (auto-qualified from prior LLM rounds)
```
=== HOT-SET SURVIVORS (LLM-qualified in prior cycles) ===
{list of tokens that survived _do_compaction_llm in previous cycle}
For each: TOKEN | DIRECTION | conf=% | source= | rounds=
Quality gate: require 1+ signal type, avg_conf >= 80%, rounds >= 1.

These are PROVEN by the AI. You are deciding WHETHER TO EXECUTE THIS CYCLE
or SKIP (market conditions changed, open slot unavailable, etc).
Output: EXECUTE:token:direction or SKIP:token:reason
```

### Section 3: New Pending Signals (awaiting first LLM review)
```
=== NEW SIGNALS (first-time review) ===
{list of pending signals with full context}
For each: TOKEN | DIRECTION | conf=% | regime=|z=|source=|entry=$

Instructions: Decide based on ALL context above.
Output: DECIDE:token:direction:confidence:reason
```

### Section 4: Market Context
```
=== MARKET CONTEXT ===
Market Z-Score: {market_z}
Fear & Greed: {fear_greed}
Open Slots: {n_open}/{MAX_OPEN} paper, {n_live}/{MAX_LIVE} live
```

### Hard Rules (stated in prompt, not enforced by parsing)
```
=== HARD RULES ===
• HOTSET_BLOCKLIST: {full list} → SKIP both directions
• SHORT_BLACKLIST: {short blacklist} → SKIP SHORT
• LONG_BLACKLIST: {long blacklist} → SKIP LONG
• CONFIDENCE FLOOR: < 50% raw → WAIT
• MIN SIGNAL QUALITY: < 2 distinct signal types → WAIT (need confluence)
• REGIME CONFLICT: strong regime opposes direction → WAIT
• SOL TOKEN: Raydium shorts not supported → SKIP SHORT
• Pump/vol: SHORT requires > $5000 Gate.io 24h volume
```

### Response Format
```
OPEN: {token}:{action}:{reason}       # CLOSE | HOLD | SL_VIOLATION
HOT: {token}:{action}:{reason}         # EXECUTE | SKIP
DECIDE: {token}:{direction}:{confidence}:{reason}  # LONG | SHORT | WAIT
SUMMARY: {n_trades_closed} trades closed, {n_hot_exec} hot executed, {n_signals_approved} approved, {n_signals_rejected} rejected
```

---

## Implementation Notes

### [X] Prompt saved to `/root/.hermes/prompt/main-prompt.md`

### ai_decider.py changes
1. Create `decide_all()` as the single entry point (replaces `__main__` logic)
2. Move all data gathering to the top of `decide_all()`
3. `get_pending_signals()` no longer calls `_do_compaction_llm()` — compaction moves to its own periodic task
4. The main loop becomes: gather → pre-filter → LLM call → parse → execute
5. `_do_compaction_llm()` renamed to `compact_signals()` and called separately by the pipeline timer (every 10 min as before), not inside the decision path
6. `ai_decide_batch()` and `ai_decide()` become internal helpers only (for manual/adhoc calls), no longer called from the main pipeline

### hotset.json still written by `compact_signals()`
- `decide_all()` READS hotset.json to get hot survivors (pre-LLM)
- `compact_signals()` (every 10 min) WRITES hotset.json
- This preserves the 2-step: first cycle earns survival_round=1, second cycle earns EXECUTE

### Backward compatibility
- `decider_run.py` calls `decide_all()` instead of `get_pending_signals()` + manual loop
- Pipeline timer unchanged (still fires every 10 min)
- `ai_decide()` kept for manual/ad-hoc use (e.g., T wants to vet a specific signal)

### Token budget
- Single call with full context will use more tokens per call
- But: fewer total calls (1 vs 2-3 per cycle)
- Monitor: if token budget is a concern, cap the number of signals sent per call (top 20 by confidence, same as current hot-set size)

### Open trade monitoring
- Currently `ai_decide_batch()` monitors open trades AND decides on signals in one call
- New design: same single call handles both — open trades are in the prompt input section
- Guardian (`hl-sync-guardian.py`) still runs its own independent monitoring cycle — different safety layer

### Error handling
- If LLM fails: ALL decisions default to WAIT, no trades closed or opened
- Guardian's independent monitoring provides safety net for open trades if LLM is down

---

## Files to Modify
- `ai_decider.py` — new `decide_all()` function, remove inline main loop, `get_pending_signals()` no longer calls `_do_compaction_llm()`
- `decider_run.py` — update to call `decide_all()`
- (No changes to `signal_schema.py`, `hermes_constants.py`, `signal_gen.py`)
