# CONSULT: Risk-Budget Discussion — Widen HML + CUT_LOSER_PNL?

## Context
You rejected wide SLs in your last decision because HML (CUT_LOSER_PNL/lev) caps the effective stop at -0.8% price at 5x. You said widening requires a **coupled CUT_LOSER_PNL + ATR_SL_MAX change with shadow trial**. T wants to have that discussion now.

**T's position:** "The shadow and trade data and the charts look like wider stops (HML etc.) could be beneficial in turning the tide towards profitability."

## The Data

### Shadow SL sweep (1000 signals, CEO-reproduced)
| SL Level | LONG WR | LONG Total PnL | SHORT WR | SHORT Total PnL |
|----------|---------|----------------|----------|-----------------|
| 0.5% (current effective) | 32.6% | +175% | 0.6% | -205% |
| 1.0% | 48.3% | +437% | 4.2% | -323% |
| 2.0% | 62.2% | +686% | 8.8% | -526% |
| **4.0%** | **68.6%** | **+889%** | 11.8% | -667% |

### With TP=1.0% modeled
| SL | LONG WR | LONG PnL |
|----|---------|----------|
| 1.0% | 60.6% | +77% |
| 2.0% | 75.7% | +209% |
| **4.0%** | **82.6%** | **+319%** |

### Current HML mechanics
- `CUT_LOSER_PNL = -4.00` (account PnL)
- `HARD_MAX_LOSS_PCT = CUT_LOSER_PNL / lev` = -0.8% price at 5x
- HML vol floor: `-0.5 × ATR` but capped at CUT_LOSER/lev
- Effect: at 5x, any trade hitting -0.8% price is killed. Sweep says 4% SL → +889%.

### Recent exit data (14d)
- hard_max_loss: 129T, -$14.82, 0% WR (by construction)
- profit-monster-trail: 172T, +$12.37
- Net: HML losses exceed ALL PM-trail winners

## Your Prior Decisions
1. CUT_LOSER_PNL was widened -3.00→-4.00 on Oct 15 (to give trail more room)
2. HML_VOL_ATR_MULT = 0.5 was added (HML = -0.5×ATR when ATR provides more room)
3. You rejected 4% SL because HML caps at -0.8% — said it needs coupled change

## Questions

1. **Should we widen CUT_LOSER_PNL?** If so, to what? The sweep suggests 4% SL needs CUT_LOSER at -8% account (at 5x) to not cap it. That's a 2x risk increase per trade.

2. **Coupled change**: raise CUT_LOSER_PNL -4%→-8% AND ATR_SL_MAX 2.5%→4% together? Or different values?

3. **Shadow first?** Your prior ruling said "shadow trial." How long? What sample size? What metrics?

4. **Position sizing interaction**: if we widen stops, should we also cut position size? Currently size-reduce is active at 0.5x. Wider stops + smaller size = same risk per trade?

5. **What's the risk budget?** At $11 position size, 5x leverage:
   - Current: max loss = $11 × 5 × 0.8% = $0.44 per trade
   - Proposed: max loss = $11 × 5 × 1.6% = $0.88 per trade (2x)
   - Is 2x risk per trade acceptable given the potential +889% swing?

6. **Evidence threshold**: what data would convince you the wider stops are justified? The shadow sweep says +889%. What sample size do you need to trust it?

Write your decision to automation/ceo/ceo_report.md with section "Risk-Budget Decision — 2026-10-21". Be direct. This is a live risk-budget decision T is asking for.
