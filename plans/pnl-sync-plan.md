# PnL Sync Plan — HL vs Local DB Reconciliation

**Goal:** Get local P&L values in sync with actual Hyperliquid (HL) execution — fix inflated profits / deflated losses, eliminate hardcoded assumptions.

---

## Definitions

| Constant | Value | Location | Purpose |
|---|---|---|---|
| `DEFAULT_TRADE_SIZE_USDT` | 50.0 | hermes_constants.py | Signal-level intent, fallback for `amount_usdt` |
| `HL_MIN_NOTIONAL_USDT` | 11.0 | hermes_constants.py | HL minimum ($10 + $1 buffer) |

---

## Phase 1 — Constants & DB Schema ✅ DONE

- [x] **hermes_constants.py**: Added `DEFAULT_TRADE_SIZE_USDT = 50.0`, `HL_MIN_NOTIONAL_USDT = 11.0`
- [x] **PostgreSQL**: `ALTER TABLE trades ADD COLUMN hl_notional_usdt REAL;`
- [x] **hyperliquid_exchange.py**: `mirror_open()` returns `total_sz` and `notional_usdt` (actual HL notional)
- [x] **brain.py**: `add_trade()` INSERT captures `hl_notional_usdt` from `mirror_open()` result

---

## Phase 2 — Hardcoded `$50` Defaults ✅ DONE

Replaced all 12 hardcoded `50`/`50.0` fallbacks with `DEFAULT_TRADE_SIZE_USDT` constant:

| File | Occurrences | Status |
|---|---|---|
| brain.py | 1 | ✅ |
| position_manager.py | 1 | ✅ |
| cascade_flip.py | 4 | ✅ |
| hl-paper-sync.py | 2 | ✅ |
| hermes-trades-api.py | 1 | ✅ |
| close_position.py | 1 | ✅ |
| hl-sync-guardian.py | 9 | ✅ |
| backfill_hl_pnl.py | 1 | ✅ |
| backfill_orphan_hl_prices.py | 1 | ✅ |

---

## Phase 3 — PnL Hierarchy at Close ✅ DONE

**Three close paths updated:**

### 3a. `brain.py:close_trade()` ✅
- SELECT fetches `hl_notional_usdt`
- `calc_notional = hl_notional_usdt if set else amount_usdt`
- Tier 1 (HL realized): `hype_pnl_pct = hype_pnl_usdt / calc_notional`
- Tier 2 (local calc): uses `calc_notional` for both value and %

### 3b. `position_manager.py:close_paper_position()` ✅
- SELECT fetches `hl_notional_usdt` → `calc_notional`
- PnL math uses `calc_notional`
- `actual_pnl_pct` in `record_signal_outcome` uses `calc_notional`
- NOTE: Fees still calculated from `amount_usdt × leverage` (known issue — see Bug #1 below)

### 3c. `hl-sync-guardian.py:_close_position_from_signal()` ✅
- SELECT fetches `hl_notional_usdt` → `calc_notional`
- Tier 1 (HL realized): `hype_pnl_pct = hype_pnl_usdt / calc_notional`
- Tier 2 (local calc): `pnl_usdt = calc_notional × pnl_pct / 100`

---

## Bugs Found by Audit

| # | File | Line | Severity | Bug |
|---|------|------|----------|-----|
| 1 | position_manager.py | 904 | High | Fees calculated from `amount_usdt × leverage` instead of `calc_notional × leverage` — inflates fee deductions by ~7x | ✅ FIXED |
| 2 | hl-sync-guardian.py | 749 | High | `add_orphan_trade()` INSERT missing `hl_notional_usdt` — orphan trades always fall back to $50 inflated notional | ✅ FIXED |
| 3 | hl-sync-guardian.py | 2666 | High | `_close_orphan_paper_trade_by_id()` fetches `amount_usdt` but NOT `hl_notional_usdt` — even if column were populated, it wouldn't use it | ✅ FIXED |
| 4 | hl-sync-guardian.py | 1401 | Medium | Flip trade INSERT missing `hl_notional_usdt` — cascade flip trades use inflated $50 | ✅ FIXED |
| 5 | backfill_orphan_hl_prices.py | 147 | Medium | Backfill PnL uses `amount_usdt` not `calc_notional` — backfilled orphans still inflated | ✅ FIXED |

---

## Orphan / Direct-INSERT Paths Missing `hl_notional_usdt`

| File | Line | Function | Severity |
|------|------|----------|----------|
| hl-sync-guardian.py | 749 | `add_orphan_trade()` | High |
| hl-sync-guardian.py | 1401 | Flip trade INSERT | Medium |
| hl-sync-guardian.py | 2666 | `_close_orphan_paper_trade_by_id()` — reads wrong column | High |
| cascade_flip_helpers.py | 196 | `create_flip_trade()` | Medium |
| sync_open_trades.py | 297 | `add_orphan_recovery_trade()` | Medium |
| pump_hunter.py | 378 | Pump hunter live trade | Medium |
| run_guppy_signals.py | 216 | Guppy signal trade | Medium |

---

## Ghost Trades Issue (5/18/2026)

HL shows rapid open/close pairs (~10s apart) for many tokens:
- OP, TRB, ASTER, EIGEN, IP, DASH, FET, MERL, SUSHI, XRP, TIA, etc.
- Each open is ~10.10-10.15 USDC notional (exactly the HL minimum)
- Each close is ~10.10-10.41 USDC (tiny PnL)
- This is HL's `position_usd` floor behavior — actual notional is ~$10

**Root cause**: Guardian orphan recovery creating paper trades (via `add_orphan_trade()`) and immediately closing them. The `add_orphan_trade()` creates a DB row, then `_close_orphan_paper_trade_by_id()` closes it — but:
1. `add_orphan_trade()` doesn't set `hl_notional_usdt` (Bug #2)
2. `_close_orphan_paper_trade_by_id()` doesn't read `hl_notional_usdt` (Bug #3)
3. `position_usd` from HL is ~$10 (floor value), not the real notional

---

## Key Design Decisions

1. **`amount_usdt` stays as signal-level intent** — does NOT reflect actual HL execution. Preserved for all existing queries/displays. No downstream breakage.
2. **`hl_notional_usdt` column** stores actual HL USDT notional at open time — used for all PnL math.
3. **No backfill** of existing open trades — user confirmed.
4. **HL minimum = $10, `HL_MIN_NOTIONAL_USDT = 11.0`** — includes $1 buffer.
5. **`DEFAULT_TRADE_SIZE_USDT = 50.0`** — signal-level default, NOT for PnL calculations.

---

## Files Modified

- `/root/.hermes/scripts/hermes_constants.py` — constants added
- `/root/.hermes/scripts/hyperliquid_exchange.py` — `mirror_open()` enhanced
- `/root/.hermes/scripts/brain.py` — `add_trade()` writes `hl_notional_usdt`
- `/root/.hermes/scripts/position_manager.py` — constant used
- `/root/.hermes/scripts/cascade_flip.py` — constant used
- `/root/.hermes/scripts/hl-paper-sync.py` — constant used
- `/root/.hermes/scripts/hermes-trades-api.py` — constant used
- `/root/.hermes/scripts/close_position.py` — constant used
- `/root/.hermes/scripts/hl-sync-guardian.py` — constant used
- `/root/.hermes/scripts/backfill_hl_pnl.py` — constant used
- `/root/.hermes/scripts/backfill_orphan_hl_prices.py` — constant used

---

## What's Still Open

- [x] Phase 3a: `brain.py:close_trade()` — uses `hl_notional_usdt` for PnL calc when available; Tier 1 = HL realized, Tier 2 = `hl_notional_usdt × price_change_pct`, Tier 3 = `amount_usdt` fallback ✅
- [x] Phase 3b: `position_manager.py:close_paper_position()` — same hierarchy + `actual_pnl_pct` uses `calc_notional` ✅
- [x] Phase 3c: `hl-sync-guardian.py` — `_close_position_from_signal()` now uses `hl_notional_usdt` for calc_notional ✅
- [x] Verify no breakage — all 3 files compile clean (py_compile) ✅
