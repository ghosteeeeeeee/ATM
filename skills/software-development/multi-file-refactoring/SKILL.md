---
name: multi-file-refactoring
title: Multi-File Refactoring & Audits
description: "Patterns for coordinated changes across many files in a codebase — JSON schema renames, shared-symbol removal, multi-pass audits, and the Hermes-specific pitfalls that derail these operations (duplicate implementations, dead blacklist imports, stale-comment drift)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [refactoring, multi-file, rename, audit, schema, migration, kill-switch, blacklist, hermes, code-quality]
    related_skills: [requesting-code-review, hermes-agent, hermes-signal-debugging]
---

# Multi-File Refactoring & Audits

Coordinated changes across many files in a codebase. Four named sub-procedures, all with the same shape: **discover → analyze → patch in safe order → verify**:

1. **JSON Schema Rename** — change a field key (e.g. `token` → `coin`) across writers, readers, dashboards
2. **Symbol Removal** — delete a shared constant/function/import across N files
3. **Multi-Pass Signal Audit** — delegate audits (no changes), verify data independently, apply fixes yourself
4. **Large Contiguous Block Removal** — when `patch` fails 2+ times on a 100+ line block, fall back to a Python line-number script for surgical deletion

Hermes-specific recurring pitfalls are listed at the end — they apply to all four procedures.

---

## 1. JSON Schema Rename (multi-file)

**Use when:** renaming a field key (e.g., `"token"` → `"coin"`) that spans multiple JSON schemas, Python writers/readers, and dashboard HTML files.

### Core Principle

**Map every schema independently first.** Each JSON file (trades.json, hotset.json, signals.json) is its own schema with its own writer(s) and reader(s). Changes must be coordinated per-schema, not done file-by-file blindly.

### Step-by-Step

**Phase 1: Discovery — Who Writes What**

1. Identify writers — grep for `json.dump` / `write_file` calls that create the target JSON
2. Identify readers — grep for `json.load` / `read_file` calls that parse it
3. Build a write-chain and read-chain per schema
4. **Rule:** If you change the writer but not a reader, the reader breaks. Change ALL readers first (or atomically change both).

**Phase 2: Schema-by-Schema Rename**

For each JSON schema (e.g., `trades.json`):

1. Update all **readers** to use the new key name
2. Update the **writer** to use the new key name
3. Regenerate the JSON (trigger a fresh write)
4. Verify raw bytes show the new key

**Order matters:** Update readers FIRST, then the writer, then regenerate. This avoids stale reads during the transition.

**Phase 3: Dashboard HTML**

- Update `${t.token}` / `${s.token}` template references to match the new JSON key
- Update table `<th>Token</th>` display labels independently (these are UI labels, not JSON field names)

**Phase 4: Verification**

```bash
python3 -c "
import json
with open('/var/www/hermes/data/trades.json') as f:
    data = json.load(f)
open_trades = data.get('open', data)
for t in open_trades[:3]:
    print('coin:', t.get('coin'), '| has token key:', 'token' in t)
"
grep -r '"token"' /var/www/hermes/data/
grep -r "'token'" /root/.hermes/scripts/*.py
```

### Common Pitfalls

- **Forgetting a reader:** gets `None` for the field, behaves incorrectly
- **Dashboard HTML lagging:** update both the JSON schema AND the HTML template
- **Atomicity:** Coordinate all changes or do "readers first" ordering
- **Display labels vs field names:** `<th>Token</th>` is a display label, not a JSON field

---

## 2. Symbol Removal (multi-file)

**Use when:** a symbol (constant, function, import) must be removed from a codebase and replaced with something else across many files (e.g. `HOTSET_BLOCKLIST` across 7 files).

### Phase 1: Reconnaissance

```bash
# Find ALL references (functional + comments)
grep -rn "SYMBOL_NAME" /root/.hermes/scripts/

# List only functional code references (exclude comments)
grep -rn "SYMBOL_NAME" /root/.hermes/scripts/ --include="*.py" | grep -v "^.*#"

# Check skill files too
grep -rn "SYMBOL_NAME" /root/.hermes/skills/
```

### Phase 2: Per-File Analysis

For each file that references the symbol:
1. Read the file around the reference line(s)
2. Determine what replacement logic is needed
3. Check if other symbols in the same file also need updating

**Key insight:** The same symbol may be used differently in different files:
- Import statements → remove from import line
- Constant definitions → remove the definition, update consumers
- Usage sites → replace with explicit alternative

### Phase 3: Patch in Order (Safe → Dependent)

1. **Definition file first** (e.g. `hermes_constants.py`) — remove the symbol definition
2. **Consumer files next** — update each usage site

This prevents accidentally leaving stale references that mask each other.

### Phase 4: Verify

```bash
grep -rn "SYMBOL_NAME" /root/.hermes/scripts/ --include="*.py" | grep -v "^.*#"

python3 -m py_compile /root/.hermes/scripts/hermes_constants.py
python3 -m py_compile /root/.hermes/scripts/ai_decider.py
# ... every modified file
```

### Phase 5: Functional Test

Trigger the component directly to confirm no crashes:

```bash
cd /root/.hermes && python3 -c "
from scripts.ai_decider import AiDecider
ad = AiDecider()
# trigger compaction path
"
```

### Pitfalls

- **Comment-only references:** grep picks up comments — filter
- **Similar names:** `SHORT_BLACKLIST` ≠ `HOTSET_BLOCKLIST`
- **Backup files:** `.bak` files with stale content
- **Scope bugs:** symbol imported at module level but undefined inside a function (try/except scope) — often the root cause
- **Directional logic:** when removing a combined list, ensure the replacement uses directional checks throughout

---

## 3. Multi-Pass Signal Audit

**Use when:** auditing 5+ related Python scripts for correctness — especially when fix scope is broad and bugs could cascade. Use when a previous fix may have introduced new issues, or when the root cause spans multiple files with similar patterns.

### Pass 1: Delegate audit only (no changes)

Spawn subagents with `goal` explicitly stating: "Recommend fixes only — do NOT make any changes." Set `max_iterations` generously (40+). Provide the full audit checklist in the task context.

**Key constraint to embed in every subagent prompt:**
> "Only RECOMMEND fixes, do NOT make any changes. List each issue with file, line (if identifiable), and exact fix recommendation."

This is critical — subagents will try to "help" by applying fixes during audit. Explicitly prohibit it.

### Pass 2: Apply fixes yourself

Never let the auditing subagent also apply fixes. Apply all recommended fixes in your own context. The subagent's value is in finding issues you might miss, not in modifying files.

### Pass 3: Verify all fix outcomes

- `python3 -m py_compile` on every modified file
- Live runtime test on the riskiest fix (in this case: the broken subquery pattern)
- Confirm fixes don't break other signals

### Audit Checklist (Signal Scripts)

For each signal script, check:

1. **Data source correctness** — `price_history` table is fresh (<1 min). `candles.db` acceptable for volume only. `ohlcv_1m` table is 7+ days stale — NEVER use.
2. **SQL subquery pattern** — must use double-subquery for LIMIT + ORDER BY ASC:
   ```sql
   SELECT timestamp, price FROM (
       SELECT timestamp, price FROM price_history
       WHERE token = ? ORDER BY timestamp DESC LIMIT N
   ) sub ORDER BY timestamp ASC
   ```
   Common bug: inner query selects only `price` but outer query orders by `timestamp` → `OperationalError: no such column: timestamp`. Fix: include `timestamp` in inner SELECT.
3. **Imports** — `sqlite3` and `time` must be imported where used
4. **No debug prints** in hot paths
5. **Dict returns match consumer code** — e.g., if consumer reads `['high']` and `['low']`, the getter must return `{open, high, low, close}`, not just `{close}`
6. **ORDER BY direction for LIMIT queries** — `ORDER BY ts ASC LIMIT N` returns the **oldest** N rows, NOT the newest. For any time-bounded signal query, you almost always want `ORDER BY ts DESC LIMIT N` (newest N rows) + reverse the result back to oldest-first if the algorithm expects chronological order. A wrong sort direction causes the freshness guard to check stale data and silently return `[]`.
7. **Freshness guards** — signals should return `[]` for stale data, not emit phantom signals

### Kill-Switch Verification (Always Check)

**Critical additional check — Dead blacklist import (P0):** After any change to hermes_constants `*_BLACKLIST` constants, verify the consuming script actually uses them.

```python
# hermes_constants.py defines:
SIGNAL_SOURCE_BLACKLIST = {'pct-hermes', 'vel-hermes', ...}

# decider_run.py imports them:
from hermes_constants import (SHORT_BLACKLIST, LONG_BLACKLIST,
    SIGNAL_SOURCE_BLACKLIST, ...)  # ← imported

# But never actually calls validate_source() or checks the blacklist!
```

**Detection:** Use grep to find all callers of blacklist constants:
```bash
grep -n "SIGNAL_SOURCE_BLACKLIST\|SHORT_BLACKLIST\|LONG_BLACKLIST" \
  /root/.hermes/scripts/decider_run.py
# If the only matches are import lines → P0: dead blacklist import
```

If `SIGNAL_SOURCE_BLACKLIST` is imported but `validate_source()` is never called in that script, the blacklist provides zero protection even though it exists. Flag as P0.

### Custom log() Arity Check

Many Hermes scripts define `def log(msg)` (single arg). Callers that pass `log(msg, 'WARN')` have the second arg silently swallowed. Verify:
```bash
grep -rn "log(f.*',\s*['\"][A-Z]" /root/.hermes/scripts/
```

### Stale-Comment Verification (RECURRING BUG PATTERN)

After any patch, cross-reference actual computed values against inline comments and docstrings.

Common failures:
- Comment says "+15%" but code does "+50%" (signal_compactor.py:200)
- Comment says "25% penalty" but code does "20% haircut" applied downstream (rs.py:496-501)

Pattern: comments drift from code during rapid iteration. Always verify:
1. Numeric values in comments match actual assignments
2. Percentages in comments match arithmetic operations
3. "applied in compactor" comments are confirmed by tracing the actual code path

Fix: update comment to match code, not the other way around.

### Duplicate-Implementation Bug (P0)

**Symptom:** A signal was migrated to `signals/` folder (with fix applied), but stale signals keep appearing. The `signals/` version works correctly in isolation, but signal_gen still fires wrong signals.

**Root cause:** `signal_gen.py` imports directly from the OLD root-level file, bypassing the `signals/__init__.py` registry entirely. The fix was applied to the NEW version but the OLD version is what actually runs.

**Example:** `accel_300_signals.py` (root, deprecated) vs `signals/accel_300.py` (new, fixed). signal_gen.py line 2673:
```python
from accel_300_signals import scan_accel_300_signals  # ← OLD, bypasses signals/ registry
```

**Audit checklist for this bug:**
1. `grep -n "from accel_300_signals\|from gap300_signals\|from macd_accel\|from rs_signals" /root/.hermes/scripts/signal_gen.py` — find direct imports
2. For each direct import, check if a `signals/<name>.py` version exists
3. If `signals/<name>.py` exists: the direct import is the bug — it bypasses the registry and any fixes applied to the signals/ version
4. Fix: change `from <name> import` to `from signals.<name> import scan_<name>` in signal_gen.py

**Prevention:** When migrating a signal to the signals/ folder, DELETE or rename the root-level file. Do not leave it in place — it creates a duplicate that signal_gen can still import directly.

### Data Freshness Verification (Always Do This First)

Before trusting any subagent's conclusion about data sources, independently verify:

```python
python3 -c "
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()
cur.execute('SELECT MAX(timestamp) FROM price_history WHERE token=?', ('BTC',))
r = cur.fetchone()
print(f'price_history BTC: {time.time() - r[0]:.0f}s ago')
cur.execute('SELECT MAX(timestamp) FROM ohlcv_1m WHERE token=?', ('BTC',))
r = cur.fetchone()
print(f'ohlcv_1m BTC: {time.time() - r[0]:.0f}s ago' if r[0] else 'ohlcv_1m: no data')
"
```

---

## 4. Large Contiguous Block Removal

**Use when:** `patch` fails 2+ times on removing a 100+ line block, or when the block spans multiple functions with no clean unique boundary strings.

### The Problem

`patch` fails on large removals because:
- Requires unique boundary strings — hard across thousands of lines
- Whitespace/indentation mismatches cause silent failures or corruption
- 3+ failed patch attempts waste time

### The Solution

Use a Python script in `terminal` to delete lines by number:

```python
python3 << 'PYEOF'
with open('file.py', 'r') as f:
    lines = f.readlines()

# Find exact boundaries
for i, l in enumerate(lines):
    if 'unique_start_marker' in l:
        start = i
    if 'unique_end_marker' in l:
        end = i
        break

new_lines = lines[:start] + lines[end+1:]
with open('file.py', 'w') as f:
    f.writelines(new_lines)
print(f"Removed lines {start+1}–{end+1}")
PYEOF
```

### When to Use

- Removing 100+ lines in one operation
- Patch has failed 2+ times on the same removal
- Block spans multiple functions with no clean unique boundary strings
- Uncertain of exact indentation

### Verification After Removal

```bash
python3 -c "import importlib; importlib.import_module('module_name')" 2>&1
```

Also verify the file is syntactically valid:

```bash
python3 -m py_compile file.py && echo "Syntax OK"
```

---

### HTML Section Replacement — Verify Target Exists First

**Before replacing any HTML section the user pastes:** grep the current file for a unique string from the pasted snippet. If grep returns nothing, the section was **already removed** in a prior session. Do not proceed — ask the user to confirm the target still exists before patching.

**Common failure mode:** User pastes a snippet referencing `id="zscore-pump"` or `id="hotEmpty"` in a paste file or old session, but the current file has already had that section removed. The patch silently succeeds on the paste file but does nothing to the real file.

**Always do:**
```bash
# Verify the target HTML actually exists in the CURRENT file before patching
grep -n 'id="zscore-pump"' /root/.hermes/web/trades.html
grep -n 'id="hotEmpty"' /root/.hermes/web/signals.html
```

**Also:** When the user pastes HTML to "replace a section" of a file they control, the paste file at `/root/.hermes/pastes/` is often the source of truth for what they want to replace — but it may be stale. Verify the target is still in the file.

## Hermes-Specific Recurring Pitfalls (apply to all 4 procedures)

### Centralized Validation — All Callers Must Use the Same Function

**The stale-caller bug:** When shared validation logic lives in one file but multiple files have their own copies, ONE caller can silently have outdated logic while the canonical function was updated.

**Detection:**
1. Find all files that reference the shared constant/function
2. For each file, check whether it CALLS the canonical function OR has its own inline implementation
3. If a file has its own implementation, it IS the bug — replace with a call to the canonical function

**Rule:** Any time you update a blacklist, combination rule, or shared constant — check ALL files that touch it. If one file has an inline copy while others call the canonical function, the inline copy IS the bug.

### The Blacklist + Kill-Switch Dual-Control Pattern

**Problem:** A signal can appear in both `SIGNAL_SOURCE_BLACKLIST` AND have a `*_ENABLED` flag. If both exist, the blacklist takes precedence — the signal never reaches the Layer 2 flag check.

**Rule:** A signal should be controlled by EITHER the blacklist OR the `*_ENABLED` flag, not both. When you want a flag to control it, REMOVE it from the blacklist. When you want it permanently blocked, ADD it to the blacklist and don't create a flag.

**Verification after any blacklist/flag change:**
```python
from hermes_constants import SIGNAL_SOURCE_BLACKLIST
from signal_schema import validate_source

assert 'pct-hermes+' not in SIGNAL_SOURCE_BLACKLIST, "Still in blacklist!"
assert validate_source('pct-hermes+') == 'pct-hermes+', "validate_source should return the source"
```

**The three valid configurations for a signal:**
| Config | Blacklist | `*_ENABLED` Flag | Result |
|--------|-----------|-----------------|--------|
| Permitted | Not in list | True | Signal passes |
| Kill-switch controlled | Not in list | False | Signal blocked by flag |
| Permanently blocked | In list | Irrelevant | Signal blocked by blacklist |

Never put a signal in both the blacklist AND set its flag to True — the blacklist wins every time.
