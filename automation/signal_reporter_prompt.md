# Signal Performance Reporter

You are analyzing signal performance for the Hermes trading system. Run every 6 hours. **Act on findings, don't just report.**

**IMPORTANT: Do NOT query OpenMemory during this task. The OpenMemory queries are failing with tenant_mismatch errors and causing timeouts. Skip all OpenMemory calls entirely.**

**IMPORTANT: Do NOT write temp files to /tmp/ — that directory is blocked. Execute Python code directly inline. If you must write a temp file, use /root/.hermes/automation/tmp/ instead.**

## Step 1: Verify Numbers (MANDATORY)

**Never trust old reports. Query the DB yourself.**

```python
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
cur = conn.cursor()

# Last 6h performance by signal+direction
cur.execute("""
    SELECT signal, direction, COUNT(*) as trades, 
           ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
           ROUND(SUM(pnl_usdt),2) as pnl
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '6 hours' AND status = 'closed'
    GROUP BY signal, direction 
    HAVING COUNT(*) >= 2
    ORDER BY pnl
""")
print("=== 6h Performance ===")
for r in cur.fetchall():
    print(r)

# Last 24h performance by signal+direction
cur.execute("""
    SELECT signal, direction, COUNT(*) as trades, 
           ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
           ROUND(SUM(pnl_usdt),2) as pnl
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '24 hours' AND status = 'closed'
    GROUP BY signal, direction 
    HAVING COUNT(*) >= 3
    ORDER BY pnl
""")
print("\n=== 24h Performance ===")
for r in cur.fetchall():
    print(r)
conn.close()
```

## Step 2: Identify Kill Candidates

**Kill immediately if ALL of these are true:**
- WR < 30% with 5+ trades (24h)
- Net PnL < -$0.10 (24h)
- Signal has been active > 24h (not just bad luck)

**Candidates for tuning if:**
- WR 30-40% with 10+ trades
- Net PnL negative but small losses per trade

## Step 3: Execute Kills

**You can disable signals directly** — don't wait for CEO approval on clear losers.

```python
# Check current status
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from hermes_constants import *

# Example: if inv-accel-300- has 0% WR with 10+ trades
# INVERSE_ACCEL_300_MINUS_ENABLED = False  # Kill it
```

For each kill:
1. Edit `scripts/hermes_constants.py` to set `*_ENABLED = False` (MUST actually change True→False)
2. Add to `NEVER_REENABLE_FLAGS` if it's a repeat offender
3. **VERIFY the flag is actually False** — re-read the file and confirm the line reads `= False`
4. Git commit: `git commit -m "signals: kill [signal] — X% WR, $Y PnL (24h)"`
5. **Report to CEO kanban:**
```markdown
## TEAM UPDATES
- [YYYY-MM-DD HH:MM] signal_reporter: Killed [signal] — [reason]
```

## Step 4: Identify Boost Candidates

**Boost if ALL of these are true:**
- WR > 55% with 5+ trades (24h)
- Net PnL > $0.05 (24h)
- Consistent across multiple tokens

Boost by increasing confidence weight in `signal_compactor.py` or adding to hot-set priority.

## Step 5: Check for Signal Inversions

```sql
-- Direction mismatches
SELECT token, signal, direction, close_reason, pnl_usdt
FROM trades 
WHERE close_time > NOW() - INTERVAL '24 hours'
  AND ((signal LIKE '%long%' AND direction = 'SHORT')
    OR (signal LIKE '%short%' AND direction = 'LONG'))
ORDER BY created_at DESC LIMIT 10;
```

If inversions found → CRITICAL bug, fix immediately.

## Step 6: Report

Write to `automation/signal_report.md`:

```
=== Signal Performance Report ===
Period: Last 6h | 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|

ISSUES:
- [any inversions, bugs, or anomalies]
```

## Key File Paths
- Brain DB: PostgreSQL at `/var/run/postgresql/brain`
- Constants: `scripts/hermes_constants.py`
- Signal outcomes: `data/signals_hermes_runtime.db`
- Trading log: `automation/trading_log.md`
