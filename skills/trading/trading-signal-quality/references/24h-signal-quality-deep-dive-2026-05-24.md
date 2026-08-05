# 24h Signal Quality Deep Dive (2026-05-24)

## Summary Stats

49 trades | 36.7% WR | -$0.32 net loss

| Exit Reason | Count | Avg PnL | Total |
|-------------|-------|---------|-------|
| profit-monster | 14 | +1.14% | +$1.65 |
| atr_sl_hit | 30 | -0.61% | -$1.87 |
| guardian_sl | 1 | -0.91% | -$0.10 |
| (blank) | 4 | +0.50% | +$0.20 |

**If ATR SL was disabled, system would be profitable.** profit-monster does all profit-taking, ATR SL takes all losses.

## Winning Trade Pattern

| Token | Signal | z-score | Conf | PnL% | Duration |
|-------|--------|---------|------|------|----------|
| MON LONG | rs-s84,zscore-pump+ | 2.3-3.1 | 82-88 | +1.51 | 13min |
| SKY LONG | zscore-pump+ | 2.25-3.30 | 83-85 | +1.0 | 7h+ |
| TIA SHORT | rs-r530,zscore-pump- | -3.10 | 88 | +1.43 | 41min |
| 2Z SHORT | rs-r28,zscore-pump- | -2.5 | 88 | +0.85 | 51min |
| XRP LONG | rs-s12,zscore-pump+ | 2.23-3.01 | 98 | +1.22 | 48min |
| ENS LONG | zscore-pump+ | high | 88 | +1.13 | 113min |
| CHIP SHORT | rs-r220,zscore-pump- | -2.5 | 88 | +1.03 | 120min |

**Common factors in winners:**
- z-score 2.0-3.1 range (not extreme)
- RSI/macd_hist present in signal stream (momentum confirmed)
- Single brief fire, not repeated re-entry attempts
- Clear directional move, no consolidation traps

## Losing Trade Pattern

| Token | Signal | z-score | Conf | PnL% | Root Cause |
|-------|--------|---------|------|------|------------|
| GALA SHORT | rs-r528,zscore-pump- | -5.63 | 88 | -1.67 | Blow-off bottom SHORT, no divergence check |
| 2Z SHORT | rs-r3125,zscore-pump- | extreme | 98 | -0.99 | Extreme z, no SHORT divergence protection |
| ONDO LONG | rs-s700,zscore-pump+ | 2.44 | 88 | -1.06 | Consolidation entry, no momentum |
| SUSHI LONG | rs-s485,zscore-pump+ | 2.61-3.70 | 80-88 | -1.01 | Repeated fires in chop, z didn't break out |
| ADA LONG | rs-r8,zscore-pump- | conf only | 63-75 | -0.80 | Pure RS, no z/momentum confirmation |
| GRIFFAIN SHORT | rs-r396,zscore-pump- | -4.81 | 98 | -0.77 | Blow-off SHORT, DIVERGENCE check bypassed |
| MORPHO SHORT | rs-r184,zscore-pump- | extreme | 86 | -0.91 | guardian_sl — price moved UP against SHORT |

**Common factors in losers:**
- z-score > 4.0 (extreme) — blow-off moves that reverse
- Repeated re-firing (COOLDOWN=5 too short, fires 5-10x in 20 min)
- rsi_14 and macd_hist always NULL in signals DB — no momentum confirmation
- Entered at resistance during consolidation, not trend continuation

## zscore-pump Threshold Analysis

**Winners:** z=2.0 to 3.1 (sweet spot)
**Losers:** z=4.0+ (extreme, likely reversal)

```python
# Current (post-T-tweak):
ZSCORE_PUMP_THRESHOLD = 3.0        # was 2.5 — good, cuts noise
ZSCORE_PUMP_LOOKBACK = 150         # was 70 — good, catches sustained trends
ZSCORE_PUMP_COOLDOWN_BARS = 5      # was 5 — STILL TOO SHORT
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 3.5  # only protects LONG
```

Key constant recommendations from 24h data:
```python
ZSCORE_PUMP_COOLDOWN_BARS = 20     # was 5 — stop re-firing in consolidation
ZSCORE_PUMP_DIVERGENCE_SHORT_Z = 3.0  # new — block SHORT at blow-off bottom
RS_DECIDER_MIN_TOUCHES = 300       # was 200 — stricter RS levels
RS_DECIDER_CONF_FLOOR = 60         # was 55 — higher floor blocks weak signals
```

## ME +4.27% Case Study

ME LONG fires at z=3.635, conf=88, moves to +4.27% → ATR SL exits at +4.27%.

**Problem:** ATR_SL_MIN_INIT=1.0% floor gave SL at 0.10129 (1.0% above entry 0.09528). Price pulled back to ~0.099 during consolidation → hit SL → gave back most of +4.27%.

**If ATR_SL_MIN_INIT was 1.5%:**
- SL = 0.09528 × 1.015 = 0.09671
- Wider buffer → holds through consolidation → stays in for full +4.27% move

**ATR thresholds for "first candle out":**
```python
ATR_SL_MIN_INIT = 0.015   # 1.5% — wider entry breathing room
ATR_SL_MIN_ACCEL = 0.003  # 0.3% — tighten fast on established positions
```

## OPP/SAME Ratio Finding (from prior analysis)

In 24h data, the worst signals (SUSHI, ADA, 2Z LONG, ONDO) all showed:
- OPP (opposing direction signals) > SAME in 60-min window before entry
- This was identified in prior session analysis — `RS_OPP_SAME_RATIO_BLOCK` constant was recommended but NOT implemented

**Evidence that OPP/SAME filtering would have prevented the worst losses:**
- SUSHI LONG: 19 pre-entry signals, mostly RS (conf 68-88), all counter-direction
- ADA LONG: 9 RS signals, conf 64-75, no momentum confirmation

## Confluence Illusion (from prior session)

`rs-s212,zscore-pump+` fires with conf=98% — RS barely qualifies (level 212 touches, RS_DECIDER_MIN_TOUCHES=200). The combo boosts confidence to 98%, making us overconfident in a weak level.

Fix: `ZSCORE_PUMP_COMBO_CONF_CAP = 92` — cap combined signal at 92%, don't let weak RS inflate signal.

## See Also

- `hermes-signal-debugging/references/divergence-long-only-short-vulnerable-2026-05-24.md`
- `atr-trailing-debug/references/atr-sl-first-candle-out-2026-05-24.md`