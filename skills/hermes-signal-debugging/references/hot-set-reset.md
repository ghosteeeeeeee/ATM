---
name: hot-set-reset
description: Analyze Hermes hot-set state and generate a reset prompt for AI review. Use when hot-set exceeds ~20 tokens, low-confidence trades are getting through, or after a threshold change (e.g., 40% → 80%). Reads hotset.json, signals runtime DB, and brain trades DB to produce a structured summary and AI prompt for deciding which tokens to keep/evict.
triggers:
  - hot-set exceeds 20 tokens
  - low-confidence trades getting through (e.g., 54%, 50% signals in hot-set)
  - after changing avg_conf threshold
  - scheduled reset
---

## What This Does
Analyzes the current hot-set queue, pending signals, and open positions — then generates a structured AI review prompt so an operator can decide which tokens to keep in the hot-set and which to evict. The ai_decider compaction logic implements the changes on the next pipeline run.

## Data Sources
- **hotset.json**: `/var/www/hermes/data/hotset.json` — current hot-set tokens
- **Runtime signals DB**: `/root/.hermes/data/signals_hermes_runtime.db` — PENDING/APPROVED signals
- **Brain trades DB**: PostgreSQL (via `_secrets.BRAIN_DB_DICT`) — open positions

## Steps

### Step 1 — Hot-set snapshot
```bash
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
hotset = d.get('hotset', [])
print(f'HOT-SET: {len(hotset)} tokens')
for t in hotset:
    print(f'  {t[\"token\"]} {t[\"direction\"]} r{t.get(\"compact_rounds\",0)} conf={t[\"confidence\"]:.0f}% signal={t.get(\"signal_type\",\"?\")} src={t.get(\"source\",\"?\")}')
"
```

### Step 2 — Pending signals queue
```bash
cd /root/.hermes/scripts && python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, signal_type, source, confidence, decision,
           review_count, compact_rounds, created_at
    FROM signals
    WHERE decision IN (\"PENDING\",\"APPROVED\")
    ORDER BY confidence DESC
    LIMIT 50
''')
rows = cur.fetchall()
print(f'PENDING/APPROVED: {len(rows)} signals')
for r in rows:
    print(f'  {r[0]:8s} {r[1]:5s} conf={r[4]:5.1f}% {r[2]:15s} src={r[3]:20s} rc={r[6] or 0} cr={r[7] or 0}')
conn.close()
"
```

### Step 3 — Open positions
```bash
cd /root/.hermes/scripts && python3 -c "
import psycopg2
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute(\"SELECT token, direction, pnl_pct, entry_price FROM trades WHERE status='open' AND server='Hermes'\")
rows = cur.fetchall()
print(f'Open positions: {len(rows)} / 10')
for r in rows:
    print(f'  {r[0]} {r[1]} pnl={r[2]:+.2f}%')
conn.close()
"
```

### Step 4 — Confidence distribution analysis
Count hot-set tokens in bands:
- 90%+ (strong)
- 80-89% (acceptable, new minimum)
- 70-79% (below new threshold — candidates for eviction)
- <70% (definitely evict)

Identify tokens with direction conflicts (same token, both LONG and SHORT).

### Step 5 — Generate AI review prompt
Print a structured summary:
- Hot-set size: N (target: 10-12)
- Open slots: 10 - open_position_count
- Table of all hot-set tokens: TOKEN | DIR | CONF | SOURCE | ROUNDS | DECISION
- Top 5 pending signals not in hot-set (potential additions)
- Eviction list (sub-threshold, single-source, conflicting direction)

## Notes
- Changes to hotset.json take effect on next ai_decider run
- ai_decider compaction logic reads hotset.json and evicts/promotes tokens
- Run this skill after threshold changes to see which tokens drop below the new bar