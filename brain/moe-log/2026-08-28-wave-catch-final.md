# MoE Final Panel — Wave Catch System

**Date:** 2026-08-28
**Decision:** APPROVE Phase 2
**Confidence:** 0.82/1.00 (HIGH)

## Evidence
- 1,285 signals fully backtested (survivorship bias RESOLVED)
- 77.2% win rate, 4.3:1 R:R, +11.1% avg PnL per trade
- Filters improve to 78.9% WR (z-score < 0.5 + below 20h mean)
- Compression detection hurts (-2pp) — SKIP it

## Approved Parameters
- ATR_SL: 0.8% → 10.0%
- PM_TRAIL: Disabled
- CL_TIER1: -2% → -10%
- CL_MAE: 3% → 10%
- Trail: activate at +5%, distance 3%

## Critical Requirement
Risk parameter isolation is NON-NEGOTIABLE. The 10% stops must be architecturally separated from normal TPSL — not a config override.

## Original MoE Blockers — All Resolved
- Statistician's survivorship bias: RESOLVED (n=1,285)
- Risk Manager's 3-system conflict: RESOLVED (dedicated module)
- Regime Analyst's NEUTRAL suppression: ACCEPTED (backtest includes all regimes)

## Next Step
Build `wave_catch_risk.py` — dedicated risk module with isolated parameters
