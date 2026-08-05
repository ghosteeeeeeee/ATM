# UMA RS Failure Analysis — June 14, 2026

## The Move
- 19:08 UTC: price = 0.3930 (swing low, bounced here)
- 19:08–22:05 UTC: rallied to 0.4114 (+4.7%)
- Current (~00:22 Jun 15): 0.4098

## Why RS Missed It

### Problem 1: Bounce lookback window too short
- `RS_BOUNCE_LOOKBACK = 6` (6 candles = 6 minutes on 1m data)
- RS only checks last 6 candles for bounce confirmation
- The bounce from 0.3930 happened ~3 hours ago — invisible to a 6-candle window
- **Fix:** increase `RS_BOUNCE_LOOKBACK` to ~200

### Problem 2: Proximity gate too tight
- Level at 0.3930 is 4.1% below current price 0.4098
- ATR(14) on 1m close-only data = 0.000138 (0.034%) — extremely tight
- Distance in ATR terms: 4.1% / 0.034% = **16.8 ATRs**
- `RS_PROXIMITY_K = 0.7` blocks any level beyond ~0.7 ATRs
- **Fix:** `RS_PROXIMITY_K` would need ~25+ (blunt instrument — catches many false levels)

## Root Cause: RS Design vs. This Pattern

RS is designed for: **price near level + recent bounce confirmation**

It cannot detect:
- Levels hit hours ago that bounced, where price has since moved away
- "Broken then recovered" supports where price broke below then reclaimed the level

The broken→recovered reclassify logic (`if broken and price > level`) only fires when `broken=True` at detection time. If the level was broken hours ago and has since recovered, the broken flag may be `False` by the time price is 4% above it.

## Data Source Notes
- `price_history` in `signals_hermes.db` = live 1m data (updated every minute)
- `candles.db` = stale aggregated data (UMA shows prices from April-May at $1.4+)
- `price_history` is **close-only**: `open=high=low=close` for every candle
- Intra-candle wicks cannot be detected

## Diagnostic Commands
```python
# Get live 1m candles
candles = rs._get_candles_1m('UMA', lookback=300)
price = candles[-1]['close']

# Compute ATR
atr = rs._atr(candles)
atr_pct = atr / price * 100

# What k is needed for a level at X?
dist_pct = abs(price - level) / price * 100
k_needed = dist_pct / atr_pct
# if k_needed > RS_PROXIMITY_K, level won't pass proximity gate

# Check bounce confirmation window
bounces = rs._bounce_confirmation(candles, level, 'LONG', atr_value=atr)
# Returns True only if a candle within 0.2*ATR of level
# is followed by a candle with close > level * 1.00025
```

## Status After Fix (June 14 2026)
- Bounce gate restructure: FIXED (both support and resistance sections)
- `RS_BOUNCE_LOOKBACK`: still at 6 — needs human decision to change
- `RS_PROXIMITY_K`: still at 0.7 — blunt change if made
