---
name: fresh-run
description: Fresh state reset for Hermes trading system — archives closed trades, clears signals DB, resets cooldowns, clears clogs. Does NOT run the pipeline.
category: trading
tags: [hermes, trading, reset, signals, cooldowns]
author: T
created: 2026-03-31
updated: 2026-04-02
---

# Fresh Run — Reset Hermes Trading State

Archives all closed trades, clears stale signals from all DBs, resets cooldowns, and clears system clogs. Does NOT run the pipeline — T controls when that happens.

## When to Use
- After any major system change (new signal logic, A/B test, pipeline refactor)
- When debugging signal confidence issues or ghost trades
- After disabling competing processes
- Before any live trading session (run pipeline manually after verifying state)

## Step 1 — Archive Closed Trades

```python
#!/usr/bin/env python3
import psycopg2, sqlite3, json, subprocess
from datetime import datetime

ts = datetime.now().strftime('%Y%m%d_%H%M')

# ── PostgreSQL (brain) ──────────────────────────────────────────────
BRAIN = {'host': '/var/run/postgresql', 'dbname': 'brain', 'user': 'postgres', 'password': 'Brain123'}
conn = psycopg2.connect(**BRAIN)
cur = conn.cursor()

# Show open trades first (don't lose track)
cur.execute("SELECT id, token, direction, entry_price, pnl_pct, leverage, created_at FROM trades WHERE status='open'")
open_trades = cur.fetchall()
print(f"[brain] Open trades: {len(open_trades)}")
for t in open_trades:
    print(f"  id={t[0]} {t[1]} {t[2]} entry={float(t[3]):.4f} pnl={float(t[4]):.2f}% {t[6]}")

# Archive closed trades to a timestamped table
cur.execute(f"""CREATE TABLE IF NOT EXISTS trades_archive_{ts} AS
               SELECT * FROM trades WHERE status='closed'""")
n_archive = cur.rowcount
cur.execute("DELETE FROM trades WHERE status='closed'")
# NOTE: Do NOT DELETE ab_results — preserve A/B test data across resets
conn.commit()

cur.execute(f"SELECT COUNT(*) FROM trades_archive_{ts}")
archived = cur.fetchone()[0]
print(f"[brain] Archived {archived} closed trades -> trades_archive_{ts}")
cur.close(); conn.close()

# ── Signals DBs ─────────────────────────────────────────────────────
# Hermes runtime signals
SIGNALS_HERMES = '/root/.hermes/data/signals_hermes_runtime.db'
conn2 = sqlite3.connect(SIGNALS_HERMES)
c = conn2.cursor()
c.execute("SELECT COUNT(*) FROM signals")
n_hermes = c.fetchone()[0]
c.execute(f"CREATE TABLE IF NOT EXISTS signals_archive_{ts} AS SELECT * FROM signals")
c.execute("DELETE FROM signals")
conn2.commit()
conn2.close()
conn3 = sqlite3.connect(SIGNALS_HERMES)
conn3.execute("VACUUM")
conn3.close()
print(f"[signals/hermes] Purged {n_hermes} signals, VACUUM'd")

# OpenClaw signals (separate DB)
SIGNALS_OC = '/root/.openclaw/workspace/data/signals.db'
try:
    conn4 = sqlite3.connect(SIGNALS_OC, timeout=5)
    c4 = conn4.cursor()
    c4.execute("SELECT COUNT(*) FROM signals")
    n_oc = c4.fetchone()[0]
    c4.execute(f"CREATE TABLE IF NOT EXISTS signals_archive_{ts} AS SELECT * FROM signals")
    c4.execute("DELETE FROM signals")
    conn4.commit()
    conn4.close()
    conn5 = sqlite3.connect(SIGNALS_OC)
    conn5.execute("VACUUM")
    conn5.close()
    print(f"[signals/openclaw] Purged {n_oc} signals, VACUUM'd")
except Exception as e:
    print(f"[signals/openclaw] Skipped: {e}")

# ── Cooldowns ──────────────────────────────────────────────────────
COOLDOWN_FILE = '/root/.openclaw/workspace/data/signal-cooldowns.json'
with open(COOLDOWN_FILE, 'w') as f:
    json.dump({}, f)
print("[cooldowns] Cleared")

# ── Clear stale bytecode ───────────────────────────────────────────
subprocess.run(['find', '/root/.hermes/scripts/', '-name', '*.pyc', '-delete'],
               capture_output=True)
print("[pycache] Cleared .pyc bytecode")

print(f"\nDONE — archive: trades_archive_{ts}")
```

Save as `/tmp/fresh_reset.py`, run with: `python3 /tmp/fresh_reset.py`

## Step 2 — Clear System Clogs

These commonly cause the pipeline to hang, skip, or re-execute same signals:

```bash
# Remove stale lock files
rm -f /tmp/hermes-pipeline.lock
rm -f /tmp/*.lock

# Remove orphaned .pid files
find /tmp /root -name "*.pid" -type f 2>/dev/null | head -20

# Check for stuck pipeline processes
ps aux | grep -E "run_pipeline|signal_gen|decider" | grep -v grep

# Clear any stuck cron/mcp-agent jobs
# List them first:  mcp_cronjob(action='list')
```

## Step 3 — Verify Clean State

```bash
# Signals DBs should be empty
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT COUNT(*) FROM signals"
sqlite3 /root/.openclaw/workspace/data/signals.db "SELECT COUNT(*) FROM signals" 2>/dev/null

# Brain should have only open trades
psql -h /var/run/postgresql -U postgres -d brain -c "SELECT COUNT(*) FROM trades WHERE status='closed'"
psql -h /var/run/postgresql -U postgres -d brain -c "SELECT COUNT(*) FROM trades WHERE status='open'"

# Cooldowns should be empty
cat /root/.openclaw/workspace/data/signal-cooldowns.json

# No pipeline locks
ls /tmp/hermes-pipeline.lock 2>/dev/null && echo "LOCK EXISTS" || echo "No lock — clean"
```

## What NOT to Do

- **Do NOT run the pipeline** as part of this skill — T decides when to run it
- **Do NOT close open trades** — they are live positions on HL
- **Do NOT delete archive tables** — historical record

## Key Lessons Learned

1. **Live trading file** is at `/var/www/hermes/data/hype_live_trading.json`, NOT `/root/.hermes/`. Check before running pipeline.
2. **Two signals DBs exist**: Hermes (`/root/.hermes/data/signals_hermes_runtime.db`) and OpenClaw (`/root/.openclaw/workspace/data/signals.db`). Purge both.
3. **Cooldowns are in a JSON file** (`/root/.openclaw/workspace/data/signal-cooldowns.json`), NOT in any database table.
4. **ghost_recovery trades** = real live positions incorrectly closed by reconciliation. Don't re-close them during reset.
5. **ZEC SHORT belongs on blacklist** — it has catastrophic loss history (-2291%, -4170%) from phantom re-entry loops.
7. **Stale pycache reverts patches** — always clear after any Python file change.
8. **Per-token regime filter** — regime hard-blocks read from PostgreSQL momentum_cache (per-token regime via `get_regime()`), NOT from aggregate `regime_4h.json`. Each token's regime is computed independently by 4h_regime_scanner. No aggregate market-wide filter exists.
9. **HOT-SET uses cooldown_tracker table** — not the cooldowns JSON file. Both must be cleared on fresh-run.
10. **confluence >= 98%** is the winning SHORT trigger. All other LONG and SHORT trades have been losers.
