# Python Gotcha: Call-Site / Signature Mismatch → Silent Failure

## Pattern

When you change a function's required arguments but forget to update all call sites,
Python does NOT raise an exception at call time if you pass fewer arguments than required.
Instead, it raises `TypeError: <func>() missing N required positional arguments` —
which WILL crash... unless the call is inside a bare `except Exception:` block that silently
swallows it.

**The dangerous case in Hermes:**
```python
# hyperliquid_exchange.py — function signature
def mirror_close(token: str, direction: str, exit_price: float = None) -> dict:
    ...

# brain.py — call site in rollback path (lines 513-521)
try:
    from hyperliquid_exchange import mirror_close
    mc = mirror_close(hype_token)   # ← WRONG: missing `direction`
    if mc and mc.get('success'):
        print(f"HL rollback succeeded")
    else:
        print(f"HL rollback returned: {mc}")  # ← prints False/NULL, no crash
except Exception as mc_err:
    print(f"HL rollback failed: {mc_err}")   # ← this WON'T catch TypeError from missing arg
```

**What happens:**
1. `mirror_close(hype_token)` → Python raises `TypeError: mirror_close() missing 1 required positional argument: 'direction'`
2. The `except Exception as mc_err:` DOES catch it → prints the error message
3. But the HL position stays open → orphan → guardian closes it

The error IS logged, but the rollback silently fails to actually close the HL position.
The caller has no way to distinguish "rollback succeeded" vs "rollback was never attempted."

## Detection

Look for any function with multiple required positional arguments, then grep call sites:
```bash
# Find functions with 2+ required positional args
grep -n "def mirror_close\|def .*(" hyperliquid_exchange.py | head -20

# For each, find all call sites and count arguments
grep -n "mirror_close(" brain.py hl-sync-guardian.py | head -20
```

## Prevention

When changing a function signature, always:
1. Change the signature
2. Search for all call sites with `grep -rn "func_name(" --include="*.py"`
3. Verify each call site passes the correct number of arguments

A type checker (mypy) would catch this at lint time. Consider adding `mypy` to the dev workflow.