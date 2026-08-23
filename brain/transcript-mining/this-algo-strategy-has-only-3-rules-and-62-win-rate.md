# Transcript Mining Report

**Source**: This Algo Strategy Has Only 3 Rules and 62% Win Rate.md  
**Date**: 2026-08-24  
**Author**: David from CriticalTrading.com  
**Book Reference**: *Short-Term Strategies That Work* by Larry Connors

## TL;DR

- **7-day high/low breakout signal** — dead-simple mean-reversion entry/exit that produces 62% WR on daily timeframe. Could be a new standalone Hermes signal.
- **ATR(20) × 2 stop loss** — volatility-adjusted stops. We already do this (`ATR_SL_MIN/MAX`), but the 2× ATR(20) is a cleaner, simpler formulation worth benchmarking against our current 1.2-3.0% range.
- **Low exposure = high risk-adjusted return** — 20% time-in-market → 7.5% absolute = 37% adjusted. This philosophy maps directly to our hotset confidence scoring.
- **Performance boost via market selection, not rule complexity** — exactly our philosophy. Instead of adding more indicators, swap ETFs → futures (or in our case: improve token selection and position sizing).
- **Diversification across uncorrelated markets** — SPY/TLT/GLD/VNQ. Hermes is crypto-only; could add BTC/ETH/SOL sector rotation.

## Ideas

### 1. 7-Day High/Low Breakout Signal
- **What**: Buy when daily close < prev 7-day low AND price > 200 MA. Sell when close > prev 7-day high. Simple, systematic, 62% WR.
- **Why Hermes**: We don't have a clean mean-reversion breakout signal like this. Our closest is `range_breakout.py` but it works on shorter timeframes. This targets daily-level structure — a missing layer in our signal stack.
- **Where**: New file `scripts/signals/seven_day_breakout.py` (or `connors_breakout.py`)
- **Effort**: small
- **Priority**: worth it

### 2. ATR(20) × 2 as Universal Stop Baseline
- **What**: Stop loss = 2 × ATR(20). Simple, volatility-adaptive, proven across 360 trades.
- **Why Hermes**: Our current ATR-based SL uses `ATR_SL_MIN=1.2%`, `ATR_SL_MAX=3.0%`, with phase-based k multipliers. The video's approach is simpler — just 2× ATR(20) with no floor/cap complexity. Worth benchmarking: is our complex phase system actually better than simple 2× ATR?
- **Where**: `scripts/tpsl_utils.py` — add a benchmark comparison
- **Effort**: trivial
- **Priority**: quick win

### 3. Exposure-Adjusted Return Metric
- **What**: Track % time in market. 20% exposure × 7.5% return = 37% risk-adjusted return.
- **Why Hermes**: We track win rate and total PnL but don't measure exposure. A token that trades 3x/day with 60% WR might be worse than one that trades 1x/day with 70% WR. Exposure-adjusted return gives us a better ranking metric for token performance.
- **Where**: `scripts/token_performance_monitor.py` — add `exposure_pct` and `adj_return` columns
- **Effort**: small
- **Priority**: worth it

### 4. Market-Diversified Multi-Asset Scoring
- **What**: Test across uncorrelated assets (equities, bonds, gold, real estate) → diversification reduces drawdown.
- **Why Hermes**: We're 100% crypto. Our "diversification" is token-level, not sector-level. Could add sector rotation logic — e.g., if BTC regime = risk-on, weight memecoin signals higher; if risk-off, weight stablecoins. Not multi-asset, but sector-level diversification within crypto.
- **Where**: `scripts/4h_regime_scanner.py` — add sector-level exposure tracking
- **Effort**: medium
- **Priority**: future

### 5. Supplementary Strategy Philosophy
- **What**: Don't use this strategy standalone. Combine with others to boost returns. The 20% exposure means 80% of the time, capital is free for other strategies.
- **Why Hermes**: Our context gate already does this — it's selective about when to fire. The philosophy validates our approach: high-confidence signals only, let capital sit when nothing is clear. Could formalize "exposure budget" — if current positions > threshold, require higher signal confidence for new entries.
- **Where**: `scripts/signal_compactor.py` — add exposure budget to `_score_signal()`
- **Effort**: small
- **Priority**: worth it

### 6. Futures Position Sizing (5% Risk Model)
- **What**: Risk 5% of equity per trade. Position size = risk_amount / (2 × ATR(20)). Adapts to both volatility AND account growth.
- **Why Hermes**: Our current sizing is `DEFAULT_TRADE_SIZE_USDT = 11.0` with 7% of balance scaling. The video's approach is more sophisticated — it scales position size inversely with stop distance. Tight stop = more contracts, wide stop = fewer. This is mathematically cleaner than fixed-dollar sizing.
- **Where**: `scripts/decider_run.py` — `_get_trade_size_usdt()` could use risk-based sizing
- **Effort**: medium
- **Priority**: worth it

### 7. Monte Carlo Validation Requirement
- **What**: Strategy must pass Monte Carlo analysis before live deployment.
- **Why Hermes**: We have `signal_quality.py` and backtest analysis, but no formal Monte Carlo simulation. Adding this as a gate before a signal goes live would catch curve-fitted strategies.
- **Where**: New script `scripts/monte_carlo_validator.py`, integrate with `signal_quality.py`
- **Effort**: medium
- **Priority**: future

## Quick Wins (do today)

1. **Benchmark 2× ATR(20) stop** — compare against our current ATR_SL range on recent trades. If 2× ATR(20) outperforms, simplify.
2. **Add exposure tracking** — simple counter: time_in_position / total_time per token. Log it alongside WR and PnL.

## Worth Discussing

1. **7-day breakout signal** — could be a solid new signal in `scripts/signals/`. Mean-reversion on daily timeframe is missing from our 1m/5m/15m stack. Risk: it's designed for daily bars; we'd need to adapt to our candle timeframes.
2. **Risk-based position sizing** — the 5% risk model is mathematically sound. Current fixed-dollar sizing leaves edge on the table.
3. **Exposure budget** — formalize the idea that we shouldn't have 10 positions open on low-confidence signals. Correlates with our `MAX_OPEN_POSITIONS = 5` but makes it dynamic.

## Skip

- **Multi-asset diversification** (SPY/TLT/GLD/VNQ) — we're crypto-only, not relevant.
- **Commission inclusion in backtest** — we already account for fees.
- **Monte Carlo** — nice to have but not urgent. Our signal quality gate is sufficient for now.
