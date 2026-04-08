
## guardian_missing closes bypass signal_outcomes (2026-04-07)

When the guardian detects a trade is missing from HL (ATR SL triggered), it closes the paper trade via `_close_paper_trade_db()` but forgot to call `_record_trade_outcome()` to update the SQLite signals DB. Always ensure both the PostgreSQL trades table AND the SQLite signal_outcomes table are updated when closing trades.

Also: the `close_reason` field should be descriptive — use `'hl_atr_sl'` when an HL fill is verified (ATR SL triggered), and `'guardian_missing'` only when no fill was found within the lookback window.

## Hyperliquid `size` field — not `szi` (2026-04-08)

`get_open_hype_positions_curl()` (aliased as `get_open_hype_positions` in position_manager.py) reads `szi` from HL internally but **outputs** `size` in its returned dict. Any code that calls this function and reads `p.get('szi')` will always get 0. Always use `p.get('size')` when reading from the returned dict of `get_open_hype_positions()`.

Also: `get_open_positions()` (brain DB) returns `size` directly — same key, different source. The two functions are distinct:
  - `get_open_positions()` → brain DB → key `"size"`
  - `get_open_hype_positions()` → HL API (via SDK) → key `"size"` in returned dict

## HL trigger orders: `limit_px` must equal `triggerPx` (2026-04-08)

When placing SL/TP as trigger orders via `build_order()`, the `limit_px` param must equal the `triggerPx` value from the order_type dict. HL validates that `limit_px == triggerPx` for trigger orders. Using `0` for `limit_px` with a trigger order causes `"Order has invalid price"`. Fix: always pass `limit_px=sl_px` / `limit_px=tp_px` alongside the trigger dict.

## `_HL_TICK_DECIMALS` — token-specific tick size map must be complete (2026-04-08)

HL requires prices to be rounded to token-specific tick sizes. The `_HL_TICK_DECIMALS` map in `hyperliquid_exchange.py` controls decimal precision for `_hl_tick_round()`. Missing tokens default to 6 decimals, which is often too many and produces invalid prices. Always check which tokens are in the map before running bulk order operations. Current known missing tokens needing entries: SCR, SAND, ETHFI, AXS, UMA, SKY.
