# hl-sync-guardian.py Fixes — June 13, 2026

## Root Cause: Guardian Mirroring Errors (AAVE, AVNT, ORDI, ME, MORPHO)

**Symptom:** Trades showing `guardian_sl` close_reason but price didn't actually breach
the stored SL. PnL was sometimes correct (e.g. AAVE SHORT exit 65.308 vs entry 65.255
= +0.08% profit, not a stop loss).

### Bug 1 — SELF-CLOSE stale TP/SL (ROOT CAUSE)

**Location:** `_check_and_close_breached_trades()`, lines ~3090-3150

**Root cause:** Stale detection only refreshed TP/SL when `entry_delta > 0.001%` or
direction changed. When re-opening at same entry price as old record, `entry_delta = 0`,
stale TP/SL from prior regime was used for breach checks → false guardian_tp/sl triggers.

**Example:** MORPHO LONG: `tp_price=1.9399` from Apr-28 (when entry ~$1.97). When price
returned to ~$1.98, entry_delta≈0, stale TP used. Since 1.9399 < 1.98 (entry),
any upward movement triggered guardian_tp. MORPHO closed at 1.9807 and 1.9821 with
`guardian_tp` reason, both were false triggers.

**Fix:** Restructure as breach-first-then-refresh:
1. Check breach using stored TP/SL (from DB, current values)
2. Always compute fresh ATR-based SL/TP and upsert to DB
3. Only fire if breach was triggered in step 1

### Bug 2 — `trigger_reason` undefined (NameError on breach)

**Location:** line 3219

After restructure, `breach_reason_str` was the variable name used, but the UPDATE
query still referenced `trigger_reason.split('(')[0].strip()` — a variable from
the OLD code that no longer existed.

**Fix:** Changed to `breach_reason_str.split('(')[0].strip()`

### Bug 3 — `speed_data['updated_at']` not coerced to float

**Location:** `_check_stale_rotation`, line 1938

`speed_data['updated_at']` was a string, `_time.time()` is float.
`float - str` → TypeError crash.

**Fix:** Wrapped in try/except with float() coercion.

### Bug 4 — `unrealizedPnl` not defensive

**Location:** `sync_pnl_from_hype`, line 1554

HL API can return numeric strings or NaN. Wrapped in try/except with NaN check.

### Bug 5 — `compute_live_pnl` crash

**Location:** `sync_pnl_from_hype`, line 1595

Wrapped in try/except, falls back to 0.0 pnl_pct on error.

### Bug 6 — HL fill arithmetic not float-coerced

**Location:** `_poll_open_fills_once` (lines 893-894), `_poll_close_fills_once` (lines 914-916)

`sz`, `px`, `closed_pnl` used directly in arithmetic without float coercion.

**Fix:**
```python
total_sz = sum(float(f['sz']) for f in token_opens)
wavg_open = sum(float(f['px']) * float(f['sz']) for f in token_opens) / total_sz
realized_pnl = sum(float(f.get('closed_pnl', 0) or 0) for f in token_closes)
```

## Verified Not Present (already fixed)

- Pattern 45 (`lev` shadow in `_close_orphan_paper_trade_by_id`) — fixed 2026-06-12
- Pattern 50 (duplicate guard missing direction) — fixed, line 1176 now SELECTs direction
- Pattern 46 (`'pos_data' in dir()`) — loop variable, always in scope
- Pattern 47 (stale branch undefined var) — resolved by restructure
- Pattern 48 (unreachable dead code after `continue`) — resolved by restructure

## Audit Approach Used

Main session only — subagent consistently times out on hl-sync-guardian.py (~4250 lines).

Workflow:
1. `python3 -m py_compile` after every patch
2. `pkill -9 -f hl-sync-guardian` before restart
3. Clear log: `> /root/.hermes/logs/sync-guardian.log`
4. Restart in background
5. Wait 70s, check for FAIL messages
6. Confirm 2 clean cycles

## Log Verification

```
HL: N positions | DB: N open trades
Orphans (HL only): none
Missing (DB only): none
Synced PnL from HL for N positions  ← no FAIL = clean
[SELF-CLOSE] MORPHO SL=X TP=Y (no breach)  ← fresh values each cycle
```
