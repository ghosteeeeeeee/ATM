# Price Collector Signal Cascade — 2026-05-28

## Symptom
Signals dead, hotset empty, no trades in 24h. All tokens show "stale price_history" in mtp_zscore logs.

## Root Cause Chain

```
price_collector timer fires every 60s
    → script takes ~90s (allMids + save_prices + _aggregate_tf × 4 + candle_seed)
    → timer fires again at t=60 while previous run still going
    → second instance hits "database is locked" on signals_hermes.db
    → crashes → price_history goes stale (not updated)
    → all signal scripts check staleness gate (120s threshold)
    → every token skipped → 0 signals → empty hotset → no trades
```

## Investigation Path

1. **Check price_history freshness:**
   ```python
   conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
   max_ts = conn.execute('SELECT MAX(timestamp) FROM price_history').fetchone()[0]
   print(f'Age: {time.time() - max_ts:.0f}s')  # >120s = stale
   ```

2. **Check what's locking the DB:**
   ```bash
   fuser /root/.hermes/data/signals_hermes.db  # shows PIDs
   ps aux | grep <PID>  # identifies the script
   ```

3. **Check candles.db WAL size:**
   ```bash
   ls -lh /root/.hermes/data/candles.db-wal  # large WAL = uncommitted changes piling up
   ```

4. **Check for concurrent aggregators:**
   ```bash
   ps aux | grep -E "_aggregate|price_collector" | grep -v grep
   systemctl list-timers --all | grep -E "1m|5m|price"
   ```

## Phase Timing (measured 2026-05-28)

Run this to profile each phase yourself:
```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from paths import *; import hype_cache as hc; import sqlite3, time

# 1: HL fetch
t0 = time.time(); hc.fetch_and_cache(); print(f'hype_cache: {time.time()-t0:.1f}s')

# 2: price write
from signal_schema import upsert_prices_from_allMids
cached = hc._read()
tokens = {u['name']: u.get('maxLeverage', 10) for u in cached.get('meta', {}).get('universe', [])}
prices = {k: float(v) for k, v in cached.get('allMids', {}).items() if v}
prices_clean = {k: v for k, v in prices.items() if k in tokens}
t0 = time.time(); upsert_prices_from_allMids(prices_clean, tokens); print(f'upsert: {time.time()-t0:.1f}s')

# 3: per-TF aggregation timing
conn = sqlite3.connect(STATIC_DB)
cconn = sqlite3.connect(CANDLES_DB, timeout=30); cconn.execute('PRAGMA journal_mode=WAL')
for tbl in ['candles_5m', 'candles_15m', 'candles_1h']:
    t0 = time.time()
    rows = cconn.execute(f'SELECT token, MAX(ts) FROM {tbl} WHERE is_closed=1 GROUP BY token').fetchall()
    print(f'{tbl} GROUP BY ({len(rows)} tokens): {time.time()-t0:.1f}s')
```

## Fixes Applied (2026-05-28)

### Fix 1: Blacklist filter in price_collector.py
Skips 130 blacklisted tokens during price write + aggregation.
- `save_prices()`: filters `tokens_clean` and `prices_clean` — only ~92 tokens stored
- `_aggregate_tf()`: filters `last_closed_dict` + `dev_rows` — ~79 tokens skipped per TF
- Eliminated ~2,600 queries per run

### Fix 2: Disabled candles_4h aggregation
None of the live signals (mtp_zscore, support_resistance, zscore_pump) use 4h candles.
Removed `(14400, 'candles_4h')` from the TF loop in `price_collector.py`.
- Reduces aggregation from 4 TFs → 3 TFs
- candles.db stops growing 4h data

### Fix 3: Removed second save_prices() call + disabled seed_universe_candles

`price_collector.py` called `save_prices()` twice per run:
- Line 543: after fetching, writes to signals_hermes.db
- Line 567: after ALL aggregation — redundant, prices haven't changed

Second call doubled DB write time unnecessarily. Removed line 567 call.

Also disabled `_seed_universe_candles(universe)` — it made 10 Binance API calls with 10s
timeout each (= up to 100s blocking), opened candles.db with only 10s timeout (failed when
candles.db was still locked from aggregation).

### Fix 4: Disabled competing candle aggregator timers

`hermes-1m-candle.timer` fires at :30 every minute — overlaps with price_collector
(which starts at :00 and takes ~30s). Both write to candles.db simultaneously → WAL
lock contention → timeouts.

Disabled both:
```bash
systemctl disable hermes-1m-candle.timer hermes-5m-candle.timer
systemctl stop hermes-1m-candle.timer hermes-5m-candle.timer
```

price_collector now handles all candle aggregation internally via `_aggregate_tf()`.
No more concurrent writers to candles.db.

### Fix 5: Timer should be changed to 2min (pending)

Once price_collector is stable at <60s runtime, change the timer to prevent future pile-up:
```
sed -i 's/OnUnitActiveSec=1min/OnUnitActiveSec=2min/' /etc/systemd/system/hermes-price-collector.timer
systemctl daemon-reload && systemctl restart hermes-price-collector.timer
```

## Key Files

- `/root/.hermes/scripts/price_collector.py` — price + candle collection
  - Blacklist filter applied (lines 23-26, ~268, ~413, ~508)
  - 4h candles disabled (line 554)
  - Second save_prices() removed (~566)
  - seed_universe_candles disabled (~570)
- `/root/.hermes/scripts/_aggregate_1m.py` — 1m candle aggregator (now disabled)
- `/root/.hermes/scripts/_aggregate_5m.py` — 5m candle aggregator (now disabled)
- `/root/.hermes/data/candles.db` — 3.4GB, candles_5m=17.5M rows
- `/root/.hermes/data/signals_hermes.db` — 1.25GB, price_history=15.7M rows

## Post-Fix Verification (2026-05-28)

```bash
# Manual run — should complete in ~30s
cd /root/.hermes/scripts && timeout 90 python3 price_collector.py
# Expected output:
#   [price_collector] Skipped 505 blacklisted tokens
#   Collected 92 prices at HH:MM:SS
#   candles_5m: last closed window XXXX (HH:MM:SS)
#   candles_15m: last closed window XXXX (HH:MM:SS)
#   candles_1h: last closed window XXXX (HH:MM:SS)
#   EXIT: 0

# Check price_history freshness
python3 -c "
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
now = int(time.time())
cur = conn.execute('SELECT COUNT(*) FROM (SELECT token FROM price_history GROUP BY token HAVING MAX(timestamp) > ?)', (now-120,))
print(f'Fresh tokens (<2min): {cur.fetchone()[0]}')
"
```

## Remaining Issues

1. Timer still at 1min — increase to 2min to prevent pile-up
2. candles_5m GROUP BY is 6.9s — partial index on is_closed=1 would help:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_candles_5m_closed ON candles_5m(token, ts) WHERE is_closed=1;
   ```
3. `_aggregate_1m.py` and `_aggregate_5m.py` still exist but are disabled — consider removing their systemd timer symlinks permanently

## Timer Configuration

```bash
# Current (problematic)
cat /etc/systemd/system/hermes-price-collector.timer
# OnUnitActiveSec=1min

# Change to 2min to prevent overlap:
sed -i 's/OnUnitActiveSec=1min/OnUnitActiveSec=2min/' /etc/systemd/system/hermes-price-collector.timer
systemctl daemon-reload && systemctl restart hermes-price-collector.timer
```

## Confluence Gate — Why Hotset Still Empty After Price Collector Fix

After price_collector was fixed, STBL SHORT appeared as a valid signal (z=-2.174, conf=85%)
but the hotset stayed empty. The reason: **CONFLUENCE-GATE-BLOCK**.

signal_compactor requires 2+ distinct signal types for same token+direction before writing to hotset.json.
Only `mtp_zscore` is firing signals. `rs` (support_resistance) and `zscore_pump` are not generating signals.

Log evidence:
```
🔒 [CONFLUENCE-GATE-BLOCK] STBL SHORT: only 1 unique types {mtp-zscore-} — need 2+
```

This is NOT a data freshness problem — it's a signal diversity problem. The confluence gate
is correctly blocking single-source signals. To get trades again:
1. Other signal types (rs, zscore_pump) need to start firing alongside mtp_zscore
2. Or the confluence threshold needs to be relaxed (not recommended — would let single-source noise through)

The price_collector fix restored data freshness. The confluence gate is now correctly filtering
on signal quality, not data availability.