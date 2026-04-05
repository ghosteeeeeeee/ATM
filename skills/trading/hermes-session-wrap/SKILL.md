---
name: hermes-session-wrap
description: Full session wrap for Hermes trading system — update-git, analyze-trades, fresh-run. Run after major coding sessions.
category: trading
tags: [hermes, git, trading, reset, analysis]
author: T
created: 2026-04-02
---

# Hermes Session Wrap — Full Run + Package

Run after any significant coding session: updates git, analyzes trades, fresh-resets the pipeline.

## Prerequisites
- GitHub token: stored in `~/.netrc` (machine `api.github.com`)
- Working directory: `/root/.hermes`
- Live trading: `hype_live_trading.json` ON — **DO NOT close open positions**

## Step 1 — update-git

Package and publish Hermes to GitHub releases + local `/var/www/git/`.

```bash
cd /root/.hermes
python3 scripts/update-git.py
```

If GitHub asset upload fails (422), zip is at `/var/www/git/` and release page still works. To upload manually:
```bash
TOKEN="***"
REPO="ghosteeeeeeee/ATM"
COMMIT=$(git rev-parse --short HEAD)
TS=$(date +%Y%m%d-%H%M)
ZIP="/var/www/git/ATM-Hermes-${TS}-full-${COMMIT}.zip"

# Find release ID:
curl -s -H "Authorization: token $TOKEN" "https://api.github.com/repos/$REPO/releases" | \
  python3 -c "import sys,json; [print(r['id'], r['tag_name']) for r in json.load(sys.stdin)[:5]]"

# Upload zip:
curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/zip" \
  --data-binary "@${ZIP}" \
  "https://uploads.github.com/repos/$REPO/releases/${RELEASE_ID}/assets?name=$(basename $ZIP)"
```

## Step 2 — analyze-trades

Archive closed trades, analyze performance, apply findings.

```python
#!/usr/bin/env python3
import psycopg2, sqlite3
from datetime import datetime

BRAIN = {'host': '/var/run/postgresql', 'dbname': 'brain', 'user': 'postgres', 'password': '***'}
conn = psycopg2.connect(**BRAIN)
cur = conn.cursor()

# Show open trades (don't touch)
cur.execute("SELECT id, token, direction, entry_price, pnl_pct, leverage, created_at FROM trades WHERE status='open'")
open_trades = cur.fetchall()
print(f"OPEN trades: {len(open_trades)}")
for t in open_trades:
    print(f"  id={t[0]} {t[1]} {t[2]} entry={float(t[3]):.6f} pnl={float(t[4]):.2f}% lev={t[5]}")

# Analyze closed trades
cur.execute("""
    SELECT token, direction, entry_price, exit_price, pnl_pct, pnl_usdt,
           ROUND(EXTRACT(EPOCH FROM (close_time - open_time))/60, 1) as duration_min,
           close_reason, experiment, exit_reason
    FROM trades WHERE status='closed' ORDER BY close_time DESC
""")
rows = cur.fetchall()
print(f"\nCLOSED trades: {len(rows)}")
wins = [r for r in rows if float(r[4] or 0) > 0]
losses = [r for r in rows if float(r[4] or 0) <= 0]
print(f"WR: {len(wins)}/{len(rows)} = {len(wins)/max(len(rows),1)*100:.0f}%")
net = sum(float(r[5] or 0) for r in rows)
print(f"Net: ${net:+.2f}")
print(f"\nWins:")
for r in wins: print(f"  {r[0]} {r[1]} {float(r[4]):+.4f}% ${float(r[5] or 0):+.2f} [{r[8]}]")
print(f"Losses:")
for r in losses: print(f"  {r[0]} {r[1]} {float(r[4]):+.4f}% ${float(r[5] or 0):+.2f} [{r[8]}]")
conn.close()
```

**Findings to apply:**
- Update SHORT_BLACKLIST / LONG_BLACKLIST in hermes_constants.py with worst performers
- Adjust confluence minimum if single/dual-source signals underperforming
- Note systematic issues (guardian_missing, hl_position_missing, etc.)

## Step 3 — hot-set-reset

Analyze the hot-set queue and generate a reset recommendation. Include this step every session wrap so stale/low-confidence tokens are evicted before the next pipeline run.

```bash
cd /root/.hermes/scripts && python3 << 'EOF'
import json, sqlite3, psycopg2
from _secrets import BRAIN_DB_DICT
from collections import defaultdict

with open('/var/www/hermes/data/hotset.json') as f:
    hs = json.load(f)
hotset = hs.get('hotset', [])
hotset_map = {(t['token'], t['direction']) for t in hotset}

print(f"=== HOT-SET: {len(hotset)} tokens ===")
for t in sorted(hotset, key=lambda x: -x['confidence']):
    print(f"  {t['token']:8s} {t['direction']:5s} r{t.get('compact_rounds',0)} conf={t['confidence']:.0f}% {t.get('signal_type','?')}")

conn_pg = psycopg2.connect(**BRAIN_DB_DICT)
cur_pg = conn_pg.cursor()
cur_pg.execute("SELECT token, direction, pnl_pct FROM trades WHERE status='open' AND server='Hermes'")
open_rows = cur_pg.fetchall()
open_tokens = {r[0] for r in open_rows}
print(f"\n=== OPEN POSITIONS: {len(open_rows)}/10 ===")
for r in open_rows:
    print(f"  {r[0]} {r[1]} pnl={r[2]:+.2f}%")
conn_pg.close()

conn_sql = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur_sql = conn_sql.cursor()
cur_sql.execute('''
    SELECT token, direction, signal_type, source, confidence, decision,
           review_count, compact_rounds
    FROM signals
    WHERE decision IN ("PENDING","APPROVED")
    ORDER BY confidence DESC
    LIMIT 50
''')
pending = cur_sql.fetchall()

by_token = defaultdict(lambda: {'best_conf': 0, 'sources': set(), 'signal_types': set(), 'decision': ''})
for r in pending:
    key = (r[0], r[1])
    if r[4] > by_token[key]['best_conf']:
        by_token[key]['best_conf'] = r[4]
    by_token[key]['sources'].add(str(r[3])[:20])
    by_token[key]['signal_types'].add(str(r[2]))
    by_token[key]['decision'] = r[5]

print(f"\n=== TOP PENDING SIGNALS ===")
for (token, direction), data in sorted(by_token.items(), key=lambda x: -x[1]['best_conf'])[:20]:
    sources = ','.join(sorted(data['sources']))[:23]
    types = ','.join(sorted(data['signal_types']))[:18]
    in_hs = 'IN-HS' if (token, direction) in hotset_map else ''
    has_open = 'OPEN' if token in open_tokens else ''
    flags = ' '.join(f for f in [in_hs, has_open] if f)
    print(f"  {token:8s} {direction:5s} {data['best_conf']:5.1f}% {sources:23s} {types:18s} {data['decision']} {flags}")
conn_sql.close()

bands = {'90+': [], '80-89': [], '70-79': [], '<70': []}
for t in hotset:
    c = t['confidence']
    if c >= 90: bands['90+'].append(t['token'])
    elif c >= 80: bands['80-89'].append(t['token'])
    elif c >= 70: bands['70-79'].append(t['token'])
    else: bands['<70'].append(t['token'])
print(f"\n=== HOT-SET DISTRIBUTION ===")
for band, tokens in bands.items():
    print(f"  {band}: {len(tokens)} — {', '.join(tokens)}")
below = len(bands['70-79']) + len(bands['<70'])
print(f"\n  → Below 80%: {below} tokens (will be blocked in next ai_decider pass)")
print(f"  → Open slots: {10 - len(open_rows)}")
print(f"  → KEEP: {len(bands['90+']) + len(bands['80-89'])} tokens | EVICT: {below} tokens")
EOF
```

**Action:** Review output. If below 80% tokens exist and slots are available, ai_decider will evict them on next run. If all slots full, eviction still applies to future passes when positions close.

## Step 4 — fresh-run

Archive closed trades, clear signals DB, reset cooldowns. **DO NOT close open positions.**

```python
#!/usr/bin/env python3
import psycopg2, sqlite3, json, subprocess
from datetime import datetime

ts = datetime.now().strftime('%Y%m%d_%H%M')
print(f"=== Fresh Run {ts} ===")

BRAIN = {'host': '/var/run/postgresql', 'dbname': 'brain', 'user': 'postgres', 'password': '***'}
conn = psycopg2.connect(**BRAIN)
cur = conn.cursor()

# Verify open trades (don't touch)
cur.execute("SELECT id, token, direction, entry_price, pnl_pct, leverage FROM trades WHERE status='open'")
open_trades = cur.fetchall()
print(f"\n[brain] OPEN trades: {len(open_trades)}")
for t in open_trades:
    print(f"  id={t[0]} {t[1]} {t[2]} pnl={float(t[4]):.2f}%")

# Archive closed
cur.execute(f"CREATE TABLE IF NOT EXISTS trades_archive_{ts} AS SELECT * FROM trades WHERE status='closed'")
n = cur.rowcount
cur.execute("DELETE FROM trades WHERE status='closed'")
conn.commit()
cur.close(); conn.close()
print(f"\n[brain] Archived {n} closed -> trades_archive_{ts}")

# Signals DBs
for db_path, label in [
    ('/root/.hermes/data/signals_hermes_runtime.db', 'hermes'),
    ('/root/.openclaw/workspace/data/signals.db', 'openclaw'),
]:
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM signals")
        n = c.fetchone()[0]
        c.execute(f"CREATE TABLE IF NOT EXISTS signals_archive_{ts} AS SELECT * FROM signals")
        c.execute("DELETE FROM signals")
        conn.commit()
        conn.close()
        conn2 = sqlite3.connect(db_path)
        conn2.execute("VACUUM"); conn2.close()
        print(f"[signals/{label}] Purged {n}, VACUUM'd")
    except Exception as e:
        print(f"[signals/{label}] Skipped: {e}")

# Cooldowns
json.dump({}, open('/root/.openclaw/workspace/data/signal-cooldowns.json', 'w'))
print(f"[cooldowns] Cleared")

# Hot-set cooldown tracker
try:
    conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
    conn.execute("DELETE FROM cooldown_tracker"); conn.commit(); conn.close()
    print(f"[cooldown_tracker] Cleared")
except: pass

# Pycache
subprocess.run(['find', '/root/.hermes/scripts/', '-name', '*.pyc', '-delete'], capture_output=True)
print(f"[pycache] Cleared")

# System locks
import os
for lf in ['/tmp/hermes-pipeline.lock', '/tmp/hermes-pipeline.running']:
    try:
        if os.path.exists(lf): os.remove(lf); print(f"[lock] Cleared: {lf}")
    except: pass

print(f"\n=== DONE — archive: trades_archive_{ts} ===")
print(f"Open positions intact: {len(open_trades)}")
```

## Verify Clean State

```python
import sqlite3, psycopg2, json

# Signals DBs
for db_path, label in [
    ('/root/.hermes/data/signals_hermes_runtime.db', 'hermes'),
    ('/root/.openclaw/workspace/data/signals.db', 'openclaw'),
]:
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM signals")
        print(f"[signals/{label}] remaining: {c.fetchone()[0]}")
        conn.close()
    except: pass

# Brain
conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres', password='***')
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM trades WHERE status='closed'")
print(f"[brain] closed: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM trades WHERE status='open'")
print(f"[brain] open: {cur.fetchone()[0]}")
conn.close()

# Cooldowns
cd = json.load(open('/root/.openclaw/workspace/data/signal-cooldowns.json'))
print(f"[cooldowns] entries: {len(cd)}")
```

## Git Commit & Push

```bash
cd /root/.hermes
git add -A && git status --short
git commit -m "your message"
python3 scripts/update-git.py
```

## What NOT to Do
- **DO NOT run the pipeline** as part of this skill — T decides when
- **DO NOT close open trades** — they are live positions
- **DO NOT delete archive tables** — historical record
- **DO NOT overwrite hype_live_trading.json** — only signal_gen.py reads it
