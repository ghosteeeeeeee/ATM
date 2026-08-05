# fast_momentum Signal Reference

**Extracted from:** `signal_gen.py` lines 1874–2015 (2026-04-18)
**File:** `/root/.hermes/scripts/signals/fast_momentum.py`
**Signal type:** `fast_momentum`
**Sources:** `fast-momentum+` (LONG), `fast-momentum-` (SHORT)

## Concept

Detects explosive short-term momentum bursts by comparing 5m z-score acceleration against 30m momentum. When the short window shows much stronger momentum than the medium window, it signals a quick move.

**Weight in signal_compactor:** 1.3x (fast-accel tier)

## Key Constants

| Constant | Value | Notes |
|----------|-------|-------|
| `ACCEL_THRESHOLD` | 0.15 | minimum z-acceleration to qualify |
| `MIN_CONFIDENCE` | 62 | minimum confidence to write signal |
| `speed_pctl` threshold | 70 | top 30% universe movers only |
| Lookback | 240 min | 4h of 1m data for z-scores |

## Signal Logic

```
z_5m  = _fast_zscore(prices[-5:])
z_30m = _fast_zscore(prices[-30:]) if len >= 30
z_60m = _fast_zscore(prices[-60:]) if len >= 60

z_accel = z_5m - z_30m
velocity = compute_zscore_velocity(prices, window=30)

LONG:  z_accel > 0.15 AND velocity > 0 AND z_5m < z_60m - 0.1
SHORT: z_accel < -0.15 AND velocity < 0 AND z_5m > z_60m + 0.1
```

Additional confirmation:
- LONG: RSI < 70, MACD histogram ≥ 0
- SHORT: RSI > 45, MACD histogram ≤ 0

## Feature Flags

Imported from `hermes_constants`:
- `FAST_MOMENTUM_ENABLED` — master toggle, return 0 if False
- `FAST_MOMENTUM_PLUS_ENABLED` — gates LONG direction
- `FAST_MOMENTUM_MINUS_ENABLED` — gates SHORT direction

## Helper Functions Extracted

- `_fast_zscore(prices_subset)` — z-score of a price list, None if <5 samples or std=0
- `compute_zscore_velocity(prices, window=240)` — z-score change over window vs prior window
- `get_momentum_stats(token, rows=None)` — returns `{rsi_14, macd_hist}` or None
- `recent_trade_exists(token, minutes)` — checks `recent_trades.json`
- `is_reasonable_price(token, price)` — rejects None, 0, negative, >1M, <0.00001

## Guards Applied

1. `token.startswith('@')` — skip internal tokens
2. `price_age_minutes(token) > 10` — skip stale prices
3. `not data.get('price')` — skip missing prices
4. `token.upper() in open_pos` — skip if position open
5. `recent_trade_exists()` — skip if traded in last 10 min
6. `SHORT_BLACKLIST / LONG_BLACKLIST` — skip if blacklisted
7. `is_delisted()` — skip delisted tokens
8. `speed_pctl < 70` — skip non-top-movers
9. Per-direction `FAST_MOMENTUM_PLUS/MINUS_ENABLED`
10. RSI/MACD confirmation per direction

## Verification

```bash
# Check signals wrote
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, signal_type, confidence, source, created_at \
   FROM signals WHERE signal_type='fast_momentum' ORDER BY created_at DESC LIMIT 5;"

# Syntax check
python3 -m py_compile /root/.hermes/scripts/signals/fast_momentum.py
```
