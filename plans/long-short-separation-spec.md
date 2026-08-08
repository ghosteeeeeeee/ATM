# LONG/SHORT Signal Separation Spec

**Date**: 2026-08-08
**Status**: IMPLEMENTED — awaiting CEO input and testing
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

## Implementation Status

### Completed
- [x] Created `ma_100_cross_short.py` with SHORT-specific params
- [x] Created `ma_100_cross_long.py` with LONG-specific params
- [x] Verified syntax
- [x] Committed to git

### Pending
- [ ] Register in `__init__.py`
- [ ] Add SHORT-specific params to `hermes_constants.py`
- [ ] Paper trade for 48h
- [ ] Compare WR with old SHORT
- [ ] Go live if WR improves by 5%+

## Next: vortex_break

After ma_100_cross testing, create:
- `vortex_break_short.py` with:
  - ADX_MIN = 25 (vs 20)
  - REQUIRE_EMA_CONFIRM = True
  - MIN_SPREAD_PCT = 0.3
- `vortex_break_long.py` with current params

---

## CEO Recommendations (2026-08-09 10:20)

### Verified SHORT Performance (7d, signal_outcomes DB)

| Signal | Trades | PnL | WR | Status |
|--------|--------|-----|----|--------|
| vortex_break_short | 2 | +$0.10 | 100% | GOOD — don't touch |
| tl_break_short | 5 | +$0.22 | 80% | GOOD |
| ma100-cross-,vortex_break_short | 4 | -$0.14 | 25% | BAD — legacy combo |
| vel-hermes- | 58 | -$1.14 | 34.5% | DEAD — killed |
| zscore-rising- | 44 | -$1.37 | 38.6% | DEAD — killed |
| inv-accel-300- | 24 | -$1.62 | 16.7% | DEAD — killed |

**Root cause:** SHORT bleeding is NOT vortex_break/ma_100_cross. It's dead signals (vel-hermes-, zscore-rising-, inv-accel-300-) still appearing in historical combos. These are already killed — trades will age out.

### 1. Should we proceed with paper testing?

**Yes, but only ma_100_cross.** vortex_break SHORT already shows 100% WR (2 trades) — splitting it risks killing a working signal for no gain. The SHORT separation for vortex_break is premature; wait for more data.

### 2. SHORT-specific parameters — assessment

| Param | Spec Value | Recommendation | Reason |
|-------|-----------|----------------|--------|
| ATR confirm | 0.4 | Keep 0.4 | 33% tighter entry = reasonable |
| Stop loss | 1.0% | Use 1.2% (current baseline) | Was 1.0%, widened to 1.2% to fix SL hits. Reverting is regression |
| Confirm candles | 3 | Keep 3 | 50% more confirmation = good |
| Volume ratio | 1.2 | Keep 1.2 | Above-average volume = quality gate |
| Regime spread | 0.3 | Keep 0.3 | Only in strong bearish = good filter |
| Blocked hours | 0-7 UTC | Keep | Low liquidity = avoid |

### 3. Should we separate vortex_break?

**No — defer.** vortex_break SHORT is +$0.10, 100% WR (2 trades). The 25% WR cited in the spec is from the `ma100-cross-,vortex_break_short` compound, not standalone. Splitting vortex_break independently risks:
- Breaking the compound that's already killed (MA_100_CROSS_MINUS=False)
- Adding complexity for a signal that's already working

**When to revisit:** If vortex_break SHORT reaches 10+ trades and WR drops below 50%.

### 4. Concerns

1. **Compactor integration missing** — new signal names (`ma_100_cross_long`, `ma_100_cross_short`) need whitelist in signal_compactor.py or they'll be blocked by the disabled-component bug
2. **No individual kill switch** — if `ma_100_cross_short` underperforms, can't disable without killing all of ma_100_cross
3. **Backward compatibility** — keeping `ma_100_cross.py` means both old and new can fire simultaneously

### Recommended Path

1. **Complete ma_100_cross registration** — add to `__init__.py` with current params (don't change SL yet)
2. **Skip vortex_break separation** — wait for more SHORT data
3. **Paper trade 48h** with ma_100_cross_long/short only
4. **If SHORT WR improves by 5%+**, tighten SL to 1.0% and expand to other signals
