# RS Signal Price Source Verification — 2026-06-08

## What Was Confirmed

### RS correctly uses price_history, NOT candles.db

Signal scripts use ONE of two data sources for 1m candles:

| Signal | Data Source | DB Table |
|--------|-------------|----------|
| `rs.py` (support_resistance) | `price_history` | `signals_hermes.db` |
| `accel_300.py` | `price_history` | `signals_hermes.db` |
| `ma_cross.py` | `price_history` | `signals_hermes.db` |
| `mtp_zscore.py` | `price_history` | `signals_hermes.db` |
| `zscore_pump.py` | `price_history` | `signals_hermes.db` |
| `guppy.py` | `candles_4h` | `candles.db` |

**RS (rs.py line 667):**
```python
_PRICE_DB = '/root/.hermes/data/signals_hermes.db'
# reads from price_history table
```

**candles.db is NOT used by RS.** `candles.db` contains pre-aggregated multi-TF data (candles_1m, candles_5m, candles_15m, candles_1h, candles_4h) written by `price_collector._aggregate_tf()`. RS reads directly from `price_history` in `signals_hermes.db`.

## Current Data State (2026-06-08)

### signals_hermes.db

| Table | Fresh | Stale | Total |
|-------|-------|-------|-------|
| `price_history` | 87 tokens (<120s) | 143 tokens | 230 |
| `ohlcv_1m` | 0 | 104 (all stale) | 104 |

**87 fresh tokens** — these are the tokens currently returned by HL `allMids`.  
**143 stale tokens** — delisted or no longer in HL universe; last updated ~May 28.

### candles.db

| Table | Fresh | Stale | Total |
|-------|-------|-------|-------|
| `candles_1m` | 0 | 230 (~11 days old) | 230 |
| `candles_5m` | 0 | 230 | 230 |
| `candles_15m` | 0 | 230 | 230 |
| `candles_1h` | 0 | 230 | 230 |

`candles.db` was seeded from `price_history` backfill on May 28. No new 1m candles are being generated — the `price_collector` aggregates 1m closes from `price_history` into `candles_1m`, but since `price_history` itself is stale for 143 tokens, the aggregation is also stale.

## RS Staleness Guard (rs.py line 699)

```python
most_recent_ts = rows[-1][0]  # seconds
if (time.time() - most_recent_ts) > 120:
    print(f"  [rs] {token}: stale price_history (last ts {most_recent_ts}, skipping)")
    return []
```

120-second threshold. If `price_history` entry is >120s old, RS returns `[]` — no signal generated.

## Blacklist Guards in RS (rs.py lines 760-763)

```python
token_upper = token.upper()
if sig['direction'] == 'LONG' and token_upper in LONG_BLACKLIST:
    continue
if sig['direction'] == 'SHORT' and token_upper in SHORT_BLACKLIST:
    continue
```

These fire AFTER the staleness guard. For stale tokens: staleness guard fires first → `[]` returned → no blacklist check reached.

## Why 143 Tokens Are Stale

HL's `allMids` returns ~87 active tokens. The other ~143 tokens (delisted, low-volume, or removed from HL universe) haven't appeared in `allMids` since the last backfill (~May 28). `price_collector` only writes prices for tokens in the current `allMids` universe — it does NOT backfill delisted tokens.

**This is expected behavior**, not a bug. Tokens not in `allMids` cannot be traded on HL, so stale prices for them are harmless.

## Systemd State: "activating" Is Normal for Type=oneshot

`hermes-price-collector.service` is `Type=oneshot`. systemd shows it as "activating (start)" while the process runs, then transitions to "deactivated successfully" when it exits. Each run takes ~90s.

**journalctl output (healthy run):**
```
Jun 08 13:34:21 python3[3448886]: Static DB already has 18127647 price_history rows
Jun 08 13:34:21 python3[3448886]:   [price_collector] Skipped 609 blacklisted tokens (not storing to DB)
Jun 08 13:34:21 python3[3448886]:   Collected 87 prices at 13:34:21
Jun 08 13:34:21 python3[3448886]:   candles_5m: last closed window 1780925100 (13:25:00)
Jun 08 13:34:21 python3[3448886]:   candles_15m: last closed window 1780924500 (13:15:00)
Jun 08 13:34:21 python3[3448886]:   candles_1h: last closed window 1780920000 (12:00:00)
Jun 08 13:34:21 systemd[1]: hermes-price-collector.service: Deactivated successfully.
Jun 08 13:34:21 systemd[1]: Finished hermes-price-collector.service - Hermes Price Collector.
Jun 08 13:34:21 systemd[1]: Consumed 1min 30.917s CPU time.
```

This is CORRECT behavior. The service completes successfully each cycle.

## How to Verify

```bash
# Check price_history freshness per token
python3 -c "
import sqlite3, time
db = '/root/.hermes/data/signals_hermes.db'
conn = sqlite3.connect(db, timeout=10)
now = time.time()
c = conn.cursor()
c.execute('SELECT COUNT(DISTINCT token) FROM price_history WHERE ? - timestamp <= 120', (now,))
print(f'Fresh tokens in price_history (<2min): {c.fetchone()[0]}')
c.execute('SELECT COUNT(DISTINCT token) FROM (SELECT token, MAX(timestamp) as ts FROM price_history GROUP BY token HAVING ts < ?)', (now-120,))
print(f'Stale tokens: {c.fetchone()[0]}')
"

# Check which tokens are fresh
python3 -c "
import sqlite3, time
db = '/root/.hermes/data/signals_hermes.db'
conn = sqlite3.connect(db, timeout=10)
now = time.time()
c = conn.cursor()
c.execute('SELECT token, MAX(timestamp), ? - MAX(timestamp) FROM price_history GROUP BY token ORDER BY ? - MAX(timestamp) LIMIT 10', (now, now))
print('Most stale tokens:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[2]:.0f}s old')
"

# Confirm RS data source
grep "_PRICE_DB\|price_history" /root/.hermes/scripts/signals/rs.py | head -5

# Check candles.db staleness
python3 -c "
import sqlite3, time
db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(db, timeout=10)
now = time.time()
c = conn.cursor()
c.execute('SELECT token, MAX(ts), ? - MAX(ts) FROM candles_1m GROUP BY token LIMIT 5', (now,))
print('candles_1m freshness:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[2]/3600:.1f}h old')
"

# Check systemd state (normal for oneshot)
systemctl status hermes-price-collector.service
journalctl -u hermes-price-collector.service -n 10
```

## Signal-Level Impact

For **RS signals specifically**:
- 87 fresh tokens → RS can generate signals (subject to blacklist guards)
- 143 stale tokens → RS staleness guard fires → `[]` returned → no signals
- Blacklist guards (lines 760-763) correctly filter blacklisted tokens before `add_signal()` is called
- Confluence gate requires 2+ signal types → even valid RS signals may be blocked if no other signal type fires for the same token
