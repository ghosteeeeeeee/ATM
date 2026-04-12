---
name: multi-file-symbol-removal
description: Systematically remove a shared symbol (constant, function, import) across multiple Python files — grep → analyze → patch → verify. Used for HOTSET_BLOCKLIST removal across 7 files.
triggers:
  - remove HOTSET_BLOCKLIST
  - remove shared symbol across files
  - multi-file refactor python
  - grep and patch multiple files
---

# Multi-File Symbol Removal SOP

When a symbol (constant, function, import) must be removed from a codebase and replaced with something else across many files:

## Phase 1: Reconnaissance

```bash
# Find ALL references (functional + comments)
grep -rn "SYMBOL_NAME" /root/.hermes/scripts/

# List only functional code references (exclude comments)
grep -rn "SYMBOL_NAME" /root/.hermes/scripts/ --include="*.py" | grep -v "^.*#"

# Check skill files too
grep -rn "SYMBOL_NAME" /root/.hermes/skills/
```

## Phase 2: Per-File Analysis

For each file that references the symbol:
1. Read the file around the reference line(s)
2. Determine what replacement logic is needed
3. Check if other symbols in the same file also need updating

**Key insight:** The same symbol may be used differently in different files:
- Import statements → remove from import line
- Constant definitions → remove the definition, update consumers
- Usage sites → replace with explicit alternative

## Phase 3: Patch in Order (Safe → Dependent)

Always patch in this order:
1. **Definition file first** (e.g. `hermes_constants.py`) — remove the symbol definition
2. **Consumer files next** — update each usage site

This prevents accidentally leaving stale references that mask each other.

## Phase 4: Verify

```bash
# No functional references remaining
grep -rn "SYMBOL_NAME" /root/.hermes/scripts/ --include="*.py" | grep -v "^.*#"

# All modified files pass syntax check
python3 -m py_compile /root/.hermes/scripts/hermes_constants.py
python3 -m py_compile /root/.hermes/scripts/ai_decider.py
python3 -m py_compile /root/.hermes/scripts/signal_schema.py
python3 -m py_compile /root/.hermes/scripts/brain.py
python3 -m py_compile /root/.hermes/scripts/hl-sync-guardian.py
python3 -m py_compile /root/.hermes/scripts/decider_run.py
python3 -m py_compile /root/.hermes/scripts/pattern_scanner.py

# Clear error logs so next run starts clean
echo "=== Cleared $(date -u) ===" > /var/www/hermes/logs/ai_decider_error.log
```

## Phase 5: Functional Test

Trigger the component directly to confirm no crashes:
```bash
cd /root/.hermes && python3 -c "
from scripts.ai_decider import AiDecider
ad = AiDecider()
# trigger compaction path
"
```

## Pitfalls

- **Comment-only references:** grep picks up comments mentioning the symbol — filter these out
- **Similar names:** `SHORT_BLACKLIST` and `LONG_BLACKLIST` are NOT the same as `HOTSET_BLOCKLIST` — don't accidentally modify the individual lists
- **Backup files:** `.bak` files with stale content may be left behind — check and remove
- **Scope bugs:** A symbol may be imported at module level but undefined inside a function (try/except scope) — this is often the ROOT CAUSE of the bug, not just a usage issue
- **Directional logic:** When removing a combined list, ensure the replacement uses directional checks (SHORT vs LONG) throughout

## HOTSET_BLOCKLIST Specific Case

- **Definition:** `HOTSET_BLOCKLIST = SHORT_BLACKLIST | LONG_BLACKLIST` in `hermes_constants.py`
- **Problem:** Combined mask prevents tokens on ONE blacklist from being used in the OTHER direction — wrong semantic model
- **Fix:** Replace each `HOTSET_BLOCKLIST` usage with explicit `SHORT_BLACKLIST` or `LONG_BLACKLIST` based on trade direction
- **Files modified (7):** hermes_constants.py, ai_decider.py, signal_schema.py, brain.py, hl-sync-guardian.py, decider_run.py, pattern_scanner.py
