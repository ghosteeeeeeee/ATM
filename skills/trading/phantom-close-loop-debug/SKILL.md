---
name: phantom-close-loop-debug
description: Fix trades stuck in guardian phantom close loop — missing entry/exit price skips causing infinite cycling
---

# Phantom Close Loop Debug

## Symptoms
- Token stuck in `guardian-missing-tracking.json` with high cycle count (e.g., 46 cycles)
- Guardian log: `Step8 SKIP` + `PHANTOM (no HL confirmation)` + `Skipping trade: missing entry/exit price`
- Trade never closes in DB despite repeated guardian attempts

## Root Cause
Two failure modes are possible — both cause the infinite loop:

**Mode A (exit_price=0):** `_get_hl_exit_price()` fallback chain fails:
1. No HL close fills found (rate-limited)
2. `fallback_price = entry_price = 0.0` (phantom trade has no entry)
3. `hype_cache.get_allMids()` returns 0.0 for token (not in cache)
4. Returns `0.0` → `_close_paper_trade_db` skips because `exit_price <= 0`

**Mode B (entry_price=0, exit_price>0):** Fallback exit price IS found (hype_cache or market price),
but `_close_paper_trade_db` skips because its sanity check fails: `entry_price=0.0` in the DB
is treated as corrupted/missing, and the function refuses to close.
- PURR (2026-04-18): exit_price=0.082 from hype_cache, but entry_price=0.00000000 in DB → SKIP
- Line 2087: `if not entry_price or not exit_price or exit_price <= 0` — entry_price=0 triggers this

Both modes leave the trade open in DB and the token stuck in `guardian-missing-tracking.json`.

## Fix
```bash
# 1. Get current price
python3 -c "import sys; sys.path.insert(0,'/root/.hermes/scripts'); import hype_cache as hc; print(hc.get_allMids().get('TOKEN','<manual_price>'))"

# 2. Close trade in DB
psql -U postgres -d brain -t -c "UPDATE trades SET status='closed', exit_price=<PRICE>, pnl_pct=0, updated_at=NOW() WHERE id=<ID> AND status='open'"

# 3. Remove from guardian-missing-tracking.json
python3 -c "
import json
d = json.load(open('/root/.hermes/data/guardian-missing-tracking.json'))
if 'TOKEN' in d: del d['TOKEN']
json.dump(d, open('/root/.hermes/data/guardian-missing-tracking.json','w'), indent=2)
"
```

## Files Involved
- `/root/.hermes/scripts/hl-sync-guardian.py` — `_get_hl_exit_price()` (line ~800), `_close_paper_trade_db()` (line ~2021)
- `/root/.hermes/data/guardian-missing-tracking.json`
- PostgreSQL `brain.trades` table
