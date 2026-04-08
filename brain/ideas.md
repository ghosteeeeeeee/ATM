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

