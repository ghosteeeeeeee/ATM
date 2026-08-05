---
name: python-nested-function-scoping-gotcha
description: Python closure scoping bug in nested functions — variables assigned inside nested functions shadow outer scope names, causing UnboundLocalError when referenced before the nested function is called.
category: software-development
tags: [python, scoping, closures, bugs, hermes]
---

# Python Nested Function Scoping Gotcha

## The Bug

In a nested function defined inside another function, **any assignment to a variable name anywhere in the outer function makes that name local throughout the entire outer function** — even if the assignment happens in the nested function AFTER the reference point.

```python
def outer():
    x = 10
    
    def inner():
        # This assignment makes 'x' a local throughout `outer`
        # even though it appears after the reference below
        x = 20  # <-- this line is the culprit
        return x + 5
    
    # BUG: References `x` here, but Python already thinks `x` is a 
    # local variable in `outer` (because of the assignment in `inner`)
    # Error: UnboundLocalError: cannot access local variable 'x'
    need = x + inner()
```

## Symptoms

- `UnboundLocalError: cannot access local variable 'slow'` (or any name)
- Error points to a line that reads a variable, not writes it
- The variable IS defined in the outer scope
- The error happens even though the read happens BEFORE the nested function is called
- Code appears to work when the nested function is NOT called (e.g., guard clause before execution)

## The Root Cause

Python compiles the outer function and sees the assignment `x = 20` inside `inner`. Python marks `x` as a **local variable of `outer`** at bytecode level. When the reference to `x` executes at runtime, Python looks up `x` in the local scope — finds it marked as local but unassigned — and raises `UnboundLocalError`.

## How to Detect

1. Search for nested `def` inside other functions
2. Check if the inner function assigns to any variable name that also appears in the outer function
3. Check references to those names in the outer function BEFORE the nested function is defined

```bash
grep -n "def " scripts/signal_gen.py | head -30
# Then manually inspect nesting
```

## The Fix

1. **Pass as parameter:** Move the variable fetch inside the nested function as a parameter
2. **Use default argument:** `def inner(x=x):` to capture outer scope value at definition time
3. **Avoid reassignment in nested scope:** Fetch the value before defining the nested function
4. **Rename to avoid shadowing:** Use distinct names like `_slow`/`slow_` to avoid accidental shadowing

## Real-World Example from Hermes

**File:** `signal_gen.py` `_run_mtf_macd_signals()` function

```python
# BROKEN: slow/sig assigned INSIDE _macd_crossover, but referenced HERE
need = _slow + _sig + 5  # UnboundLocalError: cannot access local variable 'slow'

def _macd_crossover():
    ...
    slow, sig = params[...]  # This makes 'slow'/'sig' locals throughout outer function
```

**Fix applied:** Moved `params = get_macd_params(token)` inside `_macd_crossover` and used distinct parameter names `_slow`, `_sig` as defaults.

## Verification

```python
# Test that the nested function can reference outer scope variables
def outer():
    values = [1, 2, 3]
    def inner():
        return sum(values)  # OK: reading, not writing
    return inner()

# Anti-pattern that breaks:
def outer_broken():
    x = 10
    def inner():
        x = 20  # Makes x local throughout outer
        return x
    return x + inner()  # UnboundLocalError
```

## Pitfalls

- This bug is invisible to linters (not a syntax error)
- It only manifests at runtime when the code path actually executes
- Commenting out the nested function call can make it "seem fixed"
- The error message is confusing: "cannot access local variable" when you're clearly reading from outer scope
