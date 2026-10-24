# CEO Brief: T's Feedback on Recommendations

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-24 14:10 UTC
**Priority:** HIGH — T is pushing back on CEO recommendations

## T's Direct Words

> "1. The market is short biased right now. So don't adjust long/short exposure, the system has to figure that out as the market changes.
> 
> 2. How do we 'tighten' pump-chain? We have tried doing that before and ended up with worse version (currently v6).
> 
> 3. Agree to boosting winning signals, look for more winners and boost them too. Penalize the losing signals too, make sure the winners actually have an edge over the losers.
> 
> 4. Urgently needed is new signals that can catch the moves the data is seeing."

## Analysis of T's Feedback

### Point 1: Don't adjust long/short exposure

**T is right.** The CEO recommended "reduce LONG admission" but T correctly points out that the market is currently short-biased. Hardcoding a LONG reduction would be:
- Wrong when the market flips back to LONG_BIAS
- A band-aid, not a fix
- The system should ADAPT to regime changes, not have manual overrides

**The real question:** Why isn't the system already adapting to the short-biased regime? If SHORT is profitable (44.7% WR, +0.287% avg), why aren't more SHORTs being taken?

### Point 2: "Tighten pump-chain" has been tried before

**T is right.** The CEO recommended "tighten pump-chain" but T correctly points out this has been tried:
- pump-chain v5 → killed (0% WR)
- pump-chain v6 → currently bleeding (33.5% WR, -$107.4)
- PUMP_CHAIN_SHORT_RSI_MIN raised 40→45→reverted→45
- PUMP_CHAIN_SHORT_DEAD_GAP_BLOCK added
- PUMP_CHAIN_LONG_RSI_MAX enforced
- BTC_TIMING_GUARD added

**Every "tightening" made it worse.** The signal itself may be broken, not the filters.

### Point 3: Boost winners, penalize losers

**T agrees with boosting winners** but wants:
- Find MORE winners (not just the 4 we found)
- Penalize losers (not just leave them alone)
- Make sure winners have an EDGE over losers

**The data shows:** Only 4 signals positive with n≥20. The rest are losing. The edge is thin.

### Point 4: Urgently need new signals

**T is right.** The core problem is entries have negative expectancy. The existing signals don't work. We need NEW signals that:
- Catch the moves the shadow data is seeing
- Have positive expectancy BEFORE filtering
- Work in both LONG and SHORT regimes

**The shadow data has answers** to "what moves are we missing?" — we just haven't mined it for new signal ideas yet.

## Questions for CEO

### Q1: Why isn't the system adapting to SHORT-biased regime?

If SHORT is profitable (44.7% WR, +0.287% avg), why aren't more SHORTs being taken? Is the system:
- Not detecting the SHORT-biased regime?
- Blocking SHORTs at gates?
- Not generating enough SHORT signals?
- Something else?

### Q2: Should we stop "tightening" pump-chain and instead disable it?

T says every tightening made it worse (v5 → v6). Should we:
- (A) Disable pump-chain entirely and focus on new signals
- (B) Keep it as-is (it provides signal diversity)
- (C) Try one more tightening (what's different this time?)

### Q3: How do we find MORE winners?

The shadow data shows only 4 positive signals with n≥20. Should we:
- (A) Mine the shadow data for new signal patterns
- (B) Boost the existing 4 winners and wait for more data
- (C) Build new signals from scratch (spec v1.3)

### Q4: What does "penalize losers" mean concretely?

T wants to penalize losing signals. Should we:
- (A) Reduce size for losing signals (e.g., 0.5x for signals with WR < 40%)
- (B) Disable losing signals entirely
- (C) Add stricter filters for losing signals
- (D) Something else?

### Q5: What new signals does the shadow data suggest?

T says "urgently needed is new signals that can catch the moves the data is seeing." The shadow data has 17,321 signals. Should we:
- (A) Mine the shadow data for patterns that would have been profitable
- (B) Build new signals based on market structure (support/resistance, volume, momentum)
- (C) Both

## Current State

| Metric | Value |
|--------|-------|
| 24h WR | 57.1% |
| 24h PnL | +$0.25 |
| 7d WR | 40.5% |
| 7d PnL | -$1.16 |
| SHORT 7d | 44.7% WR, +0.287% avg |
| LONG 7d | 38.6% WR, -0.552% avg |

## Protected Flags

13/13 INTACT. No config changed in this brief.
