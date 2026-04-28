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

## Closed Trade Data Quality Audit

Use these queries to audit closed trade data quality in PostgreSQL:

```sql
-- 1. Close reason distribution with PnL totals
SELECT close_reason, COUNT(*), AVG(pnl_pct), SUM(pnl_pct)
FROM trades WHERE server='Hermes' AND status='closed'
GROUP BY close_reason ORDER BY COUNT(*) DESC;

-- 2. Exit price validity
SELECT
    COUNT(*) FILTER (WHERE exit_price = 0 OR exit_price IS NULL) as zero_exit,
    COUNT(*) FILTER (WHERE exit_price = current_price) as eq_current_market,
    COUNT(*) FILTER (WHERE exit_price != 0 AND exit_price IS DISTINCT FROM current_price) as valid_exit,
    COUNT(*) as total
FROM trades WHERE server='Hermes' AND status='closed';

-- 3. Zero-PnL trades (not PHANTOM_CLOSE)
SELECT id, token, direction, pnl_pct, entry_price, exit_price, current_price, close_reason
FROM trades WHERE server='Hermes' AND status='closed' AND pnl_pct = 0 AND close_reason != 'PHANTOM_CLOSE';

-- 4. PHANTOM_CLOSE trades (exit_price=0)
SELECT id, token, direction, pnl_pct, entry_price, exit_price, current_price, leverage, close_time
FROM trades WHERE server='Hermes' AND status='closed' AND close_reason = 'PHANTOM_CLOSE';

-- 5. Duplicate token entries (no more than 1 open position per token)
SELECT token, COUNT(*) as open_count
FROM trades WHERE server='Hermes' AND status='open'
GROUP BY token HAVING COUNT(*) > 1;

-- 6. Entry feature NULL check (all should be populated)
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE entry_rsi_14 IS NULL) as null_rsi,
    COUNT(*) FILTER (WHERE entry_macd_hist IS NULL) as null_macd,
    COUNT(*) FILTER (WHERE entry_bb_position IS NULL) as null_bb,
    COUNT(*) FILTER (WHERE entry_regime_4h IS NULL) as null_regime
FROM trades WHERE server='Hermes' AND status IN ('open', 'closed');
```

## Known Data Quality Issues

| Issue | Symptom | Root Cause | Fix |
|-------|---------|------------|-----|
| PHANTOM_CLOSE | `exit_price=0, pnl_pct=0` | Guardian waits only 6s for HL fills; HL takes up to 5 min | Increase polling to 150s + PHANTOM_CLOSE retry queue |
| Exit = Current Price | `exit_price = current_price` | `_get_hl_exit_price()` falls back to market price when HL fills don't arrive | Same as above |
| Zero-PnL trades | `pnl_pct=0` but closed | `exit_price = entry_price` for unchanged positions | May be legitimate; verify with HL fill lookup |
| PROVE duplicates | 12 closed trades for 1 token | Re-entry without closing existing position | Add dedup check before new entries |

## DB vs Dashboard Divergence Pattern

**Symptom:** PostgreSQL `stop_loss`/`target` columns have correct/expected values, but dashboard shows wrong values (e.g., fixed 5% TP instead of ATR-computed values).

**Root Cause (common):** A second process is writing to the same DB columns after the primary updater, overwriting correct values with stale ones.

**Diagnosis:**
```bash
# Step 1: Query DB — are values correct there?
psql "host=/var/run/postgresql dbname=brain user=postgres" -t -c "
SELECT token, direction, entry_price, stop_loss, target,
       ROUND((stop_loss/entry_price - 1)*100, 2) as sl_pct,
       ROUND((target/entry_price - 1)*100, 2) as tp_pct
FROM trades WHERE status != 'closed' AND status != 'liquidated' ORDER BY token;"

# Step 2: Compare to dashboard
cat /var/www/hermes/data/trades.json | python3 -c "
import json, sys; d = json.load(sys.stdin)
for p in d.get('open', []):
    entry = float(p['entry']); sl = float(p.get('sl',0)); tp = float(p.get('tp',0))
    print(f\"{p['token']} SL={sl}({((sl/entry-1)*100):+.2f}%) TP={tp}({((tp/entry-1)*100):+.2f}%)\")"

# Step 3: Find ALL writers to stop_loss/target columns in DB
grep -n "stop_loss.*UPDATE\|UPDATE.*stop_loss\|target.*UPDATE\|UPDATE.*target" \
    /root/.hermes/scripts/*.py
```

**Fix:** Identify which writer is authoritative for each column. For ATR-based SL/TP:
- `position_manager` is the **sole owner** of `stop_loss` and `target` columns
- Any other writer (e.g., `hl-sync-guardian`) must write ONLY `entry_price`, `direction`, `leverage` — NOT `stop_loss` or `target`

**Lesson from 2026-04-15:** Three bugs stacked on ATR trailing:
1. `position_manager._pm_get_atr()` imported `decider_run._ATR_CACHE` (removed) → FATAL import error, pipeline crashed every cycle
2. `_dr_atr()` proxy imported removed `decider_run._atr_multiplier` → cascading import failures  
3. `hl-sync-guardian` UPDATE at line ~897 wrote `stop_loss`/`target` with fixed-% values every 30s, overwriting ATR values

**Checklist for ATR trailing issues:**
- [ ] DB has ATR-based SL/TP values (query above)
- [ ] Dashboard matches DB (compare percentages)
- [ ] Pipeline log: `grep "ATR.*Updated" /root/.hermes/logs/pipeline.log | tail -5`
- [ ] No FATAL import errors in pipeline log
- [ ] No second process overwriting SL/TP columns in DB

## Common Traps

- `/root/.hermes/data/trades.json` may be **empty/stale** — the real file is at `/var/www/hermes/data/trades.json`
- Port 59999 `python3 -m http.server` serves **root filesystem**, unrelated to dashboard
- Port 8501 streamlit serves a **different ML dashboard**, not the trades dashboard
- `SKIP_COINS` in guardian (`{'AAVE', 'MORPHO', 'ASTER', 'PAXG', 'AVNT'}`) bypasses reconcile loop
- **ATR values come from `atr_cache.json`** (local file, no HL API) — never hit HL for ATR
- **`_dr_atr()` and `_pm_get_atr()` in position_manager** — these are the only ATR sources for trailing; any import from `decider_run` for ATR is broken/dead code
