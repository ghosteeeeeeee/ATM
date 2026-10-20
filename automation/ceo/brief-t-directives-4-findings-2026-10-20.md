# CEO Brief: T's Directives on 4 Shadow Findings

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-20 22:10 UTC
**Priority:** HIGH — T's specific directives on each finding

## T's Direct Words

> 1. If winrate for volume-breakout-long is as bad as you say, flipping the signal should reverse the trade, and thus be profitable. Try that first in shadow-mode — the real trade and the flipped trade, let's see which one does better.
>
> 2. If hmacd_mtf is giving back as much as you say, then see what the outcomes are for the other exit engines. We're simulating all correct? So what happens on the rr-exit, pm_trail, atr_sl, pump-chain-exit — we should have all this data. If we don't, then build it in.
>
> 3. Pump-chain has some really spectacular trade signals, big gains, and that is overwritten by the high volume bad signals. We definitely have to filter it better. The arm was a step in the right direction — if price hasn't moved in X mins then we're out — but that keeps us from buying before a pump. Some of our highest gainers were held for multiple hours, up to 6-8 hours.
>
> 4. Ichimoku has historically been a loser. If we can make it a winner by following it in shadow mode, we can apply the template to more signals.

## Analysis of T's Directives

### Directive 1: Flip volume-breakout-long+ in shadow mode

**T's logic**: If WR is 14.3%, flipping should give 85.7% WR.

**What to build**: Shadow flip test — simulate both original (LONG) and flipped (SHORT) on the same signals. Compare outcomes.

**Implementation**: Add `--flip-test` mode to shadow_trader.py that:
- Takes all volume-breakout-long+ signals
- Simulates original direction (LONG)
- Simulates flipped direction (SHORT)
- Compares net PnL, WR, MFE, MAE

### Directive 2: Check hmacd_mtf exit engine outcomes

**T's question**: What would other exit engines have done for hmacd_mtf SHORT signals?

**What we have**: The shadow trader already simulates 7 exit engines on every signal. The `exit_*_json` columns store per-engine results.

**What to check**: For hmacd_mtf SHORT signals that were first-exited by ATR (the default), what would PM Trail, Hard Max, Cut Loser, etc. have done?

**Implementation**: Query `exit_pm_trail_json`, `exit_atr_json`, etc. for hmacd_mtf signals and compare.

### Directive 3: Better pump-chain filtering

**T's insight**: "Pump-chain has some really spectacular trade signals, big gains, and that is overwritten by the high volume bad signals."

**The arm timeout problem**: "If price hasn't moved in X mins then we're out — but that keeps us from buying before a pump. Some of our highest gainers were held for multiple hours, up to 6-8 hours."

**Analysis needed**: 
- What's the distribution of hold times for pump-chain winners vs losers?
- Do winners take longer to develop (6-8 hours) while losers die fast?
- If so, the arm timeout is killing winners before they develop

**Implementation**: Add pump-chain hold-time analysis to `--analyze-hml` or new `--analyze-pump` mode.

### Directive 4: Make ichimoku a winner

**T's goal**: "If we can make it a winner by following it in shadow mode, we can apply the template to more signals."

**Approach**: 
- Test different entry conditions for ichimoku (RSI filters, regime filters, confluence requirements)
- Test different exit engines for ichimoku
- Find the combination that makes ichimoku profitable
- Apply that template to other losing signals

**Implementation**: Add ichimoku-specific analysis to shadow trader — test parameter variations in shadow mode.

## CEO Decision Needed

1. **Should we build the flip test for volume-breakout-long+?** (T directive 1)
2. **Should we query existing exit engine data for hmacd_mtf?** (T directive 2 — data may already exist)
3. **Should we build pump-chain hold-time analysis?** (T directive 3)
4. **Should we build ichimoku parameter testing?** (T directive 4)

## What T Wants

T wants iterative improvement based on shadow data. Each finding leads to a specific test:
- Flip bad signals and see if reversed is profitable
- Check all exit engines, not just the first-to-fire
- Filter high-volume bad signals without killing high-gain signals
- Find the winning template and apply it to other signals

This is the "keep learning from it" approach T mentioned earlier.

## Protected Flags

13/13 INTACT. No config changed in this brief.
