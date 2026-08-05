# Price Collector — Timing & Lock Contention (2026-05-16)

## Measured Cycle Time

**Total: ~87s**

| Step | Duration | Notes |
|------|----------|-------|
| Python imports | 2.0s | One-time cost per run |
| `fetch_all_prices()` HL API | 0.1s | Very fast — cached connection |
| `save_prices()` DB write | 2.0s | Writes 190 tokens + backfill gaps |
| `_aggregate_tf()` x4 TFs | **82s** | candles.db WAL lock contention |
| `_seed_universe_candles()` | 0.0s | Negligible |

The 4-TF candle aggregation step (5m/15m/1h/4h into candles.db) is the bottleneck.

## Staleness Threshold Issue

zscore_pump.py `_get_1m_prices()` line 145:
```python
if (time.time() - most_recent_ts) > 120:
    return []  # → stale warning
```

At 87s nominal cycle time, the 120s threshold is barely sufficient. Any lock contention on candles.db (which also affects price_collector completing its writes) pushes the effective staleness past 120s.

**False stale warning example** (2026-05-16 17:01):
- Last price_collector run: 16:49 (age 3.6 min at scan time)
- price_collector.service was still running the candle aggregation step
- zscore_pump scanned while awaiting next collector run
- 183/191 tokens still valid — data was NOT actually stale, just mid-gap between runs

**Fix:** Raise to 180s — absorbs lock-contention variance without changing architecture.

## Lock Contention Pattern

```
price_collector.py  (PID A) — holding candles.db WAL lock
  └─ _aggregate_tf() for 5m/15m/1h/4h

hermes-1m-candle.service (PID B) — _aggregate_1m.py also needs candles.db WAL
  └─ "database is locked" — blocked by PID A
```

**Result:** price_collector gets "database is locked" for all 4 TF aggregations. They still succeed on retry after PID B releases. But this adds latency.

The two aggregators are redundant — price_collector already aggregates all TFs including 1m. The separate `hermes-1m-candle.timer` adds lock contention with no benefit.

## DB Freshness Check

```python
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
c.execute("SELECT MAX(timestamp), COUNT(DISTINCT token) FROM price_history")
r = c.fetchone()
print(f"Max ts: {r[0]} ({time.ctime(r[0])}), age={time.time()-r[0]:.0f}s, tokens={r[1]}")
conn.close()
```