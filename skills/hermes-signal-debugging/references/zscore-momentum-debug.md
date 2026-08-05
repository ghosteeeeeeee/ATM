---
name: zscore-momentum-debug
description: Debug zscore_momentum emitting 0 signals — wrong data source in _get_latest_prices()
version: 1.0.0
author: Hermes Agent
tags: [debugging, signals, zscore]
metadata:
  hermes:
    related_skills: [hermes-signal-debugging]
---

# zscore_momentum Debugging — Data Source Fix

## Context
`zscore_momentum.py` had `_get_latest_prices()` querying a `token_prices` table that doesn't exist, causing 0 signals to be emitted silently.

## Root Cause
```python
# Broken — table doesn't exist:
cur.execute("SELECT token, price FROM token_prices WHERE price > 0")
```

Other scanners (ma_cross, r2_trend, etc.) use `get_all_latest_prices()` from `signal_schema` instead.

## Fix
```python
# Correct — use signal_schema like all other scanners:
from signal_schema import get_all_latest_prices
prices = get_all_latest_prices()
```

## Verification
```python
from zscore_momentum import _run_zscore_momentum_signals, _get_latest_prices, clear_cache
clear_cache()
prices = _get_latest_prices()
print(f'Tokens with prices: {len(prices)}')  # should be ~190
added = _run_zscore_momentum_signals(prices)
print(f'Signals: {added}')  # should be > 0
```

## Files
- `/root/.hermes/scripts/zscore_momentum.py` — fixed `_get_latest_prices()`
- `/root/.hermes/scripts/signal_gen.py` — import added at line ~2116
