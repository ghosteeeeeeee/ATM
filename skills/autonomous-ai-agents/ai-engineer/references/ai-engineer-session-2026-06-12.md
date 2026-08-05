# ai-engineer Session Audit — 2026-06-12

## Session Context

HL trade history (June 11 2026) showed ~20 trades that weren't in local PostgreSQL:
AAVE (2 opens/closes), AVNT (3+ opens/closes), ORDI, SKR, MERL, PURR, TIA, FET, ME.

Root cause: orphan creation path was unreachable (dead `continue` at line 1199), and
`_poll_open_fill_once` was dead code (never called anywhere).

## Fixes Applied

### hl-sync-guardian.py — 11 fixes verified, 4 bugs found + fixed

| Fix | Lines | Description |
|-----|-------|-------------|
| 1 | ~1521 | `sync_pnl_from_hype` float coercion crash — `float(prices.get(token, entry) or entry)` with NaN guard |
| 2 | ~3762 | Path B orphan INSERT ON CONFLICT DO NOTHING + 3-branch fallback |
| 3 | ~3048 | `_check_hard_stops` stale-refresh direction mismatch check |
| 4 | ~1088 | `reconcile_hype_to_paper` always writes `hl_entry_price` (not gated on entry_delta) |
| 5 | 1195-1199 | REMOVED `continue` that blocked orphan creation — orphan creation now reachable |
| 6 | 876 | `_poll_open_fill_once` now wired into all 3 orphan paths |
| 7 | ~1122 | `reconciled_id` path: uses actual HL fill price, writes both `entry_price` AND `hl_entry_price` |
| 8 | ~1172 | `dup_row` path: same fix, `dup_entry` from `_poll_open_fill_once` |
| 9 | ~1277 | `_close_orphan_paper_trade_by_id` uses `hl_entry` (not stale `entry_px`) for notional |
| 10 | ~1250 | `int(lev)` type coercion in `add_orphan_trade` call |
| 11 | 1743/1394/1399/1599/1996 | All 5 `close_position` calls use `slippage=CLOSE_SLIPPAGE` (was default 2%) |

### Bugs Found by ai-engineer Subagent (566s audit, no timeout)

**BUG-1 (MEDIUM) — `lev = 1` shadowed function parameter**  
`_close_orphan_paper_trade_by_id` line 2676: local `lev = 1` shadowed the `lev` parameter.
When `amount_usdt_override` was provided (orphan path), `elif conn_lookup:` was skipped,
`lev` stayed 1 instead of the passed-in `int(lev)` from `hl_pos`.
Fix: removed `lev = 1`. Parameter value is correct for orphan path; DB lookup only runs
when `amount_usdt_override` is None.

**BUG-2 (LOW) — `'pos_data' in dir()` wrong idiom**  
Line 1282: `pos_data` is the for-loop variable, always in scope. Direct reference is safer.
Fix: `_sz = float(pos_data.get('size', 0))` (removed `if 'pos_data' in dir() else 0`).

**BUG-3 (LOW) — Stale self-close branches used undefined variables**  
Refactoring `if entry_delta > 0.001 or direction_changed:` into explicit branches
initially used `new_sl`/`new_tp` — but these were defined INSIDE the original `if` block.
Fix: use `record['sl_price']` and `record['tp_price']` directly (already loaded at line 3062).

**BUG-A (MEDIUM) — close_position default 2% slippage vs guardian's 0.5%**  
All 5 `close_position(token)` calls used default slippage=0.02 (2%) instead of
`CLOSE_SLIPPAGE=0.005` (0.5%) configured in the guardian.
Affected: lines 1743, 1394, 1399, 1599, 1996.
Fix: `close_position(token, slippage=CLOSE_SLIPPAGE)` on all 5.

### False Positives (verified before implementing)

**Bug B — `_sweep_blocklist_trades` missing `_save_closed_set()`:** FALSE POSITIVE.
`_save_closed_set()` IS called at line 2893. Subagent misread the code.

**Bug C — `int(lev * 1000000)` encoding inconsistency:** INFORMATIONAL, not a bug.
Used only in ON CONFLICT race-handler path. Harmless.

## Files Verified Clean

**brain.py:** `add_trade()` uses actual HL fill price (`result.get("hl_entry_price")`) for
both `entry_price` and `hl_entry_price`. No stale signal_price usage found.

**signal_compactor.py:** Confluence gate correct (2+ types). Accel-300 standalone bypass
at lines 585-590 is intentional feature, not a bug. `_signal_type_key()` correctly
collapses rs-r136/rs-r50 to `rs` (intentional deduplication).

**position_manager.py:** `_in_profit` bug only existed in dead code `_compute_dynamic_sl`
(zero callers). Live path via `tpsl_utils.compute_atr_sl_tp` is clean.

## What's Still Pending

**Backfill:** AAVE @ 15:40, AVNT @ 13:44, AVNT @ 14:14 on 2026-06-11 — no DB records.
The guardian fix prevents future occurrences; a separate backfill script is needed
to repair existing gaps.

**brain.py entry price for hotset pipeline:** Trades created by `decider_run` → `brain.py`
still write `signal_price` (pipeline mid-estimate) to `hl_entry_price` via the hotset
execution path. The `add_trade()` fix only covers the `mirror_open` path (HL-verified).
The hotset pipeline path needs a separate fix to fetch actual HL fill price.

## ai-engineer Subagent Performance — 2026-06-12

- Batch 1 (hl-sync-guardian.py): 566s, 26 API calls, completed ✅
- Batch 2 (position_manager.py): timed out at 600s, 28 API calls ❌
  → Ran remaining checks directly in main session (5 min)
- Batch 3 (brain.py + signal_compactor.py): 210s, 13 API calls, completed ✅

**Delegation hygiene that worked:**
- Specific line ranges for each fix (not "check the file")
- Trade timeline + DB schema in context
- P0 constants check in main session before delegation
- Syntax check before delegation
- 20-min timeout (1200s) for complex multi-file audits

**Key lesson:** position_manager.py timed out at 600s even with 20-min timeout request.
The subagent hit its internal 600s limit regardless of the outer timeout parameter.
Ran position_manager checks directly in main session — 5 minutes to verify all findings.