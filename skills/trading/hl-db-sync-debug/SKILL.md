---
name: hl-db-sync-debug
description: Debug why Hyperliquid (HL) positions and the Hermes signal DB are out of sync — phantom entries, missing trades, wrong decisions.
tags: [trading, hyperliquid, debugging, sqlite, postgresql, sync]
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, hyperliquid, debugging, sqlite, postgresql]
    data_stores:
      - signals_hermes_runtime.db (SQLite)
      - brain.trades (PostgreSQL)
      - HL API (get_open_hype_positions_curl)
---

# HL/DB Sync Debug

Systematic debugging when Hyperliquid positions don't match what Hermes thinks is open or closed.

## Investigation Order

Run each query in sequence — the answer usually emerges by comparing across all three sources.

### 1. SQLite — signals table

```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()

# All decisions and counts
c.execute('SELECT decision, COUNT(*) FROM signals GROUP BY decision ORDER BY COUNT(*) DESC')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')

# executed=1 but decision != 'EXECUTED' — DATA CORRUPTION
c.execute('SELECT COUNT(*) FROM signals WHERE executed=1 AND decision != "EXECUTED"')
print(f'executed=1 but wrong decision: {c.fetchone()[0]}')

# EXECUTED signals (real trades)
c.execute('''
  SELECT token, direction, signal_type, created_at, compact_rounds
  FROM signals WHERE decision = "EXECUTED" ORDER BY created_at
''')
for row in c.fetchall():
    print(f'  EXECUTED: {row}')

# SKIPPED entries by token (pollution indicator)
c.execute('''
  SELECT token, direction, COUNT(*) as cnt, MIN(created_at), MAX(created_at)
  FROM signals WHERE decision = "SKIPPED"
  GROUP BY token, direction ORDER BY cnt DESC
''')
for row in c.fetchall():
    print(f'  SKIPPED {row[0]} {row[1]}: {row[2]}x from {row[3]} to {row[4]}')
```

### 2. PostgreSQL — brain.trades (open positions)

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2

conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()

# Schema check
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'trades'")
cols = [r[0] for r in cur.fetchall()]
print('brain.trades columns:', cols)

# Open positions
cur.execute("""
  SELECT token, direction, entry_price, amount_usdt, status, pnl_pct, pnl_usdt,
         open_time, server, signal
  FROM trades WHERE status = 'open' ORDER BY open_time DESC
""")
for r in cur.fetchall():
    print(f'  {r[0]} {r[1]} entry={r[2]} amt=${r[3]} pnl={r[5]:+.4f} opened={r[7]} server={r[8]}')

# Closed since N hours ago
cur.execute("""
  SELECT token, direction, entry_price, exit_price, pnl_pct, pnl_usdt,
         open_time, close_time, close_reason
  FROM trades WHERE status = 'closed'
  AND close_time >= '2026-04-16 18:00:00'
  ORDER BY close_time DESC LIMIT 20
""")
for r in cur.fetchall():
    print(f'  CLOSED: {r[0]} {r[1]} exit={r[3]} pnl={r[4]:+.4f} reason={r[8]}')
```

### 3. Hyperliquid API — actual positions

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_hype_positions_curl

result = get_open_hype_positions_curl()
# Returns dict: {TOKEN: {size, direction, entry_px, unrealized_pnl, leverage}}
for token, p in result.items():
    print(f'  HL {token} {p["direction"]} sz={p["size"]} entry={p["entry_px"]} pnl={p["unrealized_pnl"]}')
```

### 4. Check for rogue systemd timers

```bash
systemctl list-timers --all | grep -i "ai\|decider\|signal\|hermes"
systemctl cat ai-decider.timer   # if exists, check what it runs
systemctl cat ai-decider.service # check ExecStart path
```

### 5. Pipeline log — who ran what recently

```bash
tail -100 /root/.hermes/logs/pipeline.log | grep -i "ai_decider\|signal_compactor\|decider_run"
```

---

## Common Bugs Found

### Bug 1: ai_decider.py still running via systemd timer
- **Symptom**: 20+ SKIPPED entries for same token, decision!=EXECUTED but executed=1
- **Cause**: `ai-decider.timer` fires every 10 min, runs `ai_decider.py` which has `update_open_positions_skipped()` that marks tokens as SKIPPED
- **Fix**: `systemctl stop ai-decider.timer && systemctl disable ai-decider.timer`

### Bug 2: decider_run writing APPROVED inside `_run_hot_set()`
- **Symptom**: APPROVED signals never get EXECUTED, or EXECUTED has wrong decision value
- **Cause**: `_run_hot_set()` was writing `decision='APPROVED'` in its own loop, racing with signal_compactor
- **Fix**: Patch `_run_hot_set()` to be READ-ONLY — only reads hotset.json and marks EXECUTED on fill

### Bug 3: speed_cache.json wrong path
- **Symptom**: All hotset entries show speed_percentile=50
- **Cause**: `speed_tracker.py` writes to `/var/www/hermes/data/speed_cache.json` but compactor reads `/root/.hermes/data/speed_cache.json`
- **Fix**: Use DB fallback to `token_speeds` table when JSON missing

### Bug 4: Phantom closes in DB
- **Symptom**: Signal has `exit_price=0` or `exit_reason='phantom_close'` but no real HL fill
- **Cause**: `mirror_open` called before HL confirmed the position existed
- **Fix**: HL-first architecture — call `mirror_open` AFTER HL confirms, never before

### Bug 5: `close_orphan_paper_trades` wrong `paper=true` filter (CRITICAL)
- **Symptom**: PostgreSQL has open trade with `paper=false` but HL has no position. Trade is stuck — never closed, never synced.
- **Discovered**: 2026-04-22 — VIRTUAL was open in PG (paper=false) with no HL position.
- **Root Cause**: `close_orphan_paper_trades` (guardian Step 4) queries only `paper=true` trades at line 2029. But `brain.py add_trade()` always writes `paper=False` for live HL trades. So live HL orphan trades (paper=false) are invisible to the orphan checker.
- **Fix**: In `hl-sync-guardian.py`, remove `paper=true` filter in `close_orphan_paper_trades`:
  ```python
  # BEFORE (line ~2029):
  WHERE status = 'open' AND paper = true AND exchange = 'Hyperliquid'
  # AFTER:
  WHERE status = 'open' AND exchange = 'Hyperliquid'
  ```
- **Also**: `reconcile_hype_to_paper` only iterates HL positions, so it can't close a PG trade that has no HL counterpart either.

### Bug 6: `executed=1` but `decision` is REJECTED/EXPIRED (data pollution)
- **Symptom**: 28,632+ signals with `executed=1` but `decision` is REJECTED (13k) or EXPIRED (15k). The `executed=1` flag means "execution path was triggered" but the signal was actually rejected/expired.
- **Root Cause**: `signal_schema.py` uses a CASE expression — `executed=CASE WHEN decision='EXECUTED' THEN 1 ELSE executed END` — which means `executed` stays `1` if it was set previously, even when `decision` changes to REJECTED/EXPIRED.
- **Impact**: `signal_compactor` query excludes `executed=1` rows (line ~245, `AND executed = 0`), so these corrupted rows are silently filtered from compaction. They pile up but cause no immediate execution harm.
- **Fix**: Add a DB cleanup query to reset `executed=0` where `decision != 'EXECUTED'`:
  ```sql
  UPDATE signals SET executed = 0 WHERE executed = 1 AND decision != 'EXECUTED';
  ```

### Bug 7: No EXECUTED signal for live HL position (signal DB desync)
- **Symptom**: HL shows TIA SHORT open, PG shows TIA SHORT open, but signals DB has no `decision='EXECUTED'` for TIA.
- **Root Cause**: `mark_signal_executed()` in `signal_schema.py` uses atomic UPDATE with `WHERE executed=0`. If decider_run crashes after HL order fills but before `mark_signal_executed()` is called, the trade is live but the signal stays PENDING.
- **Fix**: Either (a) make `mark_signal_executed` idempotent by also checking HL fills, or (b) have guardian backfill EXECUTED decisions by comparing PG open trades to signals DB.

---

## Key Insight: Three Independent Systems

Hermes has **three independent position sources**:
1. `signals_hermes_runtime.db` (SQLite) — signal lifecycle
2. `brain.trades` (PostgreSQL) — trade record
3. Hyperliquid API — ground truth

**They must agree.** When they don't:
1. HL is source of truth for what's actually open
2. `brain.trades` should mirror HL via `mirror_open`/`mirror_close`
3. `signals` table should have `decision='EXECUTED'` when HL confirms a fill

If `signals` has EXECUTED but `brain.trades` doesn't have the trade → `mirror_open` failed
If `brain.trades` has open but `signals` doesn't → `signal_compactor` was overridden by ai_decider pollution

## Critical Debugging Pattern: 3-Way Simultaneous Query

When investigating sync issues, always query all three sources at the same time. The desync pattern emerges from comparing them:

```python
# Run ALL THREE in the same script — desync only visible when comparing
import sqlite3, psycopg2, json
from hyperliquid_exchange import get_open_hype_positions_curl
from _secrets import BRAIN_DB_DICT

hl = {t: d for t,d in get_open_hype_positions_curl().items()}
hl_open = set(hl.keys())

conn_pg = psycopg2.connect(**BRAIN_DB_DICT)
cur_pg = conn_pg.cursor()
cur_pg.execute("SELECT token, direction, status FROM trades WHERE status='open'")
pg_open = {r[0]: r[1] for r in cur_pg.fetchall()}
pg_set = set(pg_open.keys())

conn_sql = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c_sql = conn_sql.cursor()
c_sql.execute('SELECT token, direction, decision FROM signals WHERE decision="EXECUTED"')
executed = {(r[0],r[1]): r[2] for r in c_sql.fetchall()}

print("In HL but NOT in PG:", hl_open - pg_set)
print("In PG but NOT in HL:", pg_set - hl_open)
for tok in pg_set & hl_set:
    key = (tok, pg_open[tok])
    if key not in executed:
        print(f"PG+HL open but NO EXECUTED signal: {tok}")
```
