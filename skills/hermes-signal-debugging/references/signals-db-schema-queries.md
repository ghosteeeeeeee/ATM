# Signal Debugging — Reference Bank (Session-Aggregated)

Reference material for hermes-signal-debugging skill. Moved from SKILL.md to reduce size.

## signals_hermes.db — Schema & Query Patterns

### Tables and Columns
- `price_history`: token, price, timestamp (Unix **seconds**, NOT ms)
- `ohlcv_1m`: token, open_time (Unix **milliseconds**), open/high/low/close/volume
- `regime_log`: regime, broad_z, long_mult, short_mult, timestamp (**no token column**)
- `latest_prices`: token, price, timestamp

### Query Patterns

```python
import sqlite3, datetime
est = datetime.timezone(datetime.timedelta(hours=-5))

db = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cs = db.cursor()

# Price history — ts in SECONDS
ts_start = int(datetime.datetime(2026, 5, 22, 0, 0, 0, tzinfo=est).timestamp())
ts_end   = int(datetime.datetime(2026, 5, 22, 4, 0, 0, tzinfo=est).timestamp())
cs.execute("""
    SELECT * FROM price_history
    WHERE token = ? AND timestamp >= ? AND timestamp <= ?
    ORDER BY timestamp
""", ('FET', ts_start, ts_end))

# regime_log — no token column, filter by timestamp only
cs.execute("""
    SELECT * FROM regime_log
    WHERE timestamp >= ? AND timestamp <= ?
    ORDER BY timestamp
""", (ts_start, ts_end))
```

### Common Bug: Wrong Timestamp Unit
- `candles.db ts` = **seconds** (e.g., 1779421080)
- `signals_hermes.db ohlcv_1m open_time` = **milliseconds** (e.g., 1779421080000)
- `price_history timestamp` = **seconds**
- Wrong unit → empty results or "year out of range" ValueError

---

## candles.db — Schema & Query Patterns

### Tables
- `candles_1m`, `candles_5m`, `candles_15m`, `candles_1h`, `candles_4h`
- Columns: token, ts (Unix **seconds**), open, high, low, close, volume, is_closed

### Query Pattern
```python
db_c = sqlite3.connect('/root/.hermes/data/candles.db')
cc = db_c.cursor()

ts_start = int(datetime.datetime(2026, 5, 22, 0, 0, 0, tzinfo=est).timestamp())
cc.execute("""
    SELECT ts, open, high, low, close, volume
    FROM candles_1m
    WHERE token = 'FET' AND ts >= ? AND ts <= ?
    ORDER BY ts
""", (ts_start, ts_end))
```

---

## Data Staleness Check — Always Do First

Before attempting to verify any signal against local data:
1. Check `MAX(ts)` / `MAX(timestamp)` for the token in the relevant table
2. Compare to the signal timestamp
3. If signal time > local max time → **CANNOT VERIFY**, report this first

```python
# Quick staleness probe
cc.execute("SELECT MAX(ts) FROM candles_1m WHERE token = 'FET'")
r = cc.fetchone()
max_local = datetime.datetime.fromtimestamp(r[0], tz=est)
signal_time = datetime.datetime(2026, 5, 22, 2, 0, 0, tzinfo=est)  # EST
print(f"Local max: {max_local} | Signal: {signal_time} | Gap: {signal_time - max_local}")
```

---

## 02:08:07 SHORT at z=+3.896 — Counter-Trend Flag

Signal: `rs-r90,rs-r96` SHORT at z=3.896, decision=EXPIRED.

During the 00:00–04:00 window, zscore-pump+ fires LONG 13 times. A SHORT at z=+3.9 is:
- A counter-trend bet (momentum indicator at extreme positive, betting on reversal)
- Plausible if calling a local top
- But zscore-pump+ (momentum pump) confluent LONG signals suggest trend-following is stronger
- Counter-trend SHORT at z=+3.9 should require very strong confluence to act on

Pattern worth noting: when zscore-pump+ is firing LONG repeatedly, a SHORT at z>3 is a divergence signal — needs to be weighed against the aggregate momentum direction.