---
name: clean-up
description: Clean orphaned and stale entries from trailing_stops.json — keeps only trades that are open in the brain DB. Run after closing positions or when the file grows large. Also backs up before cleaning.
category: trading
author: T
created: 2026-04-06
---

# Trailing Stops Cleanup

Clean orphaned entries from `trailing_stops.json` — keeps only active open positions from the brain DB. Safe to run anytime; backs up before writing.

## When to Run

- After bulk-closing positions
- When `trailing_stops.json` has hundreds of stale entries
- Before a fresh backtest or audit
- After any session where trades were manually closed or orphaned

## Script

Save as `/tmp/cleanup_trailing_stops.py`:

```python
#!/usr/bin/env python3
"""Clean orphaned entries from trailing_stops.json — keeps only active DB trades."""
import json, os, sys
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2

TRAILING_FILE = '/var/www/hermes/data/trailing_stops.json'
BACKUP_FILE  = TRAILING_FILE + '.bak'

with open(TRAILING_FILE) as f:
    data = json.load(f)

# Get all open trade IDs from DB
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("SELECT id FROM trades WHERE status = 'open' AND server = 'Hermes'")
open_ids = {str(r[0]) for r in cur.fetchall()}
conn.close()

kept = 0
removed = 0
for tid, tdata in list(data.items()):
    is_orphaned = bool(tdata.get('orphaned_at'))
    not_in_db = tid not in open_ids
    if is_orphaned or not_in_db:
        del data[tid]
        removed += 1
    else:
        kept += 1

# Backup old file
with open(BACKUP_FILE, 'w') as f:
    json.dump(data, f, indent=2)

# Write cleaned
with open(TRAILING_FILE, 'w') as f:
    json.dump(data, f, indent=2)

print(f"Kept: {kept}, Removed: {removed}")
print(f"Backup: {BACKUP_FILE}")
print(f"Cleaned trailing_stops.json: {len(data)} entries remain")
```

## How to Run

```bash
python3 /tmp/cleanup_trailing_stops.py
```

## What It Does

1. Loads `trailing_stops.json`
2. Queries brain DB for all open trade IDs (`status='open' AND server='Hermes'`)
3. Deletes any entry that:
   - Has `orphaned_at` timestamp (marked as closed by position_manager)
   - Has a trade ID not in the open positions DB
4. Backs up the cleaned state to `trailing_stops.json.bak`
5. Writes the cleaned file back

## Verification

```bash
# Count entries before and after
jq 'length' /var/www/hermes/data/trailing_stops.json

# Verify kept entries match open positions
python3 -c "
import psycopg2, json, sys; sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute(\"SELECT id, token FROM trades WHERE status='open' AND server='Hermes'\")
db_ids = {str(r[0]) for r in cur.fetchall()}
conn.close()
with open('/var/www/hermes/data/trailing_stops.json') as f:
    ts_ids = set(json.load(f).keys())
print('In DB:', sorted(db_ids))
print('In trailing_stops:', sorted(ts_ids))
print('Missing from trailing_stops:', db_ids - ts_ids)
"
```

## Pitfalls

- **Never delete the backup** — restore with `cp trailing_stops.json.bak trailing_stops.json`
- If position_manager is mid-run, wait for it to finish before cleaning
- Orphaned entries from April 1 (2026) are safe to remove — those trades are long closed
