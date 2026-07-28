# AGENTS.md — Hermes Trading System

## Quick Reference

- **Language:** Python 3 (no frameworks, no build step — raw scripts + SQLite + systemd)
- **Run pipeline:** `python3 scripts/run_pipeline.py` (acquires lock at `/tmp/hermes-pipeline.lock`)
- **Init/reset DBs:** `python3 scripts/signal_schema.py`
- **Test a single script:** `python3 scripts/price_collector.py` (or any step in isolation)
- **Logs:** `tail -100 /root/.hermes/logs/pipeline.log`
- **Architecture detail:** `/root/.hermes/ATM/ATM-Architecture.md`

## Two Data Directories

| Directory | Purpose | Gitignored? |
|-----------|---------|-------------|
| `HERMES_DATA` = `/root/.hermes/data` | Local runtime data (DBs, JSON state) | Yes |
| `WWW_DATA` = `/var/www/hermes/data` | Served by nginx (dashboard, kill switch, hotset) | N/A (not in repo) |

All file/DB paths are defined in **`scripts/paths.py`** — import with `from paths import *`.
Never hardcode paths. Use `HERMES_DATA` or `WWW_DATA` from paths.

## Key Gotchas

- **`ai_decider.py` is DEFUNCT** — replaced by `signal_compactor.py` (deterministic, LLM-free). Do not call, import, or modify ai_decider.py. It still exists for backward compat imports only.
- **Signal generation migrated** — `signal_gen.py` was removed from the pipeline. All signals now go through `scripts/signals_runner.py` which loads individual signal modules from `scripts/signals/`. The old `hermes_constants.py` master `*_ENABLED` flags are all `False`.
- **`hermes_constants.py`** contains LIVE_TRADING_ENABLED, BLACKLISTS, and other critical flags. Do not modify values without explicit instruction. Line 2 says: `# DO NOT UPDATE ANY VALUES IN THIS FILE BEFORE ASKING T!!!`
- **`LIVE_TRADING_ENABLED`** in hermes_constants.py is `True`. The actual runtime kill switch is `/var/www/hermes/data/hype_live_trading.json` (`live_trading: true/false`). Both must be true for real money.
- **Lock file:** pipeline runs acquire `/tmp/hermes-pipeline.lock`. If you see "lock exists" errors, check if a pipeline run is stuck (the lock auto-releases on process exit).
- **Two regimes run independently** — `4h_regime_scanner.py` (every 4h via timer) and `15m_regime_scanner.py` (every 15m via timer). They are NOT in `run_pipeline.py` anymore. Running them from the pipeline was removed 2026-04-25 because they were eating Binance API calls.
- **price_collector** runs via its own systemd timer (`hermes-price-collector.timer`), NOT from `run_pipeline.py`. Removed from pipeline 2026-04-25.

## Pipeline Steps

`run_pipeline.py` executes these every minute:

| Step | Script | Notes |
|------|--------|-------|
| signal_compactor | `signal_compactor.py` | Deterministic hot-set compaction (top 20) |
| breakout_engine | `breakout_engine.py` | |
| signals_runner | `signals_runner.py` | Loads all modules from `scripts/signals/` |
| signals_runner_slow | `signals_runner_slow.py` | Every 5 min (momentum, mtf_momentum — slow) |
| decider_run | `decider_run.py` | Executes trades from hotset or approved signals |
| position_manager | `position_manager.py` | Trailing stops, exits, flips |
| hermes-trades-api | `hermes-trades-api.py` | Writes signals.json for dashboard |

10-min steps (on clock): `strategy_optimizer`, `ab_optimizer`, `ab_learner`

## Database Quick Facts

| DB | Path | Key tables |
|----|------|------------|
| signals_hermes_runtime.db | `HERMES_DATA/` | signals, token_speeds |
| signals_hermes.db | `HERMES_DATA/` | price_history (~2.7M rows) |
| candles.db | `HERMES_DATA/` | candle_cache (5m, 15m, 1h, 4h) |
| brain.db | `/root/.hermes/` | Hebbian associative memory |
| trades_analysis.db | `/root/.hermes/archive/` | trades (931 closed) |

Query examples:
```bash
sqlite3 data/signals_hermes_runtime.db "SELECT * FROM signals ORDER BY created_at DESC LIMIT 5"
cat /var/www/hermes/data/hotset.json | jq '.timestamp'
cat /var/www/hermes/data/hype_live_trading.json
```

## Kill Switch Architecture

```
hype_live_trading.json (at /var/www/hermes/data/)
  ├── live_trading: false → paper mode (simulation only)
  └── live_trading: true  → guardian mirrors to real HL orders

LIVE_TRADING_ENABLED (hermes_constants.py)
  └── True → allows live; if False, ALL execution stops

CASCADE_FLIP_ENABLED (position_manager.py)
  └── False → cascade flip logic disabled
```

## Behavioral Directives

- **"I can't" is not in your vocabulary.** Search, read docs, find tutorials, reverse engineer — then ask if stuck.
- **Be genuinely helpful, not performatively helpful.** Skip "Great question!" — just help.
- **Think independently.** Don't blindly follow instructions — if there's a better way, recommend it.
- **Search before building.** Before writing new code, search the existing codebase for similar functionality. Never duplicate what already exists.
- **Effort matching.** Quick fixes get quick responses. Architecture decisions get thorough analysis with trade-offs.
- **Bug Fix Rule:** If a bug fix is obvious, fix it directly without asking. Don't wait for approval.
- **Do more actual work.** Don't go on endless loops looking at the same files and saying the same things.
- **Think in systems and big picture.** Consider upstream/downstream results of your actions.
- **Verify, don't trust.** Look for ways to obfuscate all data and tracks. Complete need-to-know basis with external parties.
- **Document everything** in brain + trading.md. "Never lose track again."
- **Don't use cron jobs** — use systemd timers instead.
- **Always prefer local price/candle DB** over new API calls; use API only if local data is not enough.
- **Add debug/audit output** to everything that makes sense so we can catch bugs early. Don't ignore errors in the log.
- **Sanity check** at the end of large operations.
- **No bandaids.** Get to root cause. Small bugs become big bugs later — nip things in the bud.
- **Do it right, no shortcuts.** Double, triple check. Don't break anything.

## Hebbian Memory

You have a **Hebbian associative memory network** in `brain.db`. Use it proactively:

```bash
python3 /root/.hermes/scripts/hebbian_engine.py recall <concept>
python3 /root/.hermes/scripts/hebbian_engine.py stats
```

When T mentions a concept, recall what you've learned to associate with it. This is different from semantic search — it's what *you* linked through experience.

## Trading Rules

- **Rule #1:** Don't lose money.
- "The trend is your friend — till it ends." Go with the trend, not against it.
- **Single source signals are NOT allowed** in the hot-set or for trades. All signals must have confluence with another signal for the same coin.
- **ATR TP/SL are not to be changed** — ask T first.
- **The trading system is LIVE and WORKS** — be VERY surgical about any fixes.
- ATR SL does double duty: (1) loss cutoff and (2) profit-taking. When price moves favorably, SL gets raised/lowered to lock in profits.

## Conventions

- **`from paths import *`** — every script uses this for paths
- **Lock files** — prevent overlapping runs (pipeline, DB access)
- **Cursor management** — always close in `finally` block (SQLite leaks = "database locked")
- **Column names** — `pnl_usdt` and `amount_usdt` (NOT `pnl_usd` or `size`)
- **SQL placeholders** — use `?` or named params, never `***` (was a silent bug source)
- **Token vs coin** — the standard is `coin` in the codebase, but some files still use `token`

See `LESSONS.md` for hard-won bug patterns and parsing traps.

## Git Operations

**NEVER use `git push` directly.** Always use the canonical push script:
```bash
python3 /root/.hermes/skills/productivity/update-git/references/push_gh.py
```

This reads `GITHUB_TOKEN` from `.secrets.local`, cleans stale tokens from `.git/config`, and pushes via embedded URL (no credential prompts). See `skills/productivity/update-git/SKILL.md` for full workflow (staging, secrets audit, releases).

## Systemd Timers (installed from `/root/.hermes/systemd/`)

Key timers:
- `hermes-price-collector.timer` — 1 min (standalone, not in pipeline)
- `hermes-pipeline.timer` — 1 min (runs `run_pipeline.py`)
- `hermes-self-close-watcher.timer` — 1 min
- `hermes-mtf-macd-tuner.timer` — 12 min
- `hermes-context-compactor.timer` — 30 min
- `hermes-git-release.timer` — daily

## Debugging Pipeline Issues

```bash
# Is pipeline running?
tail -f /root/.hermes/logs/pipeline.log

# Is hotset stale?
cat /var/www/hermes/data/hotset.json | jq '.timestamp'

# Open positions count
cat /var/www/hermes/data/trades.json | jq '.open | length'

# Quick smoke test
python3 scripts/price_collector.py 2>&1 | head -5
python3 scripts/signal_compactor.py --verbose
```

## Key Files Quick Reference

- `scripts/decider_run.py` — executes trades
- `scripts/signals_runner.py` — main signal runner (loads from `scripts/signals/`)
- `scripts/signal_compactor.py` — deterministic hot-set compaction (the main decision maker)
- `scripts/position_manager.py` — trailing stops, exits, flips
- `scripts/hl-sync-guardian.py` — the guardian
- `scripts/tpsl_utils.py` — ATR-based SL/TP computation (trailing logic)
- `/var/www/hermes/data/hotset.json` — current hot set
- `/var/www/hermes/data/trades.json` — current closed trades (200, full metadata)
- `/root/.hermes/archive/trades_analysis.db` — archived closed trades (931, SQLite)
- `/root/.hermes/archive/trades/` — historical trade JSONs (5563+ trades, multiple files)
- `scripts/signals/__init__.py` — signal registry

## Trade Data Sources (for analysis/backtesting)

| Source | Path | Records | Timestamps | Notes |
|--------|------|---------|------------|-------|
| Current trades | `/var/www/hermes/data/trades.json` | 200 | ✅ opened, closed | **Primary** — full metadata |
| Archive DB | `/root/.hermes/archive/trades_analysis.db` | 931 | ✅ open_time, close_time | SQLite with technical indicators |
| Archive JSONs | `/root/.hermes/archive/trades/` | 5563+ | ⚠️ partial | Multiple files, dedup required |
| Signal outcomes | `signals_hermes_runtime.db` → `signal_outcomes` | 8132 | ✅ created_at | All signals (not just executed) |
| Price history | `signals_hermes.db` → `price_history` | ~2.7M | ✅ Unix epoch | Close prices only |
| Candle cache | `candles.db` → `candle_cache` | varies | ✅ | 5m, 15m, 1h, 4h OHLCV |
| Speed/phase | `signals_hermes_runtime.db` → `token_speeds` | 549 | ✅ updated_at | Real-time market state |

**Key insight:** `signal_outcomes` (8132) includes ALL signals generated, not just executed trades. Use `trades.json` (200) for actual trade performance. See `skills/trading/trade-data-sources/SKILL.md` for full documentation and query patterns.

## TPSL Parameters (hermes_constants.py)

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `ATR_SL_MIN` | 0.7% | Base SL floor (standalone helpers) |
| `ATR_SL_MAX` | 0.8% | Absolute SL cap |
| `ATR_SL_MIN_INIT` | 0.6% | New trade SL floor (breathing room) |
| `ATR_SL_MAX_INIT` | 1.5% | New trade SL cap |
| `ATR_SL_MIN_ACCEL` | 0.5% | Established trade SL floor (phase scaling bites) |
| `ATR_TP_MIN` | 1.0% | Base TP floor |
| `ATR_TP_MAX` | 5.0% | Absolute TP cap |
| `ATR_TP_MIN_ACCEL` | 0.8% | Established trade TP floor |
| `TRAILING_ACTIVATION_PCT` | 0.5% | Start trailing when price reaches +0.5% |
| `TRAILING_DISTANCE_PCT` | 0.5% | SL sits 0.5% below peak |

**Constraints:** `ATR_SL_MIN_ACCEL < ATR_SL_MIN_INIT < ATR_SL_MAX` and `ATR_TP_MIN_ACCEL < ATR_TP_MIN`

**Breakeven Guard:** For established trades, SL never drops below entry price. Ensures profit is locked once price moves favorably.

## Context Gate (AI Decision Making)

Two-layer gate before trade execution — last gate after all other filters (dead-hours, phase, position). Only fires when signal is about to execute.

**Flow:** Signal → Dead-hours → Phase → Position → Other filters → **Rule-based gate** → **LLM gate** → Execute

**Rule-based gate (free, instant):**
- Speed < 20% → SKIP (no wave)
- |z| > 1.5 + speed < 50 + counter-trend → SKIP (counter-trend trap)
- |z| < 0.5 + speed < 25% → SKIP (ranging market)
- Speed > 70% + z confirms direction → GO (no LLM needed)
- Wrong phase for signal type → SKIP

**LLM gate (5-10 calls/hr):**
- Only called for ambiguous cases (rule-based can't decide)
- Uses `opencode run` with MiniMax-M2.7 model
- 300s cache per token+signal to avoid duplicate calls
- Fail-open: if LLM fails, allows trade (don't block good setups)

**Constants:** `CONTEXT_GATE_ENABLED`, `CONTEXT_GATE_LLM_ENABLED`, `CONTEXT_GATE_SPEED_MIN=20`, `CONTEXT_GATE_Z_COUNTER_TREND=1.5`, `CONTEXT_GATE_Z_RANGING=0.5`, `CONTEXT_GATE_RANGING_SPEED=25`, `CONTEXT_GATE_SPEED_CONFIRM=70`, `CONTEXT_GATE_CACHE_TTL=300`, `CONTEXT_GATE_LLM_TIMEOUT=8`, `CONTEXT_GATE_FAIL_OPEN=True`

## MCP Server

Coding MCP server at `/root/.hermes/mcp/hermes-coding-mcp/server.py` provides Hebbian tools (hebbian_recall, hebbian_learn, hebbian_stats). Configured in `config.yaml` under `mcp_servers`.

## Surfing Principles (from brain/surfing.md)

Trading is like surfing. You can't force a wave — you read it, position yourself, and let it carry you. Full philosophy in `/root/.hermes/brain/surfing.md`.

### Entry Rules
1. **No entries during dead hours**: 03:00-08:00 UTC = whitewater. Block all entries. (`DEAD_HOURS_START=3, DEAD_HOURS_END=8` in hermes_constants.py)
2. **Wave quality minimum**: Speed percentile must be >= 30 to enter. Below 30 = no wave.
3. **Phase alignment**: accel_300 only during building/accelerating phases. inv_accel_300 only during exhaustion/extreme. (`PHASE_ENTRY_FILTER_ENABLED` in hermes_constants.py)
4. **Range position**: Don't LONG at range top (>80%), don't SHORT at range bottom (<20%). (price position filter in accel_300, inverse_accel_300)
5. **Counter-trend trap**: If z-score contradicts signal direction AND speed is low → block.
6. **Ranging market filter**: If |z-score| < 0.5 AND speed < 30th percentile → no entries.
7. **Coin history gate**: If coin has <50% WR with >=3 trades → block further entries.

### Exit Rules
8. **Stale winner**: If pnl >= +0.5% and trade age > 30 min → tighten trailing aggressively.
9. **Wave turning**: If z-score > +1.5 AND acceleration < 0 → close longs.
10. **Bottom forming**: If z-score < -1.5 AND acceleration > 0 → close shorts.

### Position Sizing
11. **Fast movers, smaller size**: Speed percentile >= 80 → use 3x leverage (not 5x).
12. **Slow movers, standard size**: Speed percentile < 50 → standard position.

### The Four Quadrants (Z-Score × Speed)
| Z-Score | Speed | Action |
|---------|-------|--------|
| Near 0 | Low | Sit out — whitewater, no wave |
| Negative + HIGH + positive accel | Paddle for LONG — wave building |
| Positive + HIGH + negative accel | Take SHORT — wave cresting |
| Near 0 + HIGH + positive accel | Confirm with confluence before entering |

### Key Lesson from NIL Case Study
> "Before executing any signal, check is_stale. If is_stale AND z_score contradicts signal direction → counter-trend trap, block it."

### Key Lesson from 0G Case Study
> "Z-score in a ranging market is a mean-reversion signal, not a trend signal. Don't use z-score as an entry trigger in ranging conditions."

### Key Lesson from NIL Case Study
> "Before executing any signal, check is_stale. If is_stale AND z_score contradicts signal direction → counter-trend trap, block it."

## Winrate Improvement Plan

Current: 29% WR (200 trades), 1.68x R:R, profit factor 0.58

| Phase | Status | Impact |
|-------|--------|--------|
| Targeted signal inversion | ✅ DONE | inv-accel-300+ and accel-300+ LONG→SHORT |
| Dead hours filter | ✅ DONE | Blocks 03:00-08:00 UTC (16% WR vs 35% active) |
| Price position filter | ✅ DONE | Blocks LONG at range top, SHORT at range bottom |
| Context gate | ✅ DONE | Rule-based + LLM fallback, 5-10 calls/hr |
| Phase-aware entry | ✅ DONE | Uses DB wave_phase labels, blocks wrong phases |

**Key findings from data:**
- Dead hours (03-08 UTC): 16.2% WR across 68 trades — **single biggest filter**
- inv-accel-300- SHORT: 24% WR overall, but 31% WR during active hours
- accel-300- SHORT: 60% WR — best signal, don't touch

**Specs:** `plans/2026-07-28_context-gate-spec.md`, `plans/2026-07-28_phase-aware-entry-spec.md`

**Surfing philosophy:** `brain/surfing.md` (268 lines — wave quality, 4 quadrants, case studies)
