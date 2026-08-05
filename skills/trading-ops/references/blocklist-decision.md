---
name: blocklist-decision
description: Analyze token PnL history across all data sources to make blacklist decisions. Run when a token needs review for SHORT_BLACKLIST or LONG_BLACKLIST eligibility.
---

# Blocklist Decision Skill

## When to Use
Run when asked to analyze a token for blacklist eligibility, or when a token has sustained losses that need historical review across all archives.

## Process

### Step 1: Query All Data Sources (in parallel)

**PostgreSQL brain DB:**
```python
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres', password='Brain123')
cur = conn.cursor()
cur.execute("""
    SELECT token, direction, pnl_pct, pnl_usdt, status, close_reason, open_time, close_time
    FROM trades WHERE token='TOKEN' ORDER BY open_time
""")
brain_trades = cur.fetchall()
conn.close()
```

**SQLite signals DB (signals_hermes_runtime.db):**
```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')

# signal_outcomes (completed trades)
outcomes = conn.execute("""
    SELECT created_at, direction, signal_type, is_win, pnl_pct, pnl_usdt, confidence
    FROM signal_outcomes WHERE token='TOKEN' ORDER BY created_at
""").fetchall()

# Active signals
active = conn.execute("""
    SELECT COUNT(*) FROM signals WHERE token='TOKEN' AND decision='PENDING'
""").fetchone()[0]

conn.close()
```

**Hyperliquid fills CSV:**
```python
import csv
with open('/root/.hermes/data/hl_fills_0x324a9713603863FE3A678E83d7a81E20186126E7.csv') as f:
    reader = csv.DictReader(f)
    fills = [r for r in reader if 'TOKEN' in str(r)]
```

### Step 2: Calculate Directional Net PnL
For each direction (LONG/SHORT):
- Sum `pnl_usdt` from `signal_outcomes` and `brain_trades`
- Count wins vs losses
- Note: signal_outcomes and brain DB may overlap — prefer brain DB for trade counts if both exist

### Step 3: Apply Blacklist Rules
Decision rules from `hermes_constants.py`:
- **SHORT_BLACKLIST**: `net_loss_on_direction <= -$2.50` OR `3+ consecutive losses on direction`
- **LONG_BLACKLIST**: `net_loss_on_direction <= -$2.50` OR `3+ consecutive losses on direction`

### Step 4: Document & Update
1. Print summary table with all trades
2. If blacklist-worthy: update `hermes_constants.py` SHORT_BLACKLIST or LONG_BLACKLIST
3. Add comment with: token, direction, total net, per-trade breakdown, date
4. Verify syntax: `python3 -m py_compile /root/.hermes/scripts/hermes_constants.py`

## Output Format
```
=== TOKEN DIRECTION ANALYSIS ===
Trades: N | WR: W/L | Net: $X.XX

| Date       | Signal      | PnL%   | PnL$   | Result |
|------------|-------------|--------|--------|--------|
| YYYY-MM-DD | signal-name | -X.XX% | $-X.XX | LOSS   |

VERDICT: TOKEN → DIRECTION_BLACKLIST ✅ | Reason
```
