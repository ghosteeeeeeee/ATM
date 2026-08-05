---
name: hl-trading-utils
description: Quick reference for Hyperliquid trading operations — closing positions, reading open positions, useful imports from hyperliquid_exchange
---
# HL Trading Utils — quick reference for Hyperliquid trading operations

## Closing a position

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import close_position

result = close_position('PENDLE')  # returns {'success': True, 'result': {...}}
```

## Getting open positions

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_hype_positions_curl

positions = get_open_hype_positions_curl()
# Returns: dict[coin_name, position_data]
# e.g. {'BTC': {'size': 0.00014, 'direction': 'SHORT', 'entry_px': 74189.0, ...}}
# NOT a list — key by coin name
```

## Getting realized PnL from fills

```python
from hyperliquid_exchange import get_realized_pnl
from datetime import datetime

# Use open_time from the trade DB row
open_time = datetime(2026, 4, 18, 14, 26, 14)
start_ms = int(open_time.timestamp() * 1000)

hl_data = get_realized_pnl('MOVE', start_ms)
# Returns: {'realized_pnl': 0.121329, 'entry_price': 0.018433, 'exit_price': 0.018654, ...}
```

## Batch order placement — `mirror_open_batch()`

Use for opening multiple positions in a **single API call** (one `/exchange` call for all orders).

```python
from hyperliquid_exchange import mirror_open_batch

tokens = [
    {"token": "HYPE", "direction": "LONG", "entry_price": 12.50, "leverage": 3},
    {"token": "BTC",  "direction": "SHORT", "entry_price": 74000, "leverage": 3},
]
# Pass prices dict to avoid per-token /info fetch — uses local prices instead
prices = {"HYPE": 12.50, "BTC": 74000}
result = mirror_open_batch(tokens, prices=prices)
# Returns: {'success': True, 'placed': 2, 'results': [{'token': 'HYPE', 'success': True, ...}, ...], 'errors': []}
```

**Rate-limit benefit:** 1 shared prices fetch + 1 bulk `/exchange` call vs N×3 API calls per token.

**CRITICAL — Market order format:** HL's `bulk_orders` does NOT accept `{"trigger": {"tpsl": "tp"}}` for open orders — that format is for TP/SL triggers only. For **market opens**, use `{"limit": {"tif": "Ioc"}}` (aggressive Limit IoC, same as SDK's `market_open` internals). `build_order(coin, side, sz, 0, "Market")` now produces the correct format automatically.

**Fallback:** If batch fails, it falls back to per-trade `mirror_open()` automatically.

## ⚠️ HL Fill Identification — Use `dir` field, NOT `side`

HL fill records have both `side` and `dir` fields. **Never use `side` alone to identify open/close fills** — this is the most common bug in HL integration code.

| Position | Open/Close | `side` | `dir`           |
|----------|-----------|--------|-----------------|
| LONG     | Open      | B      | Open Long       |
| LONG     | Close     | A      | Close Long      |
| SHORT    | Open      | A      | Open Short      |
| SHORT    | Close     | B      | Close Short     |

**Correct filter:** `"Open" in f.get("dir", "")` or `"Close" in f.get("dir", "")`

**Wrong filter:** `f["side"] == "A"` or `f["side"] == "B"` — misses LONG closes and SHORT opens

Affected functions in `hyperliquid_exchange.py`:
- `get_realized_pnl()` — open fills: `is_open_fill()`, close fills: `is_close_fill()`
- `mirror_get_exit_fill()` — uses `"Close" in dir`
- `mirror_get_entry_fill()` — uses `"Open" in dir`

## Other useful imports from hyperliquid_exchange

- `place_order` — open a single position
- `mirror_open_batch` — open **multiple** positions in one API call (preferred for batching)
- `cancel_all_open_orders` — cancel all open orders
- `get_exchange` — get exchange instance

## Common errors

- `ModuleNotFoundError: No module named 'hl'` or `hyperliquid_exchange` → need `sys.path.insert(0, '/root/.hermes/scripts')` before the import
- `TypeError: string indices must be integers` from `get_open_hype_positions_curl` → you're treating the dict as a list; it returns `dict[coin, data]`, iterate with `for coin, data in positions.items()`
