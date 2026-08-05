# rs.py Proximity Threshold — Diagnostic Pattern

## Problem
RS signals not firing despite fresh price_history data. The proximity gate (RS_PROXIMITY_K) is rejecting all levels.

## Root Cause
RS_PROXIMITY_K=0.7 is too tight for low-ATR tokens. For AAVE (ATR%=0.015%), 0.7 ATR = 0.011% of price ≈ $0.007 in price units. Swing levels from historical data are naturally 7–100+ ATR away.

## Diagnostic Query
```python
# Run this to find the blocking factor for any token
candles = rs._get_candles_1m(token, lookback=rs.RS_LOOKBACK_CANDLES)
price = candles[-1]['close']
atr = rs._atr(candles, 30)
sh, sl = rs._find_swing_highs_lows(candles, rs.RS_LEVEL_LOOKBACK)
all_levels = [float(l) for _, l in sl] + [float(h) for _, h in sh]
min_dist_atr = min(abs(price - l) for l in all_levels) / atr
print(f"Closest level: {min_dist_atr:.1f} ATR (threshold: {rs.RS_PROXIMITY_K})")
```

## Three Data Sources in signals_hermes.db
| Table | Used By | Freshness |
|-------|---------|-----------|
| `price_history` | rs.py (`_get_candles_1m`) | Varies by token (0.3min–stale) |
| `latest_prices` | `get_all_latest_prices()` | All 230 tokens fresh |
| `ohlcv_1m` | `get_ohlcv_1m()` in signal_schema | Stale/empty |

Note: `get_all_latest_prices()` returns 230 tokens from `latest_prices`, but rs.py only processes tokens whose `price_history` is <2min old. Many tokens in prices_dict are excluded by the freshness guard in `_get_candles_1m`.

## Threshold Reference
- RS_PROXIMITY_K=0.7: level must be within 0.7 ATR of price
- At ATR%=0.015% (AAVE): 0.7 ATR = 0.0105% of price ≈ $0.007
- Typical min_dist for swing levels: 5–100 ATR (far above threshold)
