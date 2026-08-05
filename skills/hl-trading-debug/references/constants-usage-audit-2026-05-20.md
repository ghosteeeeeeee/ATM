# Constants Usage Audit — 2026-05-20

## Discovery

`hermes_constants.py` defines two constants that were NOT imported anywhere in the codebase:
- `DEFAULT_TRADE_SIZE_USDT = 50.0` — signal-level trade size
- `HL_MIN_NOTIONAL_USDT = 11.0` — HL minimum notional

Despite being defined, no Python file imported them. All trade sizing used hardcoded `50.0`.

## Deployment (2026-05-20)

After defining where each constant should be used, they were deployed across:

| File | Line | Usage | Status |
|------|------|-------|--------|
| brain.py | 337 | `_get_trade_size_usdt` fallback | FIXED |
| position_manager.py | 883 | amount_usdt fallback | FIXED |
| position_manager.py | 1096 | HL backfill amt fallback | FIXED |
| hl-sync-guardian.py | 3754 | orphan trade size | FIXED |
| hl-sync-guardian.py | 696 | get_db_open_trades parser | FIXED |

`HL_MIN_NOTIONAL_USDT` — not yet deployed anywhere. Currently only referenced in the constant definition itself.

## Key Lesson

Constants defined in `hermes_constants.py` but not imported are silently unused. Always `grep` the entire codebase after adding a constant to verify it's actually imported and used before relying on it elsewhere.