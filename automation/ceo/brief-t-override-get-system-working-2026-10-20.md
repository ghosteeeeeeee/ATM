# CEO Brief: T Overrides — "Get the system working"

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-20 14:20 UTC
**Priority:** CRITICAL — T is overruling the previous verdict

## T's Direct Words

> "So from the looks of it we're not going to be doing much trading, just waiting for things to get better somehow on their own. No trades means no new data (to change gate/filters, figure out what's the issue), means no system conditions changes, means we're dead in the water. Forget the confluence gate and ichimoku, get the system working."

## T's Core Argument (The Death Spiral)

T is pointing out a **logical trap** in the previous CEO verdict:

1. CEO said: "Fix bugs first, then measure WR for 24h, then decide"
2. T's response: **"No trades means no data means no improvement means dead in the water"**

The CEO's plan requires data to evaluate. But the system can't generate data because it can't generate trades. This is a **chicken-and-egg problem**:

- To loosen gates safely, we need data showing loosening is safe
- To get data, we need trades
- To get trades, we need to loosen gates

**The system is stuck in a loop.**

## Current State (Verified)

- **24h:** 16 trades, −$0.29, 18.8% WR
- **7d:** 170 trades, −$3.27, 34.1% WR
- **Open:** 2 trades
- **Guardrail:** 50% size (WR < 35%)
- **Hotset:** 84 non-empty writes today (NOT empty)
- **Compactor:** queries 3-5 combo_keys/cycle, writes 0-1 tokens to hotset
- **Decider:** 142 EXEC attempts today, 17 trades in PostgreSQL

## The Death Spiral Explained

```
No trades → No new data → Can't evaluate gate changes → Can't improve → No trades
```

The CEO's previous plan:
1. Fix ichimoku structural bug (123 signals/24h that can never pass)
2. Fix cross-layer vol-gate/RSI mismatch (~70 wasted executions/day)
3. Measure WR for 24h
4. If WR >45% → revisit gate loosening

**T's objection:** Steps 1-2 fix "wasted" signals, but those signals were never going to trade anyway. Fixing them doesn't increase trade volume. Step 3 requires trades to measure. We're stuck.

## What T Wants

**"Forget the confluence gate and ichimoku, get the system working."**

T is saying:
- Don't fix theoretical bugs that don't increase trade volume
- Actually loosen the gates that are blocking trades
- Let the system trade, collect real data, then decide

## The Real Question for CEO

**Is the CEO willing to let the system trade at a higher rate, even at 34% WR, to generate the data needed to improve?**

The previous verdict said: "Gates are protecting a losing system."

T's counter: "The system is already losing. Gates aren't protecting anything — they're just preventing us from learning why it's losing."

## Options (Revised per T's directive)

**Option 1: Emergency loosening (T's preference)**
- Revert SHORT_RSI_FLOOR 45→35 (revert Oct 18 change)
- Disable SHORT_MIDBAND_BLOCK (added Oct 16)
- Add pump-chain- SHORT back to EXTREME allowed list (revert Oct 16)
- Add 'ichimoku' to STANDALONE_BYPASS_SIGNALS (let it trade)
- Keep CONFLUENCE_GATE but relax for bullish regime
- **Result:** 3-5x more trades, collect data for 24h, then decide

**Option 2: Regime-conditional loosening**
- Loosen gates ONLY when BTC is bullish (above EMA300, momentum positive)
- Keep gates tight when BTC is bearish/neutral
- **Result:** Trade the bullish breakout, protect against bearish chop

**Option 3: Shadow mode for all loosened gates**
- Don't actually loosen — run all loosened gates in shadow mode
- Log what WOULD have traded vs what actually traded
- Collect counterfactual data for 24h
- **Result:** Data without risk, but doesn't address T's "no trades = no data" argument

**Option 4: CEO's previous plan (fix bugs first)**
- Fix ichimoku emitter
- Fix cross-layer mismatch
- Measure WR
- **Result:** T says this doesn't increase trade volume, so doesn't generate data

## My Recommendation

**Option 1 (emergency loosening) with Option 2 (regime-conditional) as a compromise.**

T is right: the death spiral is real. The system needs trades to generate data. The previous verdict's plan doesn't break the loop.

But the CEO's concern is valid: loosening at 34% WR could bleed faster.

**Compromise:** Loosen gates ONLY in bullish regime. BTC just broke out bullish. Let the system trade the breakout. If WR improves in bullish regime → keep loosened. If WR stays at 34% → re-tighten.

This addresses both concerns:
- T gets trades and data
- CEO gets regime-conditional protection

## Protected Flags

13/13 INTACT. No config changed in this brief.
