# Silent ImportError Debug — Hermes `signal_schema.py` Pattern

**Date:** 2026-04-16
**Symptom:** A fix to a validation check appears correct in source code, but signals keep bypassing it.

## Problem

A `try/except ImportError: pass` silently bypassed ALL code in the `try` block — including critical security checks (blacklists). The exception was never logged, so it was invisible.

## Symptoms

- A fix to a validation check appeared correct in source code
- `import signal_schema; inspect.getsource()` showed the fix was there
- Direct calls to the function still bypassed the check
- Signals kept appearing despite the blocklist

## How to Diagnose (in order)

### Step 1: Verify the fix is actually in the loaded module

```python
import signal_schema
import inspect
src = inspect.getsource(signal_schema.add_signal)
print('Fix present:', 'any(bl in source' in src)
```

### Step 2: Check if the module is loaded from the right file

```python
print(inspect.getfile(signal_schema.add_signal))  # verify path
```

### Step 3: Inspect bytecode `co_names` to see what the function actually references

```python
print(signal_schema.add_signal.__code__.co_names)
# If you see 'ImportError' in co_names, there's likely a bare except somewhere
```

### Step 4: Use monkey-patching to trace execution

```python
_original = module.add_signal
def debug_add_signal(*args, **kwargs):
    print(f'[DEBUG] called with args={args}')
    result = _original(*args, **kwargs)
    print(f'[DEBUG] result={result}')
    return result
module.add_signal = debug_add_signal
```

### Step 5: Test with a direct call

```python
result = module.add_signal('TEST', 'LONG', 'type', 'pct-hermes+', confidence=65)
# If it returns an ID instead of None, something is bypassing the check
```

### Step 6: Find the actual exception

Add this INSIDE the except block temporarily:

```python
except ImportError as e:
    import traceback; traceback.print_exc()  # TEMP DEBUG
    pass  # original
```

## The Hermes `signal_schema.py` Bug (2026-04-16)

```python
# BROKEN — SOURCE_KILL_SWITCH doesn't exist in hermes_constants.py
try:
    from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST, SIGNAL_SOURCE_BLACKLIST, SOURCE_KILL_SWITCH
    if direction.upper() == 'SHORT' and token.upper() in SHORT_BLACKLIST: return None
    if direction.upper() == 'LONG' and token.upper() in LONG_BLACKLIST: return None
    if any(bl in source for bl in SIGNAL_SOURCE_BLACKLIST): return None  # NEVER REACHED
    for blocked_prefix in SOURCE_KILL_SWITCH:  # raises NameError → ImportError
        if source.startswith(blocked_prefix): return None
except ImportError:
    pass  # ALL checks bypassed silently!!
```

## Prevention Rules

1. **Never use bare `except ImportError: pass`** — always log or re-raise
2. **Test imports in isolation first**: `from module import NAME`
3. **If a check appears correct but doesn't work**: check bytecode (`__code__.co_names`) for `ImportError`
4. **Clear `.pyc` cache** when patching: `rm -f scripts/__pycache__/*.pyc`
5. **Restart processes** after patching — Python caches imports in memory

## Related Files

- `/root/.hermes/scripts/signal_schema.py` — `add_signal()` function (lines ~385-415)
- `/root/.hermes/scripts/hermes_constants.py` — `SIGNAL_SOURCE_BLACKLIST`, `SOURCE_KILL_SWITCH` (doesn't exist)

## See Also

- `accel-300-hermes-constants-import-gap-jun-2026.md` — related import-gap class of bugs
- `signal-runner-rs-silent-skip-2026-05-08.md` — similar silent-skip pattern in a different module
