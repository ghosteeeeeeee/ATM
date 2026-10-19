# Verdict: ai-trader+ TAT-eligibility screen — FAIL (NOT eligible)

**Date:** 2026-10-19 16:45 UTC
**Agent:** brain_auditor #23
**Rule applied:** TAT-eligibility meta-rule (pre-registered 2026-10-17, exit-ladder grid verdict):
  eligible ⟺ median_winner_hold < T < median_loser_hold AND separation ≥ 2× AND candle-OOS bar passes.
**Subject:** signal-scoped trail-arm-timeout for `ai-trader+` (creative idea from 2026-10-18 run: "signal-scoped exit T=25-30 fast-bleed profile").

## Data (PostgreSQL, verified this run)

| Metric | 30d | 14d |
|--------|-----|-----|
| Trades | 29 | 29 |
| Median winner hold | **42m** | 42m |
| Median loser hold | **33m** | 33m |
| Median MFE winners | 1.215% | — |
| Median MFE losers | 0.153% | — |
| Losers dying <25m | 8/17 | — |
| Losers dying <30m | 11/17 | — |
| Winners closing <45m | 7/12 | — |

## Verdict mechanics

Meta-rule requires `median_winner_hold < T < median_loser_hold`.
Observed: `42m < T < 33m` — **mathematically impossible.** Winners hold LONGER than losers (inverted from the TAT-needed shape). No T exists where the cut fires after losers die but before winners exit.

Secondary confirmation: 7/12 winners close <45m — any fixed-time cut at T∈[25,45] false-kills ≥58% of winners. This is the same failure mode that killed universal MFE-CUT (40% fk) — even worse here.

MFE does separate (1.215 vs 0.153) but that lever is MFE-CUT, already candle-OOS FAILED 2026-10-17 on the universal grid and not resuscitable via TAT framing.

## Consequences

1. **2026-10-18 creative "ai-trader signal-scoped exit T=25-30" is FORMALLY DEAD.** Do not re-propose without new data that inverts the hold-median relationship.
2. Live bleed lever for ai-trader+ remains **entry-side**: death-zone advisory (holding) + EXTREME LONG conf-demote shadow (collecting, n=16, re-eval at n≥20).
3. No shadow ship, no config change. Zero behavior.

## Dual-condition TAT OOS (bb-bounce-v2-long+, run 04:39 today) — also FAIL

Prior creative (Oct 18): dual-condition (age≥55m ∧ peak-MFE<0.20 ∧ live-pnl<−0.20).
30d candle OOS (n=51 closed, 4 fires): net **−$0.06**, save +$0.11, cost −$0.17, fk 2/27 = 7.4%.
Bars: net>0 FAIL, n≥15 FAIL, fk≤20% PASS.
**Single live fires stay zero-behavior collecting; no flip path.** TAT shadow for bb-bounce continues as counterfactual instrumentation only (3 would-fires on 7d: ME, ETC, BABY).

## Protected flags

13/13 INTACT. No config changed.
