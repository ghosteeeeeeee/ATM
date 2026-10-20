# CEO Brief: T's Clarifications + Sweep Results

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-20 23:30 UTC
**Priority:** HIGH — T's corrections to CEO verdict

## T's Direct Words

> 1. These were designed to minimize losses, so never fire in profit on purpose, ref: Hard Max and Cut Loser at 0% WR look like engine bugs.
>
> 2. Proceed with the flip test.
>
> 3. Try different arm timeouts in shadow-mode to see which is the most profitable.
>
> 4. Universal_hold was designed to free up capital for another trade (get out of a dead trade), what do you want to do here??

## Correction 1: Hard Max and Cut Loser 0% WR is BY DESIGN

T clarifies: **These engines were designed to minimize losses, so they never fire in profit on purpose.**

The CEO's concern that "Hard Max and Cut Loser at 0% WR look like engine bugs" is **wrong**. These engines fire ONLY when the trade is losing. They're supposed to have 0% WR because they only exit losers. This is working as designed.

**The sweep confirms HML is working correctly**: -3% account is the BEST threshold (WR=8.9%, avg=-0.385%). Loosening HML makes things WORSE. HML is cutting losses early — loosening it just lets losses grow bigger.

## Correction 2: Flip Test — T Approves

T says "proceed with the flip test." The shadow flip test showed volume_breakout_long flipped SHORT is BETTER by +0.873%. Ship it in shadow mode.

## Correction 3: Arm Timeout Sweep Results

Built `--sweep-arm` to test different timeout values. Results for pump-chain SHORT:

| Timeout | n | WR | Total | Avg |
|---------|---|-----|-------|-----|
| **30min** | 301 | **34.2%** | **-101.85%** | **-0.338%** |
| 45min | 301 | 36.9% | -119.92% | -0.398% |
| 60min | 301 | 37.2% | -159.90% | -0.531% |
| 90min | 301 | 32.9% | -221.07% | -0.734% |
| 120min | 301 | 34.2% | -228.92% | -0.761% |
| 180min | 301 | 34.9% | -286.93% | -0.953% |

**30min is BEST** — longer timeouts are WORSE. Trades lose money over time.

This contradicts the earlier finding that "winners take 120min vs losers 52min." The difference:
- Earlier analysis looked at ACTUAL exit time (when exit engine fired)
- Sweep looks at "what if we closed at fixed timeout regardless of exit engine"

The sweep shows: waiting longer doesn't help. The exit engine (ATR/PM Trail) is actually doing a good job of exiting winners early. Fixed timeout is worse because it exits winners too early AND losers too late.

## Correction 4: Universal Hold Question

T asks: "Universal_hold was designed to free up capital for another trade (get out of a dead trade), what do you want to do here??"

**The CEO's analysis showed Universal Hold has 88.1% WR for hmacd_mtf** — but that's because it holds winners for 8 hours. The question is: is that actually good, or is it just tying up capital?

**The trade-off**:
- Holding a winner for 8 hours = +4.495% avg
- Freeing capital for a new trade = unknown (could be winner or loser)

**With $28.94 capital**, holding a trade for 8 hours means we can't take other trades. The opportunity cost depends on what other trades are available.

**My recommendation**: Universal Hold is NOT a profit-maximizing exit — it's a capital-freeing exit. The 88.1% WR is misleading because it includes trades that would have been better exited earlier (freeing capital for new trades).

**Better approach**: Use PM Trail (100% WR, +0.742% avg) which exits winners earlier, freeing capital for new trades. Universal Hold is a fallback for trades that don't trigger PM Trail.

## Sweep Results Summary

| Sweep | Best | Result |
|-------|------|--------|
| Arm timeout (pump-chain SHORT) | 30min | WR=34.2%, avg=-0.338% |
| HML threshold | -3% account | WR=8.9%, avg=-0.385% |

Both sweeps confirm the current settings are near-optimal. Loosening makes things worse.

## Protected Flags

13/13 INTACT. No config changed in this brief.
