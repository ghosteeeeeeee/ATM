# PnL Sync + Ghost Trade Prevention — 2026-05-19 Session

## What Was Fixed

### BUG 1 — brain.py: sig_id=None rollback silently skipped (FIXED)
**File:** `decider_run.py:1943-1957`
**Problem:** When `sig_id=None` (legacy hot-set signals), `rollback_signal_executed(token, direction, signal_id=None)` matched nothing (WHERE signal_id=NULL never matches). Signal stayed `executed=1` permanently → no retry possible → orphan HL position left dangling.
**Fix:** Added token+direction fallback: `mark_signal_executed(token, direction, signal_id=None, executed=0)` — no signal_id filter, matches by token+direction only.

### BUG 2 — brain.py: total_sz=None fallback corrupts hl_notional (FIXED)
**File:** `brain.py:489-497`
**Problem:** When `mirror_get_entry_fill` fell back, `total_sz=None` → `hl_notional = result.get("notional_usdt")` = signal-level ~$50 → guardian uses wrong inflated notional for PnL (5x actual).
**Fix:** `hl_notional = None` when `total_sz` missing → guardian uses `hype_realized_pnl_usdt` as ground truth instead.

### BUG 3 — hl-sync-guardian.py: hype_realized_pnl_pct uses price-based pct when realized_pnl=None (FIXED)
**File:** `hl-sync-guardian.py:3355`
**Problem:** Self-close path wrote `hype_realized_pnl_pct = computed_pnl_pct` (price-based) even when `realized_pnl=None`.
**Fix:** `round(realized_pnl_value / calc_notional * 100, 4) if realized_pnl_value else None`

### BUG 4 — brain.py: hl_notional computed from actual HL fill (FIXED)
**File:** `brain.py:489`
**Fix:** `hl_notional = round(total_sz * fill_px, 4)` when both available.

### BUG 5 — brain.py: DB INSERT failure = silent stderr=empty (FIXED)
**File:** `brain.py:560`
**Fix:** Full exception + traceback + all params printed to pipeline.log on DB INSERT failure.

### BUG 6 — brain.py: return None after failed rollback = orphan HL position (FIXED)
**File:** `brain.py:597`
**Fix:** `sys.exit(1)` instead of `return None` → decider_run fires signal rollback automatically.

## New Debug Logging Added

| Stage | File | Log |
|--------|------|-----|
| mirror_open call | brain.py:472 | `[brain.py] → mirror_open(coin, direction, entry_price, leverage)` |
| mirror_open result | brain.py:473 | `[brain.py] ← mirror_open returned: success=..., total_sz=..., notional_usdt=...` |
| hl_notional computed | brain.py:488 | `✓ hl_notional computed: total_sz=X × fill_px=Y = Z` |
| hl_notional fallback | brain.py:494 | `⚠️ total_sz or fill_px missing — hl_notional=None (guardian will use HL realized PnL)` |
| DB INSERT success | brain.py:543 | `✅ coin DIRECTION trade#ID confirmed on HL @ $price` + `📊 PnL notional: signal-level=$X → actual HL=$Y` |
| DB INSERT failure | brain.py:560 | `❌ DB INSERT FAILED: type, traceback, all params` |
| HL rollback failure | brain.py:576 | `⚠️ HL rollback failed: err — coin may be orphaned on HL!` |
| Orphan audit state | brain.py:588 | `=== AUDIT: DB INSERT FAILURE STATE ===` — full coin state |
| sig_id=None fallback | decider_run.py:1947 | `⚠️ sig_id=None — attempting token+direction fallback rollback` |

## Verified Compile Clean
```bash
python3 -m py_compile brain.py && python3 -m py_compile decider_run.py && python3 -m py_compile hl-sync-guardian.py
# ALL COMPILE OK
```

## AAVE "executed=1 but no open trade" — NOT a ghost trade
AAVE showed `executed=1` in hot-set display with no open HL or DB position. Investigation revealed:
- AAVE LONG #10044 closed May 16 at 11:22 — correct historical close
- `executed=1` means signal was consumed by that closed trade
- Pipeline showed `No signals above 50% confidence — skipping execution` at 20:42-20:45
- Hot-set was empty (0 entries) at 20:46
- No phantom HL positions confirmed via `get_open_hype_positions_curl()`
- **Lesson:** `executed=1` in a display does NOT mean "currently open" — it means "signal was used". Always cross-reference with HL and DB.

## HL Rate-Limit (Not a Bug)
Guardian showed 429 errors at 20:36-20:45 — normal HL API throttling, auto-retries with backoff. Pipeline ran independently at 20:42-20:45. System was fully operational.

## Signal Lifecycle (Verified Complete Chain)
```
decider_run: sig_id claimed → execute_trade() → brain.py _place_hl_trade()
brain.py: mirror_open() → DB INSERT → success → return trade_id
brain.py: DB INSERT fails → sys.exit(1) (non-zero)
decider_run: RC=1 → rollback_signal_executed(token, direction, sig_id=None)
decider_run: sig_id=None fallback → mark_signal_executed(token, direction, signal_id=None) → unclaim
guardian: next cycle → orphan detected → _close_orphan_paper_trade_by_id
```
All links verified functional.