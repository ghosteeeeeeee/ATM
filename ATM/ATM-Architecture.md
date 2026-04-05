```
MARKET DATA
    │
    ▼
price_collector.py          ──→ price_history (SQLite static + runtime)
    │                              ~1.7M rows
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │
    ▼
signal_gen.py               ──→ signals DB (PENDING / WAIT / APPROVED / EXECUTED)
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              SPEED FEATURE: token_speeds table (536 tokens)
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
decider-run.py              ──→ TWO PATHS:
    │                              1. _run_hot_set() → hotset.json
    │                                 Enforces: wave-phase, counter-trend trap, regime alignment,
    │                                 overextended filter, cooldown, 10-max-open-positions gate
    │                              2. get_approved_signals() → reads APPROVED from DB
    │                                 Enforces: counter-trend trap, regime alignment (fixed 2026-04-05)
    │                                 Both paths write to paper trades DB only.
    │
    ▼
hyperliquid_exchange.py     ──→ HL API (paper only — decider-run hardcodes paper=True)
    │                              mirror_open() for paper trades
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              THE KILL SWITCH: reads hype_live_trading.json
    │                              If live_trading=true: mirror_open() to real HL orders
    │                              Reconciles HL positions ↔ paper DB
    │                              Marks guardian_missing / hl_position_missing closes
position_manager.py          ──→ trailing stops, stale winner/loser exits, cascade flips
    │                              ro-trailing-stop.service (Dallas, Python only)
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              reconciles HL positions ↔ paper DB
    │                              marks guardian_missing / hl_position_missing closes
hermes-trades-api.py        ──→ writes signals.json for web dashboard
```

### Pipeline Schedule
| Step | Frequency | Script |
|------|-----------|--------|
| Price collection | Every 1 min | `price_collector.py` |
| Regime scan | Every 1 min | `4h_regime_scanner.py` |
| Signal generation | Every 1 min | `signal_gen.py` |
| Hot-set execution | Every 1 min | `decider-run.py` |
| Position management | Every 1 min | `position_manager.py` |
| Web dashboard | Every 1 min | `update-trades-json` |
| AI decision + compaction | Every 10 min | `ai_decider.py` |
| Strategy optimization | Every 10 min | `strategy_optimizer.py` |
| A/B optimization | Every 10 min | `ab_optimizer.py` |
| A/B learner | Every 10 min | `ab_learner.py` |

