# Price Action Data Source for Closed-Trade Analysis

**For 1m-resolution price action during a trade, use `price_history` in `/root/.hermes/data/signals_hermes.db`.**

## Schema

```sql
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY,
    token TEXT,
    price REAL,
    timestamp INTEGER  -- Unix seconds
);
```

## Query pattern

```python
import sqlite3
db = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = db.cursor()
cur.execute("""
    SELECT timestamp, price FROM price_history
    WHERE token=? AND timestamp BETWEEN ? AND ?
    ORDER BY timestamp
""", (token, open_unix, close_unix))
```

## Common Pitfalls

**Pitfall 1: column is `timestamp` not `ts`.** A query like `SELECT MAX(ts) FROM price_history` returns "no such column" error and looks like the table is empty. The 20M+ row table is fine; the column name is the trap.

**Pitfall 2: don't use 5m candles for in-trade analysis.** `candles_5m` in `/root/.hermes/data/candles.db` has 5m resolution and misses intra-bar wicks. For MFE/MAE on a 90-second trade, the 5m candle can show only one bar and miss the entire adverse excursion.

**Pitfall 3: `candles_1m` is also incomplete.** Despite having 10M+ rows, `candles_1m` in `candles.db` has gaps for many tokens. The `price_history` table in `signals_hermes.db` is more complete (140k rows per token for active tokens).

**Pitfall 4: highest_price in `trades` table is unreliable for orphan trades.** Default value is 1.0 and is only updated on the regular path, NOT on the guardian_orphan close path. Always cross-check with actual price_history data. See `hl-trading-debug/references/aster-10s-reopen-bug-2026-06-25.md` for a concrete example.

## MFE/MAE Calculation Pattern

```python
def mfe_mae(trade, prices):
    """prices is list of (timestamp, price) tuples from price_history."""
    if not prices:
        return 0, 0
    arr = [p[1] for p in prices]
    if trade['dir'] == 'LONG':
        mfe = (max(arr) - trade['entry']) / trade['entry'] * 100
        mae = (trade['entry'] - min(arr)) / trade['entry'] * 100
    else:  # SHORT
        mfe = (trade['entry'] - min(arr)) / trade['entry'] * 100
        mae = (max(arr) - trade['entry']) / trade['entry'] * 100
    return mfe, mae
```

## When to use which source

| Question | Source |
|---|---|
| Price path during a specific trade | `signals_hermes.db:price_history` (1m) |
| 5m OHLC for backtest | `candles.db:candles_5m` |
| 1h / 4h candles for regime | `candles.db:candles_1h` / `candles_4h` |
| In-trade SL/TP targets | `trades.stop_loss`, `trades.target` |
| Whether SL was actually hit | `signals_hermes.db:price_history` (1m actual high/low) |
| Whether `trades.highest_price` is accurate | cross-check with `price_history` |
