# zscore-pump Counter-Regime Quick-Reference (2026-05-17)

## The Bug
zscore_pump.py `allowed_direction()` returned `True` (allow LONG) when regime was DOWN even though the zscore was positive (overbought bounce, not a pump). Result: counter-trend LONGs flooding the hot-set.

## Root Cause
```python
# WRONG (before fix):
return direction in ("BOTH", "LONG") or (direction == "LONG" and regime in ("NEUTRAL", "UP"))

# CORRECT (after fix):
return direction in ("BOTH", "LONG") or (direction == "LONG" and regime in ("NEUTRAL", "UP") and current_z > 0)
```

## Key Lesson
Positive z ≠ bullish for LONG. If regime is DOWN and z is positive, that's an overbought bounce — a SHORT scenario, not LONG. The direction filter must check regime alignment, not just the sign of z.

## See Also
- Full post-mortem: `zscore-pump-counter-trend-2026-05-17.md` in this directory
- Signal implementation: `signals/zscore_pump.py` lines 270-295
