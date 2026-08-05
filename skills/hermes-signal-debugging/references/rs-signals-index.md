# RS Signal Debug — Reference Index

This umbrella covers all RS signal debugging reference materials.

## Core Diagnosis
- `rs-param-diagnosis-2026-06-17.md` — Source-level verification of RS_PROXIMITY_K, RS_BOUNCE_THRESH_ATR, RS_TOUCH_HARD_CAP, inverted kill-switch constants, and the DISABLED-in-comment/True-in-code pattern.

## Closed Trades Analysis  
- `rs-closed-trades-deep-dive-2026-06-17.md` — Full analysis of 931 trades (757 with RS signals). Covers touch count buckets vs WR/PnL, signal combo quality, cap boundary analysis, live pipeline status.

## Quick Reference (from deep dive)
| Finding | Value |
|---------|-------|
| Best RS combo | RS+zscore (54.1% WR, +1.06% avg PnL) |
| Worst RS combo | RS+accel (30.9% WR, +0.24% avg PnL) — dominates dataset |
| Best SHORT bucket | 151-200 touches (66.7% WR, +2.01% avg PnL) |
| Worst SHORT bucket | 201-300 touches (17.4% WR, -0.22% avg PnL) |
| Worst LONG bucket | 121-150 touches (18.4% WR, -0.02% avg PnL) |
| Natural cap ceiling | 201-300 — both directions perform poorly here |
| Recommended cap | 200 — captures best SHORT bucket, still blocks exhausted zone |
| SHORT vs LONG | SHORT dominates: 44.9% WR vs 31.6% WR, +0.68% vs +0.32% avg PnL |
