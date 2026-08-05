# Signal Debugging Probes & Scripts

Quick diagnostic commands for troubleshooting signal issues in the Hermes trading system.

## Hot-set Health Check

```bash
cat /var/www/hermes/data/hotset.json | python3 -c "
import json, sys, time
d = json.load(sys.stdin)
print(f'Entries: {len(d.get(\"entries\",[]))}')
for e in d.get('entries',[]):
    age = (time.time() - e.get('added_at',0))/60
    print(f'  {e[\"token\"]:10} {e[\"direction\"]:5} conf={e[\"confidence\"]:5.1f} age={age:.1f}m sig={e.get(\"signal\",\"\")[:30]}')
"
```

## Signal DB Counts by Type (last 24h)

```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "
SELECT signal_type, direction, COUNT(*) as cnt
FROM signals WHERE created_at >= datetime('now','-24 hours')
GROUP BY signal_type, direction ORDER BY cnt DESC LIMIT 20;
"
```

## Opp/Same Ratio Check (per token)

Check opposing vs same-dir signals in 60-min window before a trade:

```bash
# For token NIL, opposing vs same-dir in last 60 min
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "
SELECT direction, COUNT(*) FROM signals
WHERE token='NIL'
  AND created_at >= datetime('now','-60 minutes')
  AND signal_type IN ('zscore_pump_long','zscore_pump_short','support_resistance')
GROUP BY direction;
"
```

## PostgreSQL Trade Audit (last 24h)

```bash
sudo -u postgres psql -d brain -c "SELECT token, direction, pnl_pct, close_reason
FROM trades WHERE close_time >= NOW() - INTERVAL '24 hours' AND status='closed'
ORDER BY pnl_pct DESC LIMIT 20;"
```

## Trade P&L by RS Touch Count

```bash
sudo -u postgres psql -d brain -c "
WITH trades_24h AS (
  SELECT token, direction, pnl_pct, signal,
         CASE WHEN pnl_pct > 0 THEN 'WIN' ELSE 'LOSS' END as outcome
  FROM trades WHERE close_time >= NOW() - INTERVAL '24 hours' AND status='closed'
)
SELECT 
  COUNT(*) as trades,
  AVG(pnl_pct) as avg_pct,
  COUNT(CASE WHEN outcome='WIN' THEN 1 END) as wins
FROM trades_24h;
"
```

## Postgres + SQLite Combined Opp/Same Analysis

Python script pattern (use in execute_code or terminal):

```python
import sqlite3, subprocess

conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()

# Get trades
result = subprocess.run(['sudo','-u','postgres','psql','-d','brain','-t','-A','-c',
    "SELECT token, direction, pnl_pct, open_time::text, signal FROM trades WHERE close_time >= NOW() - INTERVAL '24 hours' AND status='closed'"],
    capture_output=True, text=True)

trades = []
for line in result.stdout.strip().split('\n'):
    if not line.strip(): continue
    p = line.split('|')
    if len(p) >= 5:
        trades.append({'token':p[0], 'direction':p[1], 'pnl_pct':float(p[2]) if p[2] else 0,
                       'open_time':p[3].strip(), 'signal':p[4], 'outcome':'WIN' if float(p[2])>0 else 'LOSS'})

# For each trade, count opp/same in 60-min window
for t in trades:
    opp_dir = 'SHORT' if t['direction']=='LONG' else 'LONG'
    open_raw = t['open_time'].replace(' ','T')
    c.execute(f"SELECT COUNT(*) FROM signals WHERE token='{t['token']}' AND direction='{opp_dir}' AND created_at<'{open_raw}' AND created_at>=datetime('{open_raw}','-60 minutes') AND signal_type IN ('zscore_pump_long','zscore_pump_short','support_resistance')")
    t['opp_60m'] = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM signals WHERE token='{t['token']}' AND direction='{t['direction']}' AND created_at<'{open_raw}' AND created_at>=datetime('{open_raw}','-60 minutes') AND signal_type IN ('zscore_pump_long','zscore_pump_short','support_resistance')")
    t['same_60m'] = c.fetchone()[0]
```