# HH_HL Signal — Unit Mismatch Bug (2026-05-09)

## Bug: breakout_strength vs HH_HL_BREAKOUT_THRESHOLD unit mismatch

**Severity: Critical — silently allowed weak breakouts to pass**

### Root Cause

In `hh_hl.py` `_detect_breakout()`, line 236:
```python
if structure == 'HH_HL' and breakout_strength >= HH_HL_BREAKOUT_THRESHOLD:
```

- `breakout_strength` is returned by `_classify_structure()` in **percent units** (e.g., `0.014 = 0.014%`)
- `HH_HL_BREAKOUT_THRESHOLD = 0.0005` is defined in **decimal fraction** (= 0.05%)
- Comparison `0.014 >= 0.0005` is always True for any breakout > 0%

This means any token within 0.0005 decimal fraction (= 0.05%) of a swing level would fire, regardless of how weak — AAVE at `break=0.014%` was passing when it needed `0.050%`.

### The Fix

Normalize to same units before comparing:
```python
if structure == 'HH_HL' and (breakout_strength / 100) >= HH_HL_BREAKOUT_THRESHOLD:
```
and:
```python
elif structure == 'LH_LL' and (breakout_strength / 100) >= HH_HL_BREAKOUT_THRESHOLD:
```

### Symptom

AAVE showed `conf=65%, break=0.014%, bars=5` firing — barely moved, wrong direction. After fix, only genuine 0.05%+ breakouts pass:
```
AVAX  LONG  break=0.050%  conf=66  bars=4  ← first real breakout
INJ   SHORT break=0.088%  conf=65  bars=5
POPCAT LONG  break=0.053%  conf=66  bars=4
SAGA  LONG  break=0.050%  conf=66  bars=4
```

### Lesson

Always verify unit consistency when comparing values from different sources. `0.014 >= 0.0005` is True but conceptually backwards — the debugger saw it but didn't catch it until trace output showed AAVE's 0.014% breakout passing. Check actual values in context, not just the comparison logic.
