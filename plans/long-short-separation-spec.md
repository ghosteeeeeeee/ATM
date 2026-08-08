# LONG/SHORT Signal Separation Spec

**Date**: 2026-08-08
**Status**: Ready for implementation
**Priority**: HIGH — improving SHORT WR from 40% to 50%+

## Problem

Current architecture uses single files for both LONG and SHORT:
- Same parameters for both directions
- Can't tune independently
- SHORT signals dragging WR (25-40% vs LONG 73%)

## Solution

Create separate files for LONG and SHORT with direction-specific parameters.

## Files to Separate

### Priority 1: HIGH (biggest performance gap)

| Signal | LONG WR | SHORT WR | Gap | File |
|--------|---------|----------|-----|------|
| ma_100_cross | 75% | 40% | +35% | ma_100_cross.py |
| vortex_break | 75% | 25% | +50% | vortex_break.py |

### Priority 2: MEDIUM

| Signal | LONG WR | SHORT WR | Gap | File |
|--------|---------|----------|-----|------|
| hzscore | 66% | 50% | +16% | hzscore.py |
| range_finder | 50% | 42% | +8% | range_finder.py |

## Implementation: ma_100_cross

### Current (ma_100_cross.py)
```python
# Same params for both directions
MA_PERIOD = 20
CROSS_CONFIRM_ATR = 0.3
MIN_ATR_PCT = 0.04
```

### New: ma_100_cross_short.py
```python
# SHORT-specific params
MA_PERIOD = 20
CROSS_CONFIRM_ATR = 0.4        # Wider entry (was 0.3)
MIN_ATR_PCT = 0.05             # Higher vol requirement (was 0.04)
STOP_LOSS_PCT = 1.0            # Tighter stop (was 1.2%)
CONFIRMATION_CANDLES = 3       # More confirmation (was 2)
MIN_VOLUME_RATIO = 1.2         # Volume above average
MAX_REGIME_SPREAD = 0.3        # Only in strong BEARISH
```

### New: ma_100_cross_long.py
```python
# LONG-specific params (keep current)
MA_PERIOD = 20
CROSS_CONFIRM_ATR = 0.3
MIN_ATR_PCT = 0.04
STOP_LOSS_PCT = 1.2
CONFIRMATION_CANDLES = 2
```

## Implementation: vortex_break

### New: vortex_break_short.py
```python
# SHORT-specific params
VORTEX_PERIOD = 14
ADX_MIN = 25                   # Higher ADX (was 20)
EMA_FAST = 20
EMA_SLOW = 50
REQUIRE_EMA_CONFIRM = True     # Must be below both EMAs
MIN_SPREAD_PCT = 0.3           # Minimum EMA spread
```

### New: vortex_break_long.py
```python
# LONG-specific params (keep current)
VORTEX_PERIOD = 14
ADX_MIN = 20
EMA_FAST = 20
EMA_SLOW = 50
```

## SHORT-Specific Improvements

### 1. Higher Entry Threshold
```python
# SHORT needs stronger signal to enter
CROSS_CONFIRM_ATR = 0.4  # vs 0.3 for LONG
ADX_MIN = 25             # vs 20 for LONG
```

### 2. Tighter Stop Loss
```python
# Protect against quick reversals
STOP_LOSS_PCT = 1.0  # vs 1.2% for LONG
```

### 3. Volume Confirmation
```python
# Require above-average volume
MIN_VOLUME_RATIO = 1.2  # Volume must be 1.2x average
```

### 4. Regime Filter
```python
# Only SHORT in confirmed BEARISH
MAX_REGIME_SPREAD = 0.3  # EMA spread must be > 0.3%
```

### 5. Time Filter
```python
# Avoid Asian session (low liquidity)
BLOCKED_HOURS = [0, 1, 2, 3, 4, 5, 6, 7]  # 00:00-07:59 UTC
```

## File Structure

```
signals/
├── ma_100_cross.py          # Keep for backward compatibility
├── ma_100_cross_long.py     # NEW: LONG-specific
├── ma_100_cross_short.py    # NEW: SHORT-specific
├── vortex_break.py          # Keep for backward compatibility
├── vortex_break_long.py     # NEW: LONG-specific
├── vortex_break_short.py    # NEW: SHORT-specific
```

## Registration

### __init__.py
```python
from signals.ma_100_cross_long import run as _ma_100_cross_long_run
from signals.ma_100_cross_short import run as _ma_100_cross_short_run
from signals.vortex_break_long import run as _vortex_break_long_run
from signals.vortex_break_short import run as _vortex_break_short_run

_SIGNALS = {
    'ma_100_cross_long': {..., 'run': _ma_100_cross_long_run},
    'ma_100_cross_short': {..., 'run': _ma_100_cross_short_run},
    'vortex_break_long': {..., 'run': _vortex_break_long_run},
    'vortex_break_short': {..., 'run': _vortex_break_short_run},
}
```

### hermes_constants.py
```python
# SHORT-specific params
MA_100_CROSS_SHORT_ATR_CONFIRM = 0.4
MA_100_CROSS_SHORT_MIN_ATR = 0.05
MA_100_CROSS_SHORT_STOP_LOSS = 1.0
MA_100_CROSS_SHORT_CONFIRM_CANDLES = 3
MA_100_CROSS_SHORT_MIN_VOLUME = 1.2
MA_100_CROSS_SHORT_MAX_REGIME = 0.3
MA_100_CROSS_SHORT_BLOCKED_HOURS = [0,1,2,3,4,5,6,7]

VORTEX_BREAK_SHORT_ADX_MIN = 25
VORTEX_BREAK_SHORT_REQUIRE_EMA = True
VORTEX_BREAK_SHORT_MIN_SPREAD = 0.3
```

## Testing Plan

1. **Paper trade new SHORT scripts** for 48h
2. **Compare WR** with old SHORT scripts
3. **If WR improves by 5%+**, go live
4. **If not**, adjust parameters

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| SHORT WR | 40% | 50%+ |
| Overall WR | 55% | 60%+ |
| PnL | +$0.33/48h | +$1.00/48h |
