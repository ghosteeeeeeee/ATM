# price_collector "database is locked" incident — 2026-05-27

## Timeline (all UTC)
- ~23:11 — price_collector starts failing with `sqlite3.OperationalError: database is locked`
- Service restarts but each run crashes with the same error
- 23:16 — last successful price data at ts `1779923501` (23:18:21)
- After 23:19 — price_collector pile-up: 2 instances running simultaneously
- 23:19:59 — manual kill of stuck instances, clean restart
- 23:20+ — price_history starts updating again

## Root Cause
`hermes-price-collector.service` is `Type=oneshot`. Script runtime is ~100s.
Timer (`hermes-price-collector.timer`) fires every 60s.
Since oneshot exits after each run, next timer fires before previous run completes.
Second instance races first for DB write access → "database is locked" → crash.
After crash, service restarts immediately → pile-up of 2+ instances.

## Key Diagnostic Commands
```bash
# Are there multiple instances?
ps aux | grep price_collector | grep -v grep
# Should be exactly 1. More = overlap.

# What's holding the DB lock?
lsof /root/.hermes/data/signals_hermes.db

# Check recent crashes
journalctl -u hermes-price-collector.service --since "20 minutes ago" | grep -E "locked|exit-code|Failed"

# Check price_history freshness
python3 -c "
import sqlite3, datetime
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
c.execute('SELECT MAX(timestamp) FROM price_history')
row = c.fetchone()
max_ts = row[0] if row else None
now = datetime.datetime.now().timestamp()
age = (now - (max_ts or 0))
print(f'Age: {age:.0f}s (threshold=120s)')
print('STALE' if age > 120 else 'FRESH')
conn.close()
"

# Check timer interval
systemctl cat hermes-price-collector.timer | grep -E "OnUnitActiveSec|OnBootSec"
```

## The Fix
Change timer interval to match or exceed script runtime:

```bash
# Option 1: Change timer to 2min (recommended — >= script runtime)
sudo systemctl edit hermes-price-collector.timer
# Add:
# [Timer]
# OnUnitActiveSec=2min

# Option 2: Keep 1min but allow overlapping starts (less safe)
# In service unit:
# [Service]
# Restart=on-failure
# RestartSec=5s
```

## Service Definition
```
Type=oneshot
Runtime: ~100s
Timer fires: every 60s
→ gap: ~40s overlap window per cycle
→ eventual pile-up after ~2 cycles
```

## Signal Cascade When price_collector Is Down
1. `price_history` table in `signals_hermes.db` stops updating
2. `mtp_zscore.py` (and all signal scripts) check `if (now - most_recent_ts) > 120: skip`
3. All 190 tokens marked "stale price_history, skipping" → 0 signals produced
4. `signal_compactor.py` gets 0 signals → hotset writes `{"hotset": [], ...}`
5. `decider_run.py` reads empty hotset → `APPROVED=0`
6. `position_manager.py` has nothing to manage, 0 open positions
7. Zero trades executed

## Verified: Pipeline Itself Was Healthy
- `hermes-pipeline.timer` active and firing every 1 min
- All pipeline steps (compactor, breakout, decider, position_manager) running
- The pipeline was correctly processing 0 signals — it just never had any to process
- Guardian (separate process) was also healthy — no trades because no signals reached it
