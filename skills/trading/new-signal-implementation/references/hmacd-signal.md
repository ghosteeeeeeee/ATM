---
name: hmacd-signal
description: "HMACD signal — standalone histogram-MACD scanner. Fires hmacd+ (LONG) or hmacd- (SHORT) when 15m AND 1H MACD histograms agree in direction."
category: signals
---

# HMACD Signal — Implementation Reference

**File:** `/root/.hermes/scripts/signals/hmacd.py`
**Extracted from:** `signal_gen.py` `_run_mtf_macd_signals()` lines 1627–1639
**Signal type:** `hmacd` | **Source tags:** `hmacd+`, `hmacd-`

## Signal Logic

```
hmacd+ = LONG  (15m hist > 0 AND 1H hist > 0)  # both TFs bullish
hmacd- = SHORT (15m hist < 0 AND 1H hist < 0)  # both TFs bearish
```

**Key simplification vs. MTF-MACD:** No z-score gate. Pure histogram agreement across two TFs.
The full MTF-MACD (signal_gen.py) layered z-score filtering on top. The hmacd signal
fires on histogram alignment alone — simpler, more frequent fires.

## MACD Computation

`_macd_crossover(token, minutes)` internal helper:

1. Fetch `minutes * 40` raw 90-sec candles from `signals_hermes.db`
2. Aggregate into target-TF candles (OHLC bucketing by timestamp)
3. Compute EMA(fast), EMA(slow) → `macd_line = fast_ema - slow_ema`
4. Compute EMA(signal) of MACD line → `signal_line`
5. Return `(histogram, macd_line, signal_line)` where `histogram = macd_line - signal_line`

Per-token tuned params via `get_macd_params(token)` from `macd_rules.py`:
- Falls back to `MACD_PARAMS['DEFAULT']` = `{fast: 12, slow: 55, signal: 15}` for unknown tokens

## Token Loop Skip Conditions (same as signal_gen.py)

```python
token.startswith('@')          # skip numeric coin IDs
price_age_minutes(token) > 10   # skip stale prices
not data.get('price')           # skip missing prices
token.upper() in open_pos       # skip if already in position
recent_trade_exists(token)      # skip if traded recently
token.upper() in SHORT_BLACKLIST # skip meme coins for SHORT
is_delisted(token.upper())      # skip delisted/halted tokens
is_reasonable_price(token, price)  # skip garbage prices
```

## Directional Gates

```python
HMACD_ENABLED       # master kill switch (hermes_constants.py)
HMACD_PLUS_ENABLED  # LONG direction gate
HMACD_MINUS_ENABLED # SHORT direction gate
```

## Constants

```python
Z_MACD_THRESH = 2.0  # defined but NOT used in hmacd.py (z-score gate stripped)
MIN_TRADE_INTERVAL_MINUTES = 15
```

## Signal Fields

```python
add_signal(
    token=token,
    direction=direction,        # 'LONG' or 'SHORT'
    signal_type='hmacd',
    source=f'hmacd-{+/-}',     # 'hmacd+' or 'hmacd-'
    confidence=min(80.0, 50 + avg_hist * 50),
    value=round(avg_hist, 6),
    price=float(price),
    exchange='hyperliquid',
    timeframe='15m_1h',
    macd_hist=avg_hist,
)
```

## Guard Helpers (self-contained)

```python
_recent_trade_exists(token, minutes)  # reads recent_trades.json
is_delisted(token)                   # wraps hyperliquid_exchange.is_delisted
is_reasonable_price(token, price)    # rejects price < 0.0001
SHORT_BLACKLIST = {'MEME', 'PEPE', 'SHIB', 'DOGE', ...}
```

## Related

- `signals/macd_1m.py` — per-token tuned 1m MACD, fires `macd_long_1m` / `macd_short_1m`
- `signals/macd_accel.py` — MACD acceleration signal
- `references/mtf-macd-backtest-findings.md` — full MTF-MACD backtest (z-score gated version)
- `signals/hmacd.py` — this signal
