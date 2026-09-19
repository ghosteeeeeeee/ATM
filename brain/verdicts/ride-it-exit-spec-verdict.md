# Ride-It Exit Spec — Independent Auditor Verdict

**Auditor:** Independent (fresh read, no prior context)
**Date:** 2026-09-19
**Files Read:** ride-it-exit-spec.md, hermes_constants.py (lines 626-675, 1395-1450, 1479-1520, 3441-3445), position_manager.py (lines 1720-1800, 2557-2696, 3008-3015), cut_loser.py (full)
**Data Source:** PostgreSQL (brain), SQLite candles DB — queried directly, not from memory

---

## Claim 1: The Ride-It system would have caught the BABY +19% spike

### Verdict: PARTIAL (with caveats)

### Evidence:

**BABY trade #15465 (volume-breakout-long+):**
- Entry: Sept 17, 16:13 at $0.010736
- Exit: Sept 17, 18:09 at $0.010740 (breakeven, ATR SL hit)
- Highest price during trade: $0.010873 (peak +1.28%)
- Lowest price during trade: $0.010730 (drawdown -0.06%)

**The spike happened AFTER the trade was closed:**
- Sept 18, 00:00: Volume explodes to 58.8M (6.7x 20-bar avg of 3.87M)
- Sept 18, 00:35: Peak at $0.012810 (+19.32% from entry)
- The spike was 8 hours after entry, 6 hours after the trade was stopped out

**Ride-It would have survived the dip:**
- 2.5x ATR SL: $0.010499 (calculated from actual ATR of $0.0000945)
- Lowest price before spike: $0.010730
- **Gap: $0.000231 (2.15% margin)** — trade easily survives

**BUT: Would Ride-It have kept the trade open for 8 hours?**
- Gear 1 (0-2h): SL at 2.5x ATR = $0.010499. Survives.
- Gear 2 (2-6h): SL tightens to 2.0x ATR. Still below lowest price. Survives.
- Gear 3 (6h+): Tight trail at 0.8% from highest. At this point highest = $0.010873, trail = $0.010786. Lowest price $0.010730 would NOT trigger this trail (it's below, not above). Survives.
- **Volume spike override at 00:15**: Volume was 58.8M (6.7x avg). This WOULD trigger the 5x threshold. Switches to 0.5% tight trail.

**The spec's timeline has errors:**
- Spec claims ATR at entry = 1.01%. Actual: **0.88%** (12% error)
- Spec claims SL at $0.010464. Actual: **$0.010499** (0.3% error)
- Spec claims spike volume was 42M. Actual: **58.8M** on first candle (40% higher)
- Spec claims spike at "00:00". Actual: spike started at 00:00, peak at 00:35

**The partial exit problem:**
- If Ride-It took 25% at +5%, 25% at +10%, 20% at +15%:
  - Gain with partials: ~12.55% (blended)
  - Gain without partials: ~15.7% (after trail catches reversal)
  - **Partial exits cost 35% of the profit on this trade**

**Confidence: HIGH**

**Notes:** The system WOULD have caught the spike IF:
1. The trade stayed open for 8+ hours (no dead money exit killed it)
2. The volume spike override triggered correctly
3. The tight 0.5% trail caught the peak before reversal

The spec's claim is directionally correct but overstated. The system would have caught a large portion of the move, but partial exits would have significantly reduced the gain.

---

## Claim 2: 2.5x ATR SL is the right balance between survival and risk

### Verdict: DISAGREE (too wide for most trades)

### Evidence:

**Volume-breakout-long+ ATR SL hits (12 trades):**
- Only 4 out of 12 had losses < 2.5%
- Average loss: 4.77% (much worse than the 1.3% SL distance)
- This suggests the ATR SL is not the primary loss mechanism — slippage or other exits are causing larger losses

**mover+ ATR SL hits (5 trades):**
- BABY: -4.05% loss (entered AFTER the spike, at $0.011611)
- BLUR: -3.96% loss
- PONS: +0.31% (data artifact — highest_price = $1.0 from $0.654 entry)
- ATOM: +7.19% win
- PONS: +0.80% win

**The problem with 2.5x ATR:**
- BABY's actual ATR was 0.88%, so 2.5x = 2.21%
- But the spec claims 2.5x ATR = 2.53% (based on wrong ATR of 1.01%)
- At 2.21% SL, you're risking $0.24 per $11 trade on a single position
- The current 1.3% SL risks $0.14 per $11 trade
- **2.5x ATR increases risk per trade by 70%**

**What the data shows:**
- Most trades that hit ATR SL do so because they were bad entries, not because the SL was too tight
- The BABY trade survived at 1.3% SL — it was stopped at breakeven, not at a loss
- Wider SL means you hold losers longer, which hurts win rate

**Confidence: HIGH**

**Notes:** The 2.5x ATR multiplier is designed to survive the BABY scenario, but BABY's drawdown was only -0.06%. The current 1.3% SL would have survived too. The real issue isn't SL width — it's that the trade was stopped out at breakeven when it should have been held longer. The gear system's time-based approach is the right solution, not wider SL.

---

## Claim 3: Volume spike override at 5x volume would catch explosive moves

### Verdict: AGREE

### Evidence:

**BABY spike volume analysis:**
- 20-bar average volume before spike: 3,870,398
- Spike candle volume: 58,873,653
- **Ratio: 15.2x** (well above the 5x threshold)
- Even the first spike candle (58.8M) was 15x the average

**The 5x threshold is realistic:**
- Normal BABY volume: 3.87M per 5m candle
- Spike volume: 58.8M (15x)
- A 5x threshold = 19.35M — this would trigger on the first spike candle
- The spike was sustained across multiple candles (58.8M, 16.8M, 12.8M, 25.9M, 10.2M, 24.7M, 16.3M, 10.3M)

**But there's a timing issue:**
- The first spike candle was at 00:00 (58.8M volume)
- By the time the system detects the volume spike (next wake cycle), some move has happened
- The spec acknowledges this: "volume spike detection lag — by the time we detect, some move has happened"
- However, the spike was sustained for 35+ minutes, so detection lag is acceptable

**Confidence: HIGH**

**Notes:** The 5x threshold is well-calibrated for BABY. However, it should be tested against other tokens. Some tokens may have naturally high volume variance, making 5x too sensitive.

---

## Claim 4: 4h dead money exit is better than pump exit's 2h

### Verdict: AGREE

### Evidence:

**How many trades held over 4h:**
- volume-breakout-long+: 3 trades held >4h, 2 were winners (67% WR)
- mover+: 1 trade held >4h, 0 were winners (0% WR)
- mover-: 0 trades held >4h

**How many trades held over 6h:**
- volume-breakout-long+: 2 trades held >6h, 2 were winners (100% WR)
- mover+: 0 trades held >6h

**The BABY case:**
- BABY spike happened 8 hours after entry
- A 2h dead money exit would have killed the trade before the spike
- A 4h dead money exit would have killed the trade at 4h (still before the spike at 8h)
- **BUT**: The dead money exit only fires if profit < 2% after 4h. BABY was at ~$0.0108 (breakeven) at 4h, so it WOULD have been killed.

**Wait — this is a problem:**
- BABY at 4h: price ~$0.0108, profit = (0.0108 - 0.010736) / 0.010736 = +0.6%
- Dead money threshold: 2%
- 0.6% < 2% → **Dead money exit would fire at 4h!**
- The spike happened at 8h, so the trade would be killed 4 hours before the spike

**This contradicts the spec's claim:**
- The spec says "4h dead money exit is better than pump exit's 2h"
- But BABY would have been killed by the 4h dead money exit anyway
- The only way to catch the 8h spike is to either:
  1. Remove the dead money exit entirely
  2. Extend it to 8h+
  3. Have the volume spike override trigger before the dead money exit

**Let me check the timing:**
- Entry: 16:13
- 4h mark: 20:13
- Dead money exit at 20:13: price ~$0.0108, profit ~0.6% < 2% → KILLED
- Spike at 00:15: trade already closed

**Confidence: HIGH**

**Notes:** The 4h dead money exit would have killed the BABY trade. The spec's claim that 4h is better than 2h is technically true (more time for delayed spikes), but it's not enough for BABY's 8h spike. The dead money threshold of 2% is too high — at 4h, BABY was only at +0.6%, which is normal for a trade waiting for a breakout.

---

## Claim 5: Partial exits at +5%, +10%, +15% are optimal

### Verdict: DISAGREE

### Evidence:

**BABY partial exit math:**
- Entry: $0.010736
- +5%: $0.011273 — would sell 25% here
- +10%: $0.011810 — would sell 25% here
- +15%: $0.012347 — would sell 20% here
- Remaining 30% rides to trail exit at ~+15.7% ($0.012420)

**Gain with partials:**
- 25% × 5% = 1.25%
- 25% × 10% = 2.50%
- 20% × 15% = 3.00%
- 30% × 15.7% = 4.71%
- **Total: 11.46%**

**Gain without partials:**
- 100% × 15.7% = 15.7%

**Partial exits cost 27% of the profit on BABY.**

**But what about risk management?**
- The argument for partials is: lock in profits on trades that don't reach the full spike
- Let's check: how many volume-breakout-long+ trades would have benefited?
  - WLD: +11.8% — partials would sell at +5%, +10%, leaving 30% to ride. Would have captured ~8.5% instead of 11.8%. Lost 28%.
  - SUPER: +8.5% — partials would sell at +5%, leaving 50% to ride. Would have captured ~6.75% instead of 8.5%. Lost 20%.
  - DYDX: +5.6% — partials would sell at +5%, leaving 50% to ride. Would have captured ~5.3% instead of 5.6%. Lost 5%.
  - GMX: +5.0% — partials would sell at +5%, leaving 75% to ride. Would have captured ~5.0% instead of 5.0%. No change.

**Partial exits hurt ALL winning trades.**

**When would partials help?**
- Only on trades that reverse after hitting +5% but before hitting the trail
- Looking at the data: most winning trades either hit ATR SL (loss) or profit-monster-trail (win)
- The trail system already handles profit-taking — partials are redundant

**Confidence: HIGH**

**Notes:** Partial exits are a form of de-risking that reduces expected value. The data shows that volume-breakout-long+ trades that win tend to win big (5-12%). Partial exits cap the upside on these trades. The existing trail system (profit-monster-trail at 0.6% activation, 1.2% distance) already handles profit-taking effectively.

---

## Claim 6: The gear system (3 phases) is better than flat trailing

### Verdict: PARTIAL

### Evidence:

**The gear system addresses real problems:**
1. **Survival (0-2h)**: Wide SL to survive normal volatility. BABY needed this — the -0.06% dip would have been survived by any reasonable SL.
2. **Momentum (2-6h)**: Tighter SL + trailing. This is where most trades either work or don't.
3. **Ride (6h+)**: Tight trail to lock in gains. This catches delayed spikes like BABY.

**But the data shows most trades don't need 3 phases:**
- volume-breakout-long+: average hold 2.09h, max 18h
- mover+: average hold 1.57h, max 5.1h
- Most trades are decided within 2 hours

**The real issue isn't phases — it's the dead money exit:**
- BABY was killed at 1h56m by ATR SL (breakeven)
- Even with Ride-It, the dead money exit at 4h would have killed it
- The gear system is irrelevant if the dead money exit fires first

**What the data suggests:**
- The gear system's value is in the ATR-based SL sizing (adapts to volatility)
- The time-based phases are less important than the volume spike override
- The volume spike override is the key innovation — it catches explosive moves regardless of time

**Confidence: MEDIUM**

**Notes:** The gear system is well-designed conceptually, but the data shows that most trades are decided quickly. The real innovation is the volume spike override, not the gear phases. The gear phases add complexity without clear benefit over flat trailing + volume spike override.

---

## Claim 7: cut_loser's MAE guard at -3% would conflict with Ride-It's 4% MAE

### Verdict: NO CONFLICT

### Evidence:

**cut_loser MAE guard stats (30 days):**
- 21 trades cut by MAE guard
- Average loss: -3.48%
- All 21 trades had negative PnL (no false positives)

**Ride-It MAE threshold: 4%**
- This is WIDER than cut_loser's 3% threshold
- Ride-It would let trades run 1% further before cutting

**But here's the key finding:**
- **ZERO trades in the last 30 days had MAE > 4%**
- The MAE guard at 3% catches everything before it reaches 4%
- Ride-It's 4% threshold is effectively unreachable with the current MAE guard

**The interaction:**
- cut_loser MAE guard fires at 3% → cuts trade
- Ride-It MAE threshold at 4% → would never fire because cut_loser already cut
- **No conflict — cut_loser is more aggressive and runs first**

**Confidence: HIGH**

**Notes:** The Ride-It MAE threshold of 4% is essentially dead code because cut_loser's MAE guard at 3% fires first. If Ride-It is intended to have its own MAE guard, it needs to either:
1. Be higher than 3% (current design — but then cut_loser always fires first)
2. Replace cut_loser's MAE guard for Ride-It trades
3. Be integrated into cut_loser with a per-signal threshold

---

## Additional Findings

### Finding 1: The spec's ATR calculation is wrong
- Spec claims ATR at entry = 1.01%
- Actual ATR (14-period, 1h): 0.88%
- **12% error** — affects all SL/TP calculations in the spec

### Finding 2: BABY's drawdown was tiny
- Lowest price before spike: $0.010730
- Drawdown from entry: -0.06%
- **The current 1.3% SL would have survived too**
- The issue wasn't SL width — it was that the ATR SL trailed up and caught the breakeven exit

### Finding 3: The volume spike override is the key innovation
- 58.8M volume on first candle (15x average)
- The 5x threshold is well-calibrated
- This is the most valuable feature of the Ride-It system

### Finding 4: Partial exits are value-destructive
- Every winning trade loses 20-35% of its gain with partial exits
- The trail system already handles profit-taking
- Partial exits add complexity without clear benefit

### Finding 5: The dead money exit is too aggressive
- BABY at 4h: +0.6% profit
- Dead money threshold: 2%
- Trade would be killed 4 hours before the spike
- The threshold should be lower (0.5-1%) or the time should be longer (6-8h)

### Finding 6: mover+ trades rarely benefit from longer holds
- Only 1 out of 12 trades held >4h (and it was a loss)
- Average peak gain: 1.57% (excluding PONS data artifact)
- The gear system's "Ride" phase (6h+) is unlikely to help mover+ trades

---

## Summary Verdicts

| Claim | Verdict | Confidence |
|-------|---------|------------|
| Ride-It would have caught BABY +19% spike | PARTIAL | HIGH |
| 2.5x ATR SL is the right balance | DISAGREE | HIGH |
| 5x volume spike override is realistic | AGREE | HIGH |
| 4h dead money exit is better than 2h | AGREE (but still kills BABY) | HIGH |
| Partial exits at +5%, +10%, +15% are optimal | DISAGREE | HIGH |
| Gear system (3 phases) is better than flat trailing | PARTIAL | MEDIUM |
| cut_loser MAE guard conflicts with Ride-It 4% MAE | NO CONFLICT | HIGH |

---

## Recommendations

1. **Fix the ATR calculation** — The spec uses 1.01% but actual is 0.88%. All SL/TP values need recalculation.

2. **Remove or weaken the dead money exit** — At 4h with 2% threshold, it kills BABY-type trades. Either:
   - Extend to 8h (but this holds losers too long)
   - Lower threshold to 0.5% (only kill truly dead trades)
   - Make it signal-specific (volume-breakout gets longer dead money window)

3. **Drop partial exits** — They reduce expected value on all winning trades. The trail system handles profit-taking.

4. **Keep the volume spike override** — This is the most valuable feature. The 5x threshold is well-calibrated.

5. **Simplify the gear system** — Most trades are decided in 2h. The 3-phase system adds complexity. Consider:
   - Phase 1: Survival (0-2h, wide SL)
   - Phase 2: Trail (2h+, tight trail)
   - Volume spike override (any time)

6. **Integrate MAE guard** — Ride-It's 4% MAE is unreachable because cut_loser fires at 3%. Either:
   - Use cut_loser's MAE guard for Ride-It trades (simplest)
   - Or give Ride-It its own MAE guard that replaces cut_loser's for these signals

7. **Paper trade first** — The spec correctly identifies this as a requirement. The BABY case is compelling but is a single data point. Need 20+ trades to validate.
