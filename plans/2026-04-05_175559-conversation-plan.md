# Hermes Workflow Upgrade Plan — Claude Code Primitives

**Date:** 2026-04-05
**Goal:** Implement Claude Code-inspired primitives into Hermes trading workflow
**Reference:** `.hermes/brain/upgrades.md` (gap analysis)

---

## CURRENT STATE

- Hermes trading bot with decider/guardian architecture
- SQLite state with WAL, but no checkpoint snapshots
- `tool_use_enforcement: auto` declared in config.yaml but not enforced
- 155 markdown persona subagents (prompt injection, not isolated processes)
- No workflow state tracking separate from conversation
- Token budget tracked informally, no pre-call hard stops
- OpenClaw LCM provides superior context management (keep this)

---

## PHASE 1 — Tool Call Safety (CRITICAL / High Effort)

### 1.1 Wire Up `tool_use_enforcement`
**File:** `/root/.hermes/scripts/decider-run.py`
**What:** Add enforcement logic for `tool_use_enforcement: auto/required/off` modes
**Approach:**
- Read `tool_use_enforcement` from config at startup
- Track tool call count per decision cycle
- If `auto` mode: warn after 10 calls, stop after 20
- If `required` mode: fail-fast if tools not called within expected window
- If `off`: log only (for cron/automated runs)
**Verification:** Unit test with mock config, test actual enforcement against runaway scenario

### 1.2 Add Circuit Breaker to Guardian
**File:** `/root/.hermes/scripts/hl-guardian.py` (or wherever guardian logic lives)
**What:** Max turns per pipeline run, hard timeout per step
**Approach:**
- Add `MAX_TOOL_CALLS_PER_RUN = 30` constant
- Add `MAX_STEP_SECONDS = 60` per pipeline step
- On breach: emit structured stop reason, rollback last action, alert
**Verification:** Kill a running pipeline mid-execution, confirm it stops cleanly

---

## PHASE 2 — Checkpoint & Recovery (CRITICAL / High Effort)

### 2.1 Checkpoint Hooks in Pipeline
**File:** `/root/.hermes/scripts/` (pipeline scripts)
**What:** Snapshot state before each major step: regime check → signal gen → order placement → fill confirmation
**Approach:**
- Create `/root/.hermes/scripts/checkpoint.py` — checkpoint(state_dict, label) function
- Snapshot writes JSON to `/root/.hermes/checkpoints/` with timestamp + label
- Keep last 50 snapshots (disk budget ~50MB)
- On restart: check for incomplete pipeline, reconstruct from last checkpoint
**Files to change:** Every pipeline script (`hl-pipeline.py`, `hl-signals.py`, etc.)

### 2.2 Recovery on Restart
**File:** `/root/.hermes/scripts/ai_decider.py` or new `recovery.py`
**What:** On startup, detect if previous run left incomplete workflow
**Approach:**
- Check `checkpoints/` for `in_progress.json`
- If found: replay decisions, confirm positions match state.db
- If mismatch: alert + halt, require human resolution
**Verification:** Kill pipeline mid-execution, restart, confirm it resumes correctly

---

## PHASE 3 — Workflow State Tracking (MAJOR / Medium Effort)

### 3.1 Explicit Workflow State Machine
**File:** `/root/.hermes/brain/workflow-state.md` (new) + code in decider
**What:** States: `PLANNED → AWAITING_APPROVAL → EXECUTING → WAITING_EXTERNAL → COMPLETED/FAILED`
**Approach:**
- Add `workflow_state` field to trades.json entry
- Transitions fire on: user approval, API call, external event (fill webhook), timeout
- Persist state in `state.db` alongside position data
- Emit event log entry on each transition
**Files to change:** `ai_decider.py`, `hl-sync-guardian.py`

### 3.2 Event Log Separate from Conversation
**File:** `/root/.hermes/data/event-log.jsonl`
**What:** Structured log of what the agent *did*, not what it said
**Format:**
```json
{"ts": "ISO8601", "event": "TOOL_CALL", "tool": "hl_place_order", "params": {...}, "result": "success", "duration_ms": 234}
{"ts": "ISO8601", "event": "WORKFLOW_STATE_CHANGE", "from": "EXECUTING", "to": "WAITING_EXTERNAL", "trade_id": "..."}
{"ts": "ISO8601", "event": "PERMISSION_DENIED", "tool": "bash", "reason": "destructive command"}
```
**Verification:** Run 10 trades, confirm event log is complete and queryable

---

## PHASE 4 — Token Budget Pre-Call Validation (MAJOR / Medium Effort)

### 4.1 Budget Projection Before API Call
**File:** `/root/.hermes/scripts/ai_decider.py`
**What:** Estimate token count before calling LLM, stop if projection exceeds budget
**Approach:**
- Track `input_tokens` from last N responses (moving average)
- Before LLM call: `projected = current_tokens + system_prompt + history + next_prompt`
- If `projected > max_budget`: compact conversation via LCM before calling
- If still over budget: emit structured stop reason `"budget_exceeded"` and skip call
**Files to change:** `ai_decider.py`, may need LCM integration
**Verification:** Inject very large prompt, confirm it compacts instead of calling

---

## PHASE 5 — Delegation Infrastructure (MAJOR / Medium Effort)

### 5.1 Wire Up Config Delegation
**File:** `/root/.hermes/config.yaml` (delegation section)
**What:** Actually use the empty `delegation:` block for subagent spawning
**Approach:**
- Add `delegation.model`, `delegation.provider` to config
- Add `delegation.max_iterations: 75` enforcement in `delegate_task` calls
- Add TTL tracking: subagent expires after N seconds regardless of token count
- Add revocation: if parent task completes, revoke subagent grants
**Files to change:** `config.yaml`, `ai_decider.py` (if it calls delegate_task), any cron scripts

### 5.2 (Future) Subagent Isolation
**Note:** 155 markdown personas are fine for now. True subprocess isolation (Claude Code's `sessions_spawn`) is a separate project requiring significant refactor. Flag as future work.

---

## PHASE 6 — Agent Type System (MODERATE / Low-Medium Effort)

### 6.1 Define 4-5 Agent Types for Hermes
**File:** `/root/.hermes/brain/agent-types.md` (new)
**What:** Constrain subagent roles like Claude Code does (explore, plan, verify, execute)
**Proposed types:**
1. **signal_explorer** — reads market data, identifies patterns, never places orders
2. **signal_analyst** — evaluates signals, assigns confidence scores, recommends action
3. **execution_agent** — places orders, handles fill confirmation, manages position
4. **guardian_agent** — verifies state consistency, checks for anomalies, approves/denies
5. **reporter** — generates summaries, updates brain files, logs to event store

**Each type gets:**
- Own allowed tools list
- Own behavioral constraints (e.g., signal_explorer cannot call `hl_place_order`)
- Own prompt template in `/root/.hermes/subagents/`

**Verification:** Attempt to call restricted tool with wrong agent type, confirm it fails

---

## IMPLEMENTATION ORDER

```
Week 1: Phase 1 (Tool safety)
  → decider-run.py enforcement
  → circuit breaker in guardian

Week 2: Phase 2 (Checkpoint)
  → checkpoint.py utility
  → checkpoint hooks in pipeline
  → recovery logic

Week 3: Phase 3 (Workflow state)
  → state machine in trades.json
  → event-log.jsonl

Week 4: Phase 4 (Token budget)
  → pre-call validation in ai_decider

Week 5-6: Phase 5 (Delegation)
  → wire up config delegation

Week 7-8: Phase 6 (Agent types)
  → define + constrain subagent roles
```

---

## RISKS & TRADE OFFS

| Risk | Mitigation |
|------|------------|
| Checkpoint system slows down pipeline (extra I/O) | Async write, batch to disk every 1s max |
| Token budget projection is inaccurate | Use conservative estimates, always round up |
| Workflow state adds complexity to already complex system | Start with 3 states only, expand later |
| Breaking existing trading logic | Add flags to disable new features, off by default |

---

## OPEN QUESTIONS

1. Should checkpoint recovery be automatic or require human confirmation?
2. Should we keep the 155 markdown personas or consolidate to ~5 typed agents?
3. Should token budget be per-session or global across all pipelines?
4. Do we need a permission audit trail UI or is JSONL sufficient for now?

---

## FILES TO CREATE

- `/root/.hermes/scripts/checkpoint.py` — checkpoint utility
- `/root/.hermes/brain/workflow-state.md` — state machine definition
- `/root/.hermes/brain/agent-types.md` — agent type definitions
- `/root/.hermes/data/event-log.jsonl` — event log (auto-created)
- `/root/.hermes/checkpoints/` — checkpoint storage (auto-created)

## FILES TO MODIFY

- `/root/.hermes/scripts/decider-run.py` — enforcement + circuit breaker
- `/root/.hermes/scripts/hl-guardian.py` — circuit breaker
- `/root/.hermes/scripts/ai_decider.py` — token budget pre-call + workflow state
- `/root/.hermes/scripts/hl-sync-guardian.py` — workflow state transitions
- `/root/.hermes/config.yaml` — delegation section wired up
- `/root/.hermes/trades.json` — add `workflow_state` field
- Pipeline scripts in `/root/.hermes/scripts/` — checkpoint hooks

## VALIDATION STEPS

For each phase:
1. Run existing test suite (if any)
2. Manual test: trigger the scenario (e.g., runaway loop for tool safety)
3. Confirm structured stop reason in output
4. Confirm event log entry recorded
5. For checkpoints: kill mid-pipeline, restart, verify clean recovery