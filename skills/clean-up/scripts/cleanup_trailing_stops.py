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
