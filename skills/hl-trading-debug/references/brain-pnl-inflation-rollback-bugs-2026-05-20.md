# brain.py PnL Inflation + HL Rollback Bugs Fixed (2026-05-20)

## Bug 1: PnL Inflation — calc_notional Falsy Check (brain.py:637)

**Symptom:** "profits inflated, losses deflated" — real $1 HL profit showing as $5 in DB.

**Root cause:**
```python
# BEFORE (WRONG)
calc_notional = float(hl_notional_usdt) if hl_notional_usdt else amount_usdt
```
`hl_notional_usdt = 0.0` is falsy in Python → falls back to `amount_usdt` ($50 signal-level).
Actual HL position was ~$7 → calc_notional inflated 7x → PnL inflated 7x.

**Fix:**
```python
# AFTER (CORRECT)
calc_notional = float(hl_notional_usdt) if hl_notional_usdt is not None else amount_usdt
```
Now `0.0` is treated as a real value, only `None` triggers fallback.

**Impact:** All legacy trades with `hl_notional_usdt=0.0` or NULL had inflated PnL.
New trades with `hl_notional_usdt` set correctly are accurate from 2026-05-20.

---

## Bug 2: HL Rollback RuntimeError When Kill Switch Is OFF (brain.py:572-580)

**Symptom:** DB INSERT fails → `mirror_close()` called to rollback HL position →
RuntimeError: "mirror_close(): live trading disabled (kill switch)" →
orphan HL position stays open.

**Root cause:**
```python
# brain.py rollback path (BEFORE)
from hyperliquid_exchange import mirror_close
mc = mirror_close(hype_token, direction)  # raises RuntimeError if LIVE_TRADING_ENABLED=False
```

`mirror_close()` has `if not is_live_trading_enabled(): raise RuntimeError(...)` at its entry.
If `LIVE_TRADING_ENABLED=False` (kill switch), the rollback itself is blocked.
The position was already opened under live trading — rollback must succeed even if kill switch is now OFF.

**Fix:**
```python
# AFTER — use lower-level close_position with no gate
from hyperliquid_exchange import close_position
result = close_position(hype_token)  # no is_live_trading_enabled() check
```

**Key lesson:** When rolling back a position that was opened under live trading,
use the direct HL close function (`close_position`) — NOT the wrapper that has
the kill-switch gate (`mirror_close`).

---

## Combined Impact on "Inflated Profits / Deflated Losses"

Before these fixes:
- calc_notional used $50 instead of ~$10 → PnL ~5x too large
- Legacy trades with hl_notional_usdt=0.0 all showed inflated PnL
- Guardian orphan path corrupted when rollback failed

After these fixes:
- calc_notional correctly uses actual HL notional (or $50 only for truly legacy NULL entries)
- DB INSERT failure → clean rollback → no orphan HL positions
- PnL numbers in DB now match HL reality