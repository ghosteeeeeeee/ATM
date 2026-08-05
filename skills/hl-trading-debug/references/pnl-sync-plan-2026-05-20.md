# P&L Sync + New Trade Entry Bug — Plan (2026-05-20)

## PART 1: New Trade Entry Bug — Root Cause Chain

```
Decider_run calls brain.add_trade()
  → brain.py:326 add_trade() starts
  → brain.py:388 Step 2: HL-first (mirror_open on HL BEFORE DB write)
    → brain.py:426 _place_hl_trade(hype_token, direction, ...)
      → brain.py:445 _get_trade_size_usdt()
      → brain.py:448 mirror_open(ht, direction, ..., size_usdt=~50)
      → HL position OPENED ✓
  → brain.py:490 DB INSERT starts
  → brain.py:504 INSERT INTO trades (...) VALUES (...)
  → brain.py:506 EXCEPTION (PG error — unique constraint on sig_id)
  → brain.py:556 EXCEPTION block fires
  → brain.py:572 HL ROLLBACK: close_position(AAVE)
  → brain.py:580 ROLLBACK SUCCEEDS ✓
  → brain.py:597 print "ROLLBACK FAILED: sig#XXXX already claimed" ← MISLEADING
  → brain.py:599 return None
  
Actual HL fills: Open 02:36:07, Close 02:36:17 (10 seconds)
Guardian then sees orphan (HL position with no DB record), closes it again
```

**Root cause:** PostgreSQL `sig_id` UNIQUE constraint — multiple processes (decider_run + signal_compactor, or two decider_run processes) race to INSERT the same signal_id. The signal_compactor claims signals in DB at 02:37:00, then decider_run tries to enter them in the same tick.

**The "ROLLBACK FAILED" message is misleading** — the HL rollback actually succeeded. The message says "FAILED" but the position was already closed. The actual failure is the DB INSERT.

**Guardian closes orphan twice** — once by brain.py rollback, once by guardian orphan detection (same position, two close orders).

## PART 2: P&L Constants — Status

| Constant | Value | Location | Used Where? |
|----------|-------|----------|-------------|
| `DEFAULT_TRADE_SIZE_USDT` | 50.0 | hermes_constants.py:247 | brain.py:641 ✓, hl-sync-guardian.py:3767 ✓, decider_run.py:337 ✗ (hardcoded) |
| `HL_MIN_NOTIONAL_USDT` | 11.0 | hermes_constants.py:252 | NOT USED ANYWHERE |

**decider_run.py:337** has hardcoded `50.0` in `_get_trade_size_usdt()` — needs to import and use `DEFAULT_TRADE_SIZE_USDT`.

**HL_MIN_NOTIONAL_USDT** is never checked before `mirror_open()` — trades below $11 may open but HL may have issues.

## PART 3: P&L Inflation/Deflation

All 309 trades in DB have `hl_notional_usdt=NULL`. When NULL (falsy 0.0), PnL calc falls back to `amount_usdt` ($50 signal-level), inflating PnL by ~3-5x for small coins that actually traded at $10-15 on HL.

**PnL columns:**
- `hype_realized_pnl_usdt` — set by guardian post-HL-fill (CORRECT, Tier 1)
- `hl_notional_usdt` — supposed to store actual HL notional (currently NULL for all trades)
- `amount_usdt` — signal-level intent, NOT actual HL notional

## Proposed Fixes

**Fix N1: Import DEFAULT_TRADE_SIZE_USDT in decider_run**
- `decider_run.py:337` — hardcoded `50.0` in `_get_trade_size_usdt()` → replace with `DEFAULT_TRADE_SIZE_USDT`

**Fix N2: Check HL_MIN_NOTIONAL_USDT before mirror_open**
- Add check before `mirror_open()` in brain.py — if intended notional < 11, skip trade and log warning

**Fix N3: PnL tiered sync**
- Tier 1: `hype_realized_pnl_usdt` from HL (already correct)
- Tier 2: When `hl_notional_usdt` is NULL (all existing trades), flag them for backfill
- Backfill: Use `signal_compactor` to find HL fill data for open trades, update `hl_notional_usdt`

**Fix N4: Fix misleading "ROLLBACK FAILED" message**
- brain.py:597 — change to "HL rollback SUCCEEDED — position closed on HL"
- This is cosmetic but helps debugging

**Fix N5: Sig_id claim race — atomize signal claiming**
- signal_compactor.py: when claiming signals for hotset, use `INSERT ... ON CONFLICT DO NOTHING` pattern
- This prevents the race where compactor claims signal at 02:37:00 and decider_run tries to claim the same signal at 02:37:01

**Fix N6: Better HL notional logging**
- When guardian detects orphan (HL position with no DB record), log actual HL notional so we can compare what HL vs DB think

## Not Approved Yet

User said "only report first lets plan" — implementation pending approval.