# Verdict: BTC Pump Rider Gradual Rally Mode

**Date:** 2026-09-11
**Plan:** `plans/2026-09-11_btc-pump-rider-gradual-rally.md`
**Auditor:** Independent (fresh eyes, no prior context)
**Data Sources:** candles_1m (44,528 BTC candles, Aug 11 - Sep 11), 141 alt tokens

---

## Executive Summary

**NO-GO.** The plan's core thesis — that alts lag BTC by 5-10 minutes and can be bought before they move — is not supported by the data. By the time the gradual rally is detected (BTC +0.5% in 30 min), 137 out of 141 alts have already moved ≥0.3%. The only "lagging" tokens are low-quality or blacklisted. The detection logic fires 36x/day (not 2-3x), and the 5-10 minute lag claim is cherry-picked from one rally.

---

## 1. Lag Claim Assessment: CHERRY-PICKED / UNVERIFIED

**Plan claims:** "Alts lag BTC by 5-10 minutes."

**Actual data at the moment of detection (12:37 UTC, when BTC first hits +0.5% in 30 min):**

| Token | Price @ 12:00 | Price @ 12:37 | Move | Status |
|-------|--------------|--------------|------|--------|
| JUP | $0.2299 | $0.2430 | +5.70% | Already moved |
| NEAR | $2.4300 | $2.5660 | +5.60% | Already moved |
| ETHFI | $0.6144 | $0.6468 | +5.27% | Already moved |
| ENA | $0.1422 | $0.1478 | +3.94% | Already moved |
| DOGE | $0.0837 | $0.0844 | +0.83% | Already moved |
| **TRX** | $0.3359 | $0.3362 | **+0.09%** | **Lagging** |
| **0G** | $0.1939 | $0.1941 | **+0.10%** | **Lagging** |
| **SKY** | $0.0593 | $0.0594 | **+0.17%** | **Lagging** |
| **WLFI** | $0.0526 | $0.0527 | **+0.19%** | **Lagging** |

**Result: 137 tokens already moved (≥0.3%), only 4 tokens lagging.** And the 4 lagging tokens are:
- TRX: Low-beta, not a typical pump rider target
- 0G: Already blacklisted in SHORT_BLACKLIST
- SKY: Already in PENALTY_TOKENS (30.8% WR)
- WLFI: Already in PENALTY_TOKENS + LOSERS

**The "5-10 minute lag" is measured from the wrong starting point.** The plan uses 12:01 as the "first signal" but BTC was only +0.3% at that point. The real rally started at 12:29-12:30 (flash crash + recovery). By 12:37, alts had 7-8 minutes to react — and they did. The lag is 2-5 minutes, not 5-10.

**Verdict: The lag claim is cherry-picked from a single rally's early window. In practice, by the time the gradual rally is detectable, there are no tradeable lagging alts.**

---

## 2. Detection Logic Assessment: TOO LOOSE

**Plan claims:** "BTC rallies >0.5% in 30min happen ~2-3 times per day."

**Actual data (30 days of BTC 1m candles):**

| Metric | Value |
|--------|-------|
| Total signals fired | 1,073 |
| Signals per day | **35.8** (not 2-3) |
| Continued up (next 30 min) | 412 (38.4%) |
| Reversed (next 30 min) | 209 (19.5%) |
| Flat | 452 (42.1%) |

**The detection is 12-18x more frequent than claimed.** The plan's "2-3 per day" estimate is off by an order of magnitude. This means:
- Too many signals = noise, not alpha
- 19.5% reversal rate = ~1 in 5 signals would catch a reversal
- Even the "continued up" signals often reverse within the 30-min window (the plan measures the NEXT 30 min, but alt trades would be held longer)

**The 3+ up candles in 15 min filter is too loose.** In a trending market, you get 3+ up candles constantly. This doesn't distinguish between a genuine rally and normal bullish noise.

**Verdict: The detection fires far too often to be a useful signal. The threshold needs to be much stricter (e.g., 1.0% in 30 min, or 5+ consecutive up candles).**

---

## 3. Alt Selection Assessment: UNSOUND

**Plan assumes:** When BTC rallies, lagging alts will follow within 5-10 minutes.

**Reality:** By the time BTC shows +0.5% in 30 min, correlated alts have ALREADY moved 3-5%. The "lagging" filter (alt 30m change < 0.3%) catches:
- Low-beta tokens that WON'T follow BTC anyway (TRX)
- Blacklisted tokens (0G)
- Underperformers (SKY, WLFI)

**The correlation filter (beta > 0.5) makes this worse.** High-beta alts move FIRST and FASTEST. They'll already be above the 0.3% threshold by detection time. The only tokens that haven't moved are low-beta ones that won't follow the rally.

**This is a paradox:** You want high-beta alts (they follow BTC), but by the time you detect the rally, high-beta alts have already moved. Low-beta alts haven't moved, but they won't follow.

**Verdict: The alt selection logic selects for low-quality tokens that won't move. The high-quality targets have already moved by detection time.**

---

## 4. False Positive Risk: HIGH

**19.5% of signals reverse within 30 minutes.** But the real risk is worse:

- The plan fires signals on alts that haven't moved yet
- If BTC reverses, the "lagging" alts won't lose much (they haven't moved up)
- BUT: if BTC continues up and the alt doesn't follow (because it's low-beta), you're stuck in a position that never reaches profit
- The ATR SL (1.2%) will trigger on normal noise

**Additional false positive vectors:**
- Flash crash at 12:30 (BTC dropped -0.85% in one candle, volume 929x) — the gradual rally detection would have fired during the recovery, but the market was extremely volatile
- Multiple consecutive signals in the same rally — the plan doesn't mention deduplication
- No cooldown between gradual rally signals (the plan's code doesn't call `set_cooldown`)

**Verdict: HIGH false positive risk. The detection fires on noise, and the alt selection catches tokens that won't follow.**

---

## 5. Is the Existing Pump Rider Broken? NO

**The pump rider is designed for explosive breakouts, not gradual rallies.** This is working as designed:

| Condition | What it catches | What it misses |
|-----------|----------------|----------------|
| Vol ≥3x, vel ≥0.15%, 2 follow-through | Sharp, violent breakouts | Slow grinds, distributed rallies |
| 1h high break + close confirmation | Clean resistance breaks | Choppy, back-and-forth moves |

**The Sep 11 rally was actually TWO events:**
1. 12:29-12:30: Flash crash (volume 929x!) — not a pump, it was a liquidation cascade
2. 12:32-14:00: Recovery rally — gradual, with pullbacks at 12:50-13:07

**The pump rider correctly rejected both:**
- Event 1: BTC dropped, not a breakout
- Event 2: Volume was 1-5x (not consistently 3x), follow-through was spotty

**Verdict: The pump rider is not broken. It's designed for a different type of move. Gradual rallies may not be reliably tradeable with a simple signal.**

---

## 6. Simpler Alternatives

### Option A: Lower volume threshold from 3x to 1.5x

**Would it have worked on Sep 11?**
- Pump rider would have fired at 13:48-13:49 (5.0x volume, +0.489% velocity)
- But follow-through was still only 1/2 (would need to relax to 1/2)
- Alt returns from 13:49 to 14:20: ENA +3.19%, JUP +2.24%, BLUR +5.69%

**Verdict: Partially.** It would catch the second leg of the rally but miss the initial move. Still better than the gradual rally mode.

### Option B: Add a momentum confirmation to the existing pump rider

Instead of a new detection mode, add:
- BTC 15m velocity >0.5% (trending, not just spiking)
- BTC 30m RSI >55 (confirming bullish momentum)
- Keep the existing volume/velocity/follow-through filters

**Verdict: More promising.** Builds on existing logic, doesn't introduce a new paradigm.

### Option C: Do nothing

The pump rider caught 3/6 winners on Sep 11 (+$0.35). The gradual rally mode would add complexity for marginal benefit. The system is already profitable.

**Verdict: Simplest.** The problem is not that the pump rider misses gradual rallies — it's that gradual rallies are hard to trade profitably with a signal-based system.

---

## 7. Plan Timeline Errors

The plan contains several factual errors about the Sep 11 rally:

| Plan Claims | Actual Data | Error |
|-------------|-------------|-------|
| "12:01 — BTC broke 1h high, volume 0.2x" | 12:01 volume was 1.6x (not 0.2x) | Volume wrong by 8x |
| "12:29 — Volume spike 17.7x" | 12:29 volume was 166x, 12:30 was 929x | Wrong timestamp and magnitude |
| "12:32-14:02 — BTC rallied +4.1%" | Actual rally was +2.9% ($76,433 → $78,600) | Overstated by 41% |
| "Alts lag BTC by 5-10 minutes" | Alts lag by 2-5 minutes | Lag overstated by 2x |
| "Rally was GRADUAL" | Rally had a flash crash (-0.85% in 1 candle) then recovery | Mischaracterized |
| "2-3 times per day" | 36 times per day | Understated by 12-18x |

**These errors cascade:** If the rally is not gradual (it had a flash crash), the "gradual rally detection" premise is flawed. If the lag is 2-5 min (not 5-10), the alt selection window is much narrower. If it fires 36x/day (not 2-3), it's noise.

---

## 8. Overall Verdict: NO-GO

| Dimension | Rating | Reason |
|-----------|--------|--------|
| Lag Claim | Cherry-picked | 137/141 alts already moved at detection time |
| Detection Logic | Too loose | 36x/day, not 2-3x; 19.5% reversal rate |
| Alt Selection | Unsound | Paradox: high-beta alts already moved, low-beta won't follow |
| False Positive Risk | HIGH | Fires on noise, catches low-quality tokens |
| Simpler Alternatives | Yes | Lower vol threshold or add momentum confirmation |
| Plan Accuracy | Poor | Multiple factual errors in timeline and data |

**Recommendation: REVISE if the team wants to pursue this direction, but the core thesis needs fundamental rethinking.** The gradual rally mode as designed would:
1. Fire 36x/day (noise)
2. Find 0-4 tradeable lagging alts per signal (all low-quality)
3. Have a 19.5% reversal rate
4. Add ~58 lines of code + 8 constants for marginal benefit

**If the goal is to catch gradual rallies:** Consider a momentum-based approach instead:
- Wait for BTC to confirm the trend (e.g., 3 consecutive 5m green candles)
- Then buy alts that are lagging on the 5m timeframe (not 30m)
- Use a tighter time window (5 min, not 30 min) for alt lag detection

---

## Confidence Level: HIGH

I verified the claims against:
- 44,528 BTC 1m candles (30 days)
- 141 alt tokens' price data during the Sep 11 rally
- The existing pump rider code (390 lines)
- hermes_constants.py pump rider parameters

The data is unambiguous: by the time the gradual rally is detectable, there are no tradeable lagging alts. The plan's core assumption is invalid.
