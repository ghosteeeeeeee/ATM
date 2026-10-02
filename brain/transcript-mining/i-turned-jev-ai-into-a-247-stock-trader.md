# Transcript Mining Report

**Source**: I Turned JEV AI Into A 24/7 Stock Trader (Full Tutorial).md  
**Date**: 2026-08-24  
**Author**: Unknown (YouTube)

## TL;DR

- Three AI trading bots built with Claude Code + Jev: Opening Range Breakout (ORB), insider news follower, and futures reversal (LVL). All returned profitability.
- **Jev-assisted ORB outperformed baseline**: ~4x fewer trades, lower drawdown, higher profitability. The AI decision layer adds value on top of a simple strategy.
- **Three-tier architecture**: strategy rules check market data first → Jev gets a structured snapshot + fixed choices (long/short/wait) → engine validates position size, stops, risk before order submission. Jev never has unlimited control.
- **VPS deployment** is critical — bots must run 24/7 on cloud infrastructure (Oracle Cloud free tier used). Security: trading-only API keys, no withdraw/deposit permissions.
- **Fees compound against HFT** — without discretion/filtering, AI bots get eaten alive by commissions before the edge materializes.

## Ideas

### 1. Three-Tier Decision Architecture (Strategy → AI → Risk Engine)
- **What**: Strategy rules check market data first. If a valid setup exists, a structured snapshot goes to the AI decision layer (Jev) with fixed choices (long/short/wait). The AI returns a decision, but the risk engine validates position size, stops, allowed directions, and risk profile before order submission.
- **Why Hermes**: This is almost exactly our architecture: signal_compactor (strategy) → context gate (AI LLM) → decider_run (risk engine). Validates our design. The one difference: Jev gets "fixed choices" rather than free-form output. Our context gate could be more explicitly constrained to binary/ternary choices.
- **Where**: `scripts/signal_compactor.py` → context gate → `scripts/decider_run.py`. Already implemented.
- **Effort**: none
- **Priority**: skip (validates existing architecture)

### 2. AI Decision Layer Reduces Trades, Increases Quality
- **What**: Jev-assisted ORB took ~4x fewer trades than baseline, had lower drawdown, and higher profitability. The AI filtered out low-quality setups that the raw strategy would have taken.
- **Why Hermes**: This is a direct validation of our context gate. We've seen similar results — the LLM context gate blocks low-quality signals. The magnitude (4x reduction) is interesting though — we might be too permissive.
- **Where**: Context gate already does this. Could analyze: what % of signals does our context gate block? Is 4x reduction the right target?
- **Effort**: analysis
- **Priority**: worth it (calibration study)

### 3. Decision Stream Logging
- **What**: Every trade decision is logged with reasoning — confidence score, fake-out risk, and the full decision stream. Allows post-hoc review and recalibration.
- **Why Hermes**: We log `_signal_metadata` in PostgreSQL but don't have a user-facing decision stream. The video shows a log where you can see "approving long decision, balancing between entering long and waiting." This level of transparency is valuable for debugging.
- **Where**: Extend `web/signals.html` or new `web/decision_stream.html`. Data already exists in PostgreSQL `_signal_metadata`.
- **Effort**: medium
- **Priority**: worth it

### 4. VPS + Security Hardening
- **What**: Bots run on VPS (Oracle Cloud free tier). API keys restricted to trading-only — no withdraw, no deposit, no transfer. Keys only work from the VPS IP.
- **Why Hermes**: We already run on a server with systemd timers. Our kill switch (`hype_live_trading.json`) + `LIVE_TRADING_ENABLED` dual-gate is our security model. The video's point about trading-only API permissions is valid — worth verifying our Hyperliquid API key permissions.
- **Where**: `.secrets.local` — verify HL API key has trading-only permissions.
- **Effort**: trivial
- **Priority**: quick win

### 5. Fee Awareness / Trade Filtering
- **What**: High-frequency AI decisions → fees compound. Without discretion, bots get eaten by commissions before the edge materializes.
- **Why Hermes**: We have signal quality gates and confidence thresholds. Our trade frequency is moderate (not HFT). But the principle applies: every signal that fires costs fees. Our `SIGNAL_QUALITY_ENABLED` + confidence gates are the right defense.
- **Where**: Already implemented.
- **Effort**: none
- **Priority**: skip (already handled)

### 6. Session-Based Trading (Asia Session Discovery)
- **What**: The LVL futures bot discovered that Asia session (overnight) was most profitable. The AI found the edge without being told to look at sessions.
- **Why Hermes**: We don't have session-based filtering. Crypto trades 24/7 so "sessions" are different — but there may be time-of-day patterns in our data. Worth analyzing: do certain hours consistently outperform?
- **Where**: PostgreSQL query — group trades by hour-of-day, measure WR and PnL.
- **Effort**: small
- **Priority**: worth it (analysis)

### 7. Cross-Market Confirmation
- **What**: The LVL bot uses other indices as confirmation — if trading ES and NQ swept previous highs, that feeds into the decision confidence.
- **Why Hermes**: Our MTF (multi-timeframe) signals do this internally. But cross-asset confirmation (e.g., BTC signal confirmed by ETH behavior) is not explicit. Could add a "market breadth" component to signal scoring.
- **Where**: `scripts/signal_compactor.py` — `_score_signal()` could add a market-breadth factor.
- **Effort**: medium
- **Priority**: future

## Quick Wins (do today)

1. **Verify HL API key permissions** — confirm it's trading-only, no withdraw/deposit. If it has broader permissions, rotate to a restricted key.
2. **Session analysis** — query PostgreSQL for time-of-day performance patterns. If a session consistently outperforms, add it as a filter/signal component.

## Worth Discussing

1. **Context gate calibration** — the video shows 4x trade reduction with AI filtering. What's our current block rate? Are we too permissive or too restrictive? Worth a data pull.
2. **Decision stream dashboard** — surface the "why" behind each trade in real-time. Data exists in `_signal_metadata`; just needs visualization.

## Skip

- **Three-tier architecture** — we already have this exact pattern.
- **Fee awareness** — our signal quality gates handle this.
- **Jev/Typesafe integration** — we're not adding a third-party AI model to our stack.
