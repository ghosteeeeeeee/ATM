---
name: hermes-signal-source-audit
description: Audit Hermes signal source names against SIGNAL_SOURCE_BLACKLIST — detect when signal scripts emit source names that are blocked, causing silent signal death. Also audit undefined constants in signal scripts.
category: trading
---

# Hermes Signal Source Name Audit

**When to use**: After adding any new signal source, after modifying SIGNAL_SOURCE_BLACKLIST, or when signals appear to generate but never reach the hot-set.

**Class**: Recurring bug pattern — signal script emits a source name that is (or becomes) in SIGNAL_SOURCE_BLACKLIST. Signals generate and write to DB but are silently blocked at compaction. Has occurred 6+ times.

**Threat model — 3 ways signals bypass the blacklist:**
1. **Substring bypass**: `'pct-hermes'` is blocked but `'pct-hermes+'` passes (substring match, not comma-component match)
2. **Missing block**: `'gap-300-'` not in blacklist but direction logic is wrong → fires wrong direction LONG when it should SHORT
3. **SyntaxError silent crash**: `accel_300_signals.py` has an em dash in docstring → whole script unimportable → signals never fire

## The Pattern

1. Signal script defines a `SOURCE_*` constant (e.g., `SOURCE_LONG = 'gap-300-'`)
2. The source name gets added to `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py` (intentionally or as a collateral block)
3. Signals generate and write to DB — no error
4. `signal_compactor.py` line 679 filters them out: `any(p in SIGNAL_SOURCE_BLACKLIST for p in source_parts)`
5. Signals never reach hot-set — silent, total failure

## Audit Checklist

### Step 0 (MUST DO FIRST): Compile check all signal scripts
```bash
cd /root/.hermes/scripts && python3 -c "
files = [list of signal scripts]
ok, fail = [], []
for f in files:
    try:
        import py_compile
        py_compile.compile(f, doraise=True)
        ok.append(f)
    except SyntaxError as e:
        fail.append((f, str(e)[:100]))
print(f'OK: {len(ok)}, FAIL: {len(fail)}')
for f, e in fail: print(f'  FAIL: {f}: {e}')
"
```
A SyntaxError in any signal script means `from X import Y` in signal_gen.run() will crash the pipeline at that point.

### Step 0b: Substring bypass check
```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from hermes_constants import SIGNAL_SOURCE_BLACKLIST
# Any blocked entry that is a prefix of an unblocked potential source
# e.g. 'pct-hermes' blocks 'pct-hermes+' via substring, not comma-component
all_potential = set()
# Known suffixes that pass through the comma-component check
potential_suffixes = ['+', '-', 'long', 'short']
for blocked in SIGNAL_SOURCE_BLACKLIST:
    for suffix in potential_suffixes:
        candidate = blocked + suffix
        if candidate not in SIGNAL_SOURCE_BLACKLIST:
            print(f"POTENTIAL BYPASS: '{blocked}' + '{suffix}' = '{candidate}' not in blacklist")
```

### Step 1: List all SOURCE_* constants in signal scripts

```bash
grep -rn "^[[:space:]]*SOURCE_\|^[[:space:]]*SOURCE_LONG\|^[[:space:]]*SOURCE_SHORT" \
  /root/.hermes/scripts/*.py | grep -v ".pyc"
```

### Step 2: Extract all emitted source names from signals DB (last 24h)

```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT DISTINCT source FROM signals WHERE created_at > datetime('now','-24 hours');"
```

### Step 3: Cross-reference against SIGNAL_SOURCE_BLACKLIST

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from hermes_constants import SIGNAL_SOURCE_BLACKLIST

# All sources from Step 2
sources = [...]  # paste from Step 2

blocked = []
for s in sources:
    parts = [p.strip() for p in s.split(',')]
    for p in parts:
        if p in SIGNAL_SOURCE_BLACKLIST:
            blocked.append(f"{s} → blocked part '{p}'")

print(f"BLOCKED: {blocked}")
```

### Step 4: Check signal scripts for undefined constant references

Signal scripts often import from `hermes_constants` but may reference constants they never imported. Check for:

```bash
# Find all hermes_constants imports in signal scripts
grep -l "from hermes_constants import\|from hermes_constants import \*" \
  /root/.hermes/scripts/*signals*.py

# For each signal script, check which constants are USED but not imported
python3 -c "
import ast, sys
with open('/root/.hermes/scripts/counter_flip_signal.py') as f:
    src = f.read()
tree = ast.parse(src)
# Find all Name nodes (variable references)
names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
# Find imported names
imports = set()
for n in tree.body:
    if isinstance(n, ast.ImportFrom) and n.module == 'hermes_constants':
        imports.update(a.name for a in n.names)
# Find hermes_constants usage (module.attr pattern)
const_refs = set()
for n in ast.walk(tree):
    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'hermes_constants':
        const_refs.add(n.attr)
print('Referenced but not imported:', const_refs - imports)
"
```

### Step 5: Verify live signals in DB

```bash
# Are any blocked sources actually writing signals?
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT source, COUNT(*) FROM signals 
   WHERE created_at > datetime('now','-1 hours') 
   GROUP BY source 
   ORDER BY COUNT(*) DESC LIMIT 20;"
```

## Bugs Found in This Session (2026-04-29)

### Bug 1: pct-hermes+ substring bypass
- `'pct-hermes'` in blacklist (exact match) but `'pct-hermes+'` passes
- `validate_source('pct-hermes+')` returns `'pct-hermes+'` (not blocked)
- The blacklist check at `signal_schema.py:405` does `source in SIGNAL_SOURCE_BLACKLIST` (exact) 
  AND `component in SIGNAL_SOURCE_BLACKLIST` for comma-separated parts
- `'pct-hermes+'` is ONE part (no comma), so exact match fails → substring match on `'pct-hermes'` in `'pct-hermes+'` does NOT trigger component check
- **Fix**: Add `'pct-hermes+'` to `SIGNAL_SOURCE_BLACKLIST`

### Bug 2: gap-300- direction naming flip
- `gap300_signals.py` lines 40-41: `SOURCE_LONG = 'gap-300-'` but this fires LONG when EMA < SMA (bearish)
- Docstring says LONG = gap widens bullish (EMA > SMA) → should use `gap-300+`  
- Comment says "flipped 2026-04-28" but the direction assignment at line 290: `direction = 'LONG' if cur_raw > 0` → raw > 0 means EMA > SMA → bullish → should emit `gap-300+` NOT `gap-300-`
- **Fix**: Swap SOURCE_LONG and SOURCE_SHORT at lines 40-41

### Bug 3: accel_300_signals.py SyntaxError
- Line 24: docstring contains em dash (U+2014) which Python's tokenizer rejects
- `signal_gen.py:2617` imports this with `from accel_300_signals import scan_accel_300_signals`
- Import happens inside `run()` → would crash the entire pipeline at that point
- **Fix**: Replace `—` with `-` in line 24 docstring

## Common Blocked Source Names (2026-04-29)

| Source | Status | Notes |
|--------|--------|-------|
| `gap-300+` | BLOCKED ✓ | Correctly blocked — would fire wrong direction |
| `gap-300-` | NOT BLOCKED — BUG | Direction wrong (fires LONG when bearish); ALSO needs SOURCE_* swap |
| `gap300-5m+`, `gap300-5m-` | BLOCKED ✓ | gap300_5m_signals.py emits these; blocked |
| `pct-hermes` | BLOCKED ✓ | Exact match works |
| `pct-hermes+` | NOT BLOCKED — BUG | Substring bypass: `'pct-hermes'` exact match doesn't cover `'pct-hermes+'` |
| `accel_300_signals` | NOT IN BLACKLIST | SyntaxError crash prevents any signals; broken docstring |
| `hzscore+`, `hzscore-` | BLOCKED ✓ | Intentionally blocked; directional variant wrong direction |
| `pattern_scanner` | BLOCKED ✓ | Intentionally blocked; too many false positives |
| `CASCADE_FLIP_ENABLED` | Undefined in counter_flip_signal.py | Not imported — NameError crash (may be caught by caller) |

## Fix Priority (updated 2026-04-29)

1. **CRITICAL**: Any source with recent signal COUNT > 0 but no hot-set entries → source name is blocked or direction is wrong
2. **CRITICAL**: Any signal script with SyntaxError → add Step 0 compile check
3. **HIGH**: Any source in DB with decision=EXECUTED that is NOT in blacklist → potential pct-hermes+ style substring bypass
4. **MEDIUM**: Any source in SIGNAL_SOURCE_BLACKLIST with recent EXECUTED signals → the block isn't working (check substring bypass)

## Key Files

- Signal blacklist: `/root/.hermes/scripts/hermes_constants.py` — `SIGNAL_SOURCE_BLACKLIST` set
- Blocker enforcement: `/root/.hermes/scripts/signal_compactor.py` — line 679
- Signal DB: `/root/.hermes/data/signals_hermes_runtime.db`
- Hot-set: `/var/www/hermes/data/hotset.json`
