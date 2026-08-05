# Hyperliquid Position API — Return Shapes & Gotchas

Quick reference for the actual return shapes of HL position-fetching helpers. The function names
mislead — they sound like they return lists but most return dicts keyed by coin.

## `get_open_hype_positions_curl()` — Dict keyed by coin (NOT list)

**File:** `hyperliquid_exchange.py` line 467+
**Returns:** `{coin_symbol: {size, direction, entry_px, unrealized_pnl, leverage}, ...}`

```python
# WRONG — throws "'str' object has no attribute 'get'"
hl = get_open_hype_positions_curl()
for p in hl:
    coin = p.get("token")        # ❌ p is a string (coin name)

# RIGHT — iterate .items() or .keys()
hl = get_open_hype_positions_curl()
hl_tokens = set(hl.keys())       # set of coin names
for coin, pos in hl.items():     # pos is the record dict
    sz = pos.get("size")
    direction = pos.get("direction")      # "LONG" | "SHORT"
    entry_px = pos.get("entry_px")        # float | None (None when HL returns null)
    pnl = pos.get("unrealized_pnl")       # float
    lev = pos.get("leverage")             # int
```

**When `entry_px` is None:** HL returned `null` (not 0). The function deliberately preserves
None so callers can fall back to trade history or DB value. Never write 0 as a sentinel —
`float(None or 0) = 0.0` overwrites real entry prices with 0 and corrupts PnL.

## `hype_cache.get_allMids()` — Dict of mids

**Returns:** `{coin_symbol: price_str, ...}` — values are STRINGS from HL, cast to float yourself.

## Known-bad pattern (WASP 2026-07-13)

WASP's `check_paper_hl_sync()` at `wasp.py:777` originally did:
```python
hl_positions = get_open_hype_positions_curl()
hl_tokens = {p.get("token") for p in hl_positions if p.get("token")}
```
This iterates dict keys (strings), so `p.get("token")` throws `'str' object has no attribute 'get'`.
Fix: `hl_tokens = set(hl_positions.keys())`.

## Diagnostic snippet

```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_hype_positions_curl
hl = get_open_hype_positions_curl()
print(f"Type: {type(hl).__name__}, keys: {list(hl.keys())[:5]}")
for coin, pos in list(hl.items())[:3]:
    print(f"  {coin}: {pos}")
```