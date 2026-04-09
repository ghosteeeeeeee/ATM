# ATR Issues — Post-Execution Review & Remaining Gaps

## Goal

Review what was completed in the 2026-04-09_185344 plan, identify what remains unresolved, and plan fixes for the outstanding issues.

---

## Context / Assumptions

### What Was Executed (2026-04-09_185344)

All 4 phases completed:

| Phase | Status | What Changed |
|---|---|---|
| Phase 1: ATR Unification | ✅ Done | `position_manager.py` — fixed `_dr_atr` proxy + 3 broken code sections; `batch_tpsl_rewrite.py` — fixed inverted k-table |
| Phase 2: Atomic Cancel-then-Place | ✅ Already existed | `clean_all_tpsl_orders` existed and is called in `reconcile_tp_sl` before placing |
| Phase 3: close_position Race | ✅ Done | Added `_save_closed_set()` BEFORE `close_position_hl` + file lock around breach close |
| Phase 4: batch vs guardian | ✅ Already correct | batch_tpsl_rewrite compute-only for guardian coins; guardian is sole HL writer |

### Current Smoke Test Results

```
✅ pipeline_errors: no errors
❌ pipeline_not_stuck: Pipeline stuck (224min old lock)
✅ price_data_fresh: prices OK (11s)
❌ signal_db: signals unreachable (SQLite empty, PG: relation "signals" does not exist)
```

### WASP Critical Issues

```
🚨 [CRITICAL] positions: 1 open trades with NULL entry_price → SKY(LONG)
🚨 [CRITICAL] pipeline: Pipeline log is 297s old — pipeline may be dead
❌ [ERROR] prices: Only 190 tokens in prices.json (expected ~229)
⚠️ [WARNING] paper-hl-sync: Cannot fetch HL positions: 'str' object has no attribute 'get'
```

---

## Proposed Approach

Triage the remaining issues into two buckets:

1. **Critical — blocks ATR/trading**: `pipeline_not_stuck` (guardian can't run), `SKY NULL entry_price` (ATR can't compute)
2. **Infrastructure — non-blocking**: `signal_db` missing (signals schema), `prices.json` truncated

---

## Step-by-Step Plan

### Step 1: Fix `pipeline_not_stuck` — Clear stale guardian lock

**File**: `/tmp/hermes-guardian.lock` (or equivalent)

**Problem**: The guardian pipeline has a stale process lock that's 224 minutes old. The lock file prevents new guardian cycles from running, which means `reconcile_tp_sl` never fires — no ATR-based TP/SL updates are being placed on HL.

**Fix**:
```bash
# Identify and remove stale guardian lock
ls -la /tmp/hermes-guardian*.lock
cat /tmp/hermes-guardian.lock  # check for PID
kill -0 <PID> 2>/dev/null && echo "process alive" || echo "process dead — safe to remove"
rm -f /tmp/hermes-guardian.lock
```

**Verification**: Run `smoke_test.py --critical` — `pipeline_not_stuck` should flip to ✅.

---

### Step 2: Fix `SKY(LONG)` NULL entry_price

**Files**: `hl-sync-guardian.py` (orphan recovery), `position_manager.py` (trade creation)

**Problem**: `SKY` has a paper trade with `entry_price = NULL`. This prevents `_compute_dynamic_sl` from computing an ATR-based stop loss (division by entry_price). The trade may have been created as an orphan with malformed data.

**Diagnosis**:
```python
# Run this to see the full SKY trade record
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute(\"SELECT id, token, entry_price, direction, status, amount_usdt, leverage FROM trades WHERE token='SKY' AND status='open'\")
print(cur.fetchall())
"
```

**Fix Options**:
- **Option A (close and re-entry)**: Close the NULL-entry SKY paper trade at current market price, then let the signal system re-generate a fresh entry with proper entry_price.
- **Option B (patch entry_price)**: If the correct entry price can be determined from HL fills, backfill `entry_price` from HL trade history.
- **Option C (self-close only)**: Mark SKY as a SKIP_COIN temporarily so `clean_all_tpsl_orders` is bypassed and `self_close_watcher` handles it.

**Recommendation**: Option A — close the malformed trade, accept the PnL impact, and let the signal regenerate clean.

---

### Step 3: Investigate `paper-hl-sync: 'str' object has no attribute 'get'`

**File**: Likely in `hyperliquid_exchange.py` or `hype_cache.py`

**Problem**: `get_open_hype_positions_curl()` is returning a string instead of a dict somewhere in the paper-HL sync path.

**Diagnosis**:
```bash
grep -n "get_open_hype_positions_curl\|paper.*hl\|hl.*positions" /root/.hermes/scripts/hl-sync-guardian.py | head -20
```

**Fix**: The function likely needs a type guard — wrap response in `isinstance(result, dict)` check before calling `.get()`.

---

### Step 4: Fix `signal_db` — Initialize signals table

**Files**: `signal_schema.py` (or `init_db.py`)

**Problem**: The PostgreSQL `signals` table does not exist. The smoke test tries `SELECT COUNT(*) FROM signals` on both SQLite and PG.

**Fix**:
```bash
# Find and run the schema init script
python3 /root/.hermes/scripts/init_db.py  # if it exists and works
# OR
psql $(python3 -c "from _secrets import BRAIN_DB_DICT; print(BRAIN_DB_DICT['dsn'])") -c "CREATE TABLE IF NOT EXISTS signals (...);"
```

**Risk**: The schema may have changed since the last init. Need to verify the current schema against what `signal_schema.py` expects.

---

### Step 5: Fix `prices.json` truncated (only 190 tokens)

**File**: `hype_cache.py` or wherever `prices.json` is written

**Problem**: `prices.json` has only 190 tokens instead of ~229. This means 39 tokens have stale/missing prices, which would cause `get_mid_price()` to return None for those tokens — breaking ATR computation.

**Diagnosis**:
```python
import json
with open('/root/.hermes/data/prices.json') as f:
    data = json.load(f)
tokens_in_prices = set(data.get('prices', {}).keys())
expected = set(open('/root/.hermes/data/tokens.txt').read().splitlines()) if exists else set()
missing = expected - tokens_in_prices
print(f"Missing {len(missing)} tokens: {list(missing)[:10]}")
```

**Fix**: Re-run the price fetch cycle. If the pipeline is stuck (Step 1), fixing that may automatically repopulate prices.json.

---

## Files Likely to Change

| File | Change |
|---|---|
| `/tmp/hermes-guardian.lock` | Delete (lock removal only) |
| `/root/.hermes/scripts/hl-sync-guardian.py` | `paper-hl-sync` type guard fix; orphan trade handling |
| `/root/.hermes/scripts/hyperliquid_exchange.py` | `get_open_hype_positions_curl` return type check |
| `/root/.hermes/scripts/signal_schema.py` | `init_db` to create missing tables |
| `/root/.hermes/data/prices.json` | Regenerate via pipeline |

## Risks / Tradeoffs

- **Risk**: Closing SKY paper trade with NULL entry may trigger a realized loss — even if the position was profitable, the NULL entry makes PnL calculation wrong.
- **Mitigation**: Close SKY at current market price (best estimate), log as `guardian_cleanup`, do not update PnL stats.
- **Risk**: `signal_db` table creation may conflict with existing schema assumptions — check `signal_schema.py` first.
- **Open Question**: Is `paper-hl-sync` blocking `reconcile_tp_sl` from running, or is it a non-critical warning?

## Validation / Test Plan

1. `python3 /root/.hermes/scripts/smoke_test.py --critical` — all checks pass
2. `python3 /root/.hermes/scripts/wasp.py` — no CRITICAL items
3. `grep -c "NULL entry_price" /root/.hermes/logs/smoke_heal.log` — should be 0
4. `tail -20 /root/.hermes/logs/guardian.log` — confirm guardian is cycling every ~1 min
