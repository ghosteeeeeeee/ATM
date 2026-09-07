# Independent Auditor Verdict: Trend-Pullback Signal

**Auditor:** Independent auditor (own-conclusions skill)  
**Date:** 2026-09-08  
**Files reviewed:** trend_pullback_signal_spec.md, open_skies.py, hermes_constants.py, inj-long-open-skies-2026-09-07.md, pullback_entry.py, hyperliquid_exchange.py, brain.py, decider_run.py, signals/__init__.py

---

## VERDICT #1: "Trend-pullback signal would capture INJ-style wins"

**Verdict: DISAGREE**  
**Confidence: HIGH**  
**Evidence:**

The INJ reference trade **fails the signal's own criteria on three separate conditions:**

| Condition | Signal Requirement | INJ Actual | Pass? |
|-----------|-------------------|------------|-------|
| Pullback depth | 1.5–5% from 20-bar high | -7.3% ($6.26→$5.80) | ✗ TOO DEEP |
| RSI | 40–70 | 83.1 | ✗ WAY OVER |
| 20-bar return | < 8% | +5.30% | ✓ |

The pullback from $6.26 peak to $5.80 entry is **-7.3%**, which exceeds the `TREND_PULLBACK_MAX_DIP_PCT = 5.0`. The spec's own detection logic would **skip this pullback as "trend broken."**

**The trade analysis document (inj-long-open-skies-2026-09-07.md) contains factual errors:**

1. **Line 19:** Claims `Price > SMA20 | $6.09 > $6.16 | ✓` — **$6.09 is NOT greater than $6.16.** This condition actually FAILED. The open-skies code at line 184 (`if price <= sma_fast: return None`) would have blocked this signal.

2. **Line 24:** Claims RSI 83.1 with "⚠️ High but not overbought at entry" — but `OPEN_SKIES_MAX_RSI = 75` (hermes_constants.py line 2844), and the code at line 189 (`if rsi > OPEN_SKIES_MAX_RSI: return None`) would have BLOCKED this signal. RSI 83.1 is well above 75.

3. **Lines 35–36:** Claims "limit order filled on pullback" — **the system only uses market orders** (`mirror_open` at hyperliquid_exchange.py line 1052: `order_type="Market"`). The entry at $5.80 was a market order that happened to execute during a price dip. This was lucky timing, not a deliberate pullback entry.

**Conclusion:** The INJ trade's entry at $5.80 was not a pullback detection — it was a market order executing at a favorable moment. The trade analysis document was written retroactively to fit a narrative, with at least 3 factual inaccuracies. The proposed signal would NOT have caught this trade.

---

## VERDICT #2: "Pullback entries are better than breakout entries"

**Verdict: DISAGREE**  
**Confidence: MEDIUM**  
**Evidence:**

The spec's entry strategy (lines 74–85) is fundamentally incompatible with the system's execution infrastructure:

```python
# This signal is designed for LIMIT ORDERS, not market orders (line 76)
entry_zone = max(sma20, nearest_support)
# If current price is above entry zone → set limit order at entry_zone
```

**All trades in Hermes execute via market orders** (hyperliquid_exchange.py line 1052). The entry_zone concept is dead code — it has no effect on actual execution. With a market order:
- Signal fires at time T when conditions are met
- Market order executes at time T+N (pipeline processing delay + execution)
- Price at execution may be anywhere — above, below, or at signal price
- The "better price" promise is unfulfillable

**The INJ trade proves this:** The open-skies signal fired at $6.09, and the market order happened to fill at $5.80 (during a dip). This was pure luck, not a pullback detection system. You cannot reliably "buy the dip" with market orders because you have zero control over fill price.

**With market orders, pullback entries and breakout entries have identical execution mechanics.** The only difference is which conditions trigger the signal — not how the trade is entered.

---

## VERDICT #3: "The signal complements open-skies (different entry timing)"

**Verdict: PARTIAL**  
**Confidence: HIGH**  
**Evidence:**

The spec claims these signals capture "the full lifecycle" — open-skies on breakout, trend-pullback on pullback. In theory, this is sound. In practice:

**Overlap with existing pullback_entry signal:**  
The codebase already has `pullback_entry.py` (registered in signals/__init__.py line 291) which detects:
- Post-impulse consolidation with volume dry-up
- BB squeeze (low volatility)
- Trend intact via EMA
- RSI confirmation
- LONG and SHORT

The proposed trend-pullback signal overlaps significantly with the existing pullback_entry:
- Both detect pullbacks in trends
- Both use RSI, volume, and trend filters
- Both aim to enter on dips

**Key differences:**
| Feature | Existing pullback_entry | Proposed trend-pullback |
|---------|------------------------|------------------------|
| Direction | LONG + SHORT | LONG only |
| Trend filter | EMA-based | SMA20 > SMA50 |
| Volume filter | Volume DRY-UP (low = good) | Volume ACTIVE (high = good) |
| Volatility | BB squeeze (low = good) | Not checked |
| S/R levels | Not checked | ≥2 support levels |
| Resistance | Not checked | Not checked |

**The volume filters are contradictory:** The existing pullback_entry requires volume to DRY UP (low volume = consolidation before next move). The proposed trend-pullback requires volume to be ACTIVE (above 50). These are opposite signals — one looks for quiet consolidation, the other for active markets. They would rarely fire together, which IS complementary, but it also means trend-pullback would miss the classic "calm before the next leg" pattern.

**The spec's "complement" claim is partially valid** — the signals would fire in different market conditions. But the trend-pullback adds marginal value over the existing pullback_entry, and both are limited by the market-order execution constraint.

---

## VERDICT #4: "The conditions are realistic and will actually fire"

**Verdict: DISAGREE**  
**Confidence: HIGH**  
**Evidence:**

The combined conditions create a very narrow detection window:

1. **Uptrend:** Price > SMA20 > SMA50 (reasonable)
2. **Pullback 1.5–5%:** Must have pulled back, but not too much (narrow window)
3. **Price above SMA20 or within 0.5%:** Pullback can't go below SMA20 (very tight)
4. **RSI 40–70:** Must have cooled from overbought but not gone oversold (narrow)
5. **≥2 support levels:** Structural requirement (may not exist for newer tokens)
6. **Volume > 50:** Active market (conflicts with typical pullback behavior — volume usually drops on pullbacks)
7. **20-bar return < 8%:** Move hasn't already happened (but if trending up, this is likely to be high)

**The fundamental contradiction:** A pullback in an uptrend naturally causes:
- RSI to drop (potentially below 40 if the pullback is deep enough)
- Volume to decrease (pullbacks are typically low-volume)
- Price to approach or cross below SMA20

The spec wants a pullback that is:
- Deep enough to be meaningful (1.5–5%)
- But not so deep that RSI drops below 40 or price crosses SMA20
- And with volume still active (unusual for pullbacks)

This is the "Goldilocks pullback" — not too deep, not too shallow, with volume still active. This will fire very rarely in practice.

**Comparison with open-skies fire rate:** Open-skies has 16 trades across its lifetime. Trend-pullback's tighter constraints suggest even fewer fires — perhaps 3–5 per month at best.

---

## VERDICT #5: "The spec logic is correct"

**Verdict: DISAGREE**  
**Confidence: HIGH**  
**Evidence:**

**Bug 1 — Entry strategy is dead code (lines 74–85):**
The entry_zone calculation and limit order logic have no effect because the system uses market orders. The signal will fire but the entry price will be whatever the market order fills at — not the calculated entry_zone.

**Bug 2 — INJ trade analysis has wrong data (line 19):**
`Price > SMA20 | $6.09 > $6.16 | ✓` — this is mathematically false. The check should be ✗.

**Bug 3 — RSI check contradicts open-skies behavior (line 24):**
RSI 83.1 is marked as passing, but open-skies blocks RSI > 75. If open-skies blocked this trade, it never would have fired. The trade analysis is inconsistent with the code.

**Bug 4 — "Limit order filled on pullback" claim (line 35):**
System uses market orders only. The entry description is inaccurate.

**Bug 5 — Support level check is vague (line 71):**
"≥2 support levels below" depends on `risk_reward_engine.build_sr_map()` which uses a 5-min cache. Support levels can appear/disappear rapidly during volatile moves. No specification of what constitutes a "support level" (lookback period, strength threshold).

**Bug 6 — 20-bar return cap conflicts with trend requirement:**
If a coin is in a strong uptrend (price > SMA20 > SMA50), the 20-bar return is likely to be > 8%, which would block the signal. The condition penalizes the very trend strength the signal is trying to capitalize on.

---

## VERDICT #6: "Should we build this?"

**Verdict: SKIP**  
**Confidence: HIGH**  
**Recommendation: Do not build as specified.**

### Reasons to SKIP:

1. **The reference case (INJ) doesn't meet the signal's own criteria** — a signal that can't catch its own inspiration trade is poorly designed.

2. **Market order incompatibility** — the spec explicitly requires limit orders (line 76) but the system only supports market orders. The entry strategy is dead code. Without limit orders, you cannot "buy the pullback" at a specific price.

3. **Existing overlap** — `pullback_entry.py` already exists and detects pullbacks in trends with a different (arguably better) approach: volume dry-up + BB squeeze = classic consolidation pattern.

4. **Too many constraints** — the "Goldilocks pullback" conditions (specific RSI range, specific pullback depth, active volume during a pullback) will fire very rarely, adding complexity for minimal signal volume.

5. **The trade analysis document is unreliable** — three factual errors undermine confidence in the analysis that motivated this spec.

### What WOULD make this valuable:

1. **Wait for limit order support** — the signal's entry strategy becomes meaningful only with limit orders. Until then, it's just another market-order signal with different detection conditions.

2. **Simplify conditions** — focus on the core edge: "price pulled back to SMA20 in an uptrend." Remove the RSI 40–70 constraint (too narrow), the volume-active constraint (contradicts pullback behavior), and the 20-bar return cap (penalizes trend strength).

3. **Use the existing pullback_entry** — rather than building a new signal, tune pullback_entry.py to be LONG-only in uptrends with SMA20/SMA50 confirmation. This builds on working code instead of creating a parallel system.

4. **Fix the INJ trade analysis** — before using it as motivation, correct the factual errors. The SMA20 comparison is wrong, the RSI claim contradicts the code, and the "limit order" description is inaccurate.

### Alternative Recommendation:

If the goal is "capture big trend moves like INJ's +40.57%", the most effective approach is:
1. Improve open-skies execution (reduce slippage, better timing)
2. Tune trailing stops to ride winners longer
3. Size up on high-conviction setups (9+ support levels, zero resistance)
4. Focus on EXTREME regime (highest win rate per trade analysis)

These improvements work within the existing system constraints and don't require a new signal with fundamental design flaws.

---

## Summary Table

| Claim | Verdict | Confidence |
|-------|---------|------------|
| Trend-pullback would capture INJ-style wins | DISAGREE | HIGH |
| Pullback entries are better than breakout entries | DISAGREE | MEDIUM |
| Signal complements open-skies | PARTIAL | HIGH |
| Conditions are realistic and will fire | DISAGREE | HIGH |
| Spec logic is correct | DISAGREE | HIGH |
| **Should we build this?** | **SKIP** | **HIGH** |

**Bottom line:** The trend-pullback signal is motivated by a trade analysis document with factual errors, designed for an execution mechanism (limit orders) that doesn't exist, and would fail to catch its own reference case (INJ). The existing `pullback_entry` signal already covers this territory with a more practical approach. Skip until limit orders are available.
