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

- `/root/.hermes/scripts/hermes-trades-api.py` — **primary pipeline script** (605 lines)
- `/root/.hermes/scripts/run_pipeline.py` — controls which scripts run in pipeline
- `/root/hermes-v3/hermes-export-v3/` — git export copy, NOT pipeline execution path
- `/var/www/hermes/data/trades.json` — owned exclusively by hermes-trades-api.py
- `/var/www/hermes/data/hotset.json` — written by ai_decider (may be stale)
