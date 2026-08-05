---
name: context-file-bloat-fix
description: Diagnose and fix CONTEXT.md and auto-generated reference file bloat when compaction tools are appending instead of replacing
triggers:
  - "CONTEXT.md is bloated"
  - "file keeps growing despite compaction"
  - "duplicate content sections in context file"
---

# Context File Bloat Fix

## When to Use
When CONTEXT.md or similar auto-generated reference files are growing uncontrollably (1MB+, >10x expected size). Symptoms: file keeps getting larger despite "compaction", duplicate content sections visible at end of file.

## How to Diagnose
```bash
wc -l /root/.hermes/CONTEXT.md
grep -n "^# ARCHITECTURE SNAPSHOT\|^# ATM ARCHITECTURE" /root/.hermes/CONTEXT.md | head -5
```
If you see the same header repeated 3+ times, the compactor is appending instead of replacing.

## Root Cause Pattern
The bug is in the compactor script's regex replacement. `re.subn(pattern, new_content, flags=re.DOTALL)` only removes the **first** match when called once. But the deeper bug is usually a **mismatch between the regex pattern and the actual file format** — e.g., the pattern expects `\n---\n` but the file has `\n---\n\n` (double newline after HR). The pattern silently matches nothing, n_removed stays 0, and the append runs anyway.

## Fix
1. Read the compactor script and find the removal regex pattern
2. Test it against the actual file content in Python:
```python
import re
with open('/root/.hermes/CONTEXT.md') as f:
    content = f.read()
pattern = r'your-pattern-here'
matches = re.findall(pattern, content, re.DOTALL)
print(f'Matches: {len(matches)}')
```
3. Adjust the pattern to match the actual whitespace/newlines
4. Use a while loop to remove ALL occurrences before appending:
```python
n_removed = 0
while True:
    new_content, n = re.subn(pattern, '', new_content, flags=re.DOTALL)
    n_removed += n
    if n == 0:
        break
if n_removed > 0:
    log(f"Removed {n_removed} old snapshot(s)")
```

## Verification
```bash
wc -l /root/.hermes/CONTEXT.md
grep -c "^# ARCHITECTURE SNAPSHOT" /root/.hermes/CONTEXT.md
# Should be exactly 1 after fix
```

## Prevention
Add a sentinel check to the compactor — if it finds >1 snapshot after removal, abort instead of appending:
```python
remaining = len(re.findall(pattern, new_content, flags=re.DOTALL))
if remaining > 1:
    log(f"FATAL: {remaining} old snapshots still present — aborting append!")
    return False
```
