---
name: morpho-postmortem
description: "Post-mortem skill capturing two critical trading system bugs found during MORPHO loss investigation: (1) falling knife RSI scoring that rewarded negative-velocity oversold setups, and (2) regime-vs-zscore conflict where market regime overrode mean-reversion signals at local tops/bottoms."
triggers:
  - MORPHO loss investigation
  - counter-regime signals being blocked
  - ai-wait-long blocked shorts at local top
  - falling knife detection
  - regime-z conflict
  - ai_decider LONG_BIAS override
  - ATOM SHORT analysis
  - choppy market false signals
  - candle staleness causing MACD false crosses
  - compactor confidence inflation
---

# MORPHO Post-Mortem: Regime-Z Conflict & Falling Knife Detection

## Context
- **Date**: 2026-04-15
- **Loss**: -2.16% ($1.08) on MORPHO LONG entered at $1.8803, stopped out at $1.8402
- **Signal**: `hmacd-,hzscore` + LONG, 92% confidence, RSI=28.33, velocity=-0.0025
- **AI decision**: `ai-wait-long` blocked SHORT at $1.73 (z=+1.06, overbought, correct call); then executed LONG at $1.88 (z=-0.32, local top, wrong call)

## Root Cause 1: Falling Knife Detection

**Problem**: `signal_gen.py` awarded +3 pts `oversold-confirm` for RSI ≤ 30 + LONG regardless of velocity direction. MORPHO had RSI=28.33 but velocity=-0.0025 (price still falling). The bonus was applied to a falling knife, not a reversal.

**Fix** (applied to `signal_gen.py` lines ~1060-1080):
```python
if rsi_val <= 30:
    if velocity >= 0 or percentile_long <= 35:
        rsi_score = +3.0
        rsi_reason = f'RSI={rsi_val:.0f}(oversold-confirm)'
    else:
        rsi_score = -2.0
        rsi_reason = f'RSI={rsi_val:.0f}(oversold-falling-knife)'
elif rsi_val <= 40:
    if velocity < 0 and percentile_long > 40:
        rsi_score = -1.0
        rsi_reason = f'RSI={rsi_val:.0f}(oversold-fading)'
    else:
        rsi_score = +1.0
        rsi_reason = f'RSI={rsi_val:.0f}(oversold)'
```

**Rule**: RSI ≤ 30 + velocity < 0 + percentile_long > 35 = falling knife, penalize -2 pts instead of +3 pts.

## Root Cause 2: Regime-Z Conflict in Extreme Market Bias

**Problem**: The 4h regime scanner identified the market as `LONG_BIAS` (93/113 tokens). The ai_decider received this as context and blocked SHORT signals (`ai-wait-long`). But the market was at a local top — the z-score said SHORT (z=+1.06 = top of range), the regime said LONG. The regime overrode the z-score at exactly the wrong moment.

**Mechanics**:
1. `4h_regime_scanner.py` → `regime_4h.json` → MORPHO: `LONG_BIAS (95%) - slope: +1.699%`
2. ai_decider reads `regime_4h.json` aggregate → `_market_regime = "LONG_BIAS"`
3. In `LONG_BIAS` market, fallback algorithm gives no penalty to LONG, no bonus to SHORT
4. SHORT signals at $1.73 (z=+1.06, RSI=69) → `ai-wait-long` REJECTED
5. LONG signal at $1.88 (z=-0.32, RSI=28, vel=-0.0025) → EXECUTED (local top)
6. Price drops, SL hit → -2.16% loss

**The conflict**: z-score said "top of range = SHORT". Regime said "uptrend = LONG". Regime won. But the slope (+1.699%/4h) was actually identifying the END of the rally, not the start. The regime scanner can't distinguish.

**Key data**:
- BTC at time of trade: z_direction=falling, z=+1.071 (top of BTC range too)
- MORPHO: z=+1.06 on Apr 14 (SHORT correct) → z=-0.32 on Apr 15 (LONG wrong)
- 113 tokens scanned, 93 LONG_BIAS, 1 SHORT_BIAS, 19 NEUTRAL

## The z_direction Semantics (from signal_gen.py line 623)

```
'rising' = avg_z < -0.3 → z-score rising → price reverting UP → at local BOTTOM (good for LONG)
'falling' = avg_z > +0.3 → z-score falling → price reverting DOWN → at local TOP (good for SHORT)
```

This was fixed on 2026-04-05 — previously it was inverted. Verify this is correct in current code.

## Proposed Fixes

### 1. Regime-Z Conflict Detector
Add to `signal_gen.py` or `ai_decider.py`:

When ALL of these are true simultaneously:
- Token regime = `LONG_BIAS` (or `SHORT_BIAS`)
- Token z-score > +0.5 (or < -0.5 for SHORT)
- z_direction contradicts regime direction

→ Flag as **regime-z conflict** → skip both directions, log warning.

```python
def detect_regime_z_conflict(token, direction, z_score, z_direction, regime):
    """Return True if z-score and regime contradict each other."""
    if regime == 'LONG_BIAS' and z_score > 0.5 and z_direction == 'falling':
        return True  # Regime says uptrend, z-score says top of range
    if regime == 'SHORT_BIAS' and z_score < -0.5 and z_direction == 'rising':
        return True  # Regime says downtrend, z-score says bottom of range
    return False
```

### 2. Symmetric Regime Penalty in Fallback
In `ai_decider.py` fallback algorithm (around line 1615):

Current:
```python
regime_bonus = 1.15 if direction.upper() == 'SHORT' and _market_regime == 'SHORT_BIAS' else (
               0.85 if direction.upper() == 'LONG' and _market_regime == 'SHORT_BIAS' else 1.0)
```

Should be symmetric:
```python
if _market_regime == 'SHORT_BIAS':
    regime_bonus = 1.15 if direction.upper() == 'SHORT' else 0.85
elif _market_regime == 'LONG_BIAS':
    regime_bonus = 1.15 if direction.upper() == 'LONG' else 0.85
else:
    regime_bonus = 1.0
```

### 3. Trend Phase Detection
The regime scanner's `slope_pct` can't distinguish start vs end of a trend. Consider:
- Adding z-score direction to regime output (is z rising or falling within the trend?)
- A "momentum exhaustion" flag when slope is high BUT z is already elevated

### 4. Short Signal Viability Check
The `check_short_trend_filter()` in `signal_gen.py` (line 784) already blocks shorts in broad uptrend (broad_avg > +0.5). But this is separate from the ai_decider ranking. If SHORT survives the filter but regime is extreme LONG_BIAS, it still needs additional scrutiny.

## Files Modified
- `/root/.hermes/scripts/signal_gen.py` — falling knife detection fix (RSI scoring)
- `/root/.hermes/scripts/ai_decider.py` — 3 NameError fixes, schema reverted, `top20_keys` added

## Key Files Referenced
- `/root/.hermes/scripts/ai_decider.py` — `_do_compaction_llm()`, fallback algorithm, market regime reading
- `/root/.hermes/scripts/signal_gen.py` — `compute_score()`, `check_short_trend_filter()`, z_direction semantics
- `/root/.hermes/scripts/4h_regime_scanner.py` — regime scanner, writes `regime_4h.json`
- `/root/.hermes/prompt/main-prompt.md` — ai_decider prompt, "counter-pressure" handling
- `/var/www/html/regime_4h.json` — current regime data (masked token names)

## ATOM SHORT Post-Mortem: Choppy Market + Compactor Confidence Inflation

- **Date**: 2026-04-26
- **Trade**: ATOM SHORT #7779, entry $2.0205, 3 open signals at 99% confidence
- **Signal**: `oc-mtf-macd-,oc-zscore-v9-,zscore-momentum-`, confidence=99%
- **Result**: Still open at +0.19% — surviving despite signal quality, not because of it

### Root Cause 1: Candle Staleness Producing False MACD Crosses

`candles.db` ATOM data was severely stale at signal time:
- `candles_1m`: latest=10:41 UTC, **195 min stale** when signal ran at 13:04
- `candles_5m`: latest=10:40 UTC, **3h15min stale**
- `candles_15m`: latest=10:15 UTC, **3h40min stale**
- `candles_1h`: latest=08:00 UTC, **5h55min stale**
- `candles_4h`: latest=00:00 UTC, **13h55min stale**

The OC MTF-MACD was checking 1m+5m candles that hadn't updated in 3+ hours. In a choppy ATOM market ($2.01-$2.03 range), MACD crosses on stale data are false signals.

### Root Cause 2: Marginal Z-Score Being Treated as Strong

zscore_momentum computed from `signals_hermes.db price_history` at signal time:
- z-score = -2.047 (barely below threshold of -2.0)
- One bar of sideways chop would have kept it above -2.0
- 60-bar lookback showed a slow grind-down, not momentum
- This was a mean-reversion call, not a momentum SHORT

### Root Cause 3: Compactor Inflating Confidence

3 signals each at ~80% confidence compounded through source weights:
- `zscore_momentum` × 1.5 (strong standalone weight)
- `oc_zscore_v9` × 1.3
- `oc_mtf_macd` × 1.3
- survival bonus (hot=1) → +15%

The compactor produced 99% confidence — but that's 3x marginal signals, not 1x strong signal.

### Lesson: Regime Check Before Execution

In choppy markets (ATOM oscillating $2.01-$2.03), MACD flips on all timeframes are noise. The fix is NOT to adjust signal weights — it's to add a chop/ADX regime filter upstream that suppresses MACD and z-score signals when the market is ranging.

### ATOM Signal Data
- Signal created: 2026-04-26 13:04:42 (id=481815), executed 13:27:27 (23 min latency)
- Entry: $2.0205, SL: $2.0255 (+0.25%), TP: $2.0104 (-0.50%)
- Multiple zscore_momentum signals fired over prior hours (all SHORT), all at same price levels
- zscore_momentum_tuner: lookback=60, threshold=2.0, WR=75%, 16 signals ALL SHORT — sample too small, directionally biased

## Test Case
MORPHO trade:
- SHORT at $1.73, z=+1.06, RSI=69, regime=LONG_BIAS, slope=+1.699% → should have been viable but blocked
- LONG at $1.88, z=-0.32, RSI=28, vel=-0.0025, regime=LONG_BIAS → executed (wrong)

Signal record in DB:
- id=20922 [Apr 14 18:03] SHORT conf=90 z=1.062 RSI=69 price=$1.752 → `ai-wait-long`
- id=56360 [Apr 15 19:32] LONG conf=92 z=-0.320 RSI=28.33 price=$1.8807 → `EXECUTED`
