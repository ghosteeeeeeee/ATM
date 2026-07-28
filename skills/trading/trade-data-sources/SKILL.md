---
name: trade-data-sources
description: |
  All local data sources for trade analysis, backtesting, and debugging.
  Use this skill when you need to query trade history, analyze performance,
  or find data for any trading-related investigation.
triggers:
  - "trade data"
  - "trade history"
  - "analyze trades"
  - "trade sources"
  - "where are trades"
  - "backtest data"
version: 1.0.0
metadata:
  hermes:
    tags: [trading, data, analysis, backtesting]
    category: trading
---

# Trade Data Sources

Complete reference for all local trade data locations.

## Quick Reference

| Source | Path | Records | Has Timestamps | Notes |
|--------|------|---------|----------------|-------|
| Current trades | `/var/www/hermes/data/trades.json` | 200 | ✅ opened, closed | **Primary source** — full metadata |
| Archive DB | `/root/.hermes/archive/trades_analysis.db` | 931 | ✅ open_time, close_time | SQLite, all columns |
| Archive JSONs | `/root/.hermes/archive/trades/` | 5563+ | ⚠️ partial | Multiple files, overlapping |
| Signal outcomes | `signals_hermes_runtime.db` → `signal_outcomes` | 8132 | ✅ created_at | All signals generated (not just executed) |
| Price history | `signals_hermes.db` → `price_history` | ~2.7M | ✅ Unix epoch | Close prices only |
| Candle cache | `candles.db` → `candle_cache` | varies | ✅ | 5m, 15m, 1h, 4h OHLCV |
| Hotset | `/var/www/hermes/data/hotset.json` | current | ✅ timestamp | Current compactor output |
| Signals dashboard | `/var/www/hermes/data/signals.json` | current | ✅ | For dashboard display |

## Detailed Source Documentation

### 1. Current Trades (PRIMARY)
**Path:** `/var/www/hermes/data/trades.json`
**Records:** 200 closed trades
**Format:** JSON with `closed` array

```python
import json
with open('/var/www/hermes/data/trades.json') as f:
    data = json.load(f)
trades = data['closed']  # list of dicts
```

**Fields per trade:**
```
coin, direction, entry, exit, opened, closed, pnl_pct, pnl_usdt,
signal, confidence, leverage, amount_usdt, close_reason, exchange
```

**Best for:** Recent performance analysis, signal quality checks, hourly/daily patterns

### 2. Archive Database
**Path:** `/root/.hermes/archive/trades_analysis.db`
**Records:** 931 trades
**Format:** SQLite

```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/archive/trades_analysis.db')
cur = conn.cursor()
cur.execute("SELECT * FROM trades WHERE open_time IS NOT NULL")
```

**Key columns:**
```
token, direction, signal, pnl_pct, open_time, close_time,
entry_price, exit_price, stop_loss, target, leverage,
_signal_z_score, _signal_rsi_14, _signal_macd_hist,
entry_regime_4h, entry_trend, close_reason
```

**Best for:** Historical analysis with technical indicators at entry

### 3. Archive JSONs
**Path:** `/root/.hermes/archive/trades/`
**Records:** 5563+ trades across ~40 files
**Format:** JSON arrays or dicts with `trades` key

```python
import json, os
archive_dir = '/root/.hermes/archive/trades'
all_trades = []
for f in sorted(os.listdir(archive_dir)):
    if f.endswith('.json'):
        with open(os.path.join(archive_dir, f)) as fp:
            data = json.load(fp)
            if isinstance(data, list):
                all_trades.extend(data)
            elif isinstance(data, dict) and 'trades' in data:
                all_trades.extend(data['trades'])
```

**WARNING:** Files overlap — always deduplicate by (coin, direction, opened[:19])

**Best for:** Deep historical analysis, older trades not in trades.json

### 4. Signal Outcomes
**Path:** `/root/.hermes/data/signals_hermes_runtime.db` → `signal_outcomes`
**Records:** 8132 rows
**Format:** SQLite

```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute("SELECT token, direction, signal_type, is_win, pnl_pct, created_at FROM signal_outcomes")
```

**Fields:**
```
token, direction, signal_type, is_win, pnl_pct, pnl_usdt,
confidence, created_at, closed_at
```

**NOTE:** Includes ALL signals generated, not just executed trades. Many were filtered before execution.

**Best for:** Signal generation analysis, win rate by signal type, overall system performance

### 5. Price History
**Path:** `/root/.hermes/data/signals_hermes.db` → `price_history`
**Records:** ~2.7M rows
**Format:** SQLite, timestamps in Unix epoch seconds

```python
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()
cutoff = time.time() - (20 * 3600)  # 20 hours ago
cur.execute("SELECT price, timestamp FROM price_history WHERE token = 'BTC' AND timestamp > ? ORDER BY timestamp", (cutoff,))
```

**Best for:** Z-score calculation, price reconstruction, backtesting

### 6. Candle Cache
**Path:** `/root/.hermes/data/candles.db` → `candle_cache`
**Records:** varies by symbol/interval
**Format:** SQLite

```python
conn = sqlite3.connect('/root/.hermes/data/candles.db')
cur = conn.cursor()
cur.execute("SELECT * FROM candle_cache WHERE symbol = 'BTCUSDT' AND interval = '5m' ORDER BY timestamp DESC LIMIT 100")
```

**Best for:** OHLCV analysis, technical indicators, multi-timeframe analysis

### 7. Runtime Speed/Phase Data
**Path:** `/root/.hermes/data/signals_hermes_runtime.db` → `token_speeds`
**Records:** 549 tokens
**Format:** SQLite, updated every minute

```python
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute("SELECT * FROM token_speeds WHERE token = 'BTC'")
```

**Fields:**
```
token, speed_percentile, wave_phase, momentum_score,
price_acceleration, is_overextended, price_change_30m
```

**Best for:** Phase analysis, speed filtering, real-time market state

## Common Analysis Patterns

### Hourly Performance
```python
from datetime import datetime
from collections import defaultdict

hour_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
for t in trades:
    entry_dt = datetime.strptime(t['opened'].split('.')[0], '%Y-%m-%d %H:%M:%S')
    hour = entry_dt.hour
    if t['pnl_pct'] > 0:
        hour_stats[hour]['wins'] += 1
    else:
        hour_stats[hour]['losses'] += 1
```

### Signal Win Rate
```python
from collections import defaultdict
signal_stats = defaultdict(lambda: {'wins': 0, 'total': 0})
for t in trades:
    signal = t.get('signal', 'unknown')
    signal_stats[signal]['total'] += 1
    if t['pnl_pct'] > 0:
        signal_stats[signal]['wins'] += 1
```

### Dead Hours Filter
```python
def is_dead_hours(opened_str):
    """Check if trade was opened during dead hours (03:00-08:00 UTC)"""
    dt = datetime.strptime(opened_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
    return 3 <= dt.hour < 8
```

### Z-Score Calculation
```python
import statistics
cur.execute("SELECT price FROM price_history WHERE token = ? AND timestamp > ?", (token, cutoff))
prices = [r[0] for r in cur.fetchall()]
if len(prices) >= 100:
    mean = statistics.mean(prices)
    std = statistics.stdev(prices)
    z_score = (prices[0] - mean) / std
```

## Key File Locations (from AGENTS.md)

| What | Path |
|------|------|
| Pipeline log | `/root/.hermes/logs/pipeline.log` |
| Hotset | `/var/www/hermes/data/hotset.json` |
| Open trades | `/var/www/hermes/data/trades.json` |
| Archived trades | `/root/.hermes/archive/trades_analysis.db` |
| Constants | `scripts/hermes_constants.py` |
| Paths | `scripts/paths.py` |
| Signal runner | `scripts/signals_runner.py` |
| Compactor | `scripts/signal_compactor.py` |
| Decider | `scripts/decider_run.py` |
| Position manager | `scripts/position_manager.py` |
| TPSL utils | `scripts/tpsl_utils.py` |
| Guardian | `scripts/hl-sync-guardian.py` |
