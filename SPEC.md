# MTF-MACD Tuner — SPEC

## Concept
An autonomous self-tuning system for MTF-MACD parameters. Each token gets its own optimal MACD config (fast/slow/signal) discovered via systematic backtesting, then continuously revalidated as market conditions change. New signals auto-register tokens for tracking.

## DB: /root/.hermes/data/mtf_macd_tuner.db

### Schema

```sql
CREATE TABLE backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_ts DATETIME DEFAULT CURRENT_TIMESTAMP,
    window_days INTEGER NOT NULL,
    tokens_tested TEXT NOT NULL,
    configs_tried INTEGER NOT NULL,
    best_token_count INTEGER NOT NULL,
    notes TEXT
);

CREATE TABLE backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES backtest_runs(id),
    token TEXT NOT NULL,
    fast INTEGER NOT NULL,
    slow INTEGER NOT NULL,
    signal INTEGER NOT NULL,
    exit_strategy TEXT NOT NULL,
    hold_minutes INTEGER NOT NULL,
    score_threshold INTEGER NOT NULL,
    regime_filter INTEGER NOT NULL,
    signals INTEGER NOT NULL,
    wins INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    win_rate REAL NOT NULL,
    profit_factor REAL NOT NULL,
    total_pnl_pct REAL NOT NULL,
    max_drawdown_pct REAL NOT NULL,
    avg_pnl_pct REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE token_best_config (
    token TEXT PRIMARY KEY,
    fast INTEGER NOT NULL,
    slow INTEGER NOT NULL,
    signal INTEGER NOT NULL,
    exit_strategy TEXT NOT NULL,
    hold_minutes INTEGER NOT NULL,
    score_threshold INTEGER NOT NULL DEFAULT 2,
    regime_filter INTEGER NOT NULL DEFAULT 1,
    win_rate REAL NOT NULL,
    profit_factor REAL NOT NULL,
    total_pnl_pct REAL NOT NULL,
    signal_count INTEGER NOT NULL,
    backtest_run_id INTEGER REFERENCES backtest_runs(id),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_stale INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE monitored_tokens (
    token TEXT PRIMARY KEY,
    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    signal_count INTEGER DEFAULT 0,
    last_signal_at DATETIME,
    is_active INTEGER NOT NULL DEFAULT 1
);
```

## Backtest Engine

`test_mtf_macd_config(token, fast, slow, signal, exit_strategy, hold_minutes, score_threshold, regime_filter, window_days=90)`:

1. Fetch `window_days` of 1h klines from Binance for token
2. Build 15m, 1h, 4h candles from raw data
3. Walk every candle as potential entry — entry triggers:
   - 15m MACD crossover (bullish or bearish)
   - `regime_filter=True`: 4H and 1H MACD must agree with direction
   - `score_threshold=N`: at least N timeframes with histogram > 0 (bullish) or < 0 (bearish)
4. Exit when:
   - `any_flip`: any TF histogram flips sign
   - `histogram_flip`: 15m histogram flips sign
   - OR `hold_minutes` elapsed
5. Return: `{wr, pf, pnl_pct, max_dd, signal_count, avg_pnl, wins, losses}`

## Param Grid

Base grid (pruned):
- fast: [8, 12]
- slow: [50, 55, 65] — slow=50 only with fast=8
- signal: [12, 15, 17, 28] — signal=28 only with slow=65
- exit_strategy: ['any_flip', 'histogram_flip']
- hold_minutes: [60, 120, 240, 480]
- score_threshold: [2, 3]
- regime_filter: [0, 1]

~200 effective combos per token after pruning.

## Tuner Script: mtf_macd_tuner.py

CLI actions:
- `sweep` — full 90d backtest for all monitored tokens
- `quick <token>` — re-test top 10 configs for one token
- `add <token>` — add token to monitored list and run initial backtest
- `report` — print current best configs for all tokens
- `stale` — mark stale configs and fall back to defaults

## Signal_gen.py Integration

1. `load_current_best_configs()` — reads token_best_config into dict at startup
2. `_macd_crossover()` — uses token-specific params from DB dict, falls back to MACD_PARAMS
3. Tokens with `is_stale=1` fall back to hardcoded MACD_PARAMS

## Cron Schedule

- **Hourly** (`0 * * * *`): quick update for top 5 active tokens
- **Daily** (`0 3 * * *`): full sweep all monitored tokens (90d)
- **Weekly** (`0 4 * * 0`): expanded param grid sweep + stale check
