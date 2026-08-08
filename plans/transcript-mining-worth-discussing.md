# Spec: Worth Discussing — Transcript Mining Ideas

**Source**: Ex-NASA Agentic Engineering Workflow transcript
**Date**: 2026-08-08
**Status**: Proposals (not yet implemented)

---

## Idea 1: Vertical Slices for Signal Development

### Problem
Signals are currently built in isolation. A signal author writes detection logic, then separately integrates with hotset, execution, and exit logic. This creates:
- Integration bugs found late
- No end-to-end testability
- Signals that "detect" but don't "trade"

### Solution
Build signals as vertical slices: detection → hotset → execution → exit, all working end-to-end with minimal logic first. Then refine each layer.

### Current Flow (Horizontal)
```
1. Write signal detection (bb_bounce.py)
2. Write hotset integration (signal_compactor.py)
3. Write execution logic (decider_run.py)
4. Write exit logic (position_manager.py)
5. Integration test (hope everything works)
6. Bug fixes (usually 2-3 rounds)
```

### Proposed Flow (Vertical Slice)
```
Phase 1: Detection (minimal)
  - Signal fires on any condition (no filters)
  - Writes to signals DB

Phase 2: Hotset (minimal)
  - Signal passes through compactor
  - Appears in hotset.json

Phase 3: Execution (minimal)
  - Decider opens position
  - Initial SL/TP set

Phase 4: Exit (minimal)
  - Position manager closes on ATR SL/TP
  - PnL recorded

[END-TO-END WORKING — signal trades with minimal logic]

Phase 5: Refine detection
  - Add quality filters
  - Add regime checks
  - Tune confidence

Phase 6: Refine execution
  - Add confluence checks
  - Add speed filters
  - Tune position sizing

Phase 7: Refine exit
  - Add trailing
  - Add wave turns
  - Tune TPSL params
```

### Implementation

**File: `/root/.config/opencode/skills/add-signal/SKILL.md`**
Replace current workflow with vertical slice phases:

```markdown
## Signal Development Workflow (Vertical Slices)

### Phase 1: Detection (30 min)
Write minimal signal detection. No filters, no regimes — just raw detection.
- Create `scripts/signals/my_signal.py`
- Output: list of (token, direction, confidence)
- Test: run it, verify it outputs signals

### Phase 2: Hotset Integration (15 min)
Wire detection into the pipeline.
- Add to `signals/__init__.py`
- Add to `signals_runner.py`
- Test: run pipeline, verify signal appears in hotset.json

### Phase 3: Execution (15 min)
Wire into decider. Minimal filters.
- Add signal type to `decider_run.py`
- Test: run pipeline, verify position opens

### Phase 4: Exit (15 min)
Verify exit logic works. No customization needed — ATR SL/TP handles it.
- Test: run pipeline, verify position closes and PnL is recorded

### [MINIMUM VIABLE SIGNAL — trades end-to-end]

### Phase 5-7: Refinement
Now add quality layers one at a time:
- Phase 5: Detection filters (regime, RSI, volume)
- Phase 6: Execution filters (confluence, speed, cooldown)
- Phase 7: Exit customization (trailing, wave turns)
```

**New file: `/root/.hermes/docs/adr/009-vertical-slice-signal-dev.md`**
```markdown
# ADR-009: Vertical Slice Signal Development

**Date**: 2026-08-08
**Status**: Proposed
**Deciders**: T

## Context
Signals built in isolation have integration bugs found late. Horizontal build (all detection, then all hotset, then all execution) delays end-to-end testing.

## Decision
Develop signals as vertical slices: detection → hotset → execution → exit, all working end-to-end with minimal logic first. Then refine each layer.

## Consequences
- Earlier integration testing
- Faster time to "first trade"
- Signal authors get quick feedback on whether detection works
- Refinement happens after signal is trading, not before

## Alternatives Considered
- Keep horizontal: familiar but slow feedback loop
- Full vertical with tests: overkill for signals (most are <100 LOC)
```

### Effort
- medium: update add-signal skill, create ADR, cultural shift

### Expected Impact
- Signal development time: 2-3 hours → 1 hour
- Integration bugs found: after full build → within 30 min
- Time to first trade: days → 1 hour

---

## Idea 2: Dual-Model Review

### Problem
One model has blind spots. Code that passes one model's review might have issues another model catches.

### Solution
Use two different frontier models to review critical changes. Each catches different things.

### When to Use
- Phantom trade fixes (critical)
- SL/TP logic changes (high risk)
- Signal logic changes (medium risk)
- New signal development (medium risk)

### Current Flow
```
1. Make change
2. bug_hunter reviews (one model)
3. Fix issues found
4. Commit
```

### Proposed Flow
```
1. Make change
2. bug_hunter reviews (model A — mimo-v2.5)
3. Fix issues found
4. opencode command sends to model B (external) for second opinion
5. Fix any additional issues
6. Commit
```

### Implementation

**File: `/root/.config/opencode/skills/bug-hunter/SKILL.md`**
Add after audit workflow:

```markdown
### Dual-Model Review (for critical changes)

For high-risk changes (SL/TP logic, phantom trade fixes, signal core logic):

1. Complete first review with primary model
2. Send to second model for second opinion:
   ```bash
   cat /root/.config/opencode/skills/opencode-command/SKILL.md
   ```
   Use opencode command to send the diff to a different model.
3. Compare findings — merge unique issues from both reviews.

When to skip dual review:
- Config changes (hermes_constants.py)
- Documentation (README, ADRs)
- Skill prompt updates
- Low-risk signal tuning
```

**New file: `/root/.hermes/docs/adr/010-dual-model-review.md`**
```markdown
# ADR-010: Dual-Model Review for Critical Changes

**Date**: 2026-08-08
**Status**: Proposed
**Deciders**: T

## Context
Single-model review has blind spots. Code that passes one model's review might have issues another catches.

## Decision
For critical changes (SL/TP logic, phantom trades, signal core), use two models for review. Primary model audits first, secondary model reviews diff for second opinion.

## Consequences
- Catches more issues before deployment
- Doubles review time for critical changes
- Requires opencode command skill (external model access)

## Alternatives Considered
- Single model with more tokens: diminishing returns
- Human review only: doesn't scale
- Skip review: too risky for critical paths
```

### Effort
- small: update bug-hunter skill, create ADR, 20 minutes to set up

### Expected Impact
- Critical bugs caught before deploy: +20-30%
- False positives: minimal (models catch different things)
- Review time: +5-10 minutes per critical change

---

## Idea 3: Incident → Agent Pipeline

### Problem
When errors happen, health_monitor logs them to error_alerts.md. But someone (human or CEO) has to notice and act. Errors can sit for hours.

### Solution
Route errors directly to an agent that diagnoses and fixes. Like the NASA video's "wake up to a PR, not an alert."

### Current Flow
```
Error occurs
  → health_monitor detects
    → Logs to error_alerts.md
      → CEO reads on next run (4h later)
        → CEO decides to fix or delegate
          → bug_hunter investigates
            → Fix applied
```
Timeline: 4-8 hours from error to fix.

### Proposed Flow
```
Error occurs
  → health_monitor detects
    → Routes to incident agent
      → Agent diagnoses (grep logs, check DB)
      → Agent applies fix (restart, config change, code fix)
      → Agent reports to kanban TEAM UPDATES
      → CEO reviews on next run
```
Timeline: 5-15 minutes from error to fix.

### Implementation

**File: `/root/.hermes/automation/health_monitor_prompt.md`**
Add after Step 4 (auto-fix):

```markdown
### Step 4B: Incident Agent (for complex issues)

If auto-fix doesn't handle it, route to incident agent:

1. **Diagnose**: Read error_alerts.md, grep logs for context
2. **Classify**: 
   - Transient (rate limit, network) → retry + log
   - Recurring (code bug) → fix code + commit
   - Unknown → escalate to CEO kanban
3. **Fix**: Apply minimal fix
4. **Verify**: Confirm error stopped
5. **Report**: Write to kanban TEAM UPDATES

### Incident Agent Rules
- Max 1 code change per incident (don't destabilize)
- Never change locked params
- If fix requires architecture change → escalate to CEO
- Log everything in error_alerts.md with fix applied
```

**New file: `/root/.hermes/docs/adr/011-incident-agent.md`**
```markdown
# ADR-011: Incident → Agent Pipeline

**Date**: 2026-08-08
**Status**: Proposed
**Deciders**: T

## Context
Errors sit for 4-8 hours before CEO notices. Health monitor logs but doesn't act on complex issues.

## Decision
Health monitor routes complex errors to an incident agent that diagnoses and fixes within 15 minutes. CEO reviews on next run.

## Consequences
- Faster error resolution (minutes vs hours)
- CEO stays informed via kanban TEAM UPDATES
- Incident agent has limited scope (1 code change max)

## Alternatives Considered
- CEO handles all errors: too slow (4h cycle)
- Real-time alerting: overkill for current scale
- Ignore errors: loses money
```

### Effort
- medium: update health_monitor prompt, create ADR, test with real errors

### Expected Impact
- Error resolution time: 4-8h → 15min
- Lost trades from unresolved errors: -50%
- CEO workload: reduced (agent handles routine fixes)

---

## Implementation Priority

| Idea | Effort | Impact | Priority |
|------|--------|--------|----------|
| Vertical slices | medium | High (faster signal dev) | 1 |
| Incident agent | medium | High (faster fixes) | 2 |
| Dual-model review | small | Medium (better quality) | 3 |

## Expected Total Effort
- Vertical slices: 2-3 hours
- Incident agent: 2-3 hours
- Dual-model review: 1 hour
- **Total: 5-7 hours**

## Expected Total Impact
- Signal development: 2-3h → 1h (-60%)
- Error resolution: 4-8h → 15min (-90%)
- Critical bug catch rate: +20-30%
