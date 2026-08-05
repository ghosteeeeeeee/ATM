# Constants Import Discovery — PnL Sync Session (2026-05-20)

## What Was Found

`DEFAULT_TRADE_SIZE_USDT = 50.0` and `HL_MIN_NOTIONAL_USDT = 11.0` were both defined in `hermes_constants.py` but ZERO files imported them.

Results of exhaustive grep across all .py files in `/root/.hermes/scripts/`:
- `from hermes_constants import` — 0 matches
- `import hermes_constants` — 0 matches

Both constants existed in hermes_constants.py but were effectively dead code. This meant:
- `DEFAULT_TRADE_SIZE_USDT` was hardcoded as `50.0` in brain.py:337, decider_run.py:142
- `HL_MIN_NOTIONAL_USDT` had no enforcement anywhere

## What Was Fixed

1. brain.py imports both from hermes_constants (line 21)
2. brain.py:426-432 — HL_MIN_NOTIONAL_USDT check before mirror_open (rejects trades below $11)
3. brain.py:337 — _get_trade_size_usdt fallback now uses DEFAULT_TRADE_SIZE_USDT constant
4. decider_run.py:142 — already had `DEFAULT_TRADE_SIZE_USDT = 50.0` defined locally (correct usage — constant definition, not fallback)
5. position_manager.py — uses DEFAULT_TRADE_SIZE_USDT constant where needed
6. hl-sync-guardian.py — uses DEFAULT_TRADE_SIZE_USDT for guardian orphan operations

## Constants Locations (As of 2026-05-20)

| Constant | Location | Value |
|----------|----------|-------|
| `DEFAULT_TRADE_SIZE_USDT` | hermes_constants.py:252 | $50.0 |
| `HL_MIN_NOTIONAL_USDT` | hermes_constants.py:252 | $11.0 (HL min $10 + $1 buffer) |
| `MIN_TRADE_USDT` | hyperliquid_exchange.py:714 | $10.0 (HL raw minimum) |
| `LIVE_TRADING_ENABLED` | hermes_constants.py:24 | False (kill switch) |

## Audit Command

To verify all constants are properly imported and used:
```bash
grep -rn "DEFAULT_TRADE_SIZE_USDT\|HL_MIN_NOTIONAL_USDT" /root/.hermes/scripts/*.py | grep -v "hermes_constants.py\|# \|comment"
```