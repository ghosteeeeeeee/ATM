# Transcript Mining Report

**Source**: I Gave JEV Control of a Trading Bot.md  
**Date**: 2026-08-24  
**Author**: Unknown (YouTube)

## TL;DR

- **Jev** is a new AI model that makes binary/programmatic decisions at 500ms speed — not language-based like Claude/GPT. Feed it programmatic inputs, get yes/no outputs with confidence scores.
- The video shows a "Jev loop" system: strategy → Jev decision engine → Alpaca paper trading → dashboard. Trades every 3-5 seconds on BTC.
- **Key insight**: Jev works best when fed binary (yes/no, 1/0) inputs — "if this then that, is this a trade? Yes or no." Nuanced language slows it down.
- The system includes live dashboards showing every data point behind each decision + a confidence score on every trade.
- Strategy quality is everything — the harness is just the vehicle; the edge comes from the strategy you plug in.

## Ideas

### 1. Binary Decision Framework for Signal Gating
- **What**: Jev's model works on binary inputs — every decision is "yes/no" with a confidence score. This maps directly to our signal architecture: each filter is a binary gate (speed > threshold? yes/no, RSI in range? yes/no).
- **Why Hermes**: Our context gate already uses rule-based → LLM cascade. The binary framing suggests we could formalize our filters as a decision tree where each node is binary, and the confidence score is derived from how many gates passed + how strongly. This is essentially what signal_compactor does, but the binary framing might make it cleaner.
- **Where**: `scripts/signal_compactor.py` — `_score_signal()` already does this; could formalize the binary gate structure.
- **Effort**: trivial
- **Priority**: skip (we already do this)

### 2. Confidence Score on Every Trade
- **What**: Jev attaches a confidence percentage to every buy/sell decision. Never 100% yes/no — always a spectrum.
- **Why Hermes**: We already have `effective_confidence` in our hotset and `confidence` on signals. This is a validation of our existing approach. But the video shows visualizing ALL data points behind each decision — we don't have that granular "why this trade fired" view.
- **Where**: `web/signals.html` — add a decision breakdown tooltip showing which filters passed/failed.
- **Effort**: small
- **Priority**: worth it

### 3. High-Frequency Decision Loop (3-5 second cadence)
- **What**: The Jev loop makes decisions every 3-5 seconds on BTC. Each dot = a buy/sell. Very high frequency, small positions.
- **Why Hermes**: Our pipeline runs on a timer, not event-driven. We already track 1m/5m candles and have speed tracking. The concept of a continuous decision loop rather than periodic scans is architecturally interesting but we already achieve similar cadence via our signal runners. The gap is that Jev reacts in real-time between candles; we wait for candle close.
- **Where**: Architecture-level — would need event-driven pipeline instead of timer-driven.
- **Effort**: large
- **Priority**: future

### 4. Real-Time Decision Dashboard
- **What**: The video shows a dark-mode dashboard with every data point behind each decision + live trade feed + confidence scores. It's a visual "explainability" layer.
- **Why Hermes**: Our dashboards show results (trades, signals, pump flow) but not the decision process in real-time. A "why did this signal fire" view — showing each filter's pass/fail, the confidence breakdown, the contributing factors — would be valuable for debugging and trust.
- **Where**: New dashboard `web/decision_engine.html` + API script. Or extend `signals.html`.
- **Effort**: medium
- **Priority**: worth it

### 5. Strategy Is Everything — Harness Is Just the Vehicle
- **What**: The video explicitly says the generic strategy is "pulled out of thin air" and real strategies are "really hard to come by." The harness (Jev + Alpaca + dashboard) is just plumbing.
- **Why Hermes**: We've built an extensive pipeline, dashboards, filters, and risk management. The video's point validates our focus on signal quality over infrastructure. We already have 60+ signals and a sophisticated compactor — the bottleneck is signal edge, not execution.
- **Where**: N/A — philosophy validation.
- **Effort**: none
- **Priority**: skip

### 6. Paper Trading → Live Trading Flip
- **What**: The system starts in paper mode and converts to live with "a flip of a switch." Same code path, different execution.
- **Why Hermes**: We already have this exact pattern: `LIVE_TRADING_ENABLED` in constants + runtime kill switch in `hype_live_trading.json`. Both must be true for real money. This is a validation of our architecture.
- **Where**: N/A — already implemented.
- **Effort**: none
- **Priority**: skip

## Quick Wins (do today)

1. **Decision breakdown on signals.html** — add a hover/expand that shows which filters passed/failed for each signal. We have the data in signal metadata; just need to surface it.

## Worth Discussing

1. **Event-driven pipeline** — instead of waiting for timer ticks, react to candle close events immediately. Would reduce latency between signal detection and execution. This addresses the "signal staleness" problem noted in AGENTS.md.
2. **Confidence calibration** — Jev's confidence scores are only meaningful if calibrated. Are our `effective_confidence` numbers actually predictive? Worth a calibration study: bucket signals by confidence and measure actual WR per bucket.

## Skip

- **Binary decision framework** — we already do this in signal_compactor.
- **Paper→live flip** — already implemented.
- **Jev integration** — we're not adding a third-party AI model to our execution path. Our signal_compactor is deterministic and LLM-free by design. The context gate LLM is the only AI decision point, and it's behind multiple safety filters.
