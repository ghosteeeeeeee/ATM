# ema_angle prices_dict Bug — 2026-05-15

## Bug Summary

**Symptom:** ema_angle fires 14-19 signals when called standalone, but 0 through `run_all_signals()` automated pipeline. No exception, silent failure.

**Root cause:** `scan_ema_angle_signals()` was trying to use `prices_dict` from `get_all_latest_prices()` as a price history input. It only has `{TOKEN: {'price': float}}` — a single current price per token, not a 500-bar history. `detect_ema_angle()` receives a single float, fails `len(prices) < EMA_ANGLE_MIN_BARS` (500 required), returns `None` for every token.

## Type Mismatch

```python
get_all_latest_prices()  # → dict[str, dict[str, float]]
# Example: {'BTC': {'price': 80965.5}, 'ETH': {'price': 1842.3}}
# NOT: {'BTC': [(ts, close), ...]}  ← what signals need for indicator computation
```

## Fix

**File:** `ema_angle.py` lines 340-345

Remove the `prices_dict` branch — always call `_get_1m_prices(token)` which reads 500 bars from `candles.db` directly:

```python
# WRONG — prices_dict only has {token: {'price': float}}, not 500-bar history:
if prices_dict and token in prices_dict:
    price = prices_dict[token].get('price')
    # ... detect_ema_angle(token, price) → len(price) < 500 → always None

# RIGHT — always fetch own candle history:
candles = _get_1m_prices(token)  # reads from candles.db, 500 bars
# ... detect_ema_angle(token, candles) → works correctly
```

## Why accel_300 Doesn't Have This Bug

`accel_300.scan_accel_300_signals()` loop calls `_get_1m_prices(token)` inside its `for token in tokens` loop — ignores `prices_dict` entirely. Every token fetches its own 500-bar history from candles.db. ema_angle was the only signal trying to use `prices_dict` as a price history input.

## Prevention Rule

Any signal that computes a derived indicator (EMA, MACD, RSI, angle, slope) requiring warmup bars must fetch its own candles from `candles.db` inside its per-token loop — never use `prices_dict` as a price series.

```python
def scan_xxx_signals(prices_dict: dict, **kwargs):
    for token in prices_dict:
        # Always fetch own history from candles.db
        candles = _get_1m_prices(token)  # or _get_5m_candles, etc.
        if len(candles) < MIN_BARS:
            continue
        # detect_xxx(token, candles) ← use the candle array, not prices_dict[token]
```

## Verification

```python
from signals import get_registered_signals, run_all_signals

# Clear in-memory cooldown cache
from signals.ema_angle import _last_signal_ts
_last_signal_ts.clear()

# Test via run_all_signals (was returning 0):
ema_signals = [s for s in get_registered_signals() if s['name'] == 'ema_angle']
results = run_all_signals(signal_list=ema_signals)
# Before fix: {'ema_angle': 0}
# After fix:  {'ema_angle': 19}
```

Also verified: `ema_angle.scan_ema_angle_signals(None)` (no prices_dict) returns 19 signals.

## Related Bugs

- Bug 17 (same session): ema_angle `abs()` made all angles positive — SHORT never fired. Fix: `math.atan(slope_n / ema_val)` (remove abs).
- Bug 1: accel-300- SHORT blocked by symmetric `gap_now < MIN_GAP_PCT` — fix was `abs(gap_now) < MIN_GAP_PCT`.