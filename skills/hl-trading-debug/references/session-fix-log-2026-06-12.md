# Session Fix Log — 2026-06-12

## All Fixes Applied to hl-sync-guardian.py

| # | Line | Bug | Status |
|---|------|-----|--------|
| 1 | ~1521 | `sync_pnl_from_hype` float coercion crash | ✅ Fixed |
| 2 | ~3762 | Path B orphan INSERT ON CONFLICT race | ✅ Fixed |
| 3 | ~3048 | `_check_hard_stops` stale-refresh direction mismatch | ✅ Fixed |
| 4 | ~1088 | `hl_entry_price` never synced in reconcile | ✅ Fixed |
| 5 | 1195-1199 | `continue` blocked orphan creation (dead code) | ✅ Fixed |
| 6 | 876 | `_poll_open_fill_once` dead code — now wired into all 3 orphan paths | ✅ Fixed |
| 7 | ~1122 | `reconciled_id` path now uses actual HL fill price | ✅ Fixed |
| 8 | ~1172 | `dup_row` path now uses actual HL fill price | ✅ Fixed |
| 9 | ~1277 | `_close_orphan_paper_trade_by_id` uses actual HL notional | ✅ Fixed |
| 10 | ~1250 | `int(lev)` type fix in `add_orphan_trade` call | ✅ Fixed |
| 11 | 1743/1394/1599/1996 | All `close_position` calls used 2% default slippage | ✅ Fixed |

## Bug A — close_position slippage mismatch (NEW from ai-engineer audit)

**Problem**: `close_position` from `hyperliquid_exchange.py` defaults to `slippage=0.02` (2%). The guardian configures `CLOSE_SLIPPAGE=0.005` (0.5%) but only `close_position_hl` (line 794) used it. All direct calls to `close_position` used the 2% default.

**Affected locations**:
- Line 1743: `_check_hard_stops` hard-stop loop
- Line 1394/1399: `_attempt_flip_position` primary + retry close
- Line 1599: stale-rotation close loop
- Line 1996: `_rotate_stale_positions`

**Fix**: `close_position(token, slippage=CLOSE_SLIPPAGE)` in all 5 locations.

**Note**: `close_position` docstring says 2% is intentional for emergency closes (wider slippage for volatile markets). The guardian's 0.5% is the right target for normal operation — `_check_hard_stops` is the emergency path and still uses wider slippage, just the configured amount instead of the hardcoded default.

## Bug B — _sweep_blocklist_trades missing _save_closed_set (FALSE POSITIVE)

**ai-engineer claim**: `_sweep_blocklist_trades` adds `trade_id_str` to `_CLOSED_THIS_CYCLE` but does NOT call `_save_closed_set()`.
## Bug B — _sweep_blocklist_trades missing _save_closed_set (FALSE POSITIVE)
**ai-engineer claim**: `_sweep_blocklist_trades` adds `trade_id_str` to `_CLOSED_THIS_CYCLE` but does NOT call `_save_closed_set()`. **VERIFIED FALSE** — `_save_closed_set()` IS called at line 2893.

## Bugs Found by ai-engineer Audit (2026-06-12) — 10 bugs, all fixed

All verified in main session before implementing. See `references/ai-engineer-false-positives-2026-05-20.md` for full false-positive pattern analysis.

| Bug | Severity | Line | Fix |
|-----|----------|------|-----|
| `pending_gone` clears pending retry but not `_CLOSED_HL_COINS` — Step 11 double-closes | HIGH | ~4269 | `_CLOSED_HL_COINS.add(tok.upper())` |
| Step 6 failure path doesn't add to `_CLOSED_HL_COINS` | HIGH | ~3896 | `_CLOSED_HL_COINS.add(coin.upper())` |
| 3 Step 6 sub-paths missing `_CLOSED_HL_COINS.add()` | MEDIUM | ~3821,3842,3867,3907 | Added to all 4 paths |
| Stale marker cleanup missing `_CLOSED_HL_COINS` | MEDIUM | ~3680 | `_CLOSED_HL_COINS.add(tok.upper())` |
| `_check_hard_stops` failure path missing `_CLOSED_HL_COINS` | MEDIUM | ~1796 | `_CLOSED_HL_COINS.add(token.upper())` |
| HL API failure early-return doesn't clear `_CLOSED_HL_COINS` | MEDIUM | ~3630 | `_CLOSED_HL_COINS.clear()` before `return` |
| `_clear_pending_retry` read-modify-write not atomic | MEDIUM | ~458 | Created `_load_pending_retry_unlocked()`, wrapped full body in lock |
| `_record_loss_cooldown` inside try block — DB fail skips cooldown | MEDIUM | ~3348 | Moved before try block |
| Pending retry success path missing `_CLOSED_HL_COINS` | MEDIUM | ~4321 | `_CLOSED_HL_COINS.add(token.upper())` |
| Pending retry no-trade_id path missing `_CLOSED_HL_COINS` | MEDIUM | ~4284 | `_CLOSED_HL_COINS.add(token.upper())` |
| CRASH introduced by session's own patch: `_poll_hl_fills_for_close(token, int(curr_price))` — market price (e.g. 61234) passed as timestamp parameter | CRASH | ~4315 | Fixed to `int(time.time() * 1000) - 300000` |

## Core Pattern: _CLOSED_HL_COINS Invariants
Every code path that removes a token from pending retry MUST also add it to `_CLOSED_HL_COINS`. This ensures `_check_and_close_breached_trades` (Step 11) always skips tokens already handled by orphan/pending retry paths.

## Backfill Still Pending
AAVE @ 15:40, AVNT @ 13:44, AVNT @ 14:14 on 2026-06-11 — these records won't repair themselves without a separate backfill script.
AAVE @ 15:40, AVNT @ 13:44, AVNT @ 14:14 on 2026-06-11 — these records won't repair themselves without a separate backfill script.