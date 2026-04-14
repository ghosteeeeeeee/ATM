---
name: progressive-delegation
description: Strategic pattern for delegating complex multi-issue investigations to subagents — start broad, narrow per round, let findings drive next steps. Prevents premature scoping and ensures thorough coverage.
triggers:
  - "delegate to fix complex system"
  - "delegate to investigate pipeline"
  - "delegate multi-step audit"
  - "delegate cascade of issues"
category: autonomous-ai-agents
author: hermes
created: 2026-04-13
---

# Progressive Delegation — Strategic Pattern for Complex Investigations

## When to Use

When facing a complex system (codebase, pipeline, infrastructure) where:
- The full scope of issues is unknown upfront
- Issues are interconnected (fixing one reveals another)
- Static analysis alone won't find everything (testing reveals real problems)
- The human expects thorough coverage, not a single-pass attempt

**Don't use for:** Simple, bounded tasks with known scope (e.g., "write this one function").

## The Pattern: 4 Rounds

### Round 1: Broad Audit + Top Priority Fixes
**Goal:** Get a system-wide view + fix the obvious critical issues
**What to delegate:**
1. Load all context files (trading.md, TASKS.md, plans/, CONFIG.md)
2. Audit the full system end-to-end
3. Fix ONLY the critical/high severity issues (the ones that block everything else)
4. Report what else needs fixing but wasn't fixed yet

**Typical output:** 5-15 issues found, 1-3 critical ones fixed

### Round 2: Specific Fixes (Based on Round 1 Findings)
**Goal:** Fix the issues that Round 1 identified but didn't fix
**Handoff includes:** Summary of Round 1 findings + previous fixes applied
**What to delegate:** Fix the next tier of issues (high/medium severity)
**Typical output:** 3-7 more issues found, 2-4 fixed, 1-3 still pending

### Round 3: Call Site / Integration Fixes
**Goal:** Wire up the fixes from Round 2 into actual execution paths
**Typical output:** Schema additions, function calls, path corrections, CLI argument fixes

### Round 4: Pipeline Verification
**Goal:** Run the system end-to-end and fix whatever breaks
**Critical:** Testing finds issues that static analysis misses (CLI interface mismatches, path issues, schema columns, wrong file references)
**Typical output:** 3-6 final fixes to get the system running cleanly

## Why This Works Better Than One Big Delegation

| One Big Delegation | Progressive Delegation |
|--------------------|-----------------------|
| Underestimates scope by 3-5x | Each round reveals真实 scope |
| Subagent gets lost in complexity | Narrow focus = higher quality output |
| No discovery of cascade issues | Fix A → reveals B → fix B |
| Static-only analysis | Pipeline test = real issues surface |
| Human gets one big answer | Human gets progress updates each round |

## Real Example from Hermes Pipeline Audit

```
Round 1: ML Pipeline Audit → Found 7 critical issues
  Fixed: regime detector bias, candle predictor killswitch
  Still pending: 5 tracking tables, decisions table, cooldown
  
Round 2: 5 Tracking Table Fixes → Implemented 2 fully, 3 partially
  Fixed: signal_schema.py (7 new functions), signal_gen.py (call sites)
  Still pending: decider-run.py, ai_decider.py, position_manager.py call sites
  
Round 3: 3 Remaining Call Sites → All done
  Fixed: decider-run.py, ai_decider.py, position_manager.py
  
Round 4: Pipeline Test → Found 4 more issues
  Fixed: brain.py CLI args, path wrong, wave_phase column missing, regime historical data
```

**Result:** 16 total issues found across 4 rounds, all resolved.

## Anti-Pattern: "Just Delegate Everything at Once"

If you give a subagent 16 issues at once:
- They pick 2-3 they can understand quickly
- They miss interconnected issues
- They don't test, so CLI/path issues slip through
- You get a partially-complete result with false confidence

## How to Handoff Between Rounds

Each round's handoff should include:
1. **What was done in previous round** (with exact file changes)
2. **What was found but not fixed yet** (the queue)
3. **What the subagent should focus on this round**
4. **Updated constraints** (what NOT to break now that X is fixed)

## Constraints to Always State

- Live trading/kill switches — never break these
- Don't modify hype_live_trading.json or _FLIP_SIGNALS
- Test after each fix (don't batch 10 fixes then test)
- If a fix would require changing execution flow, ask first
- DB schema changes need verification (sqlite3 .schema)

## Testing as Discovery

Always include a pipeline test in Round 4:
```bash
# Run the actual pipeline
cd /root/hermes-v3/hermes-export-v3 && python3 signal_gen.py 2>&1 | tail -30
cd /root/hermes-v3/hermes-export-v3 && python3 decider_run.py 2>&1 | tail -30

# Check DB state
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT COUNT(*) FROM X"
sqlite3 /root/.hermes/data/signals_hermes_runtime.db ".schema Y"

# Verify imports don't crash
python3 -c "import sys; sys.path.insert(0, '/path/to'); from module import *; print('OK')"
```

Real issues found by testing (not static analysis):
- CLI argument mismatch (brain.py missing --sl-distance arg)
- Path wrong in run_pipeline.py (/root/.hermes/scripts/ vs hermes-export-v3/)
- Schema column missing (wave_phase in token_speeds)
- Historical data vs new data confusion (regime_log)
