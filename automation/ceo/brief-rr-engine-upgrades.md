# DECISION REQUESTED: RR Engine Smart Upgrades Plan

Review the plan at `plans/2026-10-13_rr-engine-smart-upgrades.md` and provide your assessment.

## Context

The RR engine has been through 4 rounds of bug fixes. It now correctly kills ~8% of real signals (down from 55%). But it has a **structural flaw**: it measures R:R at the worst possible moment — the bottom of dumps, the top of pumps.

**Example:** BTC dumped from 83,086 to 82,315, RSI 16.1, z-score -2.4. The engine says SHORT R:R=0.75 "poor." 20 SHORT signals across two batches — every single one crushed by grade C/D R:R. The engine penalizes entries for being extended, which is exactly when the trade has the most edge.

## The Plan (4 upgrades)

### Upgrade 1: Momentum-Aware R:R (CORE FIX)
When price is actively moving in the trade direction, project TP using recent velocity instead of nearest S/R. During a dump, TP = where the dump is heading, not where the nearest floor is.

### Upgrade 2: Timeframe-Aware SL/TP (user's favorite)
Accept timeframe hint from signal, scale SL/TP expectations. 1m scalps get tight targets, 4h swings get wide targets.

### Upgrade 3: Signal Quality Context
Signals that passed confluence + trend alignment get softer R:R requirements.

### Upgrade 4: Fibonacci Retracement Levels
Add Fibonacci levels (0.236, 0.382, 0.500, 0.618, 0.786) from most recent significant swing to S/R map. Reuse existing code from `hh_hl_signals.py`.

## What I Need From You

1. **Is this the right approach?** Or is there a simpler/better fix for signal starvation?
2. **Implementation order** — is momentum-aware first the right priority?
3. **Risks** — what could go wrong with momentum projection?
4. **Constants** — are the proposed values reasonable?
5. **Any upgrades you'd add or remove?**

## Key Files
- Plan: `plans/2026-10-13_rr-engine-smart-upgrades.md`
- Engine: `scripts/risk_reward_engine.py`
- Constants: `scripts/hermes_constants.py` (search RR_ENGINE_)
- Integration: `scripts/signal_compactor.py` (rr_mult in _score_signal)
- Existing Fibonacci: `scripts/hh_hl_signals.py` (lines 342-361)
