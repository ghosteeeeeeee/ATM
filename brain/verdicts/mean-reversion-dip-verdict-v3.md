# Independent Auditor Verdict — Mean Reversion Dip Spec v3

**Auditor:** Independent subagent (no prior context, fresh read)
**Date:** 2026-09-07
**Files Read:**
- `/root/.hermes/brain/specs/mean_reversion_dip_spec.md` (106 lines)
- `/root/.hermes/scripts/signals/open_skies.py` (358 lines)
- `/root/.hermes/scripts/hermes_constants.py` (2938 lines)
- `/root/.hermes/scripts/signals/pullback_entry.py` (292 lines)

---

## === INDEPENDENT VERDICT ===

**Claim:** A 6-condition signal that generates "TOP NOTCH quality" trades, where "every trade should be a winner," targeting better than open-skies' 62% win rate across 16 trades.

**Verdict: DISAGREE** — The spec has a critical mathematical contradiction, several logical flaws, and insufficient depth to achieve the claimed quality.

**Evidence:**

### CRITICAL: Bollinger Band Position is Mathematically Impossible

The spec claims at INJ entry (18:00 UTC):
- Price = $5.8140 = SMA20 (exact touch)
- BB Position = 0.833

**This is mathematically impossible.** BB position is computed as:

```
BB Position = (Price - Lower Band) / (Upper Band - Lower Band)
BB Middle = SMA(20) = SMA20
```

When Price = SMA20 (the BB middle line):
```
Position = (SMA20 - (SMA20 - 2σ)) / ((SMA20 + 2σ) - (SMA20 - 2σ))
         = 2σ / 4σ
         = 0.50
```

**If price equals SMA20, the BB position MUST be ≈ 0.50, not 0.833.** Having BB = 0.833 at SMA20 is a contradiction. This means either:
1. The claimed INJ values were computed incorrectly (wrong BB period or wrong data)
2. The values were estimated/fabricated rather than computed from actual 1m candles
3. The BB uses a different period than 20 (not stated in the spec)

**This invalidates the entire "verified against INJ" claim in Section 3.**

### ISSUE 2: RSI 74.5 Is Overbought, Not "Not Exhausted"

Section 2 states: "RSI 74.5 = bullish momentum — trend has energy, not exhausted"

RSI > 70 is textbook overbought. The system's own CONF_FILTER notes: "90+ trades are the worst performers (48.7% WR)" — high-confidence/overbought entries are precisely the kind of setup that historically underperforms. The spec allows RSI up to 85, which is extremely aggressive.

### ISSUE 3: Only 1 Reference Trade — Massive Overfitting Risk

The entire spec is reverse-engineered from a single trade (INJ +40.57%). The spec explicitly states: "Reference: INJ LONG 2026-09-07 — +40.57% (5x)." Building a signal around one data point is the definition of overfitting. The 6 conditions were selected TO MATCH this one trade, not to generalize.

### ISSUE 4: Entry/Exit Rules Are Vague

Section 4:
- "SL: Below SMA50 (or 1.5 × ATR)" — which? Both are mentioned, no priority
- "TP: SMA10 or trailing stop" — which? No concrete R:R calculation
- "Hold: Multi-hour (INJ held 7 hours)" — how many hours? What's the max?

**R:R Analysis with stated targets:**
- Entry: $5.8140 (at SMA20)
- TP at SMA10: $5.83 → +0.28%
- SL below SMA50: $5.77 → -0.76%
- R:R = 0.28/0.76 = **0.37:1** — terrible

With trailing stop and a +40% move, R:R is excellent (hindsight). But at entry time, the measurable R:R is poor.

### ISSUE 5: Volume Condition Is Meaningless

Condition 6: "Avg volume > 50" with INJ value 3921. A threshold of 50 for raw volume count passes on virtually every tradeable token. This condition provides zero selectivity.

### ISSUE 6: No Regime Filter

The spec doesn't mention which market regime this should fire in. The system has REGIME_ENABLED=True and several signals are regime-specific. A trend-following dip-buying signal should only fire in BULL regime. In NEUTRAL or BEAR, buying pullbacks to SMA20 is catching falling knives.

### ISSUE 7: Naming Is Misleading

The spec calls this "Mean Reversion Dip" but the thesis is TREND CONTINUATION (buying pullback to dynamic support in established uptrend). Mean reversion = contrarian trade against extended move. This signal = trend-following entry on pullback. Different classification, different risk profile.

### ISSUE 8: Only 6 Conditions — Too Simple for "TOP NOTCH"

Open-skies (the reference signal) has 7 conditions + confidence scoring with 4 bonus categories. MRDIP has 6 flat conditions with no bonus scoring. For a signal claiming "every trade should be a winner," 6 simple conditions is insufficient.

### Comparison: What Open-Skies Does Better

| Feature | Open-Skies | MRDIP |
|---------|-----------|-------|
| Conditions | 7 | 6 |
| Confidence scoring | 4 bonus categories | None in spec |
| S/R structure check | Yes (support levels + resistance) | No |
| Higher highs check | Yes (structural confirmation) | No |
| Volume filter | Spike (confirms breakout) | "Quiet" (no confirmation) |
| Reference trades | 16 (62% WR) | 1 (one trade) |

---

**Confidence: HIGH** — The mathematical contradiction (BB position at SMA20) is objectively verifiable and invalidates the core data.

**Quality Assessment: LOW** — Will NOT produce winning trades as specified. The conditions are too permissive (RSI up to 85, volume >50, no regime filter), the R:R is poor (0.37:1 with stated TP/SL), and the spec is overfitted to one trade.

**Recommendation: MODIFY** — Do not build as-is.

---

## Suggested Modifications

### Must-Fix (Blockers)

1. **Fix the BB position claim.** Either:
   - Recompute INJ's BB position with the correct period and document it honestly
   - Remove the BB condition entirely if it can't be verified
   - Change BB interpretation: if BB > 0.60 is the threshold, acknowledge this means "price still near upper band" (not a deep pullback)

2. **Tighten RSI range to 50-70.** A genuine pullback to SMA20 should show RSI cooling below 70. If RSI is still 74.5, the pullback hasn't materialized on momentum.

3. **Add regime filter.** Only fire in BULL regime. Add `MRDIP_REGIME = 'BULL'` constant.

4. **Define concrete SL/TP.** Pick ONE:
   - Option A: SL = 1.5 × ATR (system standard), TP = trailing stop (let it run)
   - Option B: SL = below SMA50 (tighter, 0.76%), TP = 1.5× SL distance (R:R 1.5:1)

5. **Add entry/exit execution rules:**
   - Max hold time (e.g., 12 hours)
   - Trailing stop activation threshold
   - Whether to use Profit Monster or bypass it

### Should-Fix (Quality Improvements)

6. **Add pullback confirmation.** Require 2+ consecutive red candles before entry (confirms actual pullback, not just a wick).

7. **Add pre-pullback size filter.** Require price to have declined at least 0.3% from10-bar high (confirms meaningful dip, not noise).

8. **Add volume ratio filter.** Replace "avg volume > 50" with "current volume < 0.7x average" (confirms quiet pullback, not selling pressure).

9. **Add speed percentile filter.** Require speed > 30 (system standard) to ensure the token has momentum.

10. **Add BB width filter.** BB width should be moderate (not too tight, not too wide). Too tight = no room for move; too wide = high volatility/risk.

11. **Tighten SMA20 proximity.** Instead of "within 0.5%", use "within 0.2%" for more precise entries.

12. **Add multi-timeframe confirmation.** Require 15m or 1h trend to be bullish (EMA20 > EMA50 on higher timeframe).

### Nice-to-Have (Edge Additions)

13. **Add BTC correlation filter.** Don't fire if BTC is falling (correlation kills alt LONGs).

14. **Add time-of-day filter.** Avoid 05:00-07:00 UTC (system dead zone).

15. **Add ATR% minimum.** Require ATR > 0.15% (system VOL_FLOOR) to ensure enough volatility.

16. **Add consecutive loss circuit breaker.** If 3+ MRDIP trades lose in a row, auto-disable for 24 hours.

17. **Consider adding to PROFIT_MONSTER_BYPASS_SIGNALS.** This is a trend-continuation signal that should ride ATR SL/TP, not get chopped by PM Trail.

### Minimum Viable Build (if proceeding despite issues)

If building anyway, at minimum:
1. Fix RSI range to 50-70
2. Add BULL regime filter
3. Use ATR SL (1.5%) + trailing stop TP (system standard)
4. Add 2-candle pullback confirmation
5. Set cooldown to 4 hours (not 2 — trend signals need room)
6. Start with paper trading only, require 20+ trades before live

---

## Summary

The spec is built on a single exceptional trade with mathematically contradictory data points. The conditions are too permissive for the claimed quality level, and the entry/exit rules are too vague for implementation. **The name "mean reversion" is wrong — this is trend continuation.** The spec needs significant revision before it should be coded. Building as-is will produce a signal that fires too often on low-quality setups and will likely underperform open-skies' 62% win rate.
