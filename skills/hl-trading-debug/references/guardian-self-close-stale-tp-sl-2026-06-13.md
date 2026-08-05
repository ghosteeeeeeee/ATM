# Guardian SELF-CLOSE Stale TP/SL — Root Cause Analysis
**Date:** 2026-06-13 | **Coins:** MORPHO, AAVE, AVNT, MET

## Symptom
Trades with `guardian_sl` or `guardian_tp` close_reason where the exit price did NOT actually breach a legitimate stop-loss or take-profit level:
- MORPHO LONG closed at $1.9807 with `guardian_tp` — but TP should be ABOVE entry ($1.98), and exit $1.9807 is BELOW entry
- AAVE SHORT closed at $65.308 with `guardian_sl` — but SL should be ABOVE entry for SHORT, and $65.308 is just 0.08% below entry $65.255

## Root Cause
The SELF-CLOSE path for **UNPROTECTABLE coins** (AAVE, MORPHO, AVNT, MET, PENDLE, ASTER, PAXG, BTC) had stale TP/SL values in `tpsl_self_close` from prior market regimes.

**The stale detection logic** only refreshed TP/SL when:
- `entry_delta > 0.001%` (entry price changed significantly), OR
- direction changed

**If neither condition was true** → stale TP/SL was used for breach detection.

### MORPHO Example
```
tpsl_self_close record (stale from 2026-04-28):
  entry_px = 1.9735
  tp_price = 1.9399695   ← this is BELOW entry for a LONG!

MORPHO reopened at:
  entry ≈ $1.98  (≈ same as stored entry → entry_delta ≈ 0)
  
Guardian used stale tp_price=1.9399 for breach check.
For a LONG: breach when price >= tp_price.
Price ~$1.983 crossed stale TP 1.9399 → guardian_tp fired!
But 1.9399 is below entry — this is NOT a real TP breach.
```

### AAVE Example
```
Old stored record (stale):
  entry ≈ $62.92
  sl_price ≈ $64.18  ← this is ABOVE entry for SHORT!

New AAVE SHORT opened at:
  entry = $65.255
  old sl_price = $64.18 < new entry = $65.255
  
For SHORT: breach when price >= sl_price.
Price $65.308 >= stale sl_price $64.18 → guardian_sl fired!
But $64.18 is below the new entry — not a real SL breach.
```

## Fix v1 (WRONG — produced dead code)
Initial fix restructured to: if record exists → compute fresh SL/TP → `continue` (skip breach check). This made the breach check **completely unreachable** — UNPROTECTABLE coins could never be closed by the guardian.

## Fix v2 (CORRECT)
1. **Breach check FIRST** using stored TP/SL from DB
2. **Always refresh** TP/SL every cycle (unconditionally via `_upsert_self_close`)
3. **Fire breach** if triggered by stored values

Both steps execute in the same cycle — breach uses stored values while fresh values are being written for next cycle.

## Other Fixes Applied This Session
1. **`unrealizedPnl` string crash** — HL returns numeric strings; defensive `float()` with NaN check
2. **`compute_live_pnl` crash** — wrapped in try/except
3. **`_check_stale_rotation` string crash** — `speed_data['updated_at']` was string; `float()` conversion added
4. **Syntax error** — dangling `except` block from v1 fix; reverted in v2
5. **Traceback logging** — `traceback.format_exc()` added to exception handler for faster diagnosis

## Verification
After fix, guardian log shows fresh SL/TP every cycle with no breach:
```
[INFO] [SELF-CLOSE] MORPHO SL=1.962664 TP=2.006147 (no breach, px=1.9765)
[INFO] Synced PnL from HL for 2 positions
```
