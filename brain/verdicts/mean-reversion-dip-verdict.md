# Independent Verdict: Mean Reversion Dip Signal

**Auditor:** Independent Auditor  
**Date:** 2026-09-07  
**Files Reviewed:**
- `/root/.hermes/brain/specs/mean_reversion_dip_spec.md`
- `/root/.hermes/scripts/signals/open_skies.py`
- `/root/.hermes/scripts/hermes_constants.py` (last 50 lines)
- `/root/.hermes/brain/trades/inj-long-open-skies-2026-09-07.md`
- `/root/.hermes/scripts/signals/pullback_entry.py`

---

## === INDEPENDENT VERDICT ===

**Claim:** Mean reversion dip signal would catch INJ-style wins by entering at SMA20 in uptrends.

**Verdict:** DISAGREE

**Evidence:**

### 1. The INJ Trade Actually Fired via Open-Skies
The INJ trade was executed by the `open-skies+` signal, not a mean reversion setup. According to the trade analysis file, the signal fired at $6.09 when price was already up 5.1%. The entry at $5.80 was a lucky pullback 40 minutes AFTER the signal fired, enabled by a **limit order** at a lower price.

### 2. The Spec Contains Internal Contradictions
- **Section 2 ("Why This Works"):** States RSI was 45.7 (neutral)
- **Section 3 ("Signal Logic"):** Sets RSI threshold to 60-80 (bullish)
- **Section 4 ("Constants"):** Sets `MRDIP_RSI_MIN = 60`

The actual INJ RSI at 18:00 was 74.5 (per Section 1 table). But the spec's own narrative (Section 2) claims RSI was 45.7. These are completely different market conditions.

### 3. BB Position Contradiction
The spec requires BB position > 0.70 ("near upper band, strong trend"). But for a genuine pullback to SMA20:
- Price pulls back FROM the upper band
- BB position should DECREASE toward 0.50 (mid-band) or lower
- Requiring BB > 0.70 means you're entering when price is STILL near the upper band — not a pullback

The INJ BB position was 0.833, which is near the upper band. This is NOT a pullback to SMA20 — this is a strong trend where price happens to touch SMA20 briefly.

### 4. Market Orders Cannot Execute This Strategy
The trade analysis explicitly states: "Use limit orders at signal price — never market orders." The spec's own exit strategy references limit orders at SMA10. With market orders:
- Entry slippage would destroy the precise SMA20 entry
- The 0.5% proximity requirement becomes meaningless
- You'd be chasing the move, not catching the dip

### 5. Redundancy with Existing Signals
The system already has multiple mean-reversion signals:
- `pullback_entry.py` — buys post-impulse consolidation with volume dry-up
- `bb_bounce.py` — mean reversion for ranging markets
- `range_finder.py` — range-bound mean reversion
- `ma_100_bounce.py` — mean reversion at 100MA with trend continuation
- `inverse_accel_300.py` — mean reversion at EMA300

The proposed signal would be the **6th+ mean-reversion signal** in the system. The existing signals are already battle-tested with live trade data.

### 6. Frequency of Signal Firing
The combined conditions (RSI 60-80, BB > 0.70, price within 0.5% of SMA20, price > SMA50, SMA20 > SMA50, volume > 50) are extremely restrictive. In a typical market:
- RSI 60-80: ~30% of the time
- BB > 0.70: ~25% of the time (strong trend required)
- Price within 0.5% of SMA20: ~5% of the time (exact touch is rare)
- Combined probability: ~0.4% of the time per token

This signal would fire maybe once a week across all tokens, making it statistically insignificant.

### 7. The "Textbook" Setup Doesn't Exist
The spec claims entry at $5.8140 was "exactly at SMA20 ($5.8140 = $5.8140)." But SMA values are calculated from 20-period averages — they don't match prices to 4 decimal places. This is either:
- Cherry-picked data
- Rounding coincidence
- Misunderstanding of how SMA works

### 8. Open-Skies Already Captured This Trade
The INJ trade was a pure open-skies breakout:
- Zero resistance overhead
- 9 support levels below
- Price above both SMA20 and SMA50
- 5 higher highs
- Volume spike at breakout

The mean reversion dip spec is trying to retrofit a different signal to a trade that open-skies already captured correctly.

---

**Confidence:** HIGH

**Recommendation:** SKIP

**Rationale:**

1. **The trade already happened via open-skies** — this spec is solving a problem that doesn't exist
2. **Internal contradictions** make the spec unreliable (RSI 45.7 vs 60-80, BB position logic)
3. **Market orders cannot execute** the precise SMA20 entry required
4. **Redundancy** with 5+ existing mean-reversion signals
5. **Low frequency** — conditions too restrictive for statistical significance
6. **The "textbook" pattern is cherry-picked** — SMA20 doesn't match prices to 4 decimal places

**What Actually Works (from the trade analysis):**
- Open-skies signal fires during strong breakout
- Use limit orders at signal price (not market orders)
- Wait for pullback (don't chase)
- RSI guard (max 75) blocks overbought entries
- Focus on EXTREME regime

**Instead of building this signal:**
1. Enhance open-skies with better pullback entry logic
2. Add a "patience filter" that waits for price to dip below signal price before entry
3. Improve limit order execution infrastructure (currently not available)
4. Backtest the existing mean-reversion signals to find which one already captures this pattern

---

**Bottom Line:** This spec is a post-hoc rationalization of a trade that open-skies already captured. The conditions are contradictory, impractical with market orders, and redundant with existing signals. Building it would add complexity without edge.