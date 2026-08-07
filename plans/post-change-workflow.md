---
name: post-change
description: Use after completing any code change, bug fix, new feature, or config update. Runs bug_hunter, implements fixes, updates memory, informs CEO, commits to git. Triggers on keywords like "verify my changes", "post-change", "wrap up", "done with changes", "finalize".
---

# Post-Change — Verify, Remember, Report, Commit

Run after every meaningful change. No exceptions. One skill, four steps, done.

## Workflow

```
change complete
  → bug_hunter (find issues, implement fixes)
    → OpenMemory (store what was done)
      → CEO (inform about changes)
        → git commit + push
```

---

## Step 1: Call bug_hunter and implement fixes

### 1A. Identify changed files

```bash
cd /root/.hermes && git diff --name-only HEAD~1
```

If no recent commit, use `git status --short`.

### 1B. Run bug_hunter

Read the changed files, then audit them:

```bash
cd /root/.hermes
python3 -c "
import sys
sys.argv = ['bug_hunter'] + sys.argv[1:]
exec(open('automation/bug_hunter_prompt.md').read())
" <list of changed files>
```

Or use the Task tool with `subagent_type: general` and prompt:

```
You are the bug_hunter. Audit these files for bugs:
[list changed files]
Check: imports, scoping, edge cases, connection leaks, common patterns.
Return: bugs found with file:line references, or "ALL CLEAR".
```

### 1C. Implement fixes

For each bug found:
1. Read the affected code
2. Apply the minimal fix
3. Verify syntax: `python3 -c "import py_compile; py_compile.compile('<file>', doraise=True)"`

### 1D. Re-run bug_hunter on fixes

After implementing fixes, verify they're clean:

```
bug_hunter pass 2: verify the fixes are correct and introduced no new issues.
```

### 1E. Commit fixes (if any)

```bash
cd /root/.hermes
git add -A
git commit -m "fix: <brief description of what was fixed>"
```

---

## Step 2: Update OpenMemory

Store what was done for cross-session continuity.

```python
openmemory_openmemory_store(
    content="What was done: [summary of changes]. "
            "Files changed: [list files]. "
            "Decisions made: [any choices]. "
            "Bugs found and fixed: [list or 'none'].",
    tags=["<topic>", "<date>"],
    type="contextual"
)
```

### What to include

| Field | Example |
|-------|---------|
| What | "Added per-direction kill-switch to vortex_break signal" |
| Files | "hermes_constants.py, signal_schema.py, vortex_break.py" |
| Decisions | "Used try/except ImportError for Layer 2 checks" |
| Bugs | "RS source matching used wrong pattern, fixed" |

---

## Step 3: Inform CEO

Report changes to the CEO automation.

```bash
cd /root/.hermes
python3 -c "
import json, datetime
report = {
    'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'event': 'changes_completed',
    'summary': '<one-line description>',
    'files_changed': [<list>],
    'bugs_fixed': [<list or empty>],
}
print(json.dumps(report, indent=2))
"
```

---

## Step 4: Commit to git

```bash
cd /root/.hermes
git add -A
git commit -m "<category>: <brief description>

- <key change 1>
- <key change 2>
- <key change 3>"
python3 /root/.hermes/skills/productivity/update-git/references/push_gh.py
```

### Commit message format

| Category | When |
|----------|------|
| `signals:` | New signal or signal changes |
| `fix:` | Bug fix |
| `scripts:` | Script changes |
| `skills:` | Skill changes |
| `config:` | Config/constants changes |
| `memory:` | OpenMemory updates |
| `plans:` | Spec/plan changes |

---

## When to skip steps

| Situation | Skip |
|-----------|------|
| Trivial change (typo, comment) | Step 1 (bug_hunter), Step 3 (CEO) |
| Config-only change | Step 1 (bug_hunter) |
| New signal | Use `add-signal` skill instead |
| Bug fix only | Step 3 (CEO) optional |

**Default: run all 4 steps.** Only skip if you're certain it's unnecessary.
