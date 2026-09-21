# Independent Verdict: Oscillator Filter Verification

**Auditor:** Independent Auditor (fresh eyes, no prior context)
**Date:** 2026-09-23
**Data Source:** PostgreSQL `brain` database (5,224 closed trades)

---

## === INDEPENDENT VERDICT ===

**Recommendation: MODIFY (major redesign required)**

**Evidence:**

The claimed worst combination (btc_score <30 + falling wave + SHORT = 19% WR, -$2.39) is **statistically verified**. However, the proposed multiplier approach has **two critical design flaws** that would cause the opposite of the intended effect.

### Finding 1: The Claims Are Accurate

| Combo | Trades | WR% | Avg PnL | Total PnL |
|-------|--------|-----|---------|-----------|
| btc<30 + falling + SHORT | 21 | 19.0% | -$0.114 | -$2.39 |
| btc<30 + falling + LONG | 14 | 28.6% | -$0.055 | -$0.77 |
| btc<30 + accelerating | 36 | 52.8% | +$0.013 | +$0.46 |
| btc>70 + (accel/decel) | 38 | 63.2% | +$0.045 | +$1.70 |

Statistical significance of worst combo: z = -3.42, p < 0.001 (HIGHLY SIGNIFICANT).
The 21 trades represent 0.4% of all trades but 36.5% of total losses (-$2.39 of -$6.54).

### Finding 2: CRITICAL — The 0.3x Multiplier Is a Hard Block, Not an Adjustment

**The CONF_FILTER in signal_compactor.py blocks trades with confidence < 65.**

The worst combo's trades have base confidence of 74-104. After applying the 0.3x multiplier:
- Minimum post-multiplier confidence: **22.2** (base 74 × 0.3)
- Maximum post-multiplier confidence: **31.2** (base 104 × 0.3)
- **ALL 21 trades would be hard-blocked** (below CONF_FILTER_MIN = 65)

This means the 0.3x multiplier is effectively a **blanket block** disguised as a confidence adjustment — the exact thing the proposal claims to avoid. It would have identical behavior to `if btc<30 and falling and SHORT: skip trade`.

### Finding 3: CRITICAL — The 1.1x Boost Would Destroy Best Trades

**The CONF_FILTER blocks trades with confidence ≥ 89.**

The "best combo" trades (btc>70 + accel/decel) have base confidence of 71-104. After applying the 1.1x multiplier:
- 21 out of 38 trades would be **pushed above CONF_FILTER_MAX (89)** and BLOCKED
- These include the highest-PnL trades: FOGO (+$0.69), CASHCAT (+$0.43), XPL (+$0.25), SOL (+$0.23)
- Only trades with base confidence < 81 would survive the boost

**The 1.1x boost would destroy the very trades it's supposed to help.**

### Finding 4: Coverage Problem — 5.3% Data, Not 8%

- Total closed trades: 5,224
- Trades with btc_score: 279 (5.3%)
- Trades with wave_phase: 1,449 (27.7%)
- Trades with BOTH: 279 (5.3%)

The btc_score data only exists from September 7, 2026 onwards (2-3 weeks). All pre-September trades have 0% coverage. The analysis is based on a very narrow time window.

### Finding 5: Sample Sizes Are Small for Multi-Way Splits

| Combo | n | Reliability |
|-------|---|-------------|
| btc<30 + falling + SHORT | 21 | Marginal (need 30+ for reliable WR) |
| btc<30 + falling + LONG | 14 | Unreliable |
| btc<30 + accelerating (any dir) | 36 | Acceptable |
| btc>70 + accel/decel (any dir) | 38 | Acceptable |

---

**Risk: What Could Go Wrong**

1. **False confidence floor effect**: The 0.3x multiplier would block trades that pass ALL other filters (regime, confluence, staleness, etc.), reducing trade frequency for no proportional benefit.

2. **False confidence ceiling effect**: The 1.1x boost would actively harm the best-performing trades by pushing them above CONF_FILTER_MAX. This is the worst possible outcome — a boost that becomes a blocker.

3. **Interaction with CONF_FILTER**: The proposal does not account for the existing confidence floor (65) and ceiling (89) in signal_compactor.py. Any multiplier that pushes confidence below 65 or above 89 has the opposite of the intended effect.

4. **Overfitting to narrow window**: The btc_score data covers only 2-3 weeks. The patterns may not generalize.

5. **Missing edge cases**: The proposal doesn't handle:
   - btc_score missing (94.7% of trades) — what multiplier applies?
   - btc_score = exactly 30 or 70 (boundary cases)
   - Wave phase = "neutral" or "bottoming" (not covered)
   - DIRECTION bias interaction (SHORT-in-NORMAL already has a penalty)

6. **635 "falling" wave trades have -$3.98 total PnL** — the falling phase is the biggest loser overall, not just in the btc<30 tier. The btc<30 filter misses most of this loss.

---

**Implementation: Where and How**

### Recommended Approach: Hard Block, Not Multiplier

Since the 0.3x multiplier effectively blocks trades anyway (below CONF_FILTER_MIN), use an explicit hard block with logging:

```python
# In signal_compactor.py, BEFORE the final_score calculation (~line 1080)
# Add after the CONF_FILTER checks:

# Oscillator gate: block worst-performing regime combinations
if btc_score < 30 and wave_phase == 'falling' and direction == 'SHORT':
    log(f"  🚫 [OSC-GATE] {token} SHORT: btc_score={btc_score:.1f} + falling wave → worst combo (19% WR, -$2.39)")
    return 0.0  # Hard block — same as CONF_FILTER approach
```

**Do NOT use the 1.1x boost** — it would push high-confidence trades above CONF_FILTER_MAX. Instead, if you want to reward best conditions, reduce the boost to 1.03-1.05x and ensure it never exceeds 88.

### Alternative: Skip the Complexity Entirely

The worst combo represents only 21 trades (0.4% of all trades, -$2.39 total). The system already has 20+ multipliers in the final_score chain (line 1720). Adding another layer for 21 trades is not cost-effective.

**Better use of engineering time**: Fix the CONF_FILTER_MAX threshold. Currently set at 89, but the data shows 95+ tier is most profitable (+$0.04 avg PnL vs -$0.004 for 80-89 tier). The CONF_FILTER_MAX may be blocking good trades.

---

**Confidence: MEDIUM**

Reason: The data is real and verifiable, but the sample size for the worst combo (21 trades) is small. The design flaw in the multiplier approach is definitive (interaction with CONF_FILTER), but the optimal solution depends on system-wide priorities.

---

## Appendix: Key Data Points

### Win Rate by btc_score Range (all directions, all wave phases)
| Range | n | WR% | Avg PnL | Total PnL |
|-------|---|-----|---------|-----------|
| 00-29 | 83 | 42.2% | -$0.029 | -$2.39 |
| 30-49 | 59 | 50.8% | +$0.036 | +$2.13 |
| 50-69 | 47 | 53.2% | +$0.012 | +$0.58 |
| 70-84 | 37 | 62.2% | +$0.020 | +$0.75 |
| 85-100 | 52 | 53.8% | +$0.033 | +$1.74 |

### Win Rate by Wave Phase (all btc_scores, all directions)
| Phase | n | WR% | Avg PnL | Total PnL |
|-------|---|-----|---------|-----------|
| decelerating | 117 | 59.0% | +$0.008 | +$0.99 |
| accelerating | 549 | 51.7% | -$0.001 | -$0.72 |
| neutral | 18 | 61.1% | -$0.006 | -$0.10 |
| falling | 634 | 52.1% | -$0.006 | -$3.98 |
| bottoming | 130 | 53.1% | -$0.011 | -$1.43 |

### Data Coverage Timeline
| Week | Trades | With btc_score | Coverage |
|------|--------|----------------|----------|
| Sep 21 | 10 | 10 | 100% |
| Sep 14 | 205 | 205 | 100% |
| Sep 7 | 331 | 63 | 19% |
| Before Sep 7 | 3,238 | 0 | 0% |

### Confidence Distribution
- Min: 51, Max: 104, Median: 91
- CONF_FILTER_MIN = 65 (hard block below)
- CONF_FILTER_MAX = 89 (hard block above)
- Trades with base confidence in 89-104 range: ~1,400 (many would be affected by 1.1x boost)
