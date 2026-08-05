# MTF-MACD Tuner — System Overview

## What It Does
Tunes MACD parameters (fast/slow/signal/hold/exit/regime_filter/score_threshold) per token using multi-timeframe analysis. Produces optimal configs stored in `token_best_config` table, consumed by `signal_gen.py` for trade signals.

## Data Sources

### Primary: `signals_hermes.db::price_history`
- **What:** 1m Hyperliquid price ticks (Hyperliquid is a perpetual futures DEX)
- **Coverage:** 190 tokens, 44 days deep, updated every ~10s
- **Tick density:** ~118 ticks/min (sparse)

### Why Sparse?
**Hyperliquid trades less than Binance.** This is by design — `price_history` stores actual Hyperliquid trade ticks, not Binance data. Hyperliquid is a perpetual futures DEX with fewer market participants than Binance spot. ~118 ticks/min is the real trade rate; there's no missing data to fill.

Options to address this:
1. **Accept it** — use what's available, fallback to Binance when insufficient signals
2. **Use Binance candles** (`candles/*.json`) — 20 tokens, real OHLCV, stale since April 11
3. **Seed Binance candles** — periodic fetch to `candles/` directory or a SQLite candles table

### Fallback: Binance API
When local data is insufficient (< warmup or < 2 signals), the tuner fetches 15m/1h/4h candles from Binance. This is the expensive path (~5,600 API calls per full sweep).

## Architecture

```
hermes-mtf-macd-tuner.timer (1m)
  └── hermes-mtf-macd-tuner.service
        └── mtf_macd_tuner.py quick
              ├── run_quick_sweep()           — all 190 tokens, local data
              │     ├── fetch_local_candles() — price_history aggregation
              │     └── quick_update()        — test top-10 prior configs
              │
              └── run_full_sweep()             — all 544 configs × all tokens
                    ├── fetch_binance_candles() — Binance API (expensive)
                    └── save to backtest_results + token_best_config
```

## Quick Sweep vs Full Sweep
| | Quick | Full |
|---|---|---|
| Frequency | 1 min (timer) | 24h (manual or separate timer) |
| Data | Local (price_history) | Binance API |
| Configs tested | Top-10 prior per token | All 544 combos |
| Tokens | 190 | 190 |
| Runtime | ~30-60s | ~10-30 min |
| Purpose | Re-evaluate known configs | Discover new configs |

## Database Schema

### `backtest_results` — all backtest runs
- 203,308 rows, 124+ tokens
- Columns: `token`, `fast`, `slow`, `signal`, `exit_strategy`, `hold_minutes`, `score_threshold`, `regime_filter`, `signals`, `wins`, `losses`, `win_rate`, `profit_factor`, `total_pnl_pct`, `max_drawdown_pct`, `avg_pnl_pct`

### `token_best_config` — current best per token (consumer: signal_gen.py)
- PRIMARY KEY: `token`
- Columns: same as backtest_results + `updated_at`
- Written via `INSERT OR REPLACE` (token is PK)

## Known Issues

### 1. Sparse Local Data → Fewer Signals
- **Problem:** Aggregating sparse 1m HL ticks into 15m candles produces "staircase" closes with fewer MACD crossovers than real Binance candles
- **Example:** A config with 9 signals on Binance may show only 1-2 on aggregated local data
- **Impact:** Quick sweep may not re-evaluate configs thoroughly enough
- **Fix:** Accept for quick refresh; full sweep with Binance handles discovery

### 2. 100% WR configs with n=1
- **Problem:** `>= 1 signal` threshold saves configs with just 1 winning trade (100% WR, infinite PF)
- **Impact:** Statistically meaningless; signal_gen.py may act on noise
- **Fix:** Require `>= 3 signals` with Binance fallback for low-signal tokens

### 3. candles/*.json Unused
- **Problem:** 20 tokens have real Binance 15m/1h/4h candles in `candles/*.json` but they're stale (April 11) and not used
- **Fix:** Integrate as higher-priority tier before falling to price_history aggregation

## Key Files
- `/root/.hermes/scripts/mtf_macd_tuner.py` — main tuner
- `/root/.hermes/data/mtf_macd_tuner.db` — tuner database
- `/root/.hermes/data/signals_hermes.db::price_history` — local tick data
- `/root/.hermes/data/candles/*.json` — stale Binance candles (20 tokens)
- `/root/.hermes/systemd/hermes-mtf-macd-tuner.timer` — 1m timer
- `/root/.hermes/systemd/hermes-mtf-macd-tuner.service` — quick sweep service

## Bug Fixes Applied
1. **`PrecomputedMACD.histogram()` IndexError** — added `or i >= len(self.sig_ema)` bounds check (April 14 crash)
2. **`INSERT OR REPLACE` for token_best_config** — PRIMARY KEY conflict on re-runs fixed
3. **`return best` restored in quick_update()** — missing return statement patched
