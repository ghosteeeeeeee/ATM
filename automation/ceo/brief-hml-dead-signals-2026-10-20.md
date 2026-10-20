# CEO Brief: HML Threshold + Dead Signals Analysis

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-20 21:50 UTC
**Priority:** HIGH — T directive: investigate HML thresholds and dead signals

## TLDR

T asked: "investigate hard_max_loss thresholds... some trades are just beyond redemption, we are on the wrong side or we bought a peak, so worth investigating is which signals are just dead wrong most of the time."

Built `--analyze-hml` into shadow_trader.py. Analysis of 4000 closed shadow outcomes shows:

1. **HML is NOT the problem** — 601 trades that didn't hit the -0.80% threshold still averaged -0.934%. The trades are fundamentally bad regardless of threshold.
2. **The real problem is entry quality** — specific signals buy peaks or are on the wrong side.

## HML Threshold Analysis

At -4% account (current, lev=5, -0.80% price):
- **995 HML exits**, avg_net = -0.937%
- **601 trades didn't hit the -0.80% threshold** but still averaged **-0.934%**
- These 601 trades were held and STILL lost money

**Conclusion**: Loosening HML won't help — the trades are fundamentally bad regardless of threshold.

## Dead Signals (bought peak / wrong side)

### Worst Signals (n>=10, WR<35%)

| Signal | Dir | n | WR | Avg | MFE | MAE | Problem |
|--------|-----|---|-----|-----|-----|-----|---------|
| volume-breakout-long+ | LONG | 34 | 11.8% | -0.575% | +0.19% | -3.89% | Barely moves up, crashes down |
| r2-trend-short3 | SHORT | 11 | 27.3% | -0.530% | +3.47% | -1.22% | High MFE but still loses |
| continuum-osc+ | LONG | 10 | 20.0% | -0.418% | +0.57% | -1.39% | Wrong side |
| pump-chain-v6+ | LONG | 208 | 28.4% | -0.214% | +3.57% | -5.29% | **Buys peaks, crashes down** |
| pump-chain+,pump-chain-v6+ | LONG | 164 | 29.9% | -0.204% | +2.99% | -4.69% | **Buys peaks, crashes down** |
| pump-chain+ | LONG | 287 | 28.2% | -0.181% | +2.88% | -4.70% | **Buys peaks, crashes down** |

### Peak Buyers (high MFE but negative outcome)

Signals that spike up then crash down — bought the peak:

| Signal | Dir | n | WR | Avg | MFE | Giveback | Problem |
|--------|-----|---|-----|-----|-----|----------|---------|
| hmacd_mtf-- | SHORT | 102 | 63.7% | -0.067% | +9.31% | +9.38% | **Gives back ALL gains** |
| volume-buildup- | SHORT | 285 | 65.6% | -0.068% | +4.74% | +4.81% | Gives back all gains |
| r2-trend-short3 | SHORT | 11 | 27.3% | -0.530% | +3.47% | +4.00% | Gives back all gains |
| ichimoku- | SHORT | 517 | 60.0% | -0.164% | +3.74% | +3.90% | Gives back all gains |
| pump-chain-v6+ | LONG | 208 | 28.4% | -0.214% | +3.57% | +3.79% | Gives back all gains |
| return_exhaustion-short | SHORT | 29 | 51.7% | -0.202% | +2.86% | +3.06% | Gives back all gains |
| doji-bottom-long | LONG | 69 | 55.1% | -0.184% | +2.42% | +2.60% | Gives back all gains |

### Wrong Side (high MAE, low MFE)

Signals that immediately go against us — wrong side of trade:

| Signal | Dir | n | WR | MFE | MAE | Ratio | Problem |
|--------|-----|---|-----|-----|-----|-------|---------|
| bb-bounce-v2-long+ | LONG | 104 | 48.1% | +0.92% | -2.23% | -0.41 | MAE 2x MFE |
| ichimoku+ | LONG | 171 | 50.3% | +0.94% | -4.06% | -0.23 | **MAE 4x MFE** |
| btc-pump-rider+ | LONG | 27 | 48.1% | +0.82% | -5.05% | -0.16 | **MAE 6x MFE** |
| volume-breakout-long+ | LONG | 34 | 11.8% | +0.19% | -3.89% | -0.05 | **MAE 20x MFE** |

## The Pattern

1. **pump-chain+ LONG signals buy peaks** — they spike up (+3% MFE) then crash down (-5% MAE). The entry is chasing the pump, not waiting for pullback. This is the #1 dead signal family (287+208+164 = 659 trades).

2. **hmacd_mtf-- SHORT signals** have huge MFE (+9.3%) but give it all back. The trail isn't catching gains — these are winning trades that become losers. Exit trailing issue, not entry issue.

3. **volume-breakout-long+** barely moves up (MFE=+0.19%) but crashes down (MAE=-3.9%). These are just bad entries — buying breakouts that immediately fail. Should be disabled.

4. **ichimoku+ LONG** has MAE 4x MFE — immediately goes against us. The signal is firing at the wrong time. Entry timing issue.

## CEO Decision Needed

### Q1: Should we disable volume-breakout-long+?
- 34 trades, 11.8% WR, -0.575% avg, MAE 20x MFE
- This signal is fundamentally broken — barely moves up, crashes down
- **Recommendation**: Disable

### Q2: Should we add a peak-buy filter to pump-chain+ LONG?
- 659 trades, ~28% WR, MFE +3%, MAE -5%
- The signal is chasing pumps — entry is at the peak
- **Recommendation**: Add a pullback filter (enter on dip, not at peak)

### Q3: Should we improve trailing for hmacd_mtf-- SHORT?
- 102 trades, 63.7% WR, MFE +9.3% but avg -0.067%
- These are winning trades that give back all gains
- **Recommendation**: Tighter trail or earlier partial profit-taking

### Q4: Should we investigate ichimoku+ LONG entry timing?
- 171 trades, 50.3% WR, MAE 4x MFE
- Signal is firing at the wrong time — immediately goes against us
- **Recommendation**: Investigate entry conditions

## What T Said

> "we can be tweaking things as the data comes in, and we can keep learning from it"

T wants iterative improvement based on shadow data. The shadow trader is now collecting ~1000 outcomes/day. We can test changes in shadow before deploying to live.

## Protected Flags

13/13 INTACT. No config changed in this brief.
