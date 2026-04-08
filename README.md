# Hermes Trading System

Hyperliquid momentum-based algorithmic trading system. Monitors 544 tokens, generates scored signals, and executes leverage trades on Hyperliquid with paper trading and live trading modes.

## System Overview

Hermes is an event-driven trading system that continuously monitors cryptocurrency markets, identifies momentum-based trading opportunities using technical indicators (RSI, MACD, z-score velocity, percentile rank), and executes trades on Hyperliquid exchange. The system supports both paper trading (simulated) and live trading, with a kill switch for safe切换.

---

## Pipeline Architecture

```
MARKET DATA
    │
    ▼
price_collector.py          ──→ signals_hermes.db::price_history (~2.7M rows)
    │                              latest_prices table (current prices)
    │
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │
    ▼
signal_gen.py               ──→ signals DB (PENDING / WAIT / APPROVED / EXECUTED)
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              token_speeds table (544 tokens)
    │
    │  Every 10 min ▼
    │
ai_decider.py               ──→ compact_signals() → hotset.json (top 20 by score)
    │                              Scoring: recency + confidence + confluence + speed_score
    │                              BLACKLIST filter (LONG_BLACKLIST / SHORT_BLACKLIST)
    │                              Solana-only filter (is_solana_only)
    │                              review_count increments on WAIT/SKIPPED
    │
    ▼
decider_run.py              ──→ TWO PATHS (both enforce bans):
    │                              1. _run_hot_set() → hotset.json
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                              Dynamic paper/live: paper = not is_live_trading_enabled()
    │                              Both paths write to paper trades DB only.
    │
    ▼
hyperliquid_exchange.py     ──→ HL API
    │                              mirror_open() for paper; mirrors to real HL when live
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              Reconciles HL positions ↔ paper DB
    │
    ▼
position_manager.py        ──→ trailing stops, stale winner/loser exits, cascade flips
    │
    ▼
hermes-trades-api.py        ──→ writes signals.json for web dashboard
```

---

## Data Stores

| File | Contents |
|------|----------|
| `signals_hermes.db` | price_history (~2.7M rows), latest_prices, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (544 tokens) |
| `state.db` | General state (messages, schema_version) |
| `predictions.db` | ML predictions |
| `/var/www/hermes/data/hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `/var/www/hermes/data/hotset.json` | Current hot set (top 20 signals) |

---

## Kill Switch

The system operates in two modes controlled by `/var/www/hermes/data/hype_live_trading.json`:

| Mode | Behavior |
|------|----------|
| `live_trading: false` | All trades stay in paper DB (simulation only) |
| `live_trading: true` | hl-sync-guardian mirrors approved trades to real Hyperliquid orders |

**Guardian reconciliation:** Every 60 seconds, hl-sync-guardian:
1. Reads the kill switch
2. If live: mirrors paper positions to real HL orders
3. Reconciles HL positions ↔ paper DB
4. Marks guardian_missing / hl_position_missing closes

---

## Key Scripts

| Script | Purpose | Frequency |
|--------|---------|-----------|
| `price_collector.py` | Fetch token prices from Hyperliquid API, store to price_history | 1 min |
| `4h_regime_scanner.py` | Determine market regime (LONG_BIAS/SHORT_BIAS/NEUTRAL) | 1 min |
| `signal_gen.py` | Generate signals using RSI, MACD, z-score velocity, percentile_rank | 1 min |
| `ai_decider.py` | OpenAI-powered signal scoring and compaction to hotset (top 20) | 10 min |
| `decider_run.py` | Execute trades from hotset or approved signals; enforces bans | 1 min |
| `hyperliquid_exchange.py` | Hyperliquid API integration (mirror_open for paper/live) | On-demand |
| `hl-sync-guardian.py` | Background service; kill switch + position reconciliation | 60s |
| `position_manager.py` | Trailing stops, stale winner/loser exits, cascade flips | 1 min |
| `hermes-trades-api.py` | REST API on :8080 — writes signals.json for dashboard | 1 min |
| `strategy_optimizer.py` | Strategy parameter optimization | 10 min |
| `ab_optimizer.py` | A/B test optimization | 10 min |
| `ab_learner.py` | A/B test learning | 10 min |

### Additional Utilities

| Script | Purpose |
|--------|---------|
| `backfill_72h.py` | Backfill last 72 hours of price history |
| `setup_hermes_db.py` | Create/reset both databases with proper schemas |
| `signal_schema.py` | Database initialization (auto-runs on first use) |
| `candle_predictor.py` | ML-based candle prediction |
| `pattern_scanner.py` | Pattern detection across tokens |
| `speed_tracker.py` | Token speed tracking |

---

## Pipeline Schedule

| Step | Frequency | Script |
|------|-----------|--------|
| Price collection | Every 1 min | `price_collector.py` |
| Regime scan | Every 1 min | `4h_regime_scanner.py` |
| Signal generation | Every 1 min | `signal_gen.py` |
| Hot-set execution | Every 1 min | `decider_run.py` |
| Position management | Every 1 min | `position_manager.py` |
| Web dashboard | Every 1 min | `hermes-trades-api.py` |
| AI decision + compaction | Every 10 min | `ai_decider.py` |
| Strategy optimization | Every 10 min | `strategy_optimizer.py` |
| A/B optimization | Every 10 min | `ab_optimizer.py` |
| A/B learner | Every 10 min | `ab_learner.py` |

---

## Hot-Set Execution Rules

When `decider_run.py` executes from hotset.json:

- **Wave alignment boost (+15%):** bottoming+LONG or falling+SHORT
- **Counter-wave penalty (0.70-0.88x):** counter-trend entries
- **Overextended BLOCKED:** except bottoming+LONG or falling+SHORT
- **Counter-trend trap:** z-score vs direction → penalty
- **Regime alignment:** tier disagrees → -20 pts

### HARD BANS (immediate rejection)
- `conf-1s` — single-source confidence
- `speed=0%` — stale token

### Approved Signal PATH (get_approved_signals)
Enforces: counter-trend trap, regime alignment
HARD BANS: conf-1s, speed=0%, loss/win cooldown

---

## Quick Start

```bash
cd /root/.hermes

# 1. Install deps
pip install requests sqlite3

# 2. Init DBs (auto-loads backfill from seed/)
python3 scripts/signal_schema.py

# 3. Run the pipeline
python3 scripts/price_collector.py
python3 scripts/signal_gen.py
python3 scripts/ai_decider.py
python3 scripts/decider_run.py

# 4. REST API for dashboard
python3 scripts/hermes-trades-api.py  # Runs on :8080
```

---

## Configuration

- `config/` — tokens, thresholds, regime parameters
- `.env` — API keys (not committed)
- `cron/jobs.json` — cron schedule

---

## Debugging

```bash
# Check price data
sqlite3 scripts/signals_hermes.db "SELECT token, COUNT(*) FROM price_history GROUP BY token LIMIT 5"

# Check runtime signals
sqlite3 scripts/signals_hermes_runtime.db "SELECT * FROM signals ORDER BY created_at DESC LIMIT 5"

# Check hotset
cat /var/www/hermes/data/hotset.json | python3 -m json.tool | head -50

# Check kill switch
cat /var/www/hermes/data/hype_live_trading.json

# Logs
tail -f /var/log/hermes/pipeline.log
tail -f /var/log/hermes/errors.log
```

---

**Last updated:** 2026-04-08 — rewrote for accuracy against ATM-Architecture.md
