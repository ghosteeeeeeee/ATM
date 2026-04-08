```
MARKET DATA
    │
    ▼
price_collector.py          ──→ signals_hermes.db::price_history (SQLite)
    │                              ~2.7M rows
    │                              latest_prices table (current prices)
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
    │                                 Hot-set execution filters:
    │                                 Wave alignment: bottoming+LONG, falling+SHORT get +15% boost
    │                                 Counter-wave: 0.70–0.88× penalty
    │                                 Overextended: BLOCKED (except bottoming+LONG, falling+SHORT)
    │                                 Counter-trend trap: z-score vs direction → penalty
    │                                 Regime alignment: tier disagrees → -20 pts
    │                                 HARD BANS: conf-1s (single-source), speed=0% (stale token)
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                                 Enforces: counter-trend trap, regime alignment
    │                                 HARD BANS: conf-1s, speed=0%, loss/win cooldown
    │                              Dynamic paper/live: paper = not is_live_trading_enabled()
    │                              Both paths write to paper trades DB only.

    ▼
hyperliquid_exchange.py     ──→ HL API
    │                              mirror_open() for paper; mirrors to real HL when live
    │                              Kill switch: /var/www/hermes/data/hype_live_trading.json
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              If live_trading=true: mirror_open() to real HL orders
    │                              Reconciles HL positions ↔ paper DB
    │                              Marks guardian_missing / hl_position_missing closes
position_manager.py         ──→ trailing stops, stale winner/loser exits, cascade flips
    │                              BUG FIX (2026-04-05): close_paper_position() used stale
    │                              current_price for PnL calc — trailing_exit trigger price was
    │                              not used. Fixed: re-extract realized PnL% from reason string
    │                              (e.g. "trailing_exit_-0.55%") to correctly trigger cooldowns.
    │                              ro-trailing-stop.service (Dallas, Python only)
    │
    ▼
hermes-trades-api.py        ──→ writes signals.json for web dashboard
```

**Scripts location:** All pipeline scripts live in `/root/.hermes/scripts/`

### Data Stores
| File | Contents |
|------|----------|
| `signals_hermes.db` | price_history (~2.7M rows), latest_prices, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (544 tokens) |
| `state.db` | General state (messages, schema_version) |
| `predictions.db` | ML predictions |
| `/var/www/hermes/data/hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `/var/www/hermes/data/hotset.json` | Current hot set (top 20 signals) |

### Pipeline Schedule
| Step | Frequency | Script |
|------|-----------|--------|
| Price collection | Every 1 min | `price_collector.py` |
| Regime scan | Every 1 min | `4h_regime_scanner.py` |
| Signal generation | Every 1 min | `signal_gen.py` |
| Hot-set execution | Every 1 min | `decider_run.py` |
| Position management | Every 1 min | `position_manager.py` |
| Web dashboard | Every 1 min | `update-trades-json` |
| AI decision + compaction | Every 10 min | `ai_decider.py` |
| Strategy optimization | Every 10 min | `strategy_optimizer.py` |
| A/B optimization | Every 10 min | `ab_optimizer.py` |
| A/B learner | Every 10 min | `ab_learner.py` |

### Pipeline Kill Switch
`hype_live_trading.json` at `/var/www/hermes/data/` controls live vs paper:
- `live_trading: false` → all trades stay in paper DB
- `live_trading: true` → guardian mirrors approved trades to real HL orders

**Last updated:** 2026-04-08 — corrected script paths, DB locations, row counts, paper/live dynamic flag
