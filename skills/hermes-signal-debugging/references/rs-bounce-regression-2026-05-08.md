# RS Signal Regression — May 8 2026 Session

## Context
T asked to review the RS signals system. They said "be careful it was working really well, so don't break it unnecessarily" and "we need to fix RS signals they added real context to other signals."

RS signals provide structural context (support/resistance) that significantly improves confluence when paired with momentum signals (accel-300+). Historical data: `accel-300+,rs-s16-150` combos = 100% WR, +343% avg peak.

## Problem
RS signals dropped from ~100-119/cycle (May 6) to near-zero today (6 signals in 17.5 hours).

## Root Cause: `_bounce_confirmation` logic was replaced between commits

The original RS signal (`rs_signals.py` committed at d31692f, Apr 28) had a single-candle bounce check:
- Price wick (`low` for support, `high` for resistance) touched level within 0.20%
- THAT candle's close > open (bullish for LONG, bearish for SHORT)
- → Bounce confirmed

The current canonical implementation (`signals/rs.py`) replaced this with a two-candle sequential requirement:
- Price `close` must be within ATR-distance of level
- The NEXT candle must close >0.05% in signal direction
- → Much harder to satisfy in ranging/choppy markets

## What Changed

### Original (d31692f, rs_signals.py lines 154-183)
```python
def _bounce_confirmation(candles: list, level: float, direction: str,
                          lookback: int = _BOUNCE_LOOKBACK) -> bool:
    if direction == 'LONG':
        for c in recent:
            touch_pct = abs(c['low'] - level) / level * 100.0
            if touch_pct < 0.20:        # wick touched level
                if c['close'] > c['open']:  # bullish candle → bounce
                    return True
    else:  # SHORT
        for c in recent:
            touch_pct = abs(c['high'] - level) / level * 100.0
            if touch_pct < 0.20:
                if c['close'] < c['open']:  # bearish candle → rejection
                    return True
```

### Current (signals/rs.py lines 174-219)
```python
def _bounce_confirmation(candles, level, direction, atr_value=None, lookback=6):
    thresh = _BOUNCE_THRESH_ATR * atr_value  # 0.20 × ATR
    if len(candles) < lookback:
        return False
    recent = candles[-lookback:]
    
    if direction == 'LONG':
        for i, c in enumerate(recent):
            if abs(c['close'] - level) < thresh:  # close at level (not wick!)
                if i + 1 < len(recent):
                    next_close = recent[i + 1]['close']
                    if next_close > c['close'] * 1.0005:  # next candle +0.05%+
                        return True
```

## Why It Broke

1. **Touch detection changed**: `low` (wick) → `close` (price convergence). With close-only candles (synthesized from 1-min ticks where open=high=low=close), the new condition only fires when price has actually settled AT the level, not just brushed it with a wick.

2. **Direction check changed**: `c['close'] > c['open']` (the same candle's direction) → `next_close > c['close'] * 1.0005` (the NEXT candle must move >0.05%). In a ranging market (current BTC), price touches the level, the next candle goes flat, and bounce=False.

3. **Combined effect**: BTC was ranging (79,400-80,200). Price touched level 79821.50 (diff=2.0 < thresh=4.33 ✓) but next candle only moved +2.0 units → rejected. No candle in 6-lookback satisfied the 39.9-unit (0.05%) threshold.

## Historical Behavior (May 6 — Working)
```
Signal rs: (2, [('BTC', 'LONG', 88, 'rs-s43'), ('ETH', 'SHORT', 75, 'rs-r16'), ('SOL', 'LONG', 86, 'rs-s430')])
Signal rs: (3, [('BTC', 'SHORT', 71, 'rs-r214'), ('ETH', 'LONG', 68, 'rs-s9'), ('ORDI', 'SHORT', 74, 'rs-r515')])
Signal rs: (2, [('BTC', 'LONG', 90, 'rs-s46'), ('ETH', 'LONG', 85, 'rs-s9')])
```
~100-119 RS signals per cycle on May 6. Today: 0 signals per cycle for 14+ hours.

## Key Constants in signals/rs.py
- `_BOUNCE_LOOKBACK = 6` (candles to check)
- `_BOUNCE_THRESH_ATR = 0.20` (ATR multiplier for touch threshold)
- `RS_PROXIMITY_K = 1.20` (level proximity in ATR units)
- `RS_MIN_TOUCHES = 3` (minimum level touches to qualify)

## Fix Recommendation
Given T's explicit warning ("be careful, it was working really well"), Option B (hybrid) is recommended:
- Keep the close-touch detection (more conservative — price must be at the level)
- Restore the single-candle directional check (the original behavior that fired on May 6)

This would make `bounce` easier to confirm in ranging markets while keeping the tighter "price must be at level" requirement.

## Verification Pattern
```python
# Test before/after from /root/.hermes/scripts
import sys; sys.path.insert(0, '.')
from signal_schema import get_all_latest_prices, init_db
from signals.rs import scan_rs_signals
init_db()
prices = {k: v for k, v in get_all_latest_prices().items() if k in ('BTC','ETH','SOL','AVAX')}
added, tokens = scan_rs_signals(prices)
print(f'added={added}, tokens={tokens}')
# Target: added >= 3 for the 4-token test set
```

## Related Bugs Fixed in Prior Sessions
- `_level_recently_broken` always False (open==close on synthesized candles)
- `_bounce_confirmation` off-by-one guard (`lookback+1` should be `lookback`)
- `high_touch` unused variable in `_build_level_touches`

## Files
- Canonical RS: `/root/.hermes/scripts/signals/rs.py`
- Deprecated RS: `/root/.hermes/scripts/rs_signals.py` (552 lines, original d31692f)
- Pipeline: `/root/.hermes/logs/pipeline.log`
- Runtime DB: `/root/.hermes/data/signals_hermes_runtime.db`