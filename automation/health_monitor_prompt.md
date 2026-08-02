# Pipeline Health Monitor + System Status Dashboard

You are the system health checker for the Hermes trading bot. Check pipeline health and report status.

## Step 1: Pipeline Health (last 30 minutes)

Run these checks:
```bash
# Recent pipeline output
journalctl -u hermes-pipeline.service --since "30 minutes ago" --no-pager | tail -20

# Check for errors
journalctl -u hermes-pipeline.service --since "30 minutes ago" --no-pager | grep -i "error\|fail\|exception" | tail -10
```

**Check for:**
- Signals generated (should be >0 in 30min)
- Hotset status (should have entries if signals exist)
- Trade execution (any new trades opened/closed)
- Errors or exceptions

## Step 2: Signal Generation Status

```bash
# Last signal timestamp
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT MAX(created_at) FROM signals"

# Signals in last hour
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT signal_type, COUNT(*) FROM signals WHERE created_at > datetime('now', '-1 hour') GROUP BY signal_type"
```

**Alert if:** 0 signals in last hour (may indicate data issue or overly restrictive params)

## Step 3: Active Positions

```bash
# Check open positions
journalctl -u hermes-pipeline.service --since "30 minutes ago" --no-pager | grep "Open positions"
```

## Step 4: System Status Summary

### Timers
```bash
systemctl list-timers hermes-* --no-pager
```

### Speed Distribution
```bash
cd /root/.hermes/scripts && python3 -c "
import sqlite3
from paths import RUNTIME_DB
conn = sqlite3.connect(RUNTIME_DB)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM token_speeds WHERE speed_percentile >= 50')
above_50 = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM token_speeds')
total = cur.fetchone()[0]
cur.close()
conn.close()
print(f'Speed: {above_50}/{total} tokens >= 50% ({above_50/total*100:.0f}%)')
"
```

### Regime Distribution
```bash
cat /var/www/hermes/data/regime_5m.json | python3 -c "
import json,sys
d = json.load(sys.stdin)
agg = d.get('aggregate', {})
print(f'Regime: {agg.get(\"long_bias\",0)} LONG / {agg.get(\"short_bias\",0)} SHORT / {agg.get(\"neutral\",0)} NEUTRAL')
"
```

### Blacklist Status
```bash
cd /root/.hermes/scripts && python3 -c "
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
print(f'Blacklist: {len(SHORT_BLACKLIST)} SHORT / {len(LONG_BLACKLIST)} LONG')
"
```

### Price Data
```bash
sqlite3 /root/.hermes/data/signals_hermes.db "SELECT COUNT(*) FROM latest_prices"
```

## Step 5: Report Format

Output a compact status report:

```
=== Hermes Health Report ===
Time: YYYY-MM-DD HH:MM UTC

PIPELINE: [OK/WARN/ERROR]
- Signals (1h): X generated
- Hotset: X tokens
- Trades: X open, X closed today
- Errors: X (or None)

MARKET:
- Regime: X LONG / X SHORT / X NEUTRAL
- Speed: X% tokens >= 50%

SYSTEM:
- Timers: X active
- Prices: X tokens
- Blacklist: X SHORT / X LONG

LAST AUTO-1HR: [time] — [brief summary of changes]
```

## Step 6: Alert Conditions

If any of these are true, flag as WARN or ERROR:
- 0 signals in last hour → WARN (check signal generation)
- Pipeline errors → ERROR
- Timer not running → ERROR
- Price data stale (>5min) → WARN
- 0 tokens with speed >= 50% → WARN (market too quiet)

## Key File Paths
- Pipeline logs: `journalctl -u hermes-pipeline.service`
- Signal DB: `data/signals_hermes_runtime.db`
- Price DB: `data/signals_hermes.db`
- Speed DB: via RUNTIME_DB
- Regime: `/var/www/hermes/data/regime_5m.json`
- Constants: `scripts/hermes_constants.py`
