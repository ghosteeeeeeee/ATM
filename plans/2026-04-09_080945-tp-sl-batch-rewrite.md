# Plan: TP/SL Batch Rewrite + Hotset Fix

## Context

**Two bugs found:**

### Bug 1 — TP/SL not being placed (4 coins: PAXG, AVNT, EIGEN, EIGEN... wait — all 9 had this)

All 9 open HL positions had `hl_sl_order_id=None` and `hl_tp_order_id=None`. The root cause is **two compounding issues**:

#### Root Cause A — `reconcile_tp_sl` never fires for these coins
The guardian's Step 10 `reconcile_tp_sl()` only runs when there are active HL positions AND their `hl_sl_order_id`/`hl_tp_order_id` are already set in DB. Since all 9 had NULLs, the guardian skipped reconciliation entirely. `reconcile_tp_sl` has a guard:
```python
# guardian line ~2280: current_sl/current_tp read from DB — but these are DB's stored SL/TP, not HL's actual SL orders
```

#### Root Cause B — Wrong price precision in `replace_tp`/`replace_sl`

`replace_tp` and `replace_sl` (lines ~1418, ~1451) use `szDecimals` as price decimals directly:
```python
decimals = _hl_tick_decimals(coin)   # ← returns szDecimals
new_px = _hl_tick_round(new_price, decimals)   # ← rounds to szDecimals decimals
```

**Wrong.** For HL perpetuals, price tick = `10^-(6 - szDecimals)`:
- SAND szDecimals=0 → price_tick=1.0 (integer only)
- AVNT szDecimals=0 → price_tick=1.0
- ASTER szDecimals=0 → price_tick=1.0
- IMX szDecimals=1 → price_tick=0.00001 (5 decimals)
- EIGEN szDecimals=2 → price_tick=0.0001 (4 decimals)
- AAVE szDecimals=2 → price_tick=0.0001
- PAXG szDecimals=3 → price_tick=0.001 (3 decimals)

Old code was rounding SL/TP prices to `szDecimals` decimals — for szDecimals=0 coins (SAND, AVNT, ASTER), this rounds to INTEGER, making SL=TP=1.0 for all of them (invalid).

**Fix:** Add `_hl_price_decimals(token)` that returns `max(0, 6 - szDecimals)`, use it in `replace_tp`/`replace_sl` instead of `szDecimals`.

### Bug 2 — Hotset empty

Hotset read path in `away_detector.py` was reading from `/root/.hermes/data/hotset.json` (wrong). Canonical path is `/var/www/hermes/data/hotset.json`. The old file existed and was empty ({}). Fixed: patched `away_detector.py` to use correct path.

---

## Three Categories of Coins After Fix

| Category | Coins | Status | Action |
|----------|-------|--------|--------|
| Fixable now | AAVE, IMX, CAKE, EIGEN, ASTER, UMA | All had TP/SL placed this session | `replace_tp/sl` fix ensures future reconciliation works |
| szDecimals=0 coins | SAND, AVNT | HL only accepts integer prices. These coins are <$1. TP/SL at integer prices are meaningless. | **Manual review needed** — these coins should not be traded on HL or need position size increase |
| Asset 187 (PAXG) | PAXG | HL returns "Invalid TP/SL price. asset=187" for any TP/SL tried | **Separate issue** — PAXG's asset config on HL may be wrong. Manual review with HL team or close/reopen position |

---

## Plan

### Step 1 — Fix `_hl_tick_round` precision bug in `hyperliquid_exchange.py`

Add a new function and patch `replace_tp`/`replace_sl`:

```python
def _hl_price_decimals(token: str) -> int:
    """HL perpetual price precision: max(0, 6 - szDecimals)."""
    sd = _hl_tick_decimals(token)
    return max(0, 6 - sd)
```

Patch `replace_tp` line ~1429: `decimals = _hl_tick_decimals(coin)` → `decimals = _hl_price_decimals(coin)`
Patch `replace_sl` line ~1462: same

Also patch `place_tp` and `place_sl` if they use `_hl_tick_round` with wrong decimals.

### Step 2 — Write a clean `batch_tpsl_rewrite.py` script

Runs every minute via cron. Clean architecture:

```
for each open HL position:
    1. Cancel ALL existing TP orders for this coin (via cancel_tp / cancel_bulk)
    2. Cancel ALL existing SL orders for this coin (via cancel_sl)
    3. Fetch ATR(14) for this coin
    4. Compute new SL and TP using ATR-based logic (same as decider_run)
    5. Round SL/TP to correct price precision (6 - szDecimals)
    6. Place new SL order
    7. Place new TP order
    8. Log result
```

**Key design decisions:**
- Batch cancel first (all cancels), then batch place (all places) — avoids order state conflicts
- Single coin per iteration with rate-limit delays between coins
- Compute SL/TP from entry_price (not current price) — same ATR logic as decider_run
- Log every placement to brain DB for audit trail
- Skip coins where both cancel AND place fail (likely structural issue: SAND, AVNT, PAXG)

### Step 3 — Write cron job

```bash
*/1 * * * * cd /root/.hermes/scripts && python3 batch_tpsl_rewrite.py >> /var/log/hermes_tpsl_rewrite.log 2>&1
```

### Step 4 — Fix the DB schema (minor)

`hl_sl_order_id` and `hl_tp_order_id` are currently nullable and set once at entry. They should be updated by the batch rewrite script. Also add `last_tpsl_sync` timestamp column to trades table.

### Step 5 — Hotset investigation

`away_detector.py` fixed. Verify by checking if cron-run hotset reads produce data now.

---

## Files to Change

| File | Change |
|------|--------|
| `hyperliquid_exchange.py` | Add `_hl_price_decimals()`, patch `replace_tp`/`replace_sl`/`place_tp`/`place_sl` to use it |
| `batch_tpsl_rewrite.py` | **NEW** — clean batch rewrite script |
| `brain/trading.md` | Document the three coin categories and manual action needed |
| `brain/TASKS.md` | Add: fix PAXG asset=187 issue, resolve SAND/AVNT position sizing |

---

## Verification

1. After patch, run: check that `place_sl('IMX', 'LONG', 0.141, 70.3)` rounds to `0.14167` not `0.1`
2. Run batch script manually, verify 6/9 coins get fresh TP/SL
3. Check cron log for errors
4. Monitor hotset population after next away-detector run
