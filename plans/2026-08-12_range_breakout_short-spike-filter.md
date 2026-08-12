# range_breakout_short Spike Filter Fixes

**Date:** 2026-08-12
**Status:** CEO APPROVED — IMPLEMENTING

## Problem
TIA and CFX SHORT losses: signal entered at spike highs after strong bullish 5m candles. Velocity filter was blind because spike happened 7-8min before signal time, outside its 5min window.

## Fixes (3 layers)

### Fix 1: Tighten velocity lookback
- Change `LIMIT 6` to `LIMIT 12` in velocity filter and spike exhaustion filter
- Covers ~10min instead of ~5min
- Catches spikes 7-8min old

### Fix 2: Enable RSI filter
- `RSI_SHORT_MIN = 0` → `RSI_SHORT_MIN = 40`
- Don't short when RSI is already low (bounce risk)

### Fix 3: 5m candle momentum check (highest impact)
- Check last 3 5m candles from candles.db
- If any had bullish close > 0.2%, block SHORT entry
- Directly catches "spike then consolidate" pattern

## Files
- `scripts/signals/range_breakout_short.py` — all 3 fixes
