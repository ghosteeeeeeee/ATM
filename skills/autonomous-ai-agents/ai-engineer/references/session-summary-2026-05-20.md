# 2026-05-20 Session Summary — PnL Sync Bugs Fixed

## What Was Fixed

7 bugs across 3 files — all compile verified clean:
- brain.py: 0.0-falsy fix (calc_notional), 0.0-falsy fix (amount_usdt), HL_MIN_NOTIONAL_USDT pre-check added
- position_manager.py: 0.0-falsy fixes at lines 883 and 1096
- hl-sync-guardian.py: 0.0-falsy fixes, guardian_orphan INSERT with hl_notional_usdt column, `_close_orphan_paper_trade_by_id` accepts `amount_usdt_override`, all 4 call sites patched

## Critical Lesson: `replace_all=True` Corrupts Large Files

```bash
# NEVER do this on hl-sync-guardian.py (1600+ lines):
patch(path, old_string, new_string, replace_all=True)  # CREATES DUPLICATE CODE BLOCKS

# If corruption occurs:
git checkout -- scripts/hl-sync-guardian.py  # revert to clean state
# Then re-apply as SEPARATE targeted patches, one location at a time
```

**Rule:** Never use `replace_all=True` on files >500 lines. Always do targeted single-location patches.

## Files That Compile Clean (2026-05-20)

```
brain.py ✓
hl-sync-guardian.py ✓
decider_run.py ✓
signal_compactor.py ✓
position_manager.py ✓
```

## Constants Status (2026-05-20)

| Constant | Location | Status |
|----------|----------|--------|
| `DEFAULT_TRADE_SIZE_USDT=50.0` | hermes_constants.py | Imported in brain.py, hl-sync-guardian.py, position_manager.py |
| `HL_MIN_NOTIONAL_USDT=11.0` | hermes_constants.py | Imported in brain.py:21, used in brain.py:426-435 pre-check (no longer dead code) |
| `MIN_TRADE_USDT=10.0` | hyperliquid_exchange.py:714 | HL raw minimum |

## PnL Tiered Hierarchy (brain.py close_trade)

- **Tier 1**: `hype_realized_pnl_usdt` from HL API — guardian-written after fill confirm
- **Tier 2**: `hl_notional_usdt × price_change_pct` — used when Tier 1 unavailable (now populated for guardian orphans)
- **Tier 3**: `amount_usdt × price_change_pct` — last resort (inflated ~5x for small positions)

## Subagent Timeout — Updated Rule

Today a focused 3-4 bug fix task completed in ~394s with 20 API calls — subagent completed successfully, no timeout. The 600s timeout ceiling is task-type-dependent:
- Full pipeline audit (10+ files, 35+ API calls): times out at 600s
- Focused fix task (3-4 bugs, 20 API calls): completes in ~400s

**Rule:** Don't assume timeout from prior experience with a DIFFERENT task type. When giving a subagent a focused fix task, allow 400-450s and monitor. Only re-delegate if the subagent explicitly times out — do not assume it will timeout based on a prior different task.

## Brain.py Trade Entry Flow (verified 2026-05-20)

```
decider_run → brain._place_hl_trade() → mirror_open (HL-first)
                                   → DB INSERT (PostgreSQL)
                                   → on INSERT fail: rollback → close_position → sys.exit(1)
                                   → orphan HL position left open
                                   → guardian detects on next cycle → closes → creates guardian_orphan paper trade
```

Guardian orphan close uses actual `sz × entry_px` from HL position data — not $50 placeholder.

## guardian_orphan INSERT — What Changed

**BEFORE (broken):**
- No `hl_notional_usdt` column in INSERT
- `amount_usdt = 50.0` hardcoded
- PnL always used $50 base (inflated ~5x)

**AFTER (fixed):**
- `hl_notional = abs(sz * entry_px_raw)` computed from HL position data
- `amount_usdt` = `hl_notional` (actual)
- `hl_notional_usdt` = `hl_notional` (actual)
- Both written to DB INSERT
- `amount_usdt_override=hl_notional` passed to `_close_orphan_paper_trade_by_id`