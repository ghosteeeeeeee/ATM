# Multi-File Import Refactors in Hermes

Pattern: When moving constants from `paths.py` → `hermes_constants.py`, a file that imports those constants from `hermes_constants` will fail at module load time if the constants don't exist yet. This crash propagates to any file that imports the broken file.

## Failure Chain Example

File A imports: `from hermes_constants import RUNTIME_DB, LOSS_COOLDOWN_FILE`
File A also imported by File B (via `import cascade_flip`)
→ cascade_flip fails to load
→ position_manager fails to load (imports cascade_flip)
→ pipeline step crashes

## Safe Sequence

1. **Verify constants exist in hermes_constants FIRST** — add missing ones before patching import lines
2. **Compile-check every affected file** before declaring success: `python3 -m py_compile file.py`
3. **Test the import chain**: `cd /root/.hermes/scripts && python3 -c "from cascade_flip import ..."`
4. **Check all files that transitively import the refactored module**:
   ```
   grep -rn "from cascade_flip\|import cascade_flip" /root/.hermes/scripts/*.py
   grep -rn "from position_manager\|import position_manager" /root/.hermes/scripts/*.py
   ```

## What to Add to hermes_constants.py Before Patching Imports

When moving path constants from paths.py to hermes_constants.py, these are the minimum required:

```python
import os

# Base directories (mirrored from paths.py)
HERMES_DATA = os.environ.get('HERMES_DATA_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))
WWW_DATA = os.environ.get('WWW_DATA_DIR', '/var/www/hermes/data')

# Derived: DB paths
RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')

# Derived: JSON / state files
LOSS_COOLDOWN_FILE = os.path.join(HERMES_DATA, 'loss_cooldowns.json')
FLIP_COUNTS_FILE = os.path.join(WWW_DATA, 'flip_counts.json')
```

## Checklist Before Any Import Refactor

- [ ] Verify target constant exists in hermes_constants (grep the file first)
- [ ] Add missing constants to hermes_constants if needed
- [ ] Compile-check: `python3 -m py_compile <file>.py`
- [ ] Import-chain test: `python3 -c "import <module>"`
- [ ] Check transitive importers (grep for them)
- [ ] Run pipeline validation