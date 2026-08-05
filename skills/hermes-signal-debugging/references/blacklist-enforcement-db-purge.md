# Blacklist Enforcement — DB Purge and Verify Scripts

## When to Use

Run the purge script when:
- Adding new entries to `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py`
- Symptoms: blacklisted signals appearing in hot-set despite being in blacklist

Run the verify script after:
- Any DB purge operation
- Any compactor cycle (via Step 12b log output)
- Before declaring the system clean

## Immediate Purge Script

```python
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
blacklist = [
    'pct-hermes+', 'pct-hermes-',
    'vel-hermes+', 'vel-hermes-',
    'gap-300+', 'gap-300-',
    'ma-cross-5m+',
    'hhh-long4', 'hhh-long5',
]
total = 0
for bl in blacklist:
    cur.execute('''
        UPDATE signals
        SET decision=\"EXPIRED\",
            expired_at=CURRENT_TIMESTAMP,
            updated_at=CURRENT_TIMESTAMP
        WHERE source LIKE ?
          AND decision IN (\"PENDING\",\"APPROVED\")
          AND executed=0
    ''', (f'%{bl}%',))
    n = cur.rowcount
    if n:
        print(f'Purged {n} {bl}')
        total += n
conn.commit()
print(f'Total: {total} signals expired')
conn.close()
"
```

## Verified-Clean Check

```python
python3 -c "
import sqlite3
from signal_schema import validate_source

conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('''
    SELECT id, source, decision
    FROM signals
    WHERE decision IN (\"PENDING\",\"APPROVED\")
      AND executed=0
''')
bad = [(rid, src, dec) for rid, src, dec in cur.fetchall()
       if validate_source(src or '') == 'unknown']

if bad:
    print(f'BAD ACTIVE SIGNALS: {len(bad)}')
    for rid, src, dec in bad:
        print(f'  id={rid} src={repr(src)} decision={dec}')
else:
    print('DB is clean — no stale blacklisted signals')
conn.close()
"
```

## Key Insight: SQL LIKE False Positives

`source LIKE '%vel-hermes-%'` matches BOTH `vel-hermes+` AND `vel-hermes-` because the `-` in `vel-hermes` satisfies the `%-%` wildcard pattern. This creates confusing counts.

Always use `validate_source()` for correctness when checking if a signal is blocked. The verify script above does this correctly.

## What Step 12b Does (Compactor Retroactive Enforcement)

Step 12b in `signal_compactor.py` runs on EVERY compaction cycle and applies the same logic as the verify script — but EXPIRES rather than just reports. If the verify script shows bad signals, the compactor will expire them on its next run automatically (via Step 12b). The purge script is for immediate cleanup to avoid waiting for the next cycle.

## Blacklist Entry Addition Checklist

When adding a new entry to `SIGNAL_SOURCE_BLACKLIST`:

1. Add to `hermes_constants.py` with dated comment and stats justification
2. Run the purge script above (immediate cleanup of pre-existing signals)
3. Run the verify script to confirm clean
4. Step 12b in compactor handles all future retroactive enforcement automatically
