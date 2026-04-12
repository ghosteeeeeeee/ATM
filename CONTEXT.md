# CONTEXT.md — Hermes ATM
## Quick Status
```
PIPELINE: ERROR (last run 64+00:0) | WASP: unknown
LIVE TRADING: ON ✅ | POSITIONS: 1 open, 0 closed (brain)
REGIME: UNKNOWN
Updated: 2026-04-12 20:54 UTC
```

## Critical Flags
- CASCADE_FLIP_ENABLED = False (position_manager.py line 78)
- hype_live_trading.json: ON — kill switch for live trading
- Guardian: running (hl-sync-guardian.service)

## Active
- hype_live_trading.json: ON (2026-04-05 05:45 UTC)
- Regime: SHORT bias
- CASCADE_FLIP_ENABLED = False (kill switch active)

## Pipeline Health
- Pipeline: RUNNING (hermes-pipeline.timer systemd)
- WASP: check via hermes-wasp.timer
- HL cache: FRESH

## Signal DBs
- Hermes: /root/.hermes/data/signals_hermes_runtime.db (local SQLite)

## HL Wallet
- 0x324a9713603863FE3A678E83d7a81E20186126E7
- Fills: /root/.hermes/data/hl_fills_*_raw.csv (2000 fills, Mar 10-25 2026)

## This Session (2026-04-10 15:38 UTC)
- T: cascade-flip disabled? CASCADE_FLIP_ENABLED=False confirmed
- Git repo packaged: ATM-Hermes-20260410-1536-full-5622130.zip → /var/www/git/
- index.html updated with latest zip
- context-compactor migrated: cron → hermes-context-compactor.timer (systemd)
- SESSION START hash enforcement wired: /root/.hermes/data/CONTEXT_MD_HASH.txt

## Architecture Reference
> Full system architecture: `/root/.hermes/ATM/ATM-Architecture.md` — read this for complete pipeline, DB, and service details. Updated automatically every 30 min.

## In Flight / Known Issues
- Pipeline BROKEN: ai_decider errors (module scope bug), 0 signals in DB
- Hotset STALE: empty hotset.json (~107 min old)
- Cascade-flip: DISABLED pending revisit

---

# ATM ARCHITECTURE SNAPSHOT (auto-generated, see: ATM-Architecture.md)
# ATM Architecture — Hermes Trading System
**Last updated:** 2026-04-12 17:30 UTC

---

## System Status
```
PIPELINE: ERROR (ai_decider broken — 0 signals in DB)
LIVE TRADING: ON ✅ (hype_live_trading.json: live_trading=true)
HOTSET: EMPTY (0 signals — stale 107+ min, ai_decider broken)
REGIME: UNKNOWN
HL Wallet: 0x324a9713603863FE3A678E83d7a81E20186126E7
```

---

## High-Level Data Flow

```
MARKET DATA (Binance + Hyperliquid)
    │
    ▼
price_collector.py          ──→ signals_hermes.db::price_history (~1.7M rows)
    │                              signals_hermes_runtime.db::latest_prices
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │                              hl_cache.json (live HL prices/positions)
    ▼
signal_gen.py               ──→ signals_hermes_runtime.db::signals
    │                              PENDING → WAIT → APPROVED → EXECUTED
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              token_speeds table (536 tokens)
    │
    │  Every 1 min (via run_pipeline.py) ▼
    │
ai_decider.py               ──→ compact_signals() → /var/www/hermes/data/hotset.json
    │  (Every 10 min)                     Top 20 by recency + confidence + confluence + speed_score
    │                              Scoring: recency + confidence + confluence + speed_score
    │                              BLACKLIST filter (LONG_BLACKLIST / SHORT_BLACKLIST)
    │                              Solana-only filter (is_solana_only)
    │                              review_count increments on WAIT/SKIPPED
    │
    ▼
decider_run.py              ──→ TWO PATHS (both enforce bans):
    │                              1. _run_hot_set() → reads hotset.json
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                              Dynamic paper/live: paper = not is_live_trading_enabled()
    │                              Both paths write to paper trades DB only.
    │
    ▼
hyperliquid_exchange.py     ──→ HL API
    │                              mirror_open() for paper; mirrors to real HL when live
    │                              Kill switch: hype_live_trading.json
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              If live_trading=true: mirror_open() to real HL orders
    │                              Reconciles HL positions ↔ paper DB
    │                              Marks guardian_missing / hl_position_missing closes
    │
position_manager.py         ──→ trailing stops, stale winner/loser exits, cascade flips
    │                          KILL SWITCH: CASCADE_FLIP_ENABLED=False (2026-04-10)
    │                              ATR-based self-close (internal, no HL trigger orders needed)
    │                              ATR_HL_ORDERS_ENABLED=False (HL order execution disabled)
    │
    ▼
hermes-trades-api.py        ──→ /var/www/hermes/data/signals.json (web dashboard)
update-trades-json.py       ──→ /var/www/hermes/data/trades.json (position state)
```

---

## Pipeline Orchestration

**Entry point:** `run_pipeline.py` — runs every 1 min via `hermes-pipeline.timer` (systemd)
- Acquires lock at `/tmp/hermes-pipeline.lock` to prevent overlapping runs
- Reads `hype_live_trading.json` to determine LIVE vs PAPER mode
- On minutes 0/10/20/30/40/50: also runs 10-minute steps

### 1-Minute Steps (every tick)
| Step | Script |
|------|--------|
| Price collection | `price_collector.py` |
| Regime scan | `4h_regime_scanner.py` |
| Signal generation | `signal_gen.py` |
| Hot-set execution | `decider_run.py` |
| Position management | `position_manager.py` |
| Dashboard update | `update-trades-json.py` |
| API write | `hermes-trades-api.py` |

### 10-Minute Steps (on the clock: :00, :10, :20, :30, :40, :50)
| Step | Script |
|------|--------|
| AI decision + compaction | `ai_decider.py` |
| Strategy optimization | `strategy_optimizer.py` |
| A/B optimization | `ab_optimizer.py` |
| A/B learner | `ab_learner.py` |

---

## Data Stores

| File | Contents |
|------|----------|
| `signals_hermes.db` | price_history (~1.7M rows static), candle_cache, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (536 tokens), predictions |
| `predictions.db` | ML predictions (~16MB, active) |
| `mtf_macd_tuner.db` | Self-tuning MACD params per token + market regime (~21MB) |
| `candle_cache.db` | Candle data for backtesting |
| `state.db` | General state (messages, schema_version) |
| `brain.db` | Hebbian associative memory network |
| `/var/www/hermes/data/hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `/var/www/hermes/data/hotset.json` | Current hot set (top 20 signals, compact_rounds tracking) |
| `/var/www/hermes/data/hl_cache.json` | Live HL prices + positions (refreshed every pipeline run) |
| `/var/www/hermes/data/signals.json` | Web dashboard signal feed |
| `/var/www/hermes/data/trades.json` | Open position state |
| `/root/.hermes/data/trailing_stops.json` | Trailing stop state |
| `/root/.hermes/data/speed_history.json` | Token speed history |
| `/root/.hermes/data/hotset.json` | Runtime copy of hotset (symlink or copy) |

---

## Kill Switch Architecture

```
hype_live_trading.json (at /var/www/hermes/data/)
    │
    ├── live_trading: false → all trades stay in paper DB
    └── live_trading: true  → guardian mirrors approved trades to real HL orders

CASCADE_FLIP_ENABLED (position_manager.py line 78)
    └── false → ALL cascade flip logic disabled

ATR_HL_ORDERS_ENABLED (position_manager.py)
    └── false → ATR-based HL trigger orders disabled (self-close uses internal DB only)
```

---

## Additional Services (systemd timers)

| Timer | Frequency | Service |
|-------|-----------|---------|
| `hermes-price-collector.timer` | 1 min | Real-time price collection |
| `hermes-hype-paper-sync.timer` | 10 min | HL ↔ paper position sync |
| `hermes-self-close-watcher.timer` | 1 min | Monitors ATR SL/TP self-close triggers |
| `hermes-candle-predictor.timer` | 10 min | ML candle direction predictions |
| `hermes-mtf-macd-tuner.timer` | 12 min | Self-tuning MACD parameter optimization |
| `hermes-away-detector.timer` | 5 min | Detects T's absence → self-init mode |
| `hermes-context-compactor.timer` | 30 min | Compacts CONTEXT.md via LLM |
| `hermes-brain-sync.timer` | 1 hour | Syncs brain memory |
| `hermes-archive-signals.timer` | daily | Archives old signals |
| `hermes-git-release.timer` | daily | Auto git commit + GitHub release |
| `hermes-smoke-test.timer` | ? | Health checks |
| `hermes-trading-checklist.timer` | ? | Trading checklist |

---

## Scripts Inventory
**Location:** `/root/.hermes/scripts/` (~60 scripts)

### Core Pipeline (in run_pipeline.py)
`price_collector.py` `4h_regime_scanner.py` `signal_gen.py` `decider_run.py`
`position_manager.py` `update-trades-json.py` `hermes-trades-api.py`
`ai_decider.py` `strategy_optimizer.py` `ab_optimizer.py` `ab_learner.py`

### ML / Predictors
`candle_predictor.py` — ML candle direction model (~49KB)
`candle_tuner.py` — Hyperparameter tuning for candle model
`backtest_mtf_macd.py` — Multi-timeframe MACD backtesting (~32KB)
`wave_backtest.py` — Wave pattern backtesting
`study_winning_combos.py` — A/B combo analysis

### Monitoring / Guardian
`hl-sync-guardian.py` — Live trading kill-switch + HL reconciliation
`wasp.py` — System health & anomaly detection (~40KB)
`smoke_test.py` — Health check tests (~19KB)
`self_close_watcher.py` — ATR self-close monitoring

### Backtesting
`backtest_candle.py` `backtest_minimax.py` `backtest_patterns.py`

### Utilities
`brain.py` — Hebbian memory + skills + session search (~35KB)
`context-compactor.py` — LLM-based context compression
`archive-signals.py` `purge_and_compact.py` — DB maintenance
`tokens.py` `top150.py` — Token list management
`speed_tracker.py` — Token speed tracking
`batch_tpsl_rewrite.py` — TP/SL batch updates

### One-Shot / Debug
`run_mcp_server.py` — MCP server for external tool access
`run_better_coder.py` — Code improvement agent
`away_detector.py` — T's presence detection
`event_log.py` `error_breadcrumbs.py` — Logging utilities
`checkpoint_utils.py` — Snapshot utilities

---

## Known Issues (2026-04-12)
1. **Pipeline BROKEN** — ai_decider errors: "name 'ai_decider' is not defined" / "name 'HOTSET_BLOCKLIST' is not defined" — module scope bug in get_pending_signals
2. **Zero signals** — signals_hermes_runtime.db has 0 PENDING/WAIT/APPROVED signals
3. **Hotset STALE** — hotset.json empty (should have 20 signals), ~107 min since last update
4. **smoke_test false positive** — `no_flapping` check is a false positive (458K-line event log always hits >10 threshold)

**Plan:** `/root/.hermes/plans/2026-04-09_230328-...` — Profit Monster close-reason bug fix + pipeline repair

---

# ATM ARCHITECTURE SNAPSHOT (auto-generated, see: ATM-Architecture.md)
# ATM Architecture — Hermes Trading System
**Last updated:** 2026-04-12 17:30 UTC

---

## System Status
```
PIPELINE: ERROR (ai_decider broken — 0 signals in DB)
LIVE TRADING: ON ✅ (hype_live_trading.json: live_trading=true)
HOTSET: EMPTY (0 signals — stale 107+ min, ai_decider broken)
REGIME: UNKNOWN
HL Wallet: 0x324a9713603863FE3A678E83d7a81E20186126E7
```

---

## High-Level Data Flow

```
MARKET DATA (Binance + Hyperliquid)
    │
    ▼
price_collector.py          ──→ signals_hermes.db::price_history (~1.7M rows)
    │                              signals_hermes_runtime.db::latest_prices
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │                              hl_cache.json (live HL prices/positions)
    ▼
signal_gen.py               ──→ signals_hermes_runtime.db::signals
    │                              PENDING → WAIT → APPROVED → EXECUTED
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              token_speeds table (536 tokens)
    │
    │  Every 1 min (via run_pipeline.py) ▼
    │
ai_decider.py               ──→ compact_signals() → /var/www/hermes/data/hotset.json
    │  (Every 10 min)                     Top 20 by recency + confidence + confluence + speed_score
    │                              Scoring: recency + confidence + confluence + speed_score
    │                              BLACKLIST filter (LONG_BLACKLIST / SHORT_BLACKLIST)
    │                              Solana-only filter (is_solana_only)
    │                              review_count increments on WAIT/SKIPPED
    │
    ▼
decider_run.py              ──→ TWO PATHS (both enforce bans):
    │                              1. _run_hot_set() → reads hotset.json
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                              Dynamic paper/live: paper = not is_live_trading_enabled()
    │                              Both paths write to paper trades DB only.
    │
    ▼
hyperliquid_exchange.py     ──→ HL API
    │                              mirror_open() for paper; mirrors to real HL when live
    │                              Kill switch: hype_live_trading.json
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              If live_trading=true: mirror_open() to real HL orders
    │                              Reconciles HL positions ↔ paper DB
    │                              Marks guardian_missing / hl_position_missing closes
    │
position_manager.py         ──→ trailing stops, stale winner/loser exits, cascade flips
    │                          KILL SWITCH: CASCADE_FLIP_ENABLED=False (2026-04-10)
    │                              ATR-based self-close (internal, no HL trigger orders needed)
    │                              ATR_HL_ORDERS_ENABLED=False (HL order execution disabled)
    │
    ▼
hermes-trades-api.py        ──→ /var/www/hermes/data/signals.json (web dashboard)
update-trades-json.py       ──→ /var/www/hermes/data/trades.json (position state)
```

---

## Pipeline Orchestration

**Entry point:** `run_pipeline.py` — runs every 1 min via `hermes-pipeline.timer` (systemd)
- Acquires lock at `/tmp/hermes-pipeline.lock` to prevent overlapping runs
- Reads `hype_live_trading.json` to determine LIVE vs PAPER mode
- On minutes 0/10/20/30/40/50: also runs 10-minute steps

### 1-Minute Steps (every tick)
| Step | Script |
|------|--------|
| Price collection | `price_collector.py` |
| Regime scan | `4h_regime_scanner.py` |
| Signal generation | `signal_gen.py` |
| Hot-set execution | `decider_run.py` |
| Position management | `position_manager.py` |
| Dashboard update | `update-trades-json.py` |
| API write | `hermes-trades-api.py` |

### 10-Minute Steps (on the clock: :00, :10, :20, :30, :40, :50)
| Step | Script |
|------|--------|
| AI decision + compaction | `ai_decider.py` |
| Strategy optimization | `strategy_optimizer.py` |
| A/B optimization | `ab_optimizer.py` |
| A/B learner | `ab_learner.py` |

---

## Data Stores

| File | Contents |
|------|----------|
| `signals_hermes.db` | price_history (~1.7M rows static), candle_cache, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (536 tokens), predictions |
| `predictions.db` | ML predictions (~16MB, active) |
| `mtf_macd_tuner.db` | Self-tuning MACD params per token + market regime (~21MB) |
| `candle_cache.db` | Candle data for backtesting |
| `state.db` | General state (messages, schema_version) |
| `brain.db` | Hebbian associative memory network |
| `/var/www/hermes/data/hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `/var/www/hermes/data/hotset.json` | Current hot set (top 20 signals, compact_rounds tracking) |
| `/var/www/hermes/data/hl_cache.json` | Live HL prices + positions (refreshed every pipeline run) |
| `/var/www/hermes/data/signals.json` | Web dashboard signal feed |
| `/var/www/hermes/data/trades.json` | Open position state |
| `/root/.hermes/data/trailing_stops.json` | Trailing stop state |
| `/root/.hermes/data/speed_history.json` | Token speed history |
| `/root/.hermes/data/hotset.json` | Runtime copy of hotset (symlink or copy) |

---

## Kill Switch Architecture

```
hype_live_trading.json (at /var/www/hermes/data/)
    │
    ├── live_trading: false → all trades stay in paper DB
    └── live_trading: true  → guardian mirrors approved trades to real HL orders

CASCADE_FLIP_ENABLED (position_manager.py line 78)
    └── false → ALL cascade flip logic disabled

ATR_HL_ORDERS_ENABLED (position_manager.py)
    └── false → ATR-based HL trigger orders disabled (self-close uses internal DB only)
```

---

## Additional Services (systemd timers)

| Timer | Frequency | Service |
|-------|-----------|---------|
| `hermes-price-collector.timer` | 1 min | Real-time price collection |
| `hermes-hype-paper-sync.timer` | 10 min | HL ↔ paper position sync |
| `hermes-self-close-watcher.timer` | 1 min | Monitors ATR SL/TP self-close triggers |
| `hermes-candle-predictor.timer` | 10 min | ML candle direction predictions |
| `hermes-mtf-macd-tuner.timer` | 12 min | Self-tuning MACD parameter optimization |
| `hermes-away-detector.timer` | 5 min | Detects T's absence → self-init mode |
| `hermes-context-compactor.timer` | 30 min | Compacts CONTEXT.md via LLM |
| `hermes-brain-sync.timer` | 1 hour | Syncs brain memory |
| `hermes-archive-signals.timer` | daily | Archives old signals |
| `hermes-git-release.timer` | daily | Auto git commit + GitHub release |
| `hermes-smoke-test.timer` | ? | Health checks |
| `hermes-trading-checklist.timer` | ? | Trading checklist |

---

## Scripts Inventory
**Location:** `/root/.hermes/scripts/` (~60 scripts)

### Core Pipeline (in run_pipeline.py)
`price_collector.py` `4h_regime_scanner.py` `signal_gen.py` `decider_run.py`
`position_manager.py` `update-trades-json.py` `hermes-trades-api.py`
`ai_decider.py` `strategy_optimizer.py` `ab_optimizer.py` `ab_learner.py`

### ML / Predictors
`candle_predictor.py` — ML candle direction model (~49KB)
`candle_tuner.py` — Hyperparameter tuning for candle model
`backtest_mtf_macd.py` — Multi-timeframe MACD backtesting (~32KB)
`wave_backtest.py` — Wave pattern backtesting
`study_winning_combos.py` — A/B combo analysis

### Monitoring / Guardian
`hl-sync-guardian.py` — Live trading kill-switch + HL reconciliation
`wasp.py` — System health & anomaly detection (~40KB)
`smoke_test.py` — Health check tests (~19KB)
`self_close_watcher.py` — ATR self-close monitoring

### Backtesting
`backtest_candle.py` `backtest_minimax.py` `backtest_patterns.py`

### Utilities
`brain.py` — Hebbian memory + skills + session search (~35KB)
`context-compactor.py` — LLM-based context compression
`archive-signals.py` `purge_and_compact.py` — DB maintenance
`tokens.py` `top150.py` — Token list management
`speed_tracker.py` — Token speed tracking
`batch_tpsl_rewrite.py` — TP/SL batch updates

### One-Shot / Debug
`run_mcp_server.py` — MCP server for external tool access
`run_better_coder.py` — Code improvement agent
`away_detector.py` — T's presence detection
`event_log.py` `error_breadcrumbs.py` — Logging utilities
`checkpoint_utils.py` — Snapshot utilities

---

## Known Issues (2026-04-12)
1. **Pipeline BROKEN** — ai_decider errors: "name 'ai_decider' is not defined" / "name 'HOTSET_BLOCKLIST' is not defined" — module scope bug in get_pending_signals
2. **Zero signals** — signals_hermes_runtime.db has 0 PENDING/WAIT/APPROVED signals
3. **Hotset STALE** — hotset.json empty (should have 20 signals), ~107 min since last update
4. **smoke_test false positive** — `no_flapping` check is a false positive (458K-line event log always hits >10 threshold)

**Plan:** `/root/.hermes/plans/2026-04-09_230328-...` — Profit Monster close-reason bug fix + pipeline repair

---

# ATM ARCHITECTURE SNAPSHOT (auto-generated, see: ATM-Architecture.md)
# ATM Architecture — Hermes Trading System
**Last updated:** 2026-04-12 17:30 UTC

---

## System Status
```
PIPELINE: ERROR (ai_decider broken — 0 signals in DB)
LIVE TRADING: ON ✅ (hype_live_trading.json: live_trading=true)
HOTSET: EMPTY (0 signals — stale 107+ min, ai_decider broken)
REGIME: UNKNOWN
HL Wallet: 0x324a9713603863FE3A678E83d7a81E20186126E7
```

---

## High-Level Data Flow

```
MARKET DATA (Binance + Hyperliquid)
    │
    ▼
price_collector.py          ──→ signals_hermes.db::price_history (~1.7M rows)
    │                              signals_hermes_runtime.db::latest_prices
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │                              hl_cache.json (live HL prices/positions)
    ▼
signal_gen.py               ──→ signals_hermes_runtime.db::signals
    │                              PENDING → WAIT → APPROVED → EXECUTED
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              token_speeds table (536 tokens)
    │
    │  Every 1 min (via run_pipeline.py) ▼
    │
ai_decider.py               ──→ compact_signals() → /var/www/hermes/data/hotset.json
    │  (Every 10 min)                     Top 20 by recency + confidence + confluence + speed_score
    │                              Scoring: recency + confidence + confluence + speed_score
    │                              BLACKLIST filter (LONG_BLACKLIST / SHORT_BLACKLIST)
    │                              Solana-only filter (is_solana_only)
    │                              review_count increments on WAIT/SKIPPED
    │
    ▼
decider_run.py              ──→ TWO PATHS (both enforce bans):
    │                              1. _run_hot_set() → reads hotset.json
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                              Dynamic paper/live: paper = not is_live_trading_enabled()
    │                              Both paths write to paper trades DB only.
    │
    ▼
hyperliquid_exchange.py     ──→ HL API
    │                              mirror_open() for paper; mirrors to real HL when live
    │                              Kill switch: hype_live_trading.json
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              If live_trading=true: mirror_open() to real HL orders
    │                              Reconciles HL positions ↔ paper DB
    │                              Marks guardian_missing / hl_position_missing closes
    │
position_manager.py         ──→ trailing stops, stale winner/loser exits, cascade flips
    │                          KILL SWITCH: CASCADE_FLIP_ENABLED=False (2026-04-10)
    │                              ATR-based self-close (internal, no HL trigger orders needed)
    │                              ATR_HL_ORDERS_ENABLED=False (HL order execution disabled)
    │
    ▼
hermes-trades-api.py        ──→ /var/www/hermes/data/signals.json (web dashboard)
update-trades-json.py       ──→ /var/www/hermes/data/trades.json (position state)
```

---

## Pipeline Orchestration

**Entry point:** `run_pipeline.py` — runs every 1 min via `hermes-pipeline.timer` (systemd)
- Acquires lock at `/tmp/hermes-pipeline.lock` to prevent overlapping runs
- Reads `hype_live_trading.json` to determine LIVE vs PAPER mode
- On minutes 0/10/20/30/40/50: also runs 10-minute steps

### 1-Minute Steps (every tick)
| Step | Script |
|------|--------|
| Price collection | `price_collector.py` |
| Regime scan | `4h_regime_scanner.py` |
| Signal generation | `signal_gen.py` |
| Hot-set execution | `decider_run.py` |
| Position management | `position_manager.py` |
| Dashboard update | `update-trades-json.py` |
| API write | `hermes-trades-api.py` |

### 10-Minute Steps (on the clock: :00, :10, :20, :30, :40, :50)
| Step | Script |
|------|--------|
| AI decision + compaction | `ai_decider.py` |
| Strategy optimization | `strategy_optimizer.py` |
| A/B optimization | `ab_optimizer.py` |
| A/B learner | `ab_learner.py` |

---

## Data Stores

| File | Contents |
|------|----------|
| `signals_hermes.db` | price_history (~1.7M rows static), candle_cache, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (536 tokens), predictions |
| `predictions.db` | ML predictions (~16MB, active) |
| `mtf_macd_tuner.db` | Self-tuning MACD params per token + market regime (~21MB) |
| `candle_cache.db` | Candle data for backtesting |
| `state.db` | General state (messages, schema_version) |
| `brain.db` | Hebbian associative memory network |
| `/var/www/hermes/data/hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `/var/www/hermes/data/hotset.json` | Current hot set (top 20 signals, compact_rounds tracking) |
| `/var/www/hermes/data/hl_cache.json` | Live HL prices + positions (refreshed every pipeline run) |
| `/var/www/hermes/data/signals.json` | Web dashboard signal feed |
| `/var/www/hermes/data/trades.json` | Open position state |
| `/root/.hermes/data/trailing_stops.json` | Trailing stop state |
| `/root/.hermes/data/speed_history.json` | Token speed history |
| `/root/.hermes/data/hotset.json` | Runtime copy of hotset (symlink or copy) |

---

## Kill Switch Architecture

```
hype_live_trading.json (at /var/www/hermes/data/)
    │
    ├── live_trading: false → all trades stay in paper DB
    └── live_trading: true  → guardian mirrors approved trades to real HL orders

CASCADE_FLIP_ENABLED (position_manager.py line 78)
    └── false → ALL cascade flip logic disabled

ATR_HL_ORDERS_ENABLED (position_manager.py)
    └── false → ATR-based HL trigger orders disabled (self-close uses internal DB only)
```

---

## Additional Services (systemd timers)

| Timer | Frequency | Service |
|-------|-----------|---------|
| `hermes-price-collector.timer` | 1 min | Real-time price collection |
| `hermes-hype-paper-sync.timer` | 10 min | HL ↔ paper position sync |
| `hermes-self-close-watcher.timer` | 1 min | Monitors ATR SL/TP self-close triggers |
| `hermes-candle-predictor.timer` | 10 min | ML candle direction predictions |
| `hermes-mtf-macd-tuner.timer` | 12 min | Self-tuning MACD parameter optimization |
| `hermes-away-detector.timer` | 5 min | Detects T's absence → self-init mode |
| `hermes-context-compactor.timer` | 30 min | Compacts CONTEXT.md via LLM |
| `hermes-brain-sync.timer` | 1 hour | Syncs brain memory |
| `hermes-archive-signals.timer` | daily | Archives old signals |
| `hermes-git-release.timer` | daily | Auto git commit + GitHub release |
| `hermes-smoke-test.timer` | ? | Health checks |
| `hermes-trading-checklist.timer` | ? | Trading checklist |

---

## Scripts Inventory
**Location:** `/root/.hermes/scripts/` (~60 scripts)

### Core Pipeline (in run_pipeline.py)
`price_collector.py` `4h_regime_scanner.py` `signal_gen.py` `decider_run.py`
`position_manager.py` `update-trades-json.py` `hermes-trades-api.py`
`ai_decider.py` `strategy_optimizer.py` `ab_optimizer.py` `ab_learner.py`

### ML / Predictors
`candle_predictor.py` — ML candle direction model (~49KB)
`candle_tuner.py` — Hyperparameter tuning for candle model
`backtest_mtf_macd.py` — Multi-timeframe MACD backtesting (~32KB)
`wave_backtest.py` — Wave pattern backtesting
`study_winning_combos.py` — A/B combo analysis

### Monitoring / Guardian
`hl-sync-guardian.py` — Live trading kill-switch + HL reconciliation
`wasp.py` — System health & anomaly detection (~40KB)
`smoke_test.py` — Health check tests (~19KB)
`self_close_watcher.py` — ATR self-close monitoring

### Backtesting
`backtest_candle.py` `backtest_minimax.py` `backtest_patterns.py`

### Utilities
`brain.py` — Hebbian memory + skills + session search (~35KB)
`context-compactor.py` — LLM-based context compression
`archive-signals.py` `purge_and_compact.py` — DB maintenance
`tokens.py` `top150.py` — Token list management
`speed_tracker.py` — Token speed tracking
`batch_tpsl_rewrite.py` — TP/SL batch updates

### One-Shot / Debug
`run_mcp_server.py` — MCP server for external tool access
`run_better_coder.py` — Code improvement agent
`away_detector.py` — T's presence detection
`event_log.py` `error_breadcrumbs.py` — Logging utilities
`checkpoint_utils.py` — Snapshot utilities

---

## Known Issues (2026-04-12)
1. **Pipeline BROKEN** — ai_decider errors: "name 'ai_decider' is not defined" / "name 'HOTSET_BLOCKLIST' is not defined" — module scope bug in get_pending_signals
2. **Zero signals** — signals_hermes_runtime.db has 0 PENDING/WAIT/APPROVED signals
3. **Hotset STALE** — hotset.json empty (should have 20 signals), ~107 min since last update
4. **smoke_test false positive** — `no_flapping` check is a false positive (458K-line event log always hits >10 threshold)

**Plan:** `/root/.hermes/plans/2026-04-09_230328-...` — Profit Monster close-reason bug fix + pipeline repair

---

# ATM ARCHITECTURE SNAPSHOT (auto-generated, see: ATM-Architecture.md)
# ATM Architecture — Hermes Trading System
**Last updated:** 2026-04-12 17:30 UTC

---

## System Status
```
PIPELINE: ERROR (ai_decider broken — 0 signals in DB)
LIVE TRADING: ON ✅ (hype_live_trading.json: live_trading=true)
HOTSET: EMPTY (0 signals — stale 107+ min, ai_decider broken)
REGIME: UNKNOWN
HL Wallet: 0x324a9713603863FE3A678E83d7a81E20186126E7
```

---

## High-Level Data Flow

```
MARKET DATA (Binance + Hyperliquid)
    │
    ▼
price_collector.py          ──→ signals_hermes.db::price_history (~1.7M rows)
    │                              signals_hermes_runtime.db::latest_prices
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │                              hl_cache.json (live HL prices/positions)
    ▼
signal_gen.py               ──→ signals_hermes_runtime.db::signals
    │                              PENDING → WAIT → APPROVED → EXECUTED
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              token_speeds table (536 tokens)
    │
    │  Every 1 min (via run_pipeline.py) ▼
    │
ai_decider.py               ──→ compact_signals() → /var/www/hermes/data/hotset.json
    │  (Every 10 min)                     Top 20 by recency + confidence + confluence + speed_score
    │                              Scoring: recency + confidence + confluence + speed_score
    │                              BLACKLIST filter (LONG_BLACKLIST / SHORT_BLACKLIST)
    │                              Solana-only filter (is_solana_only)
    │                              review_count increments on WAIT/SKIPPED
    │
    ▼
decider_run.py              ──→ TWO PATHS (both enforce bans):
    │                              1. _run_hot_set() → reads hotset.json
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                              Dynamic paper/live: paper = not is_live_trading_enabled()
    │                              Both paths write to paper trades DB only.
    │
    ▼
hyperliquid_exchange.py     ──→ HL API
    │                              mirror_open() for paper; mirrors to real HL when live
    │                              Kill switch: hype_live_trading.json
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              If live_trading=true: mirror_open() to real HL orders
    │                              Reconciles HL positions ↔ paper DB
    │                              Marks guardian_missing / hl_position_missing closes
    │
position_manager.py         ──→ trailing stops, stale winner/loser exits, cascade flips
    │                          KILL SWITCH: CASCADE_FLIP_ENABLED=False (2026-04-10)
    │                              ATR-based self-close (internal, no HL trigger orders needed)
    │                              ATR_HL_ORDERS_ENABLED=False (HL order execution disabled)
    │
    ▼
hermes-trades-api.py        ──→ /var/www/hermes/data/signals.json (web dashboard)
update-trades-json.py       ──→ /var/www/hermes/data/trades.json (position state)
```

---

## Pipeline Orchestration

**Entry point:** `run_pipeline.py` — runs every 1 min via `hermes-pipeline.timer` (systemd)
- Acquires lock at `/tmp/hermes-pipeline.lock` to prevent overlapping runs
- Reads `hype_live_trading.json` to determine LIVE vs PAPER mode
- On minutes 0/10/20/30/40/50: also runs 10-minute steps

### 1-Minute Steps (every tick)
| Step | Script |
|------|--------|
| Price collection | `price_collector.py` |
| Regime scan | `4h_regime_scanner.py` |
| Signal generation | `signal_gen.py` |
| Hot-set execution | `decider_run.py` |
| Position management | `position_manager.py` |
| Dashboard update | `update-trades-json.py` |
| API write | `hermes-trades-api.py` |

### 10-Minute Steps (on the clock: :00, :10, :20, :30, :40, :50)
| Step | Script |
|------|--------|
| AI decision + compaction | `ai_decider.py` |
| Strategy optimization | `strategy_optimizer.py` |
| A/B optimization | `ab_optimizer.py` |
| A/B learner | `ab_learner.py` |

---

## Data Stores

| File | Contents |
|------|----------|
| `signals_hermes.db` | price_history (~1.7M rows static), candle_cache, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (536 tokens), predictions |
| `predictions.db` | ML predictions (~16MB, active) |
| `mtf_macd_tuner.db` | Self-tuning MACD params per token + market regime (~21MB) |
| `candle_cache.db` | Candle data for backtesting |
| `state.db` | General state (messages, schema_version) |
| `brain.db` | Hebbian associative memory network |
| `/var/www/hermes/data/hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `/var/www/hermes/data/hotset.json` | Current hot set (top 20 signals, compact_rounds tracking) |
| `/var/www/hermes/data/hl_cache.json` | Live HL prices + positions (refreshed every pipeline run) |
| `/var/www/hermes/data/signals.json` | Web dashboard signal feed |
| `/var/www/hermes/data/trades.json` | Open position state |
| `/root/.hermes/data/trailing_stops.json` | Trailing stop state |
| `/root/.hermes/data/speed_history.json` | Token speed history |
| `/root/.hermes/data/hotset.json` | Runtime copy of hotset (symlink or copy) |

---

## Kill Switch Architecture

```
hype_live_trading.json (at /var/www/hermes/data/)
    │
    ├── live_trading: false → all trades stay in paper DB
    └── live_trading: true  → guardian mirrors approved trades to real HL orders

CASCADE_FLIP_ENABLED (position_manager.py line 78)
    └── false → ALL cascade flip logic disabled

ATR_HL_ORDERS_ENABLED (position_manager.py)
    └── false → ATR-based HL trigger orders disabled (self-close uses internal DB only)
```

---

## Additional Services (systemd timers)

| Timer | Frequency | Service |
|-------|-----------|---------|
| `hermes-price-collector.timer` | 1 min | Real-time price collection |
| `hermes-hype-paper-sync.timer` | 10 min | HL ↔ paper position sync |
| `hermes-self-close-watcher.timer` | 1 min | Monitors ATR SL/TP self-close triggers |
| `hermes-candle-predictor.timer` | 10 min | ML candle direction predictions |
| `hermes-mtf-macd-tuner.timer` | 12 min | Self-tuning MACD parameter optimization |
| `hermes-away-detector.timer` | 5 min | Detects T's absence → self-init mode |
| `hermes-context-compactor.timer` | 30 min | Compacts CONTEXT.md via LLM |
| `hermes-brain-sync.timer` | 1 hour | Syncs brain memory |
| `hermes-archive-signals.timer` | daily | Archives old signals |
| `hermes-git-release.timer` | daily | Auto git commit + GitHub release |
| `hermes-smoke-test.timer` | ? | Health checks |
| `hermes-trading-checklist.timer` | ? | Trading checklist |

---

## Scripts Inventory
**Location:** `/root/.hermes/scripts/` (~60 scripts)

### Core Pipeline (in run_pipeline.py)
`price_collector.py` `4h_regime_scanner.py` `signal_gen.py` `decider_run.py`
`position_manager.py` `update-trades-json.py` `hermes-trades-api.py`
`ai_decider.py` `strategy_optimizer.py` `ab_optimizer.py` `ab_learner.py`

### ML / Predictors
`candle_predictor.py` — ML candle direction model (~49KB)
`candle_tuner.py` — Hyperparameter tuning for candle model
`backtest_mtf_macd.py` — Multi-timeframe MACD backtesting (~32KB)
`wave_backtest.py` — Wave pattern backtesting
`study_winning_combos.py` — A/B combo analysis

### Monitoring / Guardian
`hl-sync-guardian.py` — Live trading kill-switch + HL reconciliation
`wasp.py` — System health & anomaly detection (~40KB)
`smoke_test.py` — Health check tests (~19KB)
`self_close_watcher.py` — ATR self-close monitoring

### Backtesting
`backtest_candle.py` `backtest_minimax.py` `backtest_patterns.py`

### Utilities
`brain.py` — Hebbian memory + skills + session search (~35KB)
`context-compactor.py` — LLM-based context compression
`archive-signals.py` `purge_and_compact.py` — DB maintenance
`tokens.py` `top150.py` — Token list management
`speed_tracker.py` — Token speed tracking
`batch_tpsl_rewrite.py` — TP/SL batch updates

### One-Shot / Debug
`run_mcp_server.py` — MCP server for external tool access
`run_better_coder.py` — Code improvement agent
`away_detector.py` — T's presence detection
`event_log.py` `error_breadcrumbs.py` — Logging utilities
`checkpoint_utils.py` — Snapshot utilities

---

## Known Issues (2026-04-12)
1. **Pipeline BROKEN** — ai_decider errors: "name 'ai_decider' is not defined" / "name 'HOTSET_BLOCKLIST' is not defined" — module scope bug in get_pending_signals
2. **Zero signals** — signals_hermes_runtime.db has 0 PENDING/WAIT/APPROVED signals
3. **Hotset STALE** — hotset.json empty (should have 20 signals), ~107 min since last update
4. **smoke_test false positive** — `no_flapping` check is a false positive (458K-line event log always hits >10 threshold)

**Plan:** `/root/.hermes/plans/2026-04-09_230328-...` — Profit Monster close-reason bug fix + pipeline repair

---

# ATM ARCHITECTURE SNAPSHOT (auto-generated, see: ATM-Architecture.md)
# ATM Architecture — Hermes Trading System
**Last updated:** 2026-04-12 17:30 UTC

---

## System Status
```
PIPELINE: ERROR (ai_decider broken — 0 signals in DB)
LIVE TRADING: ON ✅ (hype_live_trading.json: live_trading=true)
HOTSET: EMPTY (0 signals — stale 107+ min, ai_decider broken)
REGIME: UNKNOWN
HL Wallet: 0x324a9713603863FE3A678E83d7a81E20186126E7
```

---

## High-Level Data Flow

```
MARKET DATA (Binance + Hyperliquid)
    │
    ▼
price_collector.py          ──→ signals_hermes.db::price_history (~1.7M rows)
    │                              signals_hermes_runtime.db::latest_prices
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │                              hl_cache.json (live HL prices/positions)
    ▼
signal_gen.py               ──→ signals_hermes_runtime.db::signals
    │                              PENDING → WAIT → APPROVED → EXECUTED
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              token_speeds table (536 tokens)
    │
    │  Every 1 min (via run_pipeline.py) ▼
    │
ai_decider.py               ──→ compact_signals() → /var/www/hermes/data/hotset.json
    │  (Every 10 min)                     Top 20 by recency + confidence + confluence + speed_score
    │                              Scoring: recency + confidence + confluence + speed_score
    │                              BLACKLIST filter (LONG_BLACKLIST / SHORT_BLACKLIST)
    │                              Solana-only filter (is_solana_only)
    │                              review_count increments on WAIT/SKIPPED
    │
    ▼
decider_run.py              ──→ TWO PATHS (both enforce bans):
    │                              1. _run_hot_set() → reads hotset.json
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                              Dynamic paper/live: paper = not is_live_trading_enabled()
    │                              Both paths write to paper trades DB only.
    │
    ▼
hyperliquid_exchange.py     ──→ HL API
    │                              mirror_open() for paper; mirrors to real HL when live
    │                              Kill switch: hype_live_trading.json
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              If live_trading=true: mirror_open() to real HL orders
    │                              Reconciles HL positions ↔ paper DB
    │                              Marks guardian_missing / hl_position_missing closes
    │
position_manager.py         ──→ trailing stops, stale winner/loser exits, cascade flips
    │                          KILL SWITCH: CASCADE_FLIP_ENABLED=False (2026-04-10)
    │                              ATR-based self-close (internal, no HL trigger orders needed)
    │                              ATR_HL_ORDERS_ENABLED=False (HL order execution disabled)
    │
    ▼
hermes-trades-api.py        ──→ /var/www/hermes/data/signals.json (web dashboard)
update-trades-json.py       ──→ /var/www/hermes/data/trades.json (position state)
```

---

## Pipeline Orchestration

**Entry point:** `run_pipeline.py` — runs every 1 min via `hermes-pipeline.timer` (systemd)
- Acquires lock at `/tmp/hermes-pipeline.lock` to prevent overlapping runs
- Reads `hype_live_trading.json` to determine LIVE vs PAPER mode
- On minutes 0/10/20/30/40/50: also runs 10-minute steps

### 1-Minute Steps (every tick)
| Step | Script |
|------|--------|
| Price collection | `price_collector.py` |
| Regime scan | `4h_regime_scanner.py` |
| Signal generation | `signal_gen.py` |
| Hot-set execution | `decider_run.py` |
| Position management | `position_manager.py` |
| Dashboard update | `update-trades-json.py` |
| API write | `hermes-trades-api.py` |

### 10-Minute Steps (on the clock: :00, :10, :20, :30, :40, :50)
| Step | Script |
|------|--------|
| AI decision + compaction | `ai_decider.py` |
| Strategy optimization | `strategy_optimizer.py` |
| A/B optimization | `ab_optimizer.py` |
| A/B learner | `ab_learner.py` |

---

## Data Stores

| File | Contents |
|------|----------|
| `signals_hermes.db` | price_history (~1.7M rows static), candle_cache, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (536 tokens), predictions |
| `predictions.db` | ML predictions (~16MB, active) |
| `mtf_macd_tuner.db` | Self-tuning MACD params per token + market regime (~21MB) |
| `candle_cache.db` | Candle data for backtesting |
| `state.db` | General state (messages, schema_version) |
| `brain.db` | Hebbian associative memory network |
| `/var/www/hermes/data/hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `/var/www/hermes/data/hotset.json` | Current hot set (top 20 signals, compact_rounds tracking) |
| `/var/www/hermes/data/hl_cache.json` | Live HL prices + positions (refreshed every pipeline run) |
| `/var/www/hermes/data/signals.json` | Web dashboard signal feed |
| `/var/www/hermes/data/trades.json` | Open position state |
| `/root/.hermes/data/trailing_stops.json` | Trailing stop state |
| `/root/.hermes/data/speed_history.json` | Token speed history |
| `/root/.hermes/data/hotset.json` | Runtime copy of hotset (symlink or copy) |

---

## Kill Switch Architecture

```
hype_live_trading.json (at /var/www/hermes/data/)
    │
    ├── live_trading: false → all trades stay in paper DB
    └── live_trading: true  → guardian mirrors approved trades to real HL orders

CASCADE_FLIP_ENABLED (position_manager.py line 78)
    └── false → ALL cascade flip logic disabled

ATR_HL_ORDERS_ENABLED (position_manager.py)
    └── false → ATR-based HL trigger orders disabled (self-close uses internal DB only)
```

---

## Additional Services (systemd timers)

| Timer | Frequency | Service |
|-------|-----------|---------|
| `hermes-price-collector.timer` | 1 min | Real-time price collection |
| `hermes-hype-paper-sync.timer` | 10 min | HL ↔ paper position sync |
| `hermes-self-close-watcher.timer` | 1 min | Monitors ATR SL/TP self-close triggers |
| `hermes-candle-predictor.timer` | 10 min | ML candle direction predictions |
| `hermes-mtf-macd-tuner.timer` | 12 min | Self-tuning MACD parameter optimization |
| `hermes-away-detector.timer` | 5 min | Detects T's absence → self-init mode |
| `hermes-context-compactor.timer` | 30 min | Compacts CONTEXT.md via LLM |
| `hermes-brain-sync.timer` | 1 hour | Syncs brain memory |
| `hermes-archive-signals.timer` | daily | Archives old signals |
| `hermes-git-release.timer` | daily | Auto git commit + GitHub release |
| `hermes-smoke-test.timer` | ? | Health checks |
| `hermes-trading-checklist.timer` | ? | Trading checklist |

---

## Scripts Inventory
**Location:** `/root/.hermes/scripts/` (~60 scripts)

### Core Pipeline (in run_pipeline.py)
`price_collector.py` `4h_regime_scanner.py` `signal_gen.py` `decider_run.py`
`position_manager.py` `update-trades-json.py` `hermes-trades-api.py`
`ai_decider.py` `strategy_optimizer.py` `ab_optimizer.py` `ab_learner.py`

### ML / Predictors
`candle_predictor.py` — ML candle direction model (~49KB)
`candle_tuner.py` — Hyperparameter tuning for candle model
`backtest_mtf_macd.py` — Multi-timeframe MACD backtesting (~32KB)
`wave_backtest.py` — Wave pattern backtesting
`study_winning_combos.py` — A/B combo analysis

### Monitoring / Guardian
`hl-sync-guardian.py` — Live trading kill-switch + HL reconciliation
`wasp.py` — System health & anomaly detection (~40KB)
`smoke_test.py` — Health check tests (~19KB)
`self_close_watcher.py` — ATR self-close monitoring

### Backtesting
`backtest_candle.py` `backtest_minimax.py` `backtest_patterns.py`

### Utilities
`brain.py` — Hebbian memory + skills + session search (~35KB)
`context-compactor.py` — LLM-based context compression
`archive-signals.py` `purge_and_compact.py` — DB maintenance
`tokens.py` `top150.py` — Token list management
`speed_tracker.py` — Token speed tracking
`batch_tpsl_rewrite.py` — TP/SL batch updates

### One-Shot / Debug
`run_mcp_server.py` — MCP server for external tool access
`run_better_coder.py` — Code improvement agent
`away_detector.py` — T's presence detection
`event_log.py` `error_breadcrumbs.py` — Logging utilities
`checkpoint_utils.py` — Snapshot utilities

---

## Known Issues (2026-04-12)
1. **Pipeline BROKEN** — ai_decider errors: "name 'ai_decider' is not defined" / "name 'HOTSET_BLOCKLIST' is not defined" — module scope bug in get_pending_signals
2. **Zero signals** — signals_hermes_runtime.db has 0 PENDING/WAIT/APPROVED signals
3. **Hotset STALE** — hotset.json empty (should have 20 signals), ~107 min since last update
4. **smoke_test false positive** — `no_flapping` check is a false positive (458K-line event log always hits >10 threshold)

**Plan:** `/root/.hermes/plans/2026-04-09_230328-...` — Profit Monster close-reason bug fix + pipeline repair

---

# ATM ARCHITECTURE SNAPSHOT (auto-generated, see: ATM-Architecture.md)
# ATM Architecture — Hermes Trading System
**Last updated:** 2026-04-12 17:30 UTC

---

## System Status
```
PIPELINE: ERROR (ai_decider broken — 0 signals in DB)
LIVE TRADING: ON ✅ (hype_live_trading.json: live_trading=true)
HOTSET: EMPTY (0 signals — stale 107+ min, ai_decider broken)
REGIME: UNKNOWN
HL Wallet: 0x324a9713603863FE3A678E83d7a81E20186126E7
```

---

## High-Level Data Flow

```
MARKET DATA (Binance + Hyperliquid)
    │
    ▼
price_collector.py          ──→ signals_hermes.db::price_history (~1.7M rows)
    │                              signals_hermes_runtime.db::latest_prices
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │                              hl_cache.json (live HL prices/positions)
    ▼
signal_gen.py               ──→ signals_hermes_runtime.db::signals
    │                              PENDING → WAIT → APPROVED → EXECUTED
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              token_speeds table (536 tokens)
    │
    │  Every 1 min (via run_pipeline.py) ▼
    │
ai_decider.py               ──→ compact_signals() → /var/www/hermes/data/hotset.json
    │  (Every 10 min)                     Top 20 by recency + confidence + confluence + speed_score
    │                              Scoring: recency + confidence + confluence + speed_score
    │                              BLACKLIST filter (LONG_BLACKLIST / SHORT_BLACKLIST)
    │                              Solana-only filter (is_solana_only)
    │                              review_count increments on WAIT/SKIPPED
    │
    ▼
decider_run.py              ──→ TWO PATHS (both enforce bans):
    │                              1. _run_hot_set() → reads hotset.json
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                              Dynamic paper/live: paper = not is_live_trading_enabled()
    │                              Both paths write to paper trades DB only.
    │
    ▼
hyperliquid_exchange.py     ──→ HL API
    │                              mirror_open() for paper; mirrors to real HL when live
    │                              Kill switch: hype_live_trading.json
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              If live_trading=true: mirror_open() to real HL orders
    │                              Reconciles HL positions ↔ paper DB
    │                              Marks guardian_missing / hl_position_missing closes
    │
position_manager.py         ──→ trailing stops, stale winner/loser exits, cascade flips
    │                          KILL SWITCH: CASCADE_FLIP_ENABLED=False (2026-04-10)
    │                              ATR-based self-close (internal, no HL trigger orders needed)
    │                              ATR_HL_ORDERS_ENABLED=False (HL order execution disabled)
    │
    ▼
hermes-trades-api.py        ──→ /var/www/hermes/data/signals.json (web dashboard)
update-trades-json.py       ──→ /var/www/hermes/data/trades.json (position state)
```

---

## Pipeline Orchestration

**Entry point:** `run_pipeline.py` — runs every 1 min via `hermes-pipeline.timer` (systemd)
- Acquires lock at `/tmp/hermes-pipeline.lock` to prevent overlapping runs
- Reads `hype_live_trading.json` to determine LIVE vs PAPER mode
- On minutes 0/10/20/30/40/50: also runs 10-minute steps

### 1-Minute Steps (every tick)
| Step | Script |
|------|--------|
| Price collection | `price_collector.py` |
| Regime scan | `4h_regime_scanner.py` |
| Signal generation | `signal_gen.py` |
| Hot-set execution | `decider_run.py` |
| Position management | `position_manager.py` |
| Dashboard update | `update-trades-json.py` |
| API write | `hermes-trades-api.py` |

### 10-Minute Steps (on the clock: :00, :10, :20, :30, :40, :50)
| Step | Script |
|------|--------|
| AI decision + compaction | `ai_decider.py` |
| Strategy optimization | `strategy_optimizer.py` |
| A/B optimization | `ab_optimizer.py` |
| A/B learner | `ab_learner.py` |

---

## Data Stores

| File | Contents |
|------|----------|
| `signals_hermes.db` | price_history (~1.7M rows static), candle_cache, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (536 tokens), predictions |
| `predictions.db` | ML predictions (~16MB, active) |
| `mtf_macd_tuner.db` | Self-tuning MACD params per token + market regime (~21MB) |
| `candle_cache.db` | Candle data for backtesting |
| `state.db` | General state (messages, schema_version) |
| `brain.db` | Hebbian associative memory network |
| `/var/www/hermes/data/hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `/var/www/hermes/data/hotset.json` | Current hot set (top 20 signals, compact_rounds tracking) |
| `/var/www/hermes/data/hl_cache.json` | Live HL prices + positions (refreshed every pipeline run) |
| `/var/www/hermes/data/signals.json` | Web dashboard signal feed |
| `/var/www/hermes/data/trades.json` | Open position state |
| `/root/.hermes/data/trailing_stops.json` | Trailing stop state |
| `/root/.hermes/data/speed_history.json` | Token speed history |
| `/root/.hermes/data/hotset.json` | Runtime copy of hotset (symlink or copy) |

---

## Kill Switch Architecture

```
hype_live_trading.json (at /var/www/hermes/data/)
    │
    ├── live_trading: false → all trades stay in paper DB
    └── live_trading: true  → guardian mirrors approved trades to real HL orders

CASCADE_FLIP_ENABLED (position_manager.py line 78)
    └── false → ALL cascade flip logic disabled

ATR_HL_ORDERS_ENABLED (position_manager.py)
    └── false → ATR-based HL trigger orders disabled (self-close uses internal DB only)
```

---

## Additional Services (systemd timers)

| Timer | Frequency | Service |
|-------|-----------|---------|
| `hermes-price-collector.timer` | 1 min | Real-time price collection |
| `hermes-hype-paper-sync.timer` | 10 min | HL ↔ paper position sync |
| `hermes-self-close-watcher.timer` | 1 min | Monitors ATR SL/TP self-close triggers |
| `hermes-candle-predictor.timer` | 10 min | ML candle direction predictions |
| `hermes-mtf-macd-tuner.timer` | 12 min | Self-tuning MACD parameter optimization |
| `hermes-away-detector.timer` | 5 min | Detects T's absence → self-init mode |
| `hermes-context-compactor.timer` | 30 min | Compacts CONTEXT.md via LLM |
| `hermes-brain-sync.timer` | 1 hour | Syncs brain memory |
| `hermes-archive-signals.timer` | daily | Archives old signals |
| `hermes-git-release.timer` | daily | Auto git commit + GitHub release |
| `hermes-smoke-test.timer` | ? | Health checks |
| `hermes-trading-checklist.timer` | ? | Trading checklist |

---

## Scripts Inventory
**Location:** `/root/.hermes/scripts/` (~60 scripts)

### Core Pipeline (in run_pipeline.py)
`price_collector.py` `4h_regime_scanner.py` `signal_gen.py` `decider_run.py`
`position_manager.py` `update-trades-json.py` `hermes-trades-api.py`
`ai_decider.py` `strategy_optimizer.py` `ab_optimizer.py` `ab_learner.py`

### ML / Predictors
`candle_predictor.py` — ML candle direction model (~49KB)
`candle_tuner.py` — Hyperparameter tuning for candle model
`backtest_mtf_macd.py` — Multi-timeframe MACD backtesting (~32KB)
`wave_backtest.py` — Wave pattern backtesting
`study_winning_combos.py` — A/B combo analysis

### Monitoring / Guardian
`hl-sync-guardian.py` — Live trading kill-switch + HL reconciliation
`wasp.py` — System health & anomaly detection (~40KB)
`smoke_test.py` — Health check tests (~19KB)
`self_close_watcher.py` — ATR self-close monitoring

### Backtesting
`backtest_candle.py` `backtest_minimax.py` `backtest_patterns.py`

### Utilities
`brain.py` — Hebbian memory + skills + session search (~35KB)
`context-compactor.py` — LLM-based context compression
`archive-signals.py` `purge_and_compact.py` — DB maintenance
`tokens.py` `top150.py` — Token list management
`speed_tracker.py` — Token speed tracking
`batch_tpsl_rewrite.py` — TP/SL batch updates

### One-Shot / Debug
`run_mcp_server.py` — MCP server for external tool access
`run_better_coder.py` — Code improvement agent
`away_detector.py` — T's presence detection
`event_log.py` `error_breadcrumbs.py` — Logging utilities
`checkpoint_utils.py` — Snapshot utilities

---

## Known Issues (2026-04-12)
1. **Pipeline BROKEN** — ai_decider errors: "name 'ai_decider' is not defined" / "name 'HOTSET_BLOCKLIST' is not defined" — module scope bug in get_pending_signals
2. **Zero signals** — signals_hermes_runtime.db has 0 PENDING/WAIT/APPROVED signals
3. **Hotset STALE** — hotset.json empty (should have 20 signals), ~107 min since last update
4. **smoke_test false positive** — `no_flapping` check is a false positive (458K-line event log always hits >10 threshold)

**Plan:** `/root/.hermes/plans/2026-04-09_230328-...` — Profit Monster close-reason bug fix + pipeline repair

---

# ATM ARCHITECTURE SNAPSHOT (auto-generated, see: ATM-Architecture.md)
# ATM Architecture — Hermes Trading System
**Last updated:** 2026-04-12 17:30 UTC

---

## System Status
```
PIPELINE: ERROR (ai_decider broken — 0 signals in DB)
LIVE TRADING: ON ✅ (hype_live_trading.json: live_trading=true)
HOTSET: EMPTY (0 signals — stale 107+ min, ai_decider broken)
REGIME: UNKNOWN
HL Wallet: 0x324a9713603863FE3A678E83d7a81E20186126E7
```

---

## High-Level Data Flow

```
MARKET DATA (Binance + Hyperliquid)
    │
    ▼
price_collector.py          ──→ signals_hermes.db::price_history (~1.7M rows)
    │                              signals_hermes_runtime.db::latest_prices
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │                              hl_cache.json (live HL prices/positions)
    ▼
signal_gen.py               ──→ signals_hermes_runtime.db::signals
    │                              PENDING → WAIT → APPROVED → EXECUTED
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              token_speeds table (536 tokens)
    │
    │  Every 1 min (via run_pipeline.py) ▼
    │
ai_decider.py               ──→ compact_signals() → /var/www/hermes/data/hotset.json
    │  (Every 10 min)                     Top 20 by recency + confidence + confluence + speed_score
    │                              Scoring: recency + confidence + confluence + speed_score
    │                              BLACKLIST filter (LONG_BLACKLIST / SHORT_BLACKLIST)
    │                              Solana-only filter (is_solana_only)
    │                              review_count increments on WAIT/SKIPPED
    │
    ▼
decider_run.py              ──→ TWO PATHS (both enforce bans):
    │                              1. _run_hot_set() → reads hotset.json
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                              Dynamic paper/live: paper = not is_live_trading_enabled()
    │                              Both paths write to paper trades DB only.
    │
    ▼
hyperliquid_exchange.py     ──→ HL API
    │                              mirror_open() for paper; mirrors to real HL when live
    │                              Kill switch: hype_live_trading.json
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              If live_trading=true: mirror_open() to real HL orders
    │                              Reconciles HL positions ↔ paper DB
    │                              Marks guardian_missing / hl_position_missing closes
    │
position_manager.py         ──→ trailing stops, stale winner/loser exits, cascade flips
    │                          KILL SWITCH: CASCADE_FLIP_ENABLED=False (2026-04-10)
    │                              ATR-based self-close (internal, no HL trigger orders needed)
    │                              ATR_HL_ORDERS_ENABLED=False (HL order execution disabled)
    │
    ▼
hermes-trades-api.py        ──→ /var/www/hermes/data/signals.json (web dashboard)
update-trades-json.py       ──→ /var/www/hermes/data/trades.json (position state)
```

---

## Pipeline Orchestration

**Entry point:** `run_pipeline.py` — runs every 1 min via `hermes-pipeline.timer` (systemd)
- Acquires lock at `/tmp/hermes-pipeline.lock` to prevent overlapping runs
- Reads `hype_live_trading.json` to determine LIVE vs PAPER mode
- On minutes 0/10/20/30/40/50: also runs 10-minute steps

### 1-Minute Steps (every tick)
| Step | Script |
|------|--------|
| Price collection | `price_collector.py` |
| Regime scan | `4h_regime_scanner.py` |
| Signal generation | `signal_gen.py` |
| Hot-set execution | `decider_run.py` |
| Position management | `position_manager.py` |
| Dashboard update | `update-trades-json.py` |
| API write | `hermes-trades-api.py` |

### 10-Minute Steps (on the clock: :00, :10, :20, :30, :40, :50)
| Step | Script |
|------|--------|
| AI decision + compaction | `ai_decider.py` |
| Strategy optimization | `strategy_optimizer.py` |
| A/B optimization | `ab_optimizer.py` |
| A/B learner | `ab_learner.py` |

---

## Data Stores

| File | Contents |
|------|----------|
| `signals_hermes.db` | price_history (~1.7M rows static), candle_cache, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (536 tokens), predictions |
| `predictions.db` | ML predictions (~16MB, active) |
| `mtf_macd_tuner.db` | Self-tuning MACD params per token + market regime (~21MB) |
| `candle_cache.db` | Candle data for backtesting |
| `state.db` | General state (messages, schema_version) |
| `brain.db` | Hebbian associative memory network |
| `/var/www/hermes/data/hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `/var/www/hermes/data/hotset.json` | Current hot set (top 20 signals, compact_rounds tracking) |
| `/var/www/hermes/data/hl_cache.json` | Live HL prices + positions (refreshed every pipeline run) |
| `/var/www/hermes/data/signals.json` | Web dashboard signal feed |
| `/var/www/hermes/data/trades.json` | Open position state |
| `/root/.hermes/data/trailing_stops.json` | Trailing stop state |
| `/root/.hermes/data/speed_history.json` | Token speed history |
| `/root/.hermes/data/hotset.json` | Runtime copy of hotset (symlink or copy) |

---

## Kill Switch Architecture

```
hype_live_trading.json (at /var/www/hermes/data/)
    │
    ├── live_trading: false → all trades stay in paper DB
    └── live_trading: true  → guardian mirrors approved trades to real HL orders

CASCADE_FLIP_ENABLED (position_manager.py line 78)
    └── false → ALL cascade flip logic disabled

ATR_HL_ORDERS_ENABLED (position_manager.py)
    └── false → ATR-based HL trigger orders disabled (self-close uses internal DB only)
```

---

## Additional Services (systemd timers)

| Timer | Frequency | Service |
|-------|-----------|---------|
| `hermes-price-collector.timer` | 1 min | Real-time price collection |
| `hermes-hype-paper-sync.timer` | 10 min | HL ↔ paper position sync |
| `hermes-self-close-watcher.timer` | 1 min | Monitors ATR SL/TP self-close triggers |
| `hermes-candle-predictor.timer` | 10 min | ML candle direction predictions |
| `hermes-mtf-macd-tuner.timer` | 12 min | Self-tuning MACD parameter optimization |
| `hermes-away-detector.timer` | 5 min | Detects T's absence → self-init mode |
| `hermes-context-compactor.timer` | 30 min | Compacts CONTEXT.md via LLM |
| `hermes-brain-sync.timer` | 1 hour | Syncs brain memory |
| `hermes-archive-signals.timer` | daily | Archives old signals |
| `hermes-git-release.timer` | daily | Auto git commit + GitHub release |
| `hermes-smoke-test.timer` | ? | Health checks |
| `hermes-trading-checklist.timer` | ? | Trading checklist |

---

## Scripts Inventory
**Location:** `/root/.hermes/scripts/` (~60 scripts)

### Core Pipeline (in run_pipeline.py)
`price_collector.py` `4h_regime_scanner.py` `signal_gen.py` `decider_run.py`
`position_manager.py` `update-trades-json.py` `hermes-trades-api.py`
`ai_decider.py` `strategy_optimizer.py` `ab_optimizer.py` `ab_learner.py`

### ML / Predictors
`candle_predictor.py` — ML candle direction model (~49KB)
`candle_tuner.py` — Hyperparameter tuning for candle model
`backtest_mtf_macd.py` — Multi-timeframe MACD backtesting (~32KB)
`wave_backtest.py` — Wave pattern backtesting
`study_winning_combos.py` — A/B combo analysis

### Monitoring / Guardian
`hl-sync-guardian.py` — Live trading kill-switch + HL reconciliation
`wasp.py` — System health & anomaly detection (~40KB)
`smoke_test.py` — Health check tests (~19KB)
`self_close_watcher.py` — ATR self-close monitoring

### Backtesting
`backtest_candle.py` `backtest_minimax.py` `backtest_patterns.py`

### Utilities
`brain.py` — Hebbian memory + skills + session search (~35KB)
`context-compactor.py` — LLM-based context compression
`archive-signals.py` `purge_and_compact.py` — DB maintenance
`tokens.py` `top150.py` — Token list management
`speed_tracker.py` — Token speed tracking
`batch_tpsl_rewrite.py` — TP/SL batch updates

### One-Shot / Debug
`run_mcp_server.py` — MCP server for external tool access
`run_better_coder.py` — Code improvement agent
`away_detector.py` — T's presence detection
`event_log.py` `error_breadcrumbs.py` — Logging utilities
`checkpoint_utils.py` — Snapshot utilities

---

## Known Issues (2026-04-12)
1. **Pipeline BROKEN** — ai_decider errors: "name 'ai_decider' is not defined" / "name 'HOTSET_BLOCKLIST' is not defined" — module scope bug in get_pending_signals
2. **Zero signals** — signals_hermes_runtime.db has 0 PENDING/WAIT/APPROVED signals
3. **Hotset STALE** — hotset.json empty (should have 20 signals), ~107 min since last update
4. **smoke_test false positive** — `no_flapping` check is a false positive (458K-line event log always hits >10 threshold)

**Plan:** `/root/.hermes/plans/2026-04-09_230328-...` — Profit Monster close-reason bug fix + pipeline repair

---

# ATM ARCHITECTURE SNAPSHOT (auto-generated, see: ATM-Architecture.md)
# ATM Architecture — Hermes Trading System
**Last updated:** 2026-04-12 17:30 UTC

---

## System Status
```
PIPELINE: ERROR (ai_decider broken — 0 signals in DB)
LIVE TRADING: ON ✅ (hype_live_trading.json: live_trading=true)
HOTSET: EMPTY (0 signals — stale 107+ min, ai_decider broken)
REGIME: UNKNOWN
HL Wallet: 0x324a9713603863FE3A678E83d7a81E20186126E7
```

---

## High-Level Data Flow

```
MARKET DATA (Binance + Hyperliquid)
    │
    ▼
price_collector.py          ──→ signals_hermes.db::price_history (~1.7M rows)
    │                              signals_hermes_runtime.db::latest_prices
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │                              hl_cache.json (live HL prices/positions)
    ▼
signal_gen.py               ──→ signals_hermes_runtime.db::signals
    │                              PENDING → WAIT → APPROVED → EXECUTED
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              token_speeds table (536 tokens)
    │
    │  Every 1 min (via run_pipeline.py) ▼
    │
ai_decider.py               ──→ compact_signals() → /var/www/hermes/data/hotset.json
    │  (Every 10 min)                     Top 20 by recency + confidence + confluence + speed_score
    │                              Scoring: recency + confidence + confluence + speed_score
    │                              BLACKLIST filter (LONG_BLACKLIST / SHORT_BLACKLIST)
    │                              Solana-only filter (is_solana_only)
    │                              review_count increments on WAIT/SKIPPED
    │
    ▼
decider_run.py              ──→ TWO PATHS (both enforce bans):
    │                              1. _run_hot_set() → reads hotset.json
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                              Dynamic paper/live: paper = not is_live_trading_enabled()
    │                              Both paths write to paper trades DB only.
    │
    ▼
hyperliquid_exchange.py     ──→ HL API
    │                              mirror_open() for paper; mirrors to real HL when live
    │                              Kill switch: hype_live_trading.json
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              If live_trading=true: mirror_open() to real HL orders
    │                              Reconciles HL positions ↔ paper DB
    │                              Marks guardian_missing / hl_position_missing closes
    │
position_manager.py         ──→ trailing stops, stale winner/loser exits, cascade flips
    │                          KILL SWITCH: CASCADE_FLIP_ENABLED=False (2026-04-10)
    │                              ATR-based self-close (internal, no HL trigger orders needed)
    │                              ATR_HL_ORDERS_ENABLED=False (HL order execution disabled)
    │
    ▼
hermes-trades-api.py        ──→ /var/www/hermes/data/signals.json (web dashboard)
update-trades-json.py       ──→ /var/www/hermes/data/trades.json (position state)
```

---

## Pipeline Orchestration

**Entry point:** `run_pipeline.py` — runs every 1 min via `hermes-pipeline.timer` (systemd)
- Acquires lock at `/tmp/hermes-pipeline.lock` to prevent overlapping runs
- Reads `hype_live_trading.json` to determine LIVE vs PAPER mode
- On minutes 0/10/20/30/40/50: also runs 10-minute steps

### 1-Minute Steps (every tick)
| Step | Script |
|------|--------|
| Price collection | `price_collector.py` |
| Regime scan | `4h_regime_scanner.py` |
| Signal generation | `signal_gen.py` |
| Hot-set execution | `decider_run.py` |
| Position management | `position_manager.py` |
| Dashboard update | `update-trades-json.py` |
| API write | `hermes-trades-api.py` |

### 10-Minute Steps (on the clock: :00, :10, :20, :30, :40, :50)
| Step | Script |
|------|--------|
| AI decision + compaction | `ai_decider.py` |
| Strategy optimization | `strategy_optimizer.py` |
| A/B optimization | `ab_optimizer.py` |
| A/B learner | `ab_learner.py` |

---

## Data Stores

| File | Contents |
|------|----------|
| `signals_hermes.db` | price_history (~1.7M rows static), candle_cache, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (536 tokens), predictions |
| `predictions.db` | ML predictions (~16MB, active) |
| `mtf_macd_tuner.db` | Self-tuning MACD params per token + market regime (~21MB) |
| `candle_cache.db` | Candle data for backtesting |
| `state.db` | General state (messages, schema_version) |
| `brain.db` | Hebbian associative memory network |
| `/var/www/hermes/data/hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `/var/www/hermes/data/hotset.json` | Current hot set (top 20 signals, compact_rounds tracking) |
| `/var/www/hermes/data/hl_cache.json` | Live HL prices + positions (refreshed every pipeline run) |
| `/var/www/hermes/data/signals.json` | Web dashboard signal feed |
| `/var/www/hermes/data/trades.json` | Open position state |
| `/root/.hermes/data/trailing_stops.json` | Trailing stop state |
| `/root/.hermes/data/speed_history.json` | Token speed history |
| `/root/.hermes/data/hotset.json` | Runtime copy of hotset (symlink or copy) |

---

## Kill Switch Architecture

```
hype_live_trading.json (at /var/www/hermes/data/)
    │
    ├── live_trading: false → all trades stay in paper DB
    └── live_trading: true  → guardian mirrors approved trades to real HL orders

CASCADE_FLIP_ENABLED (position_manager.py line 78)
    └── false → ALL cascade flip logic disabled

ATR_HL_ORDERS_ENABLED (position_manager.py)
    └── false → ATR-based HL trigger orders disabled (self-close uses internal DB only)
```

---

## Additional Services (systemd timers)

| Timer | Frequency | Service |
|-------|-----------|---------|
| `hermes-price-collector.timer` | 1 min | Real-time price collection |
| `hermes-hype-paper-sync.timer` | 10 min | HL ↔ paper position sync |
| `hermes-self-close-watcher.timer` | 1 min | Monitors ATR SL/TP self-close triggers |
| `hermes-candle-predictor.timer` | 10 min | ML candle direction predictions |
| `hermes-mtf-macd-tuner.timer` | 12 min | Self-tuning MACD parameter optimization |
| `hermes-away-detector.timer` | 5 min | Detects T's absence → self-init mode |
| `hermes-context-compactor.timer` | 30 min | Compacts CONTEXT.md via LLM |
| `hermes-brain-sync.timer` | 1 hour | Syncs brain memory |
| `hermes-archive-signals.timer` | daily | Archives old signals |
| `hermes-git-release.timer` | daily | Auto git commit + GitHub release |
| `hermes-smoke-test.timer` | ? | Health checks |
| `hermes-trading-checklist.timer` | ? | Trading checklist |

---

## Scripts Inventory
**Location:** `/root/.hermes/scripts/` (~60 scripts)

### Core Pipeline (in run_pipeline.py)
`price_collector.py` `4h_regime_scanner.py` `signal_gen.py` `decider_run.py`
`position_manager.py` `update-trades-json.py` `hermes-trades-api.py`
`ai_decider.py` `strategy_optimizer.py` `ab_optimizer.py` `ab_learner.py`

### ML / Predictors
`candle_predictor.py` — ML candle direction model (~49KB)
`candle_tuner.py` — Hyperparameter tuning for candle model
`backtest_mtf_macd.py` — Multi-timeframe MACD backtesting (~32KB)
`wave_backtest.py` — Wave pattern backtesting
`study_winning_combos.py` — A/B combo analysis

### Monitoring / Guardian
`hl-sync-guardian.py` — Live trading kill-switch + HL reconciliation
`wasp.py` — System health & anomaly detection (~40KB)
`smoke_test.py` — Health check tests (~19KB)
`self_close_watcher.py` — ATR self-close monitoring

### Backtesting
`backtest_candle.py` `backtest_minimax.py` `backtest_patterns.py`

### Utilities
`brain.py` — Hebbian memory + skills + session search (~35KB)
`context-compactor.py` — LLM-based context compression
`archive-signals.py` `purge_and_compact.py` — DB maintenance
`tokens.py` `top150.py` — Token list management
`speed_tracker.py` — Token speed tracking
`batch_tpsl_rewrite.py` — TP/SL batch updates

### One-Shot / Debug
`run_mcp_server.py` — MCP server for external tool access
`run_better_coder.py` — Code improvement agent
`away_detector.py` — T's presence detection
`event_log.py` `error_breadcrumbs.py` — Logging utilities
`checkpoint_utils.py` — Snapshot utilities

---

## Known Issues (2026-04-12)
1. **Pipeline BROKEN** — ai_decider errors: "name 'ai_decider' is not defined" / "name 'HOTSET_BLOCKLIST' is not defined" — module scope bug in get_pending_signals
2. **Zero signals** — signals_hermes_runtime.db has 0 PENDING/WAIT/APPROVED signals
3. **Hotset STALE** — hotset.json empty (should have 20 signals), ~107 min since last update
4. **smoke_test false positive** — `no_flapping` check is a false positive (458K-line event log always hits >10 threshold)

**Plan:** `/root/.hermes/plans/2026-04-09_230328-...` — Profit Monster close-reason bug fix + pipeline repair

---

## Last Updated
- 2026-04-12 17:30 UTC — Complete rewrite. Added all timers, services, ML scripts, known issues.
- 2026-04-08 — Corrected script paths, DB locations, row counts, paper/live dynamic flag
