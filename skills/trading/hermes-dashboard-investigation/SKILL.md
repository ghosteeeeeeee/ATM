---
name: hermes-dashboard-investigation
description: Investigate why data doesn't appear in Hermes trades.html dashboard
trigger: "When trades.html shows empty/wrong data, or when investigating the trades data pipeline"
---

# Hermes Dashboard Investigation Pattern

## Critical Path
```
Guardian (hl-sync-guardian.py)
  → PostgreSQL brain DB (trades table)
  → hermes-trades-api.py (pipeline, every 1 min)
  → /var/www/hermes/data/trades.json       ← LIVE DATA (95KB)
  → nginx :54321 → /data/trades.json      ← SERVED BY NGINX
  → trades.html (JS fetch every 30s)
```

**Two trades.json files — know which is which:**
- `/var/www/hermes/data/trades.json` — **LIVE**, served by nginx, written by hermes-trades-api.py from PostgreSQL
- `/root/.hermes/data/trades.json` — **STALE/SEED**, may be empty or old, NOT served by anything
- `/root/.hermes/web/data/trades.json` — **OLD SEED**, not used since Apr 5

**Pipeline runs every 1 minute** (fixed from 10 min on 2026-04-14). guardian writes to PostgreSQL, hermes-trades-api.py reads PostgreSQL and writes to `/var/www/hermes/data/trades.json`.

## Investigation Steps

1. **Find the HTTP server** — `ss -tlnp | grep <port>` to identify what serves the endpoint
2. **Check nginx config** — for aliases like `alias /var/www/hermes/data/trades.json`
3. **Find what writes the JSON** — grep scripts for `trades.json` writes
4. **Check pipeline logs** — `pipeline.log` shows who writes the data file each cycle
5. **Map the data source** — guardian writes to PostgreSQL brain DB, not directly to the JSON

## Common Traps

- `/root/.hermes/data/trades.json` may be **empty/stale** — the real file is at `/var/www/hermes/data/trades.json`
- Port 59999 `python3 -m http.server` serves **root filesystem**, unrelated to dashboard
- Port 8501 streamlit serves a **different ML dashboard**, not the trades dashboard
- `SKIP_COINS` in guardian (`{'AAVE', 'MORPHO', 'ASTER', 'PAXG', 'AVNT'}`) bypasses reconcile loop
