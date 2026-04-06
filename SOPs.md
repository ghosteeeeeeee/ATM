# SOPs.md - Standard Operating Procedures

## Security Rule

**Never expose ports publicly.** All services (gateway, VNC, dashboards on port 80, etc.) must bind to localhost only (127.0.0.1). SSH (port 333 on Dallas) is the ONLY exception that may be exposed externally.

---

## Memory & Documentation

### After Each Session
- Save key facts to `brain.md`
- Update `CONTEXT.md` if anything significant happened (new trades, system fixes, wins/losses, decisions)

### CONTEXT.md (`/root/.hermes/CONTEXT.md`)
- T's living session doc — keep it short and tidy
- Update after significant events: new trades, system fixes, wins/losses, important decisions
- Current snapshot should reflect what's active right now

### Trading Live Log (`/root/.hermes/brain/trading.md`)
- **Updated every 10 minutes by the pipeline** (written by `ai_decider.py` + pipeline hooks)
- Contains: current positions, hot-set status, 7-day stats, active ideas, live log of bugs/fixes, known issues
- This is the system's live journal — everything to do with the trading system goes here
- Any significant event (trade closed, bug found, fix applied, idea generated) gets a timestamped entry

---

## API Calls

**Use `requests.post()` for all local HTTP API loops** (Ollama, Hyperliquid, etc.) — ~3x faster than subprocess curl. Subprocess curl is fine for one-off shell commands, not loops.

---

## Skills

### After Hard Tasks (5+ tool calls)
- Save the approach as a skill with `skill_manage create`
- Include: trigger conditions, exact commands, pitfalls, verification steps

### If a Skill is Wrong or Stale
- Patch it immediately with `skill_manage patch` — don't wait to be asked
- Outdated skills are liabilities

---

## Git

- Commit meaningful changes to `/root/.hermes` regularly
- **jobs.json stays untracked** (`git rm --cached`) — contains job prompts, file paths, architecture details
- Always review cron/jobs.json for sensitive content before (re)committing

---

## Ollama Fallback

If cloud APIs (MiniMax) are unavailable, fall back to Ollama at `localhost:11434` with model `qwen2.5:1.5b`. This ensures resilience for overnight/background runs.

---

## Trading System

### AI Trading Machine (ATM) — Core Trading System
All primary trading system files for the standalone Docker are organized in:
**`/root/.hermes/ATM/`**

Includes: position_manager, signal_gen, ai_decider, decider-run, price_collector, guardian, and all configs.
See [ATM-Architecture.md](./ATM/ATM-Architecture.md) for full system design.

### ATM Config
- [`ATM/config/stoploss.md`](./ATM/config/stoploss.md) — Stop-loss, trailing SL, cascade flip, wave turn, stale exit rules

### Dashboards
- **Kanban Board:** http://127.0.0.1:54321/projects — Project task board (drag-and-drop, seeded from TASKS.md)
- **Hermes Dashboard:** http://127.0.0.1:54321/ — Main Hermes UI
- **Learning Streamlit:** http://127.0.0.1:54321/learning — ML dashboards (W&B, A/B tests, ai_decider, signals)

### Key Files
- `ai_decider.py` — compaction + scoring + AI decision gate
- `hotset.json` (`/var/www/hermes/data/hotset.json`) — authoritative hot-set (written every 10 min)
- `signals.json` (`/var/www/hermes/data/signals.json`) — web dashboard output (reads hotset.json, enriched with live RSI)
- `hermes-trades-api.py` — writes signals.json for web UI
- `price_collector.py` — seeds price DB + candle DB every minute (cron: `* * * * *`)
- `signal_schema.py` — local SQLite read layer (price_history, latest_prices, ohlcv_1m)

---

## Price Architecture (Local DB First)

### Rule: All price reads MUST route to local SQLite first.

The local SQLite DB (`signals_hermes.db`) is the single source of truth for all price data. External API calls (HL allMids, Binance candles) are **WRITE-ONLY** into the local DB — no script should ever read price from an API directly when the local DB has the data.

### Data Flow

```
HL allMids API (1 call/min via price_collector cron)
    → writes to → signals_hermes.db: latest_prices + price_history

Binance klines API (candle fetches for active tokens)
    → writes to → signals_hermes.db: ohlcv_1m

All reading scripts (signal_gen, ai_decider, etc.)
    → read from → signals_hermes.db (local SQLite)
```

### Tables in `signals_hermes.db`

| Table | Source | Update Frequency | Used By |
|---|---|---|---|
| `latest_prices` | HL allMids via price_collector | Every minute | All scripts needing current price |
| `price_history` | HL allMids via price_collector | Every minute | RSI, z-score, MACD, historical analysis |
| `ohlcv_1m` | Binance klines via price_collector | Every minute (active tokens only) | Pattern detection, intraday analysis |

### Price Reading Functions (signal_schema.py)

```python
get_latest_price(token)        # Current price — local DB only
get_price_history(token, lookback_minutes)  # Time series — local DB only
get_all_latest_prices()        # All current prices — local DB only
get_ohlcv_1m(token, lookback_minutes)     # 1m candles — local DB, falls back to Binance fetch
```

### Price Collector Cron

```
* * * * * python3 /root/.hermes/scripts/price_collector.py >> /root/.hermes/logs/price-collector.log 2>&1
```

What it does every minute:
1. Fetches HL allMids (1 API call → all ~229 tokens)
2. Writes to `latest_prices` + `price_history`
3. Identifies active tokens (hot-set + open positions)
4. Fetches 1m Binance candles for active tokens → writes to `ohlcv_1m`

### For Pattern Detection (chart patterns, Wyckoff, Elliot Wave)

Use `get_ohlcv_1m()` from `signal_schema.py` — it reads from the local `ohlcv_1m` table which is seeded by Binance 1m klines. Active tokens get ~240 candles (last 4 hours) refreshed every minute.

If `ohlcv_1m` is empty for a token, `fetch_binance_candles()` can be called directly to seed it.

### Wrong Way (Don't Do This)

```python
# BAD: Direct API call bypassing local DB
import requests
r = requests.get('https://api.binance.com/...')  # ← Don't read API directly

# GOOD: Read from local DB
from signal_schema import get_latest_price
price = get_latest_price('IMX')  # ← Always local DB first
```

### External Price APIs (Write-Only)

- **HL allMids** (`https://api.hyperliquid.xyz/info`, `{"type": "allMids"}`) — current prices for all tokens. Called by `price_collector.py` only.
- **Binance klines** (`https://api.binance.com/api/v3/klines`) — 1m OHLCV candles for pattern detection. Called by `fetch_binance_candles()` in `price_collector.py`. No auth needed.

