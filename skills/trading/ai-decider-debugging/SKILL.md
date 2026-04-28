---
name: ai-decider-debugging
description: DEPRECATED — ai_decider.py is DEFUNCT (replaced by signal_compactor.py). This skill is stale. Use signal-compaction and hermes-dual-writer-debug instead. Kept for diagnostic queries only.
tags: [hermes, hot-set, ai-decider, debug, defunct]
---
deprecated: true
---

# AI-Decider / Hot-Set Debugging Skill

## When to Use
When the hot-set in `hotset.json` seems wrong — wrong tokens, wrong sources, wrong counts, or signals that should be there are missing.

## Diagnostic Steps (in order)

### 1. Check the data sources
```bash
# Current hotset.json (canonical source)
python3 -c "
import json, time
d = json.load(open('/var/www/hermes/data/hotset.json'))
print(f'Written: {time.strftime(\"%H:%M:%S\", time.localtime(d[\"timestamp\"]))} UTC')
print(f'Tokens: {len(d[\"hotset\"])}')
for s in d['hotset']: print(f'  {s[\"token\"]:<10} {s[\"direction\"]} conf={s.get(\"confidence\",\"?\")}% src={s.get(\"source\",\"?\")[:40]}')
"

# Signals DB — hot_cycle_count breakdown
python3 - << 'EOF'
import sqlite3
db = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM signals WHERE hot_cycle_count >= 1")
print(f"Signals with hot_cycle_count>=1: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM signals WHERE hot_cycle_count = 0")
print(f"Signals with hot_cycle_count=0: {cur.fetchone()[0]}")
conn.close()
EOF
```

### 2. Check what the LLM sees (fresh signals query)
```python
# This is the query inside ai_decider._llm_compaction() line ~1159
python3 - << 'EOF'
import sqlite3
db = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("""
    SELECT token, direction, signal_type, confidence, source, created_at
    FROM signals
    WHERE decision = 'PENDING'
      AND executed = 0
      AND created_at > datetime('now', '-10 minutes')
      AND confidence >= 60
    ORDER BY confidence DESC
    LIMIT 50
""")
rows = cur.fetchall()
from collections import Counter
print(f"Fresh signals (last 10 min): {len(rows)}")
sources = Counter(r[4] for r in rows)
print("Sources:")
for s, c in sources.most_common(): print(f"  {s}: {c}")
EOF
```

### 3. Check DB round tracking vs hotset.json round tracking
```python
python3 - << 'EOF'
import sqlite3, json
db = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
for tok in ['SOL', 'HBAR', 'XPL', 'ENS']:
    cur.execute("""
        SELECT token, direction, hot_cycle_count, confidence, source, decision
        FROM signals
        WHERE token=? AND hot_cycle_count >= 1
        ORDER BY hot_cycle_count DESC LIMIT 3
    """, (tok,))
    rows = cur.fetchall()
    print(f"\n{tok} DB hot_cycle_count:")
    for r in rows:
        print(f"  {r[1]:<6} rounds={r[2]} conf={r[3]} decision={r[5]}")

with open('/var/www/hermes/data/hotset.json') as f:
    hs = json.load(f)
print(f"\n{tok} hotset.json:")
for s in hs['hotset']:
    if s['token'] in ['SOL', 'HBAR', 'XPL', 'ENS']:
        print(f"  {s['direction']:<6} survival_round={s.get('survival_round','?')} conf={s.get('confidence','?')}%")
conn.close()
EOF
```

### 4. Check pipeline logs for LLM output
```bash
grep -i "llm-compaction\|parsed.*ranked\|APPROVED.*signals\|write.*hotset" \
  /root/.hermes/logs/pipeline.log | tail -20
```

### 5. Check the last LLM debug output
```bash
cat /tmp/llm_compaction_content.txt | head -80  # First 80 lines = LLM reasoning
```

## Common Failure Modes Found

### Bug: 10-min window breaks APPROVED update for survivor tokens
**Symptom:** Token has `survival_round=N` in hotset.json but `hot_cycle_count=0` in DB.
**Root cause:** `_llm_compaction()` APPROVED UPDATE (line ~1715) has `WHERE created_at > datetime('now', '-10 minutes')`. If a survivor token's PENDING signal was created 11+ min ago, UPDATE affects 0 rows. Token stays PENDING in DB.

**Fix needed:** Remove the 10-min constraint from the APPROVED UPDATE, or sync `survival_round` from hotset.json → DB `hot_cycle_count` after writing hotset.json.

### Bug: Empty HOT-SURVIVORS section causes re-ranking from scratch
**Symptom:** LLM sees no survivors, re-ranks fresh signals only, drops high-round survivors.
**Root cause:** `hotset.json` was empty or stale when ai_decider loaded it. `prev_hotset` dict is empty → survivor context is blank.

### Bug: `***` placeholder fills valid hot-set slots
**Symptom:** High-round survivor is missing, replaced by `***` in hotset.json.
**Root cause:** LLM hallucinates `***` as a token. Recovery logic at line ~1560 tries to match by direction+confidence, can recover incorrectly.

## OC Signal Source Debugging Pattern

When OC-derived signals show wrong source names in hotset/dashboard:

1. Check the OC source file — what bare value does OC actually send?
```bash
python3 -c "
import json
d = json.load(open('/var/www/hermes/data/oc_pending_signals.json'))
from collections import Counter
sources = Counter(s.get('source','') for s in d.get('pending_signals',[]))
print('OC sources:', dict(sources))
"
```

2. Check DB — what source was actually written?
```sql
SELECT token, direction, source, signal_type FROM signals
WHERE source LIKE '%zscore%' ORDER BY created_at DESC LIMIT 5;
```

3. Check hotset.json — what does compactor output?
```bash
cat /var/www/hermes/data/hotset.json | python3 -c "
import sys,json
d=json.load(sys.stdin)
for s in d['hotset']: print(s.get('token'), s.get('source'))
"
```

4. Check the normalization code in `oc_signal_importer.py` — the OC source key
   in the JSON may be bare (e.g. `'zscore-v9'`) while the code checks for
   the already-prefixed form (e.g. `'oc-pending-zscore-v9'`). The else clause
   at line ~159 does `f'oc-pending-{oc_source}'` — this is the bug.

**Key lesson:** OC JSON bare source values must be matched exactly. If OC sends
`zscore-v9`, check for `'zscore-v9'`, not `'oc-pending-zscore-v9'`.

## Key Files
- `ai_decider.py` — LLM compaction (line ~1100-1750)
- `decider_run.py` — hot-set execution (line ~748-900)
- `signal_schema.py` — signal creation, `hot_cycle_count` reset on new signal
- `oc_signal_importer.py` — OC → Hermes signal normalization
- `/var/www/hermes/data/hotset.json` — canonical hot-set
- `/var/www/hermes/data/oc_pending_signals.json` — OC source signals
- `/root/.hermes/data/signals_hermes_runtime.db` — signal records

## Relevant Skills
- `pipeline-review` — full pipeline health check
- `hermes-signal-debugging` — signal_gen output debugging
