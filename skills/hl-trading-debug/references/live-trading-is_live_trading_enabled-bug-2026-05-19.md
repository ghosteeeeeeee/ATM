# live-trading is_live_trading_enabled Bug — 2026-05-19 / REVERSED 2026-05-20

## Root Cause (Final Fix)
`hyperliquid_exchange.is_live_trading_enabled()` was temporarily changed to read `hype_live_trading.json` via `_load_flags().get("live_trading", False)`. This created a NEW phantom-trade bug: decider_run uses `--real` from the file (live_trading=true) while brain.py called `is_live_trading_enabled()` which returned the constant (live_trading=False). decider_run logged success, brain.py printed REJECTED. No DB record, no HL position, guardian created phantom orphans.

**FINAL FIX:** Reverted to returning `hermes_constants.LIVE_TRADING_ENABLED` directly. SINGLE SOURCE OF TRUTH = hermes_constants.LIVE_TRADING_ENABLED. hype_live_trading.json is completely ignored by all code.

```python
# FIRST FIX (caused new phantom trades on 2026-05-20)
def is_live_trading_enabled() -> bool:
    return _load_flags().get("live_trading", False)  # reads hype_live_trading.json

# FINAL FIX (2026-05-20)
def is_live_trading_enabled() -> bool:
    return LIVE_TRADING_ENABLED  # hermes_constants — single source of truth
```

## How the Bug Fired (from first fix attempt)
1. `hype_live_trading.json` set to `{"live_trading": true}` → decider_run passes `--real` flag
2. `decider_run.py` logs `→ ENTERED` + marks signal EXECUTED when RC=0
3. `brain.py` calls `is_live_trading_enabled()` → returns `False` (constant) → prints `❌ REJECTED: X — live_trading is DISABLED` → returns `None`
4. decider_run catches RC=1 → fires rollback → but sig_id=None → rollback SQL `WHERE signal_id=%s` with NULL → matches nothing → signal stuck EXECUTED=1
5. No HL position, no DB record → guardian orphan path fires on next cycle → orphan record created

## Phantom Trades That Fired (2026-05-19 23:48)
AAVE, GALA, AXS — opened+closed on HL, guardian created orphan records. AAVE short entry=87.43, closed at 87.44, pnl=-0.0024%.

## Files Affected
- `hyperliquid_exchange.py:239` — `is_live_trading_enabled()` returns `LIVE_TRADING_ENABLED` constant
- `decider_run.py` — signal marked EXECUTED only AFTER brain.py confirms `✅ trade #N` in stdout
- `signal_compactor.py` — purges EXECUTED signals only after PostgreSQL cross-check (any trade for token = not phantom)
- `brain.py:704` — added DEBUG print at entry to trace live-trading state

## Key Lesson
**Two live-trading switches must agree or phantom trades fire.** If decider_run uses file-based `--real`/`--paper` but brain.py uses `is_live_trading_enabled()` function, they MUST return the same value. The single source of truth is `hermes_constants.LIVE_TRADING_ENABLED`. Set it to False to kill-switch all live trading.

## Verification
```python
from hyperliquid_exchange import is_live_trading_enabled
from hermes_constants import LIVE_TRADING_ENABLED
print(f'LIVE_TRADING_ENABLED (constant) = {LIVE_TRADING_ENABLED}')
print(f'is_live_trading_enabled() = {is_live_trading_enabled()}')
# Both must agree — if is_live_trading_enabled() != LIVE_TRADING_ENABLED, bug still present
```

## Pending Issues (2026-05-20)
- `LIVE_TRADING_ENABLED = False` in hermes_constants — kill switch is OFF
- New trades still not going live — is_live_trading_enabled() now correctly returns False
- Guardian orphan path still firing for AAVE/GALA/AXS from May 19 session (stale positions)
- Remaining bugs: signal claiming race condition (sig_id=None), systemd timer overlap possible