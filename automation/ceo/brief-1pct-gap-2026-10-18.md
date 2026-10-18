# Brief: 1% Daily Growth Gap — Decision Needed Now

**From:** T
**Date:** 2026-10-18 15:35 UTC
**Urgency:** HIGH — T is watching the account bleed and wants a decision

## The Situation

T checked in on vacation mode progress. The system is at breakeven, not growing. T wants 1% daily portfolio growth.

**Current state (verified from PostgreSQL + HL):**
- HL account: $28.94
- 1% daily target: $0.29/day
- Current 24h: +$0.08 (15T, 6W/9L, 40% WR)
- 7d: -$3.65 (205T, 33.7% WR)
- Guardrail: reduced size to 30% (not paused) at 7d WR 33.7% < 35%

**The math:**
- 6 winners total: +$0.69 (best: ALT SHORT trail_sl +$0.47, +12.65%)
- 9 losers total: -$0.61 (worst: WLD -$0.15, ETC -$0.09, IO -$0.08)
- Net: +$0.08. Need $0.29. Gap: $0.21/day.

## The Tension

The MoE identified 3 fixes that target exactly this gap:
1. Hard_max_loss realign: +$0.23-0.47/day
2. Confidence clamp: +$0.20-0.40/day
3. Kill broken SHORT tail: +$0.13-0.17/day

But vacation mode rules say "shadow-first, no enforcement." These fixes need 1-2 weeks of shadow data before shipping. By then the market has moved.

T's frustration: "still getting creamed from the looks of it... we're shooting for a modest 1% portfolio growth every day."

## What T Wants Decided

1. **Ship the confidence clamp NOW?** It caps conf at 100 — doesn't change trade behavior, just stops the >100 garbage in the DB (119 rows in 30d, max 499.4). This is a data quality fix, not a trading logic change. Would immediately rebalance which trades execute.

2. **Ship hard_max_loss realign as shadow?** Logs corrected thresholds, doesn't change stops. Starts collecting data today instead of waiting.

3. **Relax vacation rules for specific fixes?** Ship with revert triggers instead of waiting for shadow data.

4. **Accept breakeven?** System stops bleeding but doesn't grow while shadow data accumulates.

## The Data

The ALT SHORT winner (+$0.47, trail_sl, +12.65%) proves the system CAN capture big moves. The problem is 9 small losers (-$0.61 total) negate it. The MoE fixes target exactly this: cut the losers, keep the winners.

At $28 portfolio, 1% daily = $0.29/day. The system is at +$0.08. The gap is $0.21/day. The MoE fixes target +$0.56-1.04/day combined — more than enough IF they work.

## What We Need

A decision: ship the fixes now with revert triggers, or accept breakeven while data accumulates. T is watching and wants growth, not another 2 weeks of shadow data.
