# 2026-05-20 Session: PnL Inflation & Phantom Execution Fixes

## Bugs Fixed Today

| File | Line | Bug | Fix |
|------|------|-----|-----|
| brain.py | 637 | `calc_notional = float(hl_notional_usdt) if hl_notional_usdt else amount_usdt` — 0.0 falsy → PnL inflated ~5x | `is not None` check |
| brain.py | 640 | `amount_usdt = float(amount_usdt or DEFAULT_TRADE_SIZE_USDT)` — 0.0 falsy for fee base | `is not None` check |
| brain.py | 572-580 | HL rollback used `mirror_close()` which raises RuntimeError when kill switch OFF | Uses `close_position()` directly |
| position_manager.py | 883 | `amount_usdt = float(row['amount_usdt'] or DEFAULT_TRADE_SIZE_USDT)` — 0.0 falsy | `is not None` check |
| position_manager.py | 1096 | `amt = float(row[0] or DEFAULT_TRADE_SIZE_USDT)` — same 0.0 falsy in HL backfill | `is not None` check |
| signal_compactor.py | 1388 | Phantom detection `LIMIT 1` without direction filter — found guardian_orphan trades, masked phantom | Added `direction=%s ORDER BY id DESC` |
| hl-sync-guardian.py | 3744 | DRY mode orphan INSERT bypass — phantom DB records during dry runs | Added `if DRY: continue` |
| away_detector.py | 110 | Split-brain: read `hype_live_trading.json` directly while everything else used constant | Delegates to hyperliquid_exchange |
| decider_run.py | 1886 | sig_id=None race: no skip when `claimed==0` — both concurrent processes proceeded to brain.py | Added `if claimed==0: skip` |

## ai-engineer Subagent False Positives (2026-05-20)

| Bug # | Claimed | Reality |
|-------|---------|---------|
| Bug 1 DRY bypass | CRITICAL — DRY mode creates phantom DB records | REAL but severity inflated — DRY runs in paper-only mode, no live HL positions affected |
| Bug 3 phantom LIMIT 1 | My fix was counterproductive — guardian_orphan found | REAL — reverted my fix and correctly added direction filter |
| Bug 4 away_detector split-brain | CRITICAL — live_trading flag mismatch | REAL — fixed |
| Bug 5 paper flag | CRITICAL — paper flag always True | WRONG — `paper = not is_live_trading_enabled()` IS correct logic |
| Bug 1 MAX_LEVERAGE | CRITICAL — v3 vs hermes-export mismatch (5 vs 10) | FALSE POSITIVE — subagent compared archive files, live file has MAX_LEVERAGE=5 correctly |
| Bug 2 pnl_usdt not in UPDATE | v3:655 had it, hermes-export:655 missing | PARTIALLY WRONG — position_manager uses `refresh_current_prices()` which DOES write pnl_usdt separately |
| Bug 3 duplicate race (position_manager) | No FOR UPDATE lock in close_position | PARTIALLY TRUE — guardian and position_manager can close same trade, but result is handled (DB closes with no error, hype-sync reconciles) |

## Key Debugging Patterns

### 0.0 Falsy Pattern (Python)
Everywhere `float(x or DEFAULT)` is used is a potential bug if `x=0.0` is a valid value. Always use explicit None check:
```python
# WRONG
amount_usdt = float(row['amount_usdt'] or DEFAULT_TRADE_SIZE_USDT)
calc_notional = float(row['hl_notional_usdt']) if row['hl_notional_usdt'] else amount_usdt
# RIGHT
amount_usdt = float(row['amount_usdt']) if row['amount_usdt'] is not None else DEFAULT_TRADE_SIZE_USDT
calc_notional = float(row['hl_notional_usdt']) if row['hl_notional_usdt'] is not None else amount_usdt
```

### Phantom Execution Chain (decider_run → brain.py)
```
decider_run.run() → mark_signal_executed(token, direction, signal_id=sig_id)
  sig_id known: UPDATE WHERE id=? AND executed=0 → claimed=0 if already done
  sig_id=None: UPDATE WHERE token=? AND direction=? AND executed=0 → ALL matching rows
  claimed=0: process skips (correct)
  claimed=1: proceed to execute_trade()
    execute_trade() → brain.py --real → mirror_open() → DB INSERT
    ✅ DB INSERT success: signal stays executed=1, trade recorded
    ❌ DB INSERT fail: sys.exit(1) → decider_run sees RC=1 → rollback_signal_executed()
      sig_id known: UPDATE WHERE id=? AND executed=1 → 1 row updated
      sig_id=None: UPDATE WHERE token=? AND direction=? AND executed=1 → 0 rows (no match if HL rollback also failed)
      → signal stuck in executed=1, no trade, phantom
```

### PnL Tiered Hierarchy (for existing trades with hl_notional_usdt=NULL)
- Tier 1: `hype_realized_pnl_usdt` from HL after fill confirm
- Tier 2: `hl_notional_usdt × price_change_pct` when available
- Tier 3: `amount_usdt × price_change_pct` (inflated, ~5x for small positions)

## Constants Status
- `LIVE_TRADING_ENABLED = False` — kill switch OFF, no live HL trades possible
- `DEFAULT_TRADE_SIZE_USDT = 50.0` — signal-level intent, NOT actual HL trade size
- `HL_MIN_NOTIONAL_USDT = 11.0` — defined in hermes_constants but NOT used anywhere in codebase (actual HL minimum is ~$10 via `MIN_TRADE_USDT` in hyperliquid_exchange.py:706)

## All Files Compile Clean (2026-05-20)
brain.py, position_manager.py, signal_compactor.py, away_detector.py, decider_run.py, hl-sync-guardian.py