# CONSULT RUN 20261019T192437Z (UTC)

You are running a BOUNDED, READ-ONLY consult. Base persona/rules follow after this block.

## HARD LIMITS (this run)
- **BUDGET: ~3 minutes. Do not exceed a few file/DB reads.**
- **READ-ONLY. Do NOT edit ANY file. Do NOT change params, flags, or blacklists.**
- Do NOT develop signals. Do NOT tune signals. Do NOT dispatch subagents.
- Do NOT write to ceo_report.md or ceo_kanban.md — answer HERE, in this session.
- No session lock is held. If you believe an edit is needed, say so as a recommendation and stop.

## THE QUESTION
Answer the directed brief below. Verify any numbers you cite with a quick query (base prompt SQL rules apply — never trust old reports). Give a clear VERDICT (approve/reject/modify + rationale). If the brief asks for a review, lead with the verdict, then the reasons.

--- BRIEF ---
# CEO Brief: No Trades → No Stats → WR Stuck at 35%

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-19 19:25 UTC
**Priority:** HIGH — T is frustrated, system is gridlocked

## TLDR

T's report: "If no trades are taken, no stats are generated, the needle does not move. Winrate is stuck at 35%. And ai-trader (not manual) is picking weird moves — enough for the auditor to demote its trades."

**The data confirms both complaints:**

1. **Signal-to-trade gap is catastrophic**: 862 signals detected in 24h, only **17 trades executed**. 98% of signals expire without execution.
2. **ai-trader (automated) is the #1 loser**: 20 trades, 30% WR, -$0.85 in 7d. ai-trader-manual (human-picked) has 45% WR — 50% better.
3. **Guardrail size reduce at 30% is creating a paradox**: Smaller positions mean smaller wins, which means the 7d WR can't climb above 35% fast enough to lift the guardrail. We're in a death spiral.

## The Numbers

### Trade frequency (last 24h)
- **862 signals detected** (SQLite, signals_hermes_runtime.db)
- **17 trades executed** (PostgreSQL)
- **Gap**: 98% of signals expire without execution
- **9-hour dead zone**: 10:34 to 19:16 — no trades at all

### ai-trader performance (7d)
| Variant | Trades | WR | PnL | Avg PnL |
|---------|--------|-----|-----|---------|
| ai-trader+ (automated LONG) | 20 | **30%** | **-$0.85** | -$0.043 |
| ai-trader- (automated SHORT) | 2 | 0% | -$0.12 | -$0.060 |
| ai-trader-pending | 2 | 0% | -$0.10 | -$0.050 |
| ai-trader-manual (human) | 11 | **45%** | -$0.12 | -$0.011 |

**Automated ai-trader total**: 24 trades, 25% WR, -$1.07
**Manual ai-trader**: 11 trades, 45% WR, -$0.12

**The automated picks are 1.8x worse than human picks on the same signal.**

### Guardrail state
- 7d WR: **33.8%** (below 35% threshold)
- 7d PnL: **-$4.13** (below -$2.00 threshold)
- Size reduce: **30% multiplier** active since 2026-10-17
- Impact: Every win is 70% smaller → WR recovery is mathematically slower

### The death spiral
1. Guardrail sees 7d WR 33.8% < 35% → activates 30% size reduce
2. Smaller positions → smaller absolute wins
3. Smaller wins → 7d WR stays stuck at 33.8% (needs 35% to lift)
4. WR can't climb because we're not generating enough trades to shift the stats
5. **Need ~50 more wins in 7d to move WR from 33.8% to 35%** — but at 17T/day and 30% WR, we only get ~5 wins/day

## Root Causes

### 1. Signal-to-trade execution gap (98% loss rate)
- 862 signals → 17 trades
- Signals are detected but blocked by: hotset scoring, decider confidence, execution filters, blacklist, regime gates
- **The pipeline is a funnel with a 2% pass rate**

### 2. ai-trader automated picks are low-quality
- Auditor verdict (2026-10-19): ai-trader+ TAT-eligibility **FAIL**
  - Median winner hold 42m > median loser hold 33m (inverted — no valid timeout exists)
  - Entry-side bleed: "death-zone advisory (holding) + EXTREME LONG conf-demote shadow (collecting, n=16)"
- ai-trader+ is taking trades that human traders would skip
- The automated entry logic is picking "weird moves" — exactly what T observed

### 3. Guardrail size reduce is counter-productive
- T already flagged this: "WR can't recover without trades"
- We reduced size to protect capital, but now we can't generate the stats needed to lift the guardrail
- **The cure is killing the patient**

## What T Wants

1. **More trades** — the needle needs to move, stats need to accumulate
2. **Better ai-trader picks** — the automated entries are worse than manual
3. **WR above 35%** — to lift the guardrail and resume normal sizing

## CEO Decision Needed

### Option A: Lift size reduce to 50% (or 100%) immediately
- **Pro**: More PnL per win → faster WR recovery → faster guardrail lift
- **Con**: More risk while 7d WR is below 35%
- **Risk**: If WR stays at 33%, losses grow faster

### Option B: Disable ai-trader automated entries (keep manual)
- **Pro**: Stops the bleeding from bad automated picks (-$1.07 in 7d)
- **Con**: Fewer trades overall → slower stat accumulation
- **Risk**: Manual entries might not scale

### Option C: Loosen execution filters to increase trade frequency
- **Pro**: More trades → more data → faster signal evaluation
- **Con**: More noise, potentially more losses
- **Risk**: Could activate bad signals alongside good ones

### Option D: Reset 7d WR window (start fresh)
- **Pro**: Removes the stale losses dragging WR down
- **Con**: Statistical manipulation, doesn't fix root cause
- **Risk**: Hides the problem instead of solving it

## My Recommendation

**Option A + Option B combined:**

1. **Lift size reduce to 50%** (not 100% — partial recovery)
   - Enough to move the needle on wins
   - Not so much that a bad day wipes us out
   - Re-evaluate in 48h

2. **Disable ai-trader+ automated entries** (keep ai-trader-manual)
   - The automated picks have 30% WR vs manual 45%
   - Auditor already flagged them as entry-side bleed
   - Manual picks are 1.8x better — trust the human

3. **Keep guardrail armed** but change threshold:
   - Pause at 7d WR < 30% (not 35%)
   - Size reduce to 50% at 7d WR < 35%
   - Normal size at 7d WR ≥ 35%

This lets the system breathe without removing all safety nets.

## Protected Flags

13/13 INTACT. No config changed in this brief.
--- END BRIEF ---

## OUTPUT
Print your answer to this session (stdout). Do NOT append to any report file. Max ~400 words unless the brief demands more detail.
