---
name: hermes-signature-change-audit
description: Audit all callers before changing a function signature in Hermes core infrastructure, and verify no silent pipeline failures afterward. Use when changing any shared function in signal_schema.py, signal_compactor.py, or any module called by pipeline scripts.
category: trading
author: T
created: 2026-04-28
---

# Hermes Function Signature Change Audit

## When to Use

When changing the signature (args, defaults, or return value) of ANY function that may be called by multiple pipeline scripts:

- `signal_schema.py` functions (`expire_pending_signals`, `add_signal`, etc.)
- `signal_compactor.py` functions
- `paths.py` constants
- `hermes_constants.py` constants
- Any shared utility used by multiple scripts in the pipeline

**Trigger phrase:** "changing signature", "updating function", "changing the args", "updating expire_pending", "modifying shared function"

## Why This Matters

Hermes is a multi-script system with timers that run independently:
- `hermes-pipeline.timer` → `run_pipeline.py` → `signal_gen`, `decider_run`, `position_manager`, `hermes-trades-api`
- `hermes-signal-compactor.timer` → `signal_compactor.py`
- `hermes-pipeline.timer` also runs `breakout_engine`

When a shared function's signature changes, one caller may crash. If that caller catches the exception and continues, the pipeline produces **zero signals silently** — PENDING goes to 0, hot-set empties, and there's no visible error in the UI. You only discover it when signals stop flowing entirely.

## Audit Procedure

### Step 1: Find ALL callers BEFORE changing anything

```bash
grep -rn "function_name" /root/.hermes/scripts/*.py
```

For example, before changing `expire_pending_signals`:
```bash
grep -rn "expire_pending_signals" /root/.hermes/scripts/
```

### Step 2: Check each caller

For each file that imports or calls the function:
1. Read the exact call site
2. Note the exact arguments passed
3. Check if the new signature is backward-compatible with the old call

### Step 3: Update ALL callers before the change goes live

If the old call was `func(minutes=60)` and you change to `func()`, you must update ALL callers first.

### Step 4: Verify pipeline recovery

After the change, verify:
```bash
# Check PENDING signals are flowing
python3 -c "
import sqlite3; conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db'); c = conn.cursor()
c.execute(\"SELECT COUNT(*) FROM signals WHERE decision='PENDING' AND executed=0\")
print('PENDING:', c.fetchone()[0])
c.execute(\"SELECT token, direction, created_at FROM signals WHERE decision='PENDING' ORDER BY created_at DESC LIMIT 5\")
for r in c.fetchall(): print(' ', r)
"

# Check hotset.json has entries
cat /var/www/hermes/data/hotset.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('hotset:', len(d['hotset']), 'entries')"

# Check pipeline journal for errors
journalctl -u hermes-pipeline.service --since "5 minutes ago" | grep -i "err\|traceback\|error"
```

### Step 5: Check the signal_gen crash pattern

The signature mismatch crash often shows up as:
```
TypeError: function_name() got an unexpected keyword argument 'X'
```

This goes to stderr/exception log but the pipeline catches it and continues. Check:
```bash
grep -i "TypeError\|NameError" /var/www/hermes/logs/pipeline.log | tail -5
```

## Key Functions with Multiple Callers (as of 2026-04-28)

| Function | Callers |
|----------|---------|
| `expire_pending_signals()` | signal_gen.py, signal_schema.py (unused) |
| `add_signal()` | Many signal generators (gap300, ema9_sma20, etc.) |
| `is_loss_cooldown_active()` | signal_compactor.py, decider_run.py, _filter_safe_prev_hotset |
| `get_regime_15m()` | signal_compactor.py, decider_run.py |

## Common Silent Failure Patterns

1. **TypeError from signature mismatch** — caught by `except Exception`, pipeline continues with 0 signals
2. **KeyError from dict field rename** — caught by `.get()`, returns None silently  
3. **ImportError from module rename** — caught by `except ImportError`, falls back to None
4. **FileLock timeout** — raises exception, pipeline continues without that step

## Post-Change Checklist

- [ ] All callers updated to match new signature
- [ ] `python3 -c "from signal_schema import ..."` — imports cleanly
- [ ] PENDING signals > 0 in runtime DB
- [ ] hotset.json has entries
- [ ] No TypeError/NameError in recent pipeline logs
- [ ] `signal_gen.py` runs for >1 second without crashing
