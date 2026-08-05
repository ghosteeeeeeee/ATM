---
name: signal-blacklist-debugging
description: Debug why signal sources added to SIGNAL_SOURCE_BLACKLIST still appear in the signals DB. Systematic approach for Hermes signal_gen system.
---
# Signal Blacklist Debugging — Hermes

## Context
When a signal source (e.g. `pct-hermes+`) is added to `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py` but signals with that source still appear in the signals DB, here's the systematic debugging approach and root causes encountered.

## Debugging Steps

### Step 1: Verify the blacklist check code is correct
Check `signal_schema.py` `add_signal()` function — the blacklist check must compare the `source` field (e.g. `'hzscore,pct-hermes+'`) against the blacklist, NOT the `signal_type` field (e.g. `'percentile_rank'`). These are different fields.

```python
# WRONG — checks signal_type
if signal_type in SIGNAL_SOURCE_BLACKLIST:

# CORRECT — checks source field  
if any(bl in source for bl in SIGNAL_SOURCE_BLACKLIST):
```

### Step 2: Check for silently swallowed ImportError
If the `try/except ImportError: pass` pattern is used around the blacklist check, ANY import error (including a missing name like `SOURCE_KILL_SWITCH`) will silently bypass ALL blacklist checks.

Fix: Remove non-existent imports, or narrow the except clause to only catch the specific import you expect.

### Step 3: Clear .pyc cache
Python caches .pyc files. If you patch a .py file, the running process may still use the old cached bytecode. Always clear cache after patching:

```bash
rm -f /root/.hermes/scripts/__pycache__/signal_schema.cpython-312.pyc
```

### Step 4: Kill stale running processes
The pipeline processes load modules at startup. If you patch a module and the process was started before the patch, it has OLD code in memory. Find and kill all pipeline processes:

```bash
pkill -f "signal_gen.py"
pkill -f "run_pipeline.py"
```

Then verify no stale processes remain before restarting.

### Step 5: The merge path bypasses blacklist
When `add_signal()` finds an existing PENDING signal for the same token+direction, it MERGES the new source into the existing one. The blacklist check fires for the NEW signal's source, but the merged result (line ~461) writes `merged_sources` directly without re-checking blacklist. This means:
- Old signal with `source='hzscore'` (blacklisted but written before fix)
- New signal with `source='mtf_macd'` (valid)
- Merge writes `source='hzscore,mtf_macd'` — hzscore slips through

Fix: Purge all signals from DB after fixing the blacklist, or add blacklist re-check in the merge path.

### Step 6: Check for invalid source strings
`hmacd+-` appearing in the DB means some code is writing a source string that doesn't follow the naming convention (`hmacd+` or `hmacd-`, not `hmacd+-`). This is a source generation bug — find and fix the generator, then add the invalid source to blacklist.

## Common Root Causes (in order of discovery frequency)
1. Wrong field checked (`signal_type` vs `source`)
2. ImportError silently swallowing the check block
3. Stale .pyc cache
4. Running processes with old code
5. Merge path bypassing blacklist
6. Invalid source string generation

## Files Involved
- `hermes_constants.py` — `SIGNAL_SOURCE_BLACKLIST` definition
- `signal_schema.py` — `add_signal()` blacklist check logic
- `signal_gen.py` — generates signals via `add_signal()`
- `pattern_scanner.py` — generates signals via `add_signal()`
- `hotset.json` — cached signal hot-set

## Test After Fix
```python
from signal_schema import add_signal
# Should return None (blocked)
assert add_signal('TEST', 'LONG', 'percentile_rank', 'pct-hermes+', confidence=65, value=75, price=1.0) is None
# Should succeed
assert add_signal('TEST2', 'LONG', 'mtf_macd', 'mtf_macd', confidence=80, value=0.5, price=1.0) is not None
```
