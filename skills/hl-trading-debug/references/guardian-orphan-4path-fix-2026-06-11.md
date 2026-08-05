# Guardian Orphan — 4-Path Fix (2026-06-11)

## Root Cause

HL trades missing from local DB (AAVE @ 15:40, AVNT @ 13:44/14:14, others) because `reconcile_hype_to_paper` had a `continue` at ~line 1199 that made the orphan creation block unreachable. Fresh HL positions with no prior reconciled state and no DB record hit the `continue` and were logged but never recorded.

Additionally, ALL orphan paths used `entry_px` from `hl_pos` (the `/info` API estimate) instead of actual HL fill prices. The `_poll_open_fill_once()` function existed but was dead code (never called).

## 4 Orphan Handling Paths in `reconcile_hype_to_paper`

### Path A — `reconciled_id` (line ~1121)
HL position has prior reconciled state → updates existing DB record.
**Fixed:** Now fetches actual HL open fill via `_poll_open_fill_once`, writes both `entry_price` AND `hl_entry_price` in UPDATE SQL.

### Path B — `dup_row` (line ~1170)
HL position has existing paper DB record → closes both HL and paper.
**Fixed:** Now fetches actual HL open fill, writes `entry_price` + `hl_entry_price` in UPDATE, passes actual fill price to `_mark_hl_reconciled`.

### Path C — Fresh orphan (line ~1199) [PREVIOUSLY DEAD]
HL position has no DB record and no prior reconciled state.
**Fixed:** Removed `continue`, added `_poll_open_fill_once` call, creates `guardian_orphan` paper trade with actual HL fill price.

### Path D — `_close_orphan_paper_trade_by_id` (line ~1277)
Called after Path C creates the orphan trade — closes the DB record.
**Fixed:** Uses `hl_entry` (actual fill price) instead of `entry_px` (/info estimate) for notional calculation. `int(lev)` coercion added.

## All Fixes Applied

| Location | Fix |
|----------|-----|
| Line ~876 | `_poll_open_fill_once()` defined — wavg open fill from 5-min window, filters `'Open' in str(f.get('dir', ''))` |
| Line ~1121 (Path A) | Added `_poll_open_fill_once` call + `hl_entry_price` column in UPDATE |
| Line ~1170 (Path B) | Added `_poll_open_fill_once` call + `hl_entry_price` in UPDATE + `int(lev)` |
| Line ~1199 | REMOVED `continue` — orphan creation block now reachable |
| Line ~1224 (Path C) | `_poll_open_fill_once` → `hl_entry`; fallback chain; `int(lev)` |
| Line ~1277 (Path D) | Uses `hl_entry` (not `entry_px`) for notional; `int(lev)` |
| Line ~1085 | `hl_entry_price` always written (not gated on entry_delta) |

## Key Insight — `hl_entry_price` vs `entry_price`

`entry_price` can match between hype_cache and DB (both stale/wrong), causing reconcile to skip the update. But `hl_entry_price` was NEVER being written in Path A and Path B — it stayed 0 or stale. The fix always writes `hl_entry_price` even when `entry_price` doesn't change.

## Secondary Fix — `sync_pnl_from_hype` float coercion

Lines ~1517-1526: `float(prices.get(token, entry) or entry)` — was crashing when prices dict contained string values (rate-limit window). Explicit `try/except` with `math.isnan()` guard.

## Remaining Work

- Backfill: AAVE @ 15:40, AVNT @ 13:44/14:14 still missing from DB — guardian fix prevents future occurrences, not a repair
- `hype_cache` root cause: `brain.py`/`decider_run` hotset pipeline writes `entry_px` from mid prices, not actual HL fill — new trades will still have wrong `hl_entry_price` until that path is fixed separately

## ai-engineer Subagent Findings (verified in main session)

- `_poll_open_fill_once` dead code: CONFIRMED via grep (1 match = definition only)
- `continue` at ~line 1199 blocks orphan creation: CONFIRMED via read_file
- `dup_row` path uses stale `entry_px` for `hl_entry_price`: CONFIRMED — FIXED
- Path A and B ARE reachable and DO handle some orphans — just not fresh ones
- Subagent correctly noted: "fresh orphans bypass reconcile and hit dead continue"

## Verification

```bash
python3 -m py_compile /root/.hermes/scripts/hl-sync-guardian.py  # Syntax OK
grep -n "_poll_open_fill_once" /root/.hermes/scripts/hl-sync-guardian.py  # 5 matches (1 def + 4 calls)
grep -n "continue$" /root/.hermes/scripts/hl-sync-guardian.py | grep "1199\|1200"  # no orphaned continue
```