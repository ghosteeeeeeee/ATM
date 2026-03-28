# Hermes Trading System

Hyperliquid momentum-based trading system. Monitors 229 tokens, scores signals, and executes leverage trades on Hyperliquid.

## Quick Start

```bash
cd /root/.hermes

# 1. Install deps
pip install requests sqlite3

# 2. Init DBs (auto-loads 177K-row backfill from seed/)
python3 scripts/signal_schema.py    # or just run any script — init_db() fires automatically

# 3. Run the pipeline
python3 scripts/price_collector.py   # collect prices from Hyperliquid
python3 scripts/signal_gen.py       # generate signals
python3 scripts/ai-decider.py       # AI decision layer
python3 scripts/decider-run.py      # execute approved trades
python3 scripts/hermes-trades-api.py # REST API on :8080
```

## Architecture

### Dual-Database Design

| DB | Path | Git? | Contents |
|----|------|------|----------|
| Static | `data/signals_hermes.db` | No (seed in `seed/`) | `price_history` (OHLC candles), `latest_prices`, `regime_log` |
| Runtime | `data/signals_hermes_runtime.db` | No | `signals`, `decisions`, `momentum_cache`, `token_intel`, `cooldown_tracker` |

**Static DB:** Backfill data — git-tracked via `seed/signals_hermes.sql`. On fresh install, `init_db()` auto-imports the seed SQL. Backfill = 41 days of 1h candles for 229 tokens (177K rows, ~14MB).

**Runtime DB:** Changes every cycle — never committed. Reset on reinstall.

### Scripts

| Script | Purpose |
|--------|---------|
| `price_collector.py` | Fetch 229 token prices from Hyperliquid API, store to DB |
| `signal_gen.py` | Compute RSI, MACD, z-score, momentum phase → generate signals |
| `ai-decider.py` | OpenAI-powered signal decision (approve/reject) |
| `decider-run.py` | Execute approved trades via Hyperliquid |
| `hermes-trades-api.py` | REST API (port 8080) — trades + signals JSON |
| `setup_hermes_db.py` | Create/reset both DBs with proper schemas |
| `backfill_72h.py` | Backfill last 72h of price history |
| `backfill_prices.py` | Backfill price data |

### Signal Flow

```
Hyperliquid API → price_collector → signal_gen → ai-decider → decider_run → Hyperliquid Trade
                                     ↓
                              signals DB (runtime)
                                     ↓
                              hermes-trades-api (JSON endpoints)
```

### Regime System

`compute_regime()` analyzes broad market z-score across top tokens:
- **BEAR**: `broad_z < -1.5` → `long_mult=1.5`, `short_mult=0.5` (fade rallies)
- **BULL**: `broad_z > +1.5` → `long_mult=1.5`, `short_mult=0.5` (fade dumps)
- **NEUTRAL**: default multipliers

### Backfill & Recovery

```bash
# Fresh install: seed auto-loads on first init_db()
# Manual backfill:
python3 scripts/backfill_72h.py

# Export current DB as SQL:
sqlite3 data/signals_hermes.db ".dump price_history latest_prices regime_log" > seed/signals_hermes.sql
```

## Config

- `config.yaml` — tokens, thresholds, regime parameters
- `.env` — API keys (not committed)
- `cron/jobs.json` — cron schedule

## Issues / Debugging

```bash
# Check DB contents
sqlite3 data/signals_hermes.db "SELECT token, COUNT(*) FROM price_history GROUP BY token LIMIT 5"
sqlite3 data/signals_hermes_runtime.db "SELECT * FROM signals ORDER BY created_at DESC LIMIT 5"

# Logs
tail -f logs/pipeline.log
tail -f logs/errors.log
```
