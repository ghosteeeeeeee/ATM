---
name: fresh-run
description: Fresh state reset for Hermes trading system — clears signals DB, archives brain trades, resets cooldowns, then runs clean pipeline test.
category: trading
tags: [hermes, trading, reset, signals, pipeline]
author: T
created: 2026-03-31
---

# Fresh Run — Reset Hermes Trading State

Complete reset of the Hermes trading system to clean state. Archives all closed trades, clears stale signals, resets cooldowns, then runs pipeline to verify.

## When to Use
- After any major system change (new signal logic, A/B test, pipeline refactor)
- When debugging signal confidence issues or ghost trades
- After disabling competing processes
- Before any live trading session

## Step 1 — Archive + Reset

Run as a Python script (not inline — complex multi-database transaction):

```python
#!/usr/bin/env python3
import psycopg2, sqlite3, json

# ── PostgreSQL (brain) ──────────────────────────────────────────────
BRAIN_DB = {'host': '/var/run/postgresql', 'dbname': 'brain', 'user': 'postgres', 'password': 'postgres'}
conn = psycopg2.connect(**BRAIN_DB)
cur = conn.cursor()

# Archive closed trades (before deleting!)
import datetime
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M')
cur.execute(f"""CREATE TABLE IF NOT EXISTS trades_archive_{ts} AS 
               SELECT * FROM trades WHERE status='closed'""")
cur.execute("DELETE FROM trades WHERE status='closed'")
cur.execute("DELETE FROM ab_results")  # AB test assignments for closed trades only
conn.commit()

cur.execute("SELECT COUNT(*) FROM trades WHERE status='open'")
open_after = cur.fetchone()[0]
cur.execute(f"SELECT COUNT(*) FROM trades_archive_{ts}")
archived = cur.fetchone()[0]
print(f"[brain] Archived {archived} closed trades | Open remaining: {open_after}")
cur.close(); conn.close()

# ── SQLite (signals) ───────────────────────────────────────────────
SIGNALS_DB = '/root/.hermes/data/signals_hermes_runtime.db'
conn2 = sqlite3.connect(SIGNALS_DB)
c = conn2.cursor()
c.execute("SELECT COUNT(*) FROM signals")
sig_before = c.fetchone()[0]
c.execute(f"CREATE TABLE IF NOT EXISTS signals_archive_{ts} AS SELECT * FROM signals")
c.execute("DELETE FROM signals")
conn2.commit()
conn2.close()
conn3 = sqlite3.connect(SIGNALS_DB)
conn3.execute("VACUUM")
conn3.close()
print(f"[signals] Cleared {sig_before} signals")

# ── Clear cooldowns (JSON file, NOT a DB table) ───────────────────
COOLDOWN_FILE = '/root/.openclaw/workspace/data/signal-cooldowns.json'
with open(COOLDOWN_FILE, 'w') as f:
    json.dump({}, f)
print("[cooldowns] Cleared")

print("DONE — fresh state ready")
```

Save as `/tmp/fresh_reset.py`, run with: `python3 /tmp/fresh_reset.py`

## Step 2 — Clear Stale Bytecode (IMPORTANT)

**Always clear pycache after patching Python files** — stale `.pyc` files can silently revert your patches. Pipeline will appear to work but run old code.

```bash
find /root/.hermes/scripts/ -name "*.pyc" -delete
```

## Step 3 — Run Pipeline

```bash
rm -f /tmp/hermes-pipeline.lock
cd /root/.hermes/scripts
python3 run_pipeline.py
```

## Step 4 — Verify Clean Output

Expected: 0 EXEC, 0 AUTO signals, signals go to AI-DECIDER. Check:
- No `EXEC:` lines in output
- No `[AUTO]` tags in signal output
- z_score populated in signals DB:
  ```sql
  sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
    "SELECT token, confidence, z_score, z_score_tier FROM signals ORDER BY created_at DESC LIMIT 5;"
  ```
- Confluence signals show `→ decider` (not `AUTO`)
- Ghost/orphan trades gone from DB

## Troubleshooting

**z_score still NULL after fix:**
- Run pipeline again — pycache might not have cleared on first attempt
- Check signals DB directly: `SELECT token, z_score FROM signals WHERE z_score IS NOT NULL LIMIT 5;`
- Verify patched function is at correct line in file

**Duplicate return statement / duplicate function blocks:**
- grep for duplicate function defs: `grep -n "^def " signal_gen.py`
- Check for duplicate RSI/MACD signal blocks at end of run() function
- Always remove old code blocks before adding patched ones

**Pipeline runs but signals still auto-execute:**
- Check for duplicate RSI/MACD signal blocks (they bypass patched functions)
- Momentum signals (score=80) enter without any z_score gate — may need ENTRY_THRESHOLD in decider-run
- Confirm live_trading is OFF in hype_live_trading.json: `cat /var/www/hermes/data/hype_live_trading.json`

## Key Lessons Learned (2026-03-31)

1. **Two versions of RSI/MACD signal functions** existed in signal_gen.py — the patched `_run_rsi_signals_for_confluence()` was called by `run_confluence_detection()`, but the ORIGINAL inline RSI/MACD blocks at lines ~1482-1520 (cap=80, no z_score, no filters) ran AFTER momentum signal loop and were still firing. Both had to be removed.
2. **Stale pycache**: patched Python code doesn't run until `.pyc` is regenerated. Always `find ... -name "*.pyc" -delete` after patching.
3. **z_score=NULL in signals DB**: caused by duplicate RSI/MACD blocks bypassing patched z_score code path.
4. **No entry threshold in decider-run**: decider-run takes any PENDING signal 60-89% and executes it. No ENTRY_THRESHOLD check exists there.
5. **Cooldowns are in a JSON file** (`/root/.openclaw/workspace/data/signal-cooldowns.json`), NOT in any database table.
6. **Live trading file** is at `/var/www/hermes/data/hype_live_trading.json`, not `/root/.hermes/hype_live_trading.json`.
7. **ghost_recovery trades** = real live positions that reconciliation code incorrectly closed. Position exists on HL but DB recorded it with paper=FALSE, so reconciliation saw DB-open/HL-missing and force-closed it.
