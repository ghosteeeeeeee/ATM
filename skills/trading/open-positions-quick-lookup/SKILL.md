---
name: open-positions-quick-lookup
description: Fast open positions lookup — brain DB, trades table, correct credentials
triggers:
  - open positions
  - open trades
  - current portfolio
  - what positions do we have
---

# Open Positions Quick Lookup

## When
User asks about open positions, open trades, current portfolio, or anything related to "what positions do we have open right now."

## The Correct Path (always)

**Source of truth**: `brain` PostgreSQL database (NOT trades.json, NOT signals_hermes_runtime.db, NOT hl-sync-guardian.py)

```python
import psycopg2
conn = psycopg2.connect(
    host='/var/run/postgresql',
    database='brain',
    user='postgres',
    password='Brain123'
)
c = conn.cursor()
c.execute("""
    SELECT token, direction, entry_price, stop_loss, target,
           leverage, amount_usdt, pnl_usdt, open_time
    FROM trades
    WHERE status='open'
    ORDER BY open_time DESC
""")
rows = c.fetchall()
for r in rows:
    print(r)
```

## Key facts to never re-derive:
- trades.json is EMPTY/bogus — do NOT use it
- signals_hermes_runtime.db is for signals, not positions
- No `positions` table — it's called `trades` in the `brain` DB
- Guardian uses this same DB for open trade queries

## Verify
```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
c = conn.cursor()
c.execute(\"SELECT COUNT(*) FROM trades WHERE status='open'\")
print('Open positions:', c.fetchone()[0])
"
```
