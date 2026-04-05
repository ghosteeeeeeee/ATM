# Plan: Hermes Trading System — Self-Contained Docker Container
## Version 2 — Plug-and-Play with Full Pipeline + Dashboards

---

## Goal
Create a Docker container that is **truly plug-and-play**: clone the repo, `docker compose up`, and have the entire trading system running — pipeline, dashboards, noVNC, SSH — with zero manual setup. Paper trading by default (no keys needed).

---

## Answers to Previous Pain Points

| Past Problem | Fix in This Plan |
|---|---|
| DB empty on fresh install — historical signals not in repo | Bundle seed SQL + a recent signal snapshot JSON in the image; auto-load on first start |
| `signals_data.json` 404 — JSON not generated | Dashboard export runs as part of pipeline, nginx serves it; `/app/hermes/web/signals_data.json` |
| CSP violation on signals.html — inline scripts blocked | Serve with `Content-Security-Policy: script-src 'unsafe-inline'` in nginx; OR fix inline scripts to use external `.js` files |
| Pipeline needs PostgreSQL schema | Run `schema_init.sql` automatically in entrypoint before pipeline starts |
| Dashboard not in pipeline | Add `dashboard_export.py` (or equivalent) to entrypoint startup + cron it every 30s |
| Hard to set up | Everything in `docker-entrypoint.sh` — one command |

---

## Network & Access Layout

```
┌──────────────────────────────────────────────────────────────┐
│  hermes-core container                                         │
│                                                               │
│  PORT 3333 ──► SSH daemon (sshd)         [PUBLIC]            │
│  PORT 8888 ──► nginx (serves noVNC +     [LOCALHOST only]    │
│                   signals.html + trades.html + JSON)          │
│  PORT 5902 ──► x11vnc (raw VNC)          [LOCALHOST only]    │
└──────────────────────────────────────────────────────────────┘
```

```bash
# Access (from client machine)
ssh -L 8888:127.0.0.1:8888 -L 5902:127.0.0.1:5902 root@<host> -p 3333
# → http://localhost:8888/signals.html
# → http://localhost:8888/trades.html
# → http://localhost:8888/vnc.html
```

---

## What Must Be in the Image (Complete File Listing)

```
/app/hermes/                          # git clone destination
├── scripts/
│   ├── *.py                          # ALL pipeline scripts (47 files)
│   ├── signal_schema.py               # DB schema + helpers
│   └── db_config.py                   # DB connection config
├── web/
│   ├── signals.html                   # Dashboard HTML
│   ├── trades.html                    # Dashboard HTML
│   ├── signals_data.json              # Populated by pipeline every 30s
│   ├── trades_data.json               # Populated by pipeline every 30s
│   ├── signals.schema.json            # (if any schema definition)
│   └── css/, js/                      # Static assets (if referenced)
├── data/                              # Created at runtime
│   ├── signals_hermes_runtime.db      # SQLite signals DB
│   ├── signals_hermes.db              # Secondary signals DB
│   ├── state.db                       # Pipeline state
│   └── prices.json                    # Current prices
├── seed/
│   ├── signals_hermes.sql             # Schema + seed data (historical signals)
│   └── schema_init.sql                # PostgreSQL schema (brain DB)
├── logs/
│   └── pipeline.log
├── hermes_constants.py
├── requirements.txt
├── setup.sh
└── run_pipeline.py                   # Or whatever the pipeline entry point is

/opt/novnc/                           # noVNC clone
/etc/ssh/sshd_config                   # SSH config
/etc/nginx/sites-available/novnc       # nginx config
/entrypoint.sh                        # Master startup script
/root/.ssh/authorized_keys            # Injected at runtime
```

---

## Step-by-Step Plan

### Step 1 — Audit the Existing Pipeline Scripts
Before writing anything, answer these questions by inspecting the current system:
1. What is the exact pipeline entry point? (`run_pipeline.py`? `run.sh`? Multiple cron jobs?)
2. What generates `signals_data.json` and `trades_data.json`? Is it a separate script or part of a dashboard module?
3. What columns does `signals_hermes_runtime.db` need? (Check `signal_schema.py` CREATE TABLE)
4. Does `db_config.py` connect to PostgreSQL or just SQLite?
5. What seed SQL files exist in `/root/.hermes/seed/`?
6. What is the `schema_init.sql` for PostgreSQL?

**Deliverable**: Confirmed list of pipeline scripts, their startup order, and their dependencies.

### Step 2 — Bundle Seed Data and Historical Snapshots

**Problem**: Fresh install = empty DB = no signals = nothing to show on dashboard.

**Fix**: Include two things in the image:
1. **Schema seed SQL** — `seed/signals_hermes.sql` with the full schema + any reference data (hot-set tokens, regime thresholds, etc.)
2. **Signal snapshot JSON** — a recent `signals_data.json` with 1,000+ historical signals so dashboards are populated immediately on first load. This is separate from the DB — it's the JSON the HTML pages poll.

```bash
# On the current working host, export:
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  ".dump signals" > seed/signals_hermes.sql

# Also export a recent signals_data.json snapshot
cp /root/.hermes/data/signals_data.json seed/signals_data_snapshot.json
cp /root/.hermes/data/trades_data.json seed/trades_data_snapshot.json
```

**Entrypoint behavior**: On first run, detect if DB is empty → load seed SQL + copy snapshot JSON to `web/signals_data.json`.

### Step 3 — Dashboard JSON Generation — Make It Continuous

**Problem**: `signals_data.json` 404 because nothing generates it continuously.

**Fix**: The pipeline must continuously update the JSON files. Options:
- If there's a `dashboard_export.py` script: call it every 30s via cron in entrypoint
- If no such script: write a lightweight `export_dashboards.py` that:
  - Queries SQLite signals DB → writes `web/signals_data.json`
  - Queries brain DB (Postgres or SQLite) → writes `web/trades_data.json`
  - Runs every 30 seconds

```python
# /app/hermes/scripts/export_dashboards.py
# Lightweight script called by cron in entrypoint
import sqlite3, json, os
from datetime import datetime

DATA_DIR = '/app/hermes/data'
WEB_DIR  = '/app/hermes/web'

def export_signals():
    conn = sqlite3.connect(f'{DATA_DIR}/signals_hermes_runtime.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM signals ORDER BY created_at DESC LIMIT 5000")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    with open(f'{WEB_DIR}/signals_data.json', 'w') as f:
        json.dump({'updated_at': datetime.now().isoformat(), 'signals': rows}, f)

def export_trades():
    # Read from brain SQLite or Postgres
    # Write web/trades_data.json
    pass

if __name__ == '__main__':
    export_signals()
    export_trades()
```

### Step 4 — Fix CSP on signals.html / trades.html

**Problem**: Inline `<script>` tags violate Content Security Policy when served by nginx.

**Fix in nginx.conf**:
```nginx
server {
    listen 127.0.0.1:8888;

    # CSP: allow inline scripts (needed for signals.html / trades.html)
    # In production, fix these HTML files to use external .js and remove 'unsafe-inline'
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; connect-src 'self' ws: wss:;";

    root /app/hermes/web;
    index signals.html trades.html;

    location / {
        try_files $uri $uri/ =404;
    }

    # Proxy /vnc → websockify
    location /vnc {
        proxy_pass http://127.0.0.1:6080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Proxy novnc static files
    location /novnc/ {
        proxy_pass http://127.0.0.1:6080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Better fix (long-term)**: Refactor `signals.html` and `trades.html` to load an external `dashboard.js` instead of inline scripts. Add `nonce` to scripts and configure nginx to add the nonce header.

### Step 5 — Ensure All Pipeline Scripts Are in the Image

Audit all scripts the pipeline needs and ensure they're all cloned/copied:
```bash
# From current host:
ls /root/.hermes/scripts/
# Compare against what's in the repo
```

If the repo is missing scripts that exist on the host, either:
- Add them to the repo first
- Or `COPY` them from the build context (not ideal — not in repo)

### Step 6 — Auto-Init DB Schema on First Start

In `docker-entrypoint.sh`:
```bash
# If signals DB is empty, load seed
if [ ! -s /app/hermes/data/signals_hermes_runtime.db ]; then
    echo "[entrypoint] Fresh DB — loading seed data..."
    # Create empty SQLite file and load schema + seed
    touch /app/hermes/data/signals_hermes_runtime.db
    sqlite3 /app/hermes/data/signals_hermes_runtime.db < /app/hermes/seed/signals_hermes.sql
fi

# Copy snapshot JSON to web dir (overwrites on fresh start)
cp /app/hermes/seed/signals_data_snapshot.json /app/hermes/web/signals_data.json 2>/dev/null || true
cp /app/hermes/seed/trades_data_snapshot.json /app/hermes/web/trades_data.json 2>/dev/null || true
```

### Step 7 — Pipeline Startup in entrypoint.sh

All pipeline scripts start in `tmux` sessions (so you can SSH in and `tmux attach` to watch them):
```bash
# Start tmux server (detached)
tmux new-session -d -s pipeline

# Start each pipeline component in its own tmux window
tmux new-window -t pipeline -n prices    'cd /app/hermes && python3 scripts/price_collector.py'
tmux new-window -t pipeline -n signals   'cd /app/hermes && python3 scripts/signal_gen.py'
tmux new-window -t pipeline -n decider   'cd /app/hermes && python3 scripts/ai_decider.py'
tmux new-window -t pipeline -n executor  'cd /app/hermes && python3 scripts/decider_run.py'
tmux new-window -t pipeline -n guardian  'cd /app/hermes && python3 scripts/hl_sync_guardian.py'
tmux new-window -t pipeline -n dashboard 'while true; do python3 scripts/export_dashboards.py; sleep 30; done'

# Optionally: Start a cron daemon and add the dashboard export as a cron job
```

### Step 8 — Paper Trading Mode (No Keys Required)

Set sensible defaults in `docker-entrypoint.sh` and/or `hermes_constants.py`:
```bash
export HL_WALLET_ADDRESS="0x0000000000000000000000000000000000000000"  # dummy
export HL_WALLET_PRIVATE_KEY="0x0000000000000000000000000000000000000000000000000000000000000000"  # dummy
export PAPER_MODE="true"
```

In `decider_run.py`, check `PAPER_MODE=true` → skip actual HL API calls, write to SQLite only.

Alternatively, use Hyperliquid's **testnet** if available, or the paper trading endpoint of the HL SDK.

**Key**: The pipeline should start and run even with dummy keys — it will generate signals and populate the DB/dashboards, just without executing real trades.

### Step 9 — Write All Files

Files to create (in order):

1. **`/app/hermes/requirements_docker.txt`** — pruned pip freeze from current host
2. **`/app/hermes/web/signals_data.json`** — seed snapshot (1,000+ signals)
3. **`/app/hermes/web/trades_data.json`** — seed snapshot (recent trades)
4. **`/app/hermes/seed/signals_hermes.sql`** — full SQLite schema + seed
5. **`/app/hermes/seed/schema_init.sql`** — PostgreSQL brain DB schema
6. **`/app/hermes/scripts/export_dashboards.py`** — generates the JSON files
7. **`/app/hermes/Dockerfile`**
8. **`/app/hermes/docker-entrypoint.sh`**
9. **`/app/hermes/sshd_config`**
10. **`/app/hermes/nginx.conf`** (CSP headers fixed)
11. **`/app/hermes/.env.docker`**
12. **`/app/hermes/docker-compose.yml`**

### Step 10 — Build and Verify

```bash
# Build
docker build -t hermes-core:latest .

# Run paper-trading mode (no keys needed)
docker run -d \
  --name hermes-core \
  -e PAPER_MODE=true \
  -p 127.0.0.1:3333:3333 \
  hermes-core:latest

# SSH in
ssh root@<host> -p 3333

# Inside container, check everything:
tmux attach -t pipeline  # watch live pipeline

# From host machine (tunnel first):
ssh -L 8888:127.0.0.1:8888 -L 5902:127.0.0.1:5902 root@<host> -p 3333
# Then open:
http://localhost:8888/signals.html    # signals dashboard
http://localhost:8888/trades.html     # trades dashboard
http://localhost:8888/vnc.html       # noVNC
```

**Verification checklist** (all via `docker exec hermes-core`):
- [ ] `sqlite3 /app/hermes/data/signals_hermes_runtime.db "SELECT COUNT(*) FROM signals"` → > 0
- [ ] `cat /app/hermes/web/signals_data.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['signals']))"` → > 0
- [ ] `curl http://localhost:8888/signals_data.json` → 200 with data
- [ ] `curl http://localhost:8888/signals.html` → 200
- [ ] `ps aux | grep -E "price_collector|signal_gen|ai_decider|decider_run"` → all running
- [ ] `chromium --version` → shows chromium version
- [ ] `nginx -t` → syntax OK

---

## Known Issues to Fix in Source Code

These bugs exist in the current codebase and should be fixed as part of this export:

| # | Issue | Fix |
|---|-------|-----|
| 1 | `signals_data.json` not generated continuously | Add `export_dashboards.py` + cron in entrypoint |
| 2 | CSP blocks inline scripts in `signals.html` | Add `Content-Security-Policy` header in nginx with `unsafe-inline`, or refactor HTML to use external `.js` |
| 3 | Pipeline requires PostgreSQL with exact schema | Add `schema_init.sql` seed + auto-init in entrypoint |
| 4 | No seed data for signals DB | Export current `signals_hermes_runtime.db` as `.sql` and include `signals_data_snapshot.json` |
| 5 | Hardcoded port 8080 in some scripts | Replace with `os.getenv('WEB_PORT', '8888')` or env var |

---

## Symlinks

Use symlinks for common paths to make the container easy to navigate:
```bash
# In entrypoint.sh or Dockerfile:
ln -sf /app/hermes/scripts  /hermes-scripts
ln -sf /app/hermes/web      /hermes-web
ln -sf /app/hermes/data     /hermes-data
ln -sf /app/hermes/logs     /hermes-logs
ln -sf /opt/novnc           /novnc
```

---

## Paper Trading Mode — How It Works

```
decider_run.py
  ├── PAPER_MODE=true? → brain.py trade add --paper (no HL API call)
  ├── PAPER_MODE=false → brain.py trade add --live (real HL API call)
  └── HL_WALLET_PRIVATE_KEY=dummy → HL SDK returns auth error on real calls
```

With `PAPER_MODE=true` and dummy keys, the full pipeline runs end-to-end:
`price_collector` → `signal_gen` → `ai_decider` → `decider_run` → `brain.py` (paper) → `signals_hermes_runtime.db` + `signals_data.json` (dashboard)

Real trades are **not** executed on Hyperliquid. Everything is paper.

---

## TODO Checklist

- [ ] **Step 1**: Audit pipeline scripts, entry points, dashboard JSON generation, seed files
- [ ] **Step 2**: Export `signals_hermes.sql` + `signals_data_snapshot.json` + `trades_data_snapshot.json` from current host
- [ ] **Step 3**: Write `export_dashboards.py` to continuously generate JSON files
- [ ] **Step 4**: Fix CSP in `nginx.conf` (add `unsafe-inline` or nonce)
- [ ] **Step 5**: Audit all 47 scripts — ensure they're all in the repo
- [ ] **Step 6**: Write auto-init DB logic in `docker-entrypoint.sh`
- [ ] **Step 7**: Write `docker-entrypoint.sh` with tmux pipeline + cron dashboard export
- [ ] **Step 8**: Verify paper trading mode works with dummy keys
- [ ] **Step 9**: Write all files (Dockerfile, nginx.conf, sshd_config, docker-compose.yml, etc.)
- [ ] **Step 10**: Build and verify — every checklist item above
- [ ] **Post-build**: Add symlinks (`/hermes-scripts`, `/hermes-web`, etc.)
- [ ] **Post-build**: Document SSH tunnel + browser access in README.docker
