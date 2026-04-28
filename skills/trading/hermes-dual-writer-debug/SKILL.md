---
name: hermes-dual-writer-debug
description: Debug data corruption/flashing in Hermes when multiple scripts write to the same output file. Diagnose and fix dual-writer conflicts in the Hermes pipeline.
category: trading
---

# Hermes Dual-Writer Debug Pattern

**Symptom:** Data in `trades.json` or `signals.json` flashes between complete and partial, or hot-set disappears from dashboard.

**Root Cause (common):** Two or more pipeline scripts writing to the same output file. One script may have a broken DB connection, producing partial data, which then overwrites the complete data from the working script.

## Step 1: Identify All Writers

Find every script that touches the target file:

```bash
# Find all writers to a file
grep -r "trades.json\|signals.json\|hotset.json" /root/.hermes/scripts/ --include="*.py" -l
grep -r "trades.json\|signals.json\|hotset.json" /root/hermes-v3/ --include="*.py" -l
grep -r "trades.json" /root/.hermes/scripts/run_pipeline.py  # check STEPS_EVERY_MIN
```

## Step 2: Determine Which Writer Is Used by Pipeline

```bash
# Check systemd service working directory
systemctl cat hermes-pipeline.service | grep WorkingDirectory
# Pipeline uses files in that WorkingDirectory, NOT the v3 git export
```

**Critical insight:** The pipeline's systemd service sets `WorkingDirectory=/root/.hermes/scripts/`. Scripts in `/root/hermes-v3/hermes-export-v3/` are a **git export copy** — they may run independently but are NOT the pipeline's execution path.

## Step 3: Check DB Connection in Each Writer

The most common failure mode:
- Script A uses `host=localhost` (TCP) → sometimes fails with "connection refused" → writes partial/empty data
- Script B uses `host=/var/run/postgresql` (Unix socket) → works reliably → writes complete data
- Script A's partial data overwrites Script B's complete data → data flashing

```python
# Test each writer's DB connection
import psycopg2
try:
    db = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='brain123')
    print("Unix socket: OK")
except Exception as e:
    print(f"Unix socket FAIL: {e}")

try:
    db = psycopg2.connect(host='localhost', database='brain', user='postgres', password='brain123', port=5432)
    print("TCP localhost: OK")
except Exception as e:
    print(f"TCP localhost FAIL: {e}")
```

## Step 4: Verify Which Script Actually Updates the File

```bash
# Check timestamps — which script ran most recently
ls -la /var/www/hermes/data/trades.json
stat /var/www/hermes/data/trades.json

# Monitor for 2 minutes — which script touches it
while true; do stat -c "%Y %n" /var/www/hermes/data/trades.json; sleep 10; done
```

## Step 5: Fix — Single Writer

1. Identify the reliable writer (usually the one with Unix socket)
2. Identify the broken writer (usually the one with TCP localhost)
3. Fix the broken writer's DB connection (change `host=localhost` → `host=/var/run/postgresql`)
4. **OR** remove the broken writer from the pipeline steps in `run_pipeline.py` (`STEPS_EVERY_MIN` or `STEPS_EVERY_5_MIN`)

**Hot-set Dual-Writer Pattern (2026-04-27)**

**Symptom**: Hot-set tokens wildly fluctuate every cycle, or silent data corruption between compaction cycles.

**Root Cause**: Multiple scripts write `/var/www/hermes/data/hotset.json` using DIFFERENT LOCK MECHANISMS — the locks don't protect each other.

**The Lock Mismatch Bug (critical)**:
| Writer | Lock used | Lock file path |
|--------|-----------|----------------|
| `signal_compactor.py` | `FileLock('hotset_json')` | `/root/.hermes/locks/hotset_json.lock` |
| `ai_decider.py` (if active) | `FileLock('hotset_json')` | `/root/.hermes/locks/hotset_json.lock` |
| `breakout_engine.py` | `fcntl.flock` | `/var/www/hermes/data/hotset.json.lock` |

`FileLock` deletes the lockfile before acquiring (line 52-56 of `hermes_file_lock.py`), so `/root/.hermes/locks/hotset_json.lock` and `/var/www/hermes/data/hotset.json.lock` are **completely independent** — no mutual exclusion between them. If both run simultaneously, both can write to `hotset.json` at the same time.

**Detect**:
```bash
# Confirm lock mismatch — these are different files
ls -la /root/.hermes/locks/hotset_json.lock
ls -la /var/www/hermes/data/hotset.json.lock

# Find all writers to hotset.json
grep -rn "hotset.json" /root/.hermes/scripts/*.py -n | grep -i "write\|dump\|open.*w"

# Check which scripts are actually running
systemctl list-timers --all | grep -E "signal-compactor|pipeline"
journalctl -u hermes-signal-compactor.service --no-pager -n 10

# Monitor hotset.json mtime to see write frequency
stat /var/www/hermes/data/hotset.json | grep Modify

# Check if breakout_engine is actually writing (usually finds 0 signals)
grep -n "Wrote\|dry=" /var/www/hermes/logs/breakout_engine.log | tail -10
```

**Confirmed active writers** (as of 2026-04-27):
1. `signal_compactor.py` — systemd timer every 1 min, uses `FileLock('hotset_json')`, atomic write via `os.replace(tmp_path, HOTSET_FILE)` ✓
2. `breakout_engine.py` — runs as pipeline step every 2 min, uses `FileLock('hotset_json')` at line 479 (same lock as signal_compactor) ✓ — properly serialized

**Fixed (2026-04-28)**:
- `signal_compactor.py` NO LONGER writes signals.json — race condition eliminated. hermes-trades-api.py is the sole writer of signals.json.
- `ai_decider.py` is DEFUNCT — no systemd timer, not running, dead code only.

**Fix**: Change breakout_engine to use `FileLock('hotset_json')` instead of its own fcntl lock:
```python
# In breakout_engine.py:
# OLD (line ~478-484):
#   lock_fd = open(HOTSET_LOCK, 'w')
#   fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
# NEW:
from hermes_file_lock import FileLock
# ... then replace the fcntl block with:
with FileLock('hotset_json'):
    # write to hotset.json
```

Also verify ai_decider.py is truly defunct for hotset writes — it has `FileLock('hotset_json')` at line 1856 which WOULD mutually exclude with signal_compactor if both were active. Check if it's being called.
## signals.json Dual-Writer Race (2026-04-28) — FIXED

**Symptom**: Hot-set in signals.html fluctuates wildly between cycles. `approved` tab shows different tokens than hot-set tab. Pending count stayed at 113 for over 30 minutes.

**Root Cause**: `signals.json` was written by TWO scripts at overlapping times:
1. `signal_compactor.py` (every 1 min) → called `_enrich_and_write_signals()` → wrote signals.json with enriched hot_set
2. `hermes-trades-api.py` (every 1 min) → `write_signals()` → rebuilt signals.json from DB query → overwrote signal_compactor's write

The actual hot-set writer is `signal_compactor` only. `signals.json` is a derived view built by `hermes-trades-api`.

**Fix applied (2026-04-28)**:
- Removed `_enrich_and_write_signals()` call from `signal_compactor.py` (lines ~963-971). Comment added: "REMOVED (2026-04-28): signal_compactor no longer writes signals.json."
- `hermes-trades-api.py` is now the SOLE writer of signals.json — it rebuilds from hotset.json every cycle.
- `_enrich_and_write_signals()` exists in signal_compactor.py as dead code (never called). Safe to leave.

**Also fixed (2026-04-28)**:
- `expire_pending_signals()` in signal_schema.py updated: now a safety-net only (60-min PENDING hard cap, 5-min APPROVED hard cap). Primary expiry is handled by signal_compactor Step 13.
- signals.html: Added EXPIRED tab between EXECUTED and REJECTED. Added `.decision-expired` CSS.

## Stale Hot-set Fallback Pattern

When `hotset.json` (written by `ai_decider`) is stale >20 min, the dashboard shows empty hot-set.

Fix: in the API script (`hermes-trades-api.py`), when `_get_hotset_from_file()` returns empty/stale, call `_build_hotset_from_db()` directly as fallback.

```python
# In hermes-trades-api.py
hotset = _get_hotset_from_file()
if not hotset or (time.time() - hotset.get('_timestamp', 0)) > 1200:
    hotset = _build_hotset_from_db()
```

## Key Files

- `/root/.hermes/scripts/signal_compactor.py` — **primary hot-set writer** (systemd timer, every 5 min)
- `/root/.hermes/scripts/ai_decider.py` — **ALSO writes hotset.json** (line 1857) — bug: should be disabled
- `/root/.hermes/scripts/breakout_engine.py` — **ALSO writes hotset.json** (line 544) — bug: should be disabled
- `/root/.hermes/scripts/decider_run.py` — calls ai_decider.py
- `/root/.hermes/scripts/run_pipeline.py` — controls pipeline steps, runs breakout_engine every 60 min
- `/etc/systemd/system/hermes-signal-compactor.timer` — compactor timer (BUG: fires every 1 min, should be 5 min)
- `/var/www/hermes/data/hotset.json` — **written by 3 scripts** (dual-writer bug)
- `/root/.hermes/data/signals_hermes_runtime.db` — signal DB
- `/root/.hermes/logs/signal-compactor.log` — compactor diagnostic log
- `/root/.hermes/logs/pipeline.log` — pipeline log
