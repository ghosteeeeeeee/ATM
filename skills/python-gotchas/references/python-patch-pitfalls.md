---
name: python-patch-pitfalls
description: Pitfalls when patching Python source files — indentation nesting of try/except, scope references in new blocks, and replace-all edge cases.
category: software-development
tags: [python, patching, bugs, hermmes]
author: Hermes Agent
created: 2026-04-22
---

# Python Patch Pitfalls

Common bugs introduced when using `patch()` or similar tools to edit Python source files.

## Pitfall 1: Indentation Nesting with `except:`

**Problem**: Replacing `except:` with `except Exception:` in code that has nested `try:` blocks can break nesting.

**Wrong** — `except` ends up at the wrong indentation level:
```python
# BEFORE (except at wrong indent — under `with`, not `try`):
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
        except Exception:   # ← was `except:`, now wrong indent
            pass

# AFTER (correct — `except` at same level as `try`):
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:        # ← correct indent
        pass
```

**How to detect**: Run `python3 -m py_compile` immediately after every patch.

**Rule**: Always read 10+ lines around the target before patching. Look for nested `try:` blocks.

---

## Pitfall 2: Scope References in New Patch Blocks

**Problem**: Adding a new `continue` or `break` block via patch that references a variable from an inner scope that isn't accessible at that point.

```python
# BROKEN — added this block:
if score <= 0:
    continue  # score comes from _score_signal()
    # but `staleness_mult` was computed inside _score_signal()
    # and is NOT in scope here — would raise NameError
    log(f"staleness_mult={staleness_mult:.2f}")

# FIXED — use only loop-scope variables:
if score <= 0:
    continue  # score is in scope
    log(f"age_h={age_h:.2f}")  # age_h was set in this loop iteration
```

**Rule**: When adding a new block inside a loop via patch, use only variables that are bound in that loop's body before the new block.

---

## Pitfall 3: `replace_all=true` in Multiple Contexts

**Problem**: Using `replace_all=true` when the same pattern appears in different contexts (e.g., two different functions with the same variable name).

```python
# Replacing `cr = row[8]` in the wrong place if it appears in multiple spots
# Use full context string (3+ lines before/after) to make unique
```

**Rule**: Use unique full-context strings when the short pattern appears more than once. Avoid `replace_all=true` unless you're certain the pattern is unique.

---

## Pitfall 4: Replacing Strings That Span Multiple Scopes

**Problem**: A simple string match might match a different occurrence than intended if the same code appears in multiple places with slightly different context.

**Rule**: When patching, include as much surrounding context as needed to uniquely identify the target. Err on the side of too much context.

---

## Verification Always

```bash
python3 -m py_compile /path/to/file.py && echo "SYNTAX OK"
```

Run immediately after every patch. Never skip — silent indentation errors are common and only caught at runtime.
