---
name: python-duplicate-function-shadowing
description: Debug Python variable shadowing — when the same variable or function name is defined twice in a file (same scope or nested), Python uses the LAST one at runtime. Covers duplicate function definitions AND duplicate local-variable-in-loop assignments.
tags: [python, debugging, bytecode, gotcha]
---

# Python Duplicate Function Shadowing Debug

## The Problem
Python compiles a `.py` file to bytecode and **uses the last definition** when multiple functions share the same name. Normal AST tools (`ast.parse`, IDE Intellisense) may not warn you — especially if one definition is injected after compilation, or if a binary gap exists between load+compile steps.

## Symptoms
- A function returns wrong values despite the source code looking correct
- A function seems to have two different implementations depending on call site
- `.pyc` cache keeps regenerating but code never "takes"
- Binary analysis shows file size > compiled bytecode size
- A call site passes `keyword_arg=value` but the "correct" source definition doesn't accept that param — because the WRONG definition (which accepts it) is what Python actually executes at runtime

## Debugging Approach

### Step 1: Find all definitions
```bash
grep -n "def _function_name" /path/to/file.py
```

This instantly shows duplicate definitions. Don't rely on AST parse — grep is definitive.

### Step 2: Read each definition and its k-values/logic
```bash
sed -n 'NNN,NNN+p' /path/to/file.py   # for each definition
```

### Step 3: Trace which one executes
Check call sites:
```bash
grep -n "_function_name(" /path/to/file.py
```

The call at runtime uses whichever definition is **last in the file**.

### Step 4: Binary gap analysis (for large files 100K+)
```bash
# Check if file bytes match compiled bytecode bytes
wc -c /path/to/file.py
python3 -c "
import ast, sys
with open('/path/to/file.py') as f:
    src = f.read()
tree = ast.parse(src)
print(f'Compiled {len(src)} bytes of {len(src)} total')
"
```
A gap means Python stopped compiling early — duplicate definitions beyond the gap are INVISIBLE to the runtime.

### Step 5: Fix
1. Delete the duplicate (wrong) definition
2. Check call sites AND function signatures simultaneously:
   ```bash
   grep -n "function_name(" /path/to/file.py          # call sites
   grep -n "def function_name\|function_name.*=" /path/to/file.py  # signatures
   ```
   **Critical case**: the wrong function may accept a param (e.g. `override_k`) that the correct one doesn't. If callers pass it as a keyword arg, Python routes to the wrong function. Removing the wrong function means the call breaks — you must also remove the keyword arg from call sites AND from the function signature.
3. If a function signature has an unused param (e.g. `override_k: float = None`) that only the wrong duplicate used, remove it from the signature too.
4. Clear `.pyc` cache: `rm -f /path/to/__pycache__/module.cpython-*.pyc`
5. Verify compile: `python3 -m py_compile /path/to/file.py`
6. Verify import: `python3 -c "import module; print('OK')"`

### Step 6: Confirm no remaining duplicates
```bash
grep -n "def _function_name" /path/to/file.py
# Should return exactly ONE match
```

## Common gotcha: patch() "Found 2 matches"
When using `patch()` to fix duplicate code, if the old_string appears in two places:
- `patch() Found 2 matches` means you need MORE surrounding context to make it unique
- Add lines before/after the target section to disambiguate
- Never use `replace_all=True` on structural changes — it will corrupt the file

## Common gotcha: Dead code still compiles
A line like `tp_pct_val = 0.05` that is immediately overwritten by `tp_pct_val = 0.0` still passes `py_compile`. Always remove it when centralizing to constants.

## Key Lesson
Normal code review assumes one definition per function. When a bug "can't be found" despite source looking right, `grep` for all definitions immediately. The duplicate was completely invisible through AST analysis showing only 135110 of 141038 bytes compiled.
