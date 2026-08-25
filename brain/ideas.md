# Ideas Backlog

## Status Legend
- `[ ]` = not started
- `[P]` = in progress
- `[!]` = blocked / needs T decision
- `[DONE]` = completed

---

## Trading System

### [P] Minimax post-prediction validator
**What:** After qwen predicts direction, ask Minimax "this model said [DIRECTION], should we trust it?" instead of asking Minimax directly for a direction.
**Why:** Minimax has safety filter blocking UP predictions. Framing as validation instead of prediction might bypass the filter.
**Status:** 2026-04-06 — tested direct prediction → safety filter blocks UP calls. Reframing approach untested.
**Next step:** Test two-step: (1) qwen gives direction, (2) Minimax validates/trust score. Could also ask "what could go wrong with this trade?" instead of direction.

### [ ] Bigger Ollama model for candle predictor
**What:** Test qwen2.5:7b or llama3.1:8b instead of qwen2.5:1.5b for direction prediction.
**Why:** 1.5B is too small for financial reasoning. 7B+ should handle numeric indicators and regime context better.
**Status:** Not started. Need GPU or enough RAM for 7B+ model.

### [ ] Forward-looking accuracy tracking
**What:** Instead of backtesting on historical predictions (97% DOWN), track live predictions vs actual next-candle outcomes.
**Why:** The current dataset is skewed to a bearish period. Live tracking gives real accuracy metrics.
**Status:** 15-min cron is running. Need to build resolution mechanism (compare predicted_direction vs actual close vs previous close).

### [ ] Inversion threshold auto-tuning
**What:** Dynamically adjust INVERSION_THRESHOLD based on live accuracy tracking.
**Why:** If qwen is only 40% accurate, inversion (flip) brings it to 60%. If it's 55%, no inversion needed.
**Status:** Not started. Needs live accuracy data first.

---

## Infrastructure

### [ ] OHLC data for candle pattern detection
**What:** Fetch proper OHLC candle data instead of close-only prices.
**Why:** Cannot detect hammer, engulfing, doji patterns without open/high/low. Current price_history only has close.
**Options:** Hyperliquid API has 1m/15m/1h/4h candles. Or CoinGecko. Or Binance klines.

### [ ] Streamlit live predictions page
**What:** Read predictions.db directly to show live current predictions, direction, confidence, interval, accuracy trending.
**Why:** Currently Streamlit only shows W&B backup files (historical). Live view doesn't exist.
**Status:** Accuracy section added to candle_predictor page but not showing. Needs restart.

---

## Research

### [ ] Why qwen has DOWN bias
**What:** Investigate whether qwen2.5:1.5b has a systematic bias toward DOWN answers in uncertain contexts.
**Why:** Pattern backtest showed both variants heavily predict DOWN (expected on 97% DOWN dataset). But also seen in live predictions.
**Finding so far:** Small models may default to "safe" answers in financial contexts. Inversion compensates.

---

_Last updated: 2026-04-06_

### 2026-04-08 07:46 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-04-09 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-04-10 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-04-11 02:45 UTC
**Per-token MACD params:** MTF-MACD backtest proves tokens prefer different signal periods:
- SOL: sig=15 optimal (91.2% WR vs 83.9% with sig=12)
- BTC: sig=12 optimal (70.0% WR vs 60.5% with sig=15, +9.5pp)
- ADA: sig=12 optimal (91.3% vs 78.3%, +13pp)
- APT: sig=12 optimal (77.8% vs 62.9%, +15pp)

**Next sprint:** Expand backtest to ETH, AVAX, LTC with full param variants. Implement per-token MACD routing in signal_gen.py. Goal: 80%+ WR across all traded tokens.

*Status: BACKLOG — needs MTF-MACD backtest expansion + ETH/AVAX/LTC analysis first*

### 2026-04-11 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-04-12 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-04-13 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-04-14 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-04-29 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-04-30 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-01 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-02 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-03 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-04 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-05 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-06 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-07 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-08 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-09 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-10 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-11 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-12 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-13 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-14 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-15 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-16 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-17 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-18 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-19 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-20 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-21 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-22 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-23 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-24 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-25 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-26 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-27 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-28 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-29 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-30 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-05-31 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-01 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-02 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-03 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-04 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-05 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-06 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-07 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-08 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-09 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-10 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-11 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-12 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-13 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-14 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-17 02:01 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-17 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-18 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-19 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-20 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-21 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-22 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-23 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-24 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-25 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-26 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-27 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-28 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-29 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-06-30 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-01 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-02 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-03 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-04 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-05 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-06 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-07 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-08 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-09 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-10 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-11 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-12 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-13 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-14 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-18 18:15 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-19 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-20 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-21 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-22 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-23 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-24 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-25 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-26 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-27 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-28 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-29 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-30 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-07-31 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-01 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-02 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-03 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-04 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-05 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-06 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-07 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-08 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-09 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-10 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-11 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-12 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-13 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-14 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-15 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-16 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-17 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-18 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-19 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-20 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-21 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-22 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-23 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-24 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None


### 2026-08-25 05:00 UTC
**Stale Tasks:** None
**Kanban Sync:** None

