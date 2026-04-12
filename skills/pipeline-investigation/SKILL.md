---
name: pipeline-investigation
description: Investigative approach when pipeline data sources are empty, missing, or unexpected. Use when standard queries return no data — discover what's actually there and adapt.
category: trading
author: Hermes
created: 2026-04-12
---

# Pipeline Investigation

Use when a pipeline review or data audit hits empty data sources. The key insight: **empty is a finding, not a stop sign**.

## When to Use

- Standard signals DB returns 0 rows
- Expected tables don't exist
- Data in a different location than documented
- Need to pivot approach mid-investigation

## Methodology

### Step 1 — Verify the Right File

```
# Check all SQLite DBs in data directory by mtime and size
find /root/.hermes/data -name "*.db" -exec ls -la {} \;

# Check if the "signals" DB is actually signals or something else
sqlite3 <path> ".tables"
sqlite3 <path> "SELECT COUNT(*) FROM signals" 2>/dev/null

# Check PostgreSQL tables
psql brain -U postgres -h /var/run/postgresql -c "\dt"
```

### Step 2 — Probe for Active Data

```
# Is predictions.db active? Check most recent entry
sqlite3 /root/.hermes/data/predictions.db "SELECT MAX(created_at) FROM predictions"

# Check mtime of all data files — newest = most active
ls -lat /root/.hermes/data/*.db /root/.hermes/data/*.json | head -20
```

### Step 3 — Check What the Pipeline is ACTUALLY Writing

```
# The most recently modified file is likely the active one
# predictions.db at 16MB = active output (128K+ rows)
# signals_hermes_runtime.db at 86KB with 0 rows = dead

# Also check JSON archives
ls -la /root/.hermes/data/closed_trades_archive.json
python3 -c "import json; d=json.load(open(f)); print(len(d), 'rows')"
```

### Step 4 — Check Pipeline Processes

```
ps aux | grep -E "signal_gen|decider|guardian|ai_decider|predictor" | grep -v grep
```

If no relevant processes running, signal generation may be disabled.

### Step 5 — Document Discrepancy

When you find the data is somewhere unexpected:
- Note the actual active DB path vs documented path
- Update brain/trading.md with correction
- Report the discrepancy as a HIGH finding

## Key Lesson

**The skill's documented DB path was wrong.** This happens frequently when:
- Pipeline was refactored but docs weren't updated
- Multiple DBs exist (runtime vs archive)
- DB path changed in a config update

**Never assume the documented path is correct.** Always verify existence + row count + recency.

## Output Template

```
PIPELINE INVESTIGATION — <date>
Expected DB: <documented path> → Found: <actual state>
Actual active DB: <path> with <N> rows

CRITICAL FINDINGS:
1. [Empty DB] signals_hermes_runtime.db has 0 rows — pipeline not writing here
2. [Active data] predictions.db has 128K rows — actual output location
3. [Directional bias] 8.6x LONG ratio discovered

Action items:
- Fix signal attribution in closed_trades_archive
- Audit candle_predictor.py DOWN prediction logic
```

## Files
- Report output: `/root/.hermes/pipeline_health_report_YYYY-MM-DD.txt`
