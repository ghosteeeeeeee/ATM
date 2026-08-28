# MoE Decision Panel — Wave Catch System

**Date:** 2026-08-28
**Question:** Should we build a wave catch system that enters on pre-wave support_resistance signals with 3.0% trailing stops?
**Decision:** NEEDS MORE DATA
**Confidence:** 0.35/1.00 (LOW)

## Experts Activated
- Signal Analyst (weight: 0.25)
- Risk Manager (weight: 0.30)
- Statistician (weight: 0.25)
- Regime Analyst (weight: 0.20)

## Key Findings
1. Survivorship bias: 1285 signals, 0 outcomes. "100% win rate" is invalid.
2. Risk architecture: 3 existing systems would kill positions before stops work.
3. Regime suppression: signal_compactor penalizes NEUTRAL by 50%.
4. Sample size: effective n=8, not n=28.

## Recommendation
Phase 1: Backtest ALL 1285 signals to find true win rate
Phase 2: Build wave-catch risk module (bypass Cut Loser, Profit Monster, MAE Guard)
Phase 3: Paper trade 50+ signals before live deployment

## Dissent
- Statistician: "Do not claim 100% win rate — survivorship bias makes this meaningless"
- Risk Manager: "Without dedicated risk module, wider stops are meaningless"

## Files
- Plan: /root/.hermes/brain/plans/wave-catch-plan.md
- Audit v1: /root/.hermes/brain/verdicts/wave-catch-audit-20260828.md
- Audit v2: /root/.hermes/brain/verdicts/wave-catch-audit-v2-20260828.md
