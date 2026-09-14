# Verdict: Volatility Regime Adaptive Signals Plan

**Date:** 2026-09-14
**Auditor:** Independent reviewer (own-conclusions)
**Plan:** `plans/2026-09-11_volatility-regime-adaptive-signals.md`
**Verdict:** 🔴 **NO-GO** — Multiple critical issues that must be resolved before implementation.

---

## Executive Summary

The plan proposes adding volatility regime classification (EXPANSION/NORMAL/COMPRESSION) to signal_compactor.py, boosting momentum signals during expansion and mean-reversion during compression. The core thesis is sound — different market regimes favor different signal types. However, the implementation has **two critical bugs** (wrong data source, massive duplication), **three design flaws**, and **zero validation data**. Implementing this as-is would add a broken multiplier that silently does nothing useful, while duplicating functionality that already exists and works.

---

## 1. Volatility Classification Assessment

**Rating: ⚠️ Thesis Correct, Thresholds Unvalidated**

The ATR ratio approach (current_ATR / average_ATR) is conceptually sound. Using a ratio relative to average normalizes across different tokens and market conditions.

**Problems:**
- **No validation that 1.5x and 0.7x are meaningful thresholds.** The plan says "ATR ratio > 1.5x is conservative" but provides zero data on how often this occurs, what the distribution looks like, or whether these thresholds separate genuinely different market states.
- **The 500-bar average window (~8 hours on 1m) may be too short.** If BTC has been volatile for 12 hours, the "average" will be elevated, and the ratio will understate the actual regime. A 24-48h average would be more robust.
- **The existing system already classifies volatility differently.** volatility_gate_v2.py uses ATR% (absolute, not ratio-based) with thresholds at 0.48% / 1.0% / 1.5%. The plan's ratio-based approach is a different paradigm — having both running simultaneously creates confusion about which classification is authoritative.

**Assessment:** The thesis is right, but the thresholds need backtesting before implementation. Don't ship arbitrary thresholds.

---

## 2. Signal Weighting Assessment

**Rating: ⚠️ Mostly Sound, But pump-chain Classification Is Wrong**

The general principle — boost momentum in expansion, boost mean-reversion in compression — aligns with trading literature and the system's own chop_detector.py classification.

**However:**
- **pump-chain is classified as MOMENTUM in the plan but MEAN_REVERSION in chop_detector.py.** The plan's signal table (line 67) gives pump-chain a 1.3x boost in EXPANSION. But chop_detector.py (line 103-108) explicitly classifies `pump-chain` as `MEAN_REVERSION` because it fires on chain correlation, not BTC momentum. The plan's code uses `signal_family == 'MOMENTUM'` check — but which function provides this family? The plan doesn't import or define it. If it uses chop_detector._classify_signal, pump-chain gets classified as MEAN_REVERSION and receives the wrong multiplier.
- **The binary MOMENTUM/MEAN_REVERSION split is too coarse.** The existing volatility_gate_v2.py uses per-signal-family multipliers (Bollinger, Momentum, Range, Exhaustion, etc.) — 15+ families with specific multipliers per (regime, phase) combination. The plan reduces this to just two buckets. This is a significant regression in granularity.
- **accel-300 is BLOCKED by SIGNAL_SOURCE_BLACKLIST** (line 441-442 of hermes_constants.py) — it's in the NEVER_REENABLE list. Boosting a dead signal does nothing.

**Assessment:** Use the existing chop_detector._classify_signal() for family classification, and align with its categorizations. Or better yet, use volatility_gate_v2.py's existing per-family multipliers instead of inventing a new system.

---

## 3. ATR Measurement Assessment — CRITICAL BUG

**Rating: 🔴 FATAL — Wrong Data Source**

The plan's code snippet (lines 118-128) queries:
```python
SELECT price_acceleration FROM token_speeds WHERE token='BTC'
```

Then normalizes it:
```python
_atr_ratio = abs(_vol_row[0]) / 0.001  # normalize to average
```

**This is wrong. `price_acceleration` is NOT a volatility proxy.**

From speed_tracker.py, `price_acceleration` = velocity_now - velocity_prior. It measures whether price is speeding up or slowing down — the *derivative of velocity*, not the *magnitude of price movement*.

Current BTC values:
- `price_acceleration`: 0.0014 (nearly zero — price velocity is flat)
- Actual ATR(14) as %: 0.3087%
- If the plan's code ran now: `_atr_ratio = abs(0.0014) / 0.001 = 1.4` → classified as NORMAL

But the real ATR ratio depends on what the 500-bar average is. The plan would compute a meaningless number because acceleration magnitude has no relationship to volatility magnitude.

**The plan should use the existing `get_atr_pct()` function from volatility_gate_v2.py**, which computes proper ATR(14) from 1h candles:
```python
from volatility_gate_v2 import get_atr_pct, classify_volatility
atr_pct = get_atr_pct('BTC')
```

Or better: use the existing `classify_volatility()` which already returns FLAT/NORMAL/HIGH/EXTREME regimes.

**Assessment:** The implementation uses the wrong field entirely. This would produce random multipliers unrelated to actual volatility. Fatal bug.

---

## 4. Conflict Check with Existing Systems — CRITICAL DUPLICATION

**Rating: 🔴 MAJOR DUPLICATION with volatility_gate_v2.py**

The existing `volatility_gate_v2.py` already implements:

| Feature | Existing (vol_gate_v2) | Plan |
|---------|----------------------|------|
| Volatility classification | FLAT/NORMAL/HIGH/EXTREME from ATR% | EXPANSION/NORMAL/COMPRESSION from ATR ratio |
| Regime-based signal gating | ✅ Per-signal allowlists per regime | ❌ None — just multipliers |
| Phase-aware multipliers | ✅ 15+ (regime,phase) combinations | ❌ 2 buckets (MOMENTUM/MEAN_REVERSION) |
| Per-signal-family multipliers | ✅ Bollinger, Momentum, Range, etc. | ❌ Binary split |
| Combined multiplier engine | ✅ vol_phase × lifecycle × inverse | ❌ Single multiplier |
| Integration in compactor | ✅ Already at lines 1391-1463 | Adds separate block |

The plan proposes adding a **second, independent volatility regime system** that:
1. Uses different thresholds (ratio-based vs absolute)
2. Uses different classifications (3 regimes vs 4)
3. Uses different data sources (price_acceleration vs ATR%)
4. Produces different multipliers (per-family vs binary)

**This will create contradictory signals.** volatility_gate_v2 might classify BTC as FLAT (ATR < 0.48%) while the plan's system classifies it as EXPANSION (ATR ratio > 1.5x). The signal would receive both a 0.6x penalty (from V2's FLAT regime) and a 1.3x boost (from the plan's EXPANSION) — net ~0.78x, which is wrong in both directions.

**Additionally:**
- The plan's chop gate relaxation (`chop_threshold * 0.5` during expansion) conflicts with BTC_CHOP_GATE_ENABLED. The chop gate is already in log-only mode (CHOP_GATE_LOG_ONLY = True). Relaxing it during expansion means momentum signals pass the chop gate even when BTC is flat — the exact opposite of the chop gate's purpose.
- The plan adds ~25 lines to signal_compactor.py AFTER the chop gate check. But volatility_gate_v2 already runs its multiplier at lines 1391-1463 of the same function. Two competing multipliers on the same signal = unpredictable behavior.

**Assessment:** This duplicates volatility_gate_v2.py's functionality with a worse implementation. The correct approach is to extend vol_gate_v2, not add a parallel system.

---

## 5. False Positive Analysis

**Rating: 🔴 NO DATA PROVIDED**

The plan claims "ATR ratio > 1.5x is conservative" but provides:
- Zero backtest data showing how often ATR > 1.5x occurs
- Zero data on the distribution of ATR ratios
- Zero data on whether expansion periods actually produce better signal performance
- The "Evidence from Last 24h" section shows 3 data points — this is anecdotal, not statistical

From the actual BTC data:
- Current ATR(14) as %: 0.3087%
- This falls in the FLAT regime of vol_gate_v2 (ATR < 0.48%)
- But the plan's ratio-based system might classify it differently depending on the average

Without knowing the ATR distribution, we can't determine:
- How often EXPANSION triggers (could be 5% of the time or 50%)
- Whether the boost multiplier actually improves outcomes
- Whether the penalties during COMPRESSION hurt more than they help

**Assessment:** The plan's "Expected Impact" table (lines 149-158) shows projected PnL improvements (+$0.66/day) with zero backtest data. This is speculation, not analysis. The testing plan (lines 186-189) starts with "LOG-ONLY (48h)" which is the right approach, but the plan should not be approved for implementation until the thesis is validated with existing data.

---

## 6. Implementation Review

**Rating: 🔴 Multiple Bugs**

### Bug 1: Wrong Data Source (Fatal)
```python
_vol_row = _vol_conn.execute(
    "SELECT price_acceleration FROM token_speeds WHERE token='BTC'"
).fetchone()
```
`price_acceleration` is velocity derivative, not volatility. See Section 3.

### Bug 2: Magic Number Normalization
```python
_atr_ratio = abs(_vol_row[0]) / 0.001  # normalize to average
```
The denominator 0.001 is arbitrary. There's no justification for this value. The current BTC price_acceleration is 0.0014, so this would produce ratio=1.4. But for a token with acceleration=0.005, ratio=5.0. These numbers have no economic meaning.

### Bug 3: Connection Leak Risk
```python
_vol_conn = sqlite3.connect(RUNTIME_DB, timeout=5)
_vol_row = _vol_conn.execute(...)
_vol_conn.close()
```
If the `.execute()` throws, `.close()` is never called. Should use try/finally:
```python
try:
    _vol_conn = sqlite3.connect(RUNTIME_DB, timeout=5)
    ...
finally:
    if _vol_conn:
        _vol_conn.close()
```

### Bug 4: Silent Exception Swallowing
```python
except Exception:
    pass
```
This catches ALL exceptions including SyntaxError, ImportError, etc. Should be:
```python
except Exception as e:
    log(f"  [WARN] Volatility regime check failed: {e}", 'WARN')
```

### Bug 5: Undefined Variable
```python
if signal_family == 'MOMENTUM':
```
`signal_family` is never defined in the code snippet. The plan says to add this after the chop gate check, but there's no import or computation of `signal_family`. It would need to call `chop_detector._classify_signal(signal_type)` or similar.

### Bug 6: Chop Gate Relaxation Conflicts
```python
if regime == 'EXPANSION':
    chop_threshold = BTC_CHOP_GATE_THRESHOLD * 0.5  # relax by 50%
```
The BTC chop gate (lines 1094-1125 of signal_compactor.py) already has its own logic. This relaxation would need to be integrated INTO the chop gate check, not applied separately. As written, it modifies a local variable that's never used by the chop gate.

---

## Overall Verdict

### 🔴 **NO-GO**

**Reasons:**

1. **Fatal data bug:** Uses `price_acceleration` (velocity derivative) instead of ATR (volatility measure). The entire system would compute meaningless multipliers.

2. **Major duplication:** volatility_gate_v2.py already implements regime-based signal adaptation with per-signal-family multipliers, phase awareness, and combined multiplier engines. The plan reinvents this worse.

3. **Conflicting systems:** Running both vol_gate_v2 and this plan's system simultaneously produces contradictory multipliers on the same signal.

4. **No validation data:** Zero backtests, zero distribution analysis, zero proof that the thresholds are meaningful.

5. **Multiple code bugs:** Undefined variables, connection leaks, silent exception swallowing, magic numbers.

### What Should Happen Instead

1. **Extend volatility_gate_v2.py** — add EXPANSION/COMPRESSION as additional classifications or modify the existing FLAT/HIGH thresholds to use ratio-based detection.

2. **Use proper ATR data** — call `get_atr_pct('BTC')` from volatility_gate_v2, not `price_acceleration` from token_speeds.

3. **Backtest first** — Query 30 days of ATR data, compute the ratio distribution, and validate that different ratio ranges produce different signal win rates.

4. **Integrate, don't duplicate** — Add the ratio-based detection to the existing VOL_PHASE_MULTS matrix in volatility_gate_v2.py, which already has the per-signal-family granularity.

5. **Fix the signal family classification** — Use chop_detector._classify_signal() which has the correct pump-chain = MEAN_REVERSION classification.

### Confidence Level

**HIGH (90%)** — The data source bug is verifiable (price_acceleration ≠ ATR), the duplication is verifiable (vol_gate_v2 already does this), and the code bugs are syntactically verifiable. The only uncertainty is whether the plan's author intended to use a different field and made a mistake, or genuinely believes price_acceleration is a volatility proxy.

---

## Appendix: BTC Current State

| Metric | Value | Source |
|--------|-------|--------|
| price_acceleration | 0.0014 | token_speeds |
| ATR(14) as % | 0.3087% | candles_1h |
| Volatility regime (vol_gate_v2) | FLAT | ATR < 0.48% |
| Plan's regime (if it worked) | NORMAL | abs(0.0014)/0.001 = 1.4 |
| Actual regime needed | FLAT/COMPRESSION | Low ATR = range-bound |

The plan would classify current BTC as NORMAL (ratio 1.4) while the actual ATR says FLAT. This demonstrates the data source bug in practice.
