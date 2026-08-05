---
name: signal-extraction-naming-pitfall-2026-05-11
description: "Bug B: Registry Name vs signal_type Mismatch — when extracting signals from signal_gen.py, all three (signal_type, source tag, registry name) must be renamed together atomically."
category: software-development
---

# Bug B: Registry Name vs signal_type Mismatch

**When adding a new signal to Hermes — applies to all signal extraction tasks.**

## The Bug

When extracting an inline signal from `signal_gen.py` into a standalone file under `signals/`:
- The `signal_type` written to the DB stays as-is
- The `source` tag stays as-is
- The registry `name` in `signals/__init__.py` is set independently

This creates three independent naming axes that can diverge. If they do:
1. signal_compactor can't route the signal correctly
2. SOURCE_BLACKLIST entries can't match the right signal
3. Hot-set source tags become ambiguous (can't tell which detection logic fired)
4. Kill-switch flags may reference the wrong signal

## The Fix

Rename all three atomically:

```python
# In signals/xxx.py (detection logic)
signal_type = 'xxx_mtf'                    # DB column value — must be unique across ALL signals
source = f'xxx_mtf-{dir_char}'              # unique per signal family, includes direction

# In signals/__init__.py (registry)
{'name': 'xxx_mtf', 'enabled': 'XXX_ENABLED', 'run': _xxx_mtf_run}

# In hermes_constants.py (blacklist comments)
# 'xxx_mtf+-', 'xxx_mtf-+'                  # update historical entries too
```

## Real Example (2026-05-11)

`hmacd` signal extracted from signal_gen.py as `signals/mtf_macd.py`:

| Attribute | Before | After |
|-----------|--------|-------|
| signal_type (DB) | `hmacd` | `hmacd_mtf` |
| source tag | `hmacd+` / `hmacd-` | `hmacd_mtf+` / `hmacd_mtf-` |
| registry name | `mtf_macd` | `hmacd_mtf` |
| hermes_constants blacklist | `hmacd+-/hmacd-+` | `hmacd_bare+-/hmacd_bare-+` |

`signals/hmacd.py` (pre-existing, separate signal) was already writing `signal_type='hmacd'` with source `hmacd+`/`hmacd-`. After fix: `hmacd_bare` vs `hmacd_mtf`. Both use same kill-switch flags (HMACD_ENABLED/PLUS/MINUS) — intentional since they're same signal family.

## What to Check After Any Signal Rename

```bash
# 1. Verify signal_type is unique across all signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT DISTINCT signal_type FROM signals ORDER BY signal_type;"

# 2. Verify source tags are unique per signal
grep "source = f'" signals/*.py

# 3. Verify registry names match signal_type
cd /root/.hermes/scripts && python3 -c "
from signals import SIGNAL_REGISTRY
for s in SIGNAL_REGISTRY:
    print(f\"{s['name']}: enabled={s['enabled']}\")
"

# 4. Verify no duplicate flag definitions
grep "XXX_ENABLED.*=.*True" hermes_constants.py | sort | uniq -d
```

## Related Bug Patterns

- **Bug #1 (Critical Bugs Reference):** Scanner returns only `int` (count), caller loops over ALL tokens. Fix: return `tuple[int, set[str]]`.
- This bug (Bug B) is a naming/architecture issue — different root cause but same class of "signals silently fail to route correctly."