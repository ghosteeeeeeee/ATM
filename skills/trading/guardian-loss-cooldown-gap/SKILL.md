---
name: guardian-loss-cooldown-gap
description: Debug and fix loss cooldown gaps when trades close via hl-sync-guardian instead of position_manager. Guardian closes trades with HL_SL_CLOSED/PHANTOM_CLOSE/MANUAL_CLOSE reasons but was NOT recording loss cooldowns — allowing immediate re-entry after losses.
version: 1.0.0
author: Hermes Agent
created: 2026-04-20
tags: [trading, hyperliquid, guardian, cooldown, bug-fix]
notes:
  - Guardian uses _close_paper_trade_db() for ALL close paths (Step8 orphan handling)
  - position_manager uses _check_atr_tp_sl_hits() for ATR-based closes
  - close_position.py (manual) has its own cooldown recording
  - If cooldown logic isn't in _close_paper_trade_db, any close reason that computes pnl_usdt < 0 will NOT record a cooldown
  - Always add cooldown recording IN _close_paper_trade_db itself, not at individual call sites
  - CRITICAL 2026-04-22: _close_paper_trade_db has TWO independent cooldown paths that can diverge
  - CRITICAL 2026-04-22: position_manager.close_paper_position may NOT write PostgreSQL cooldowns
    Example: SCR:LONG had losing trade pnl=-0.0894% but NO cooldown in either store (guardian_closed=False)
---

# Guardian Loss Cooldown Gap — Investigation & Fix

## Symptoms

- A token (e.g. FIL) takes a loss via `HL_SL_CLOSED` in `hl-sync-guardian.py`
- `loss_cooldowns.json` does NOT have an entry for that token+direction
- The decider immediately opens a new trade in the same direction
- T sees: "FIL just lost and got another trade right away"

## Root Cause

Loss cooldown recording was scattered across 3 files with inconsistent coverage:

| File | Close Reason | Calls set_loss_cooldown? |
|------|-------------|-------------------------|
| `position_manager.py` | ATR SL/TP hits | ✅ YES (line ~946) |
| `hl-sync-guardian.py` | HL_SL_CLOSED, PHANTOM_CLOSE | ❌ NO (before fix) |
| `hl-sync-guardian.py` | ORPHAN_PAPER, MAX_POSITIONS, etc. | ❌ NO |
| `close_position.py` | manual_close | ✅ YES |

`hl-sync-guardian.py` was closing trades with computed losses but **never recording cooldowns**.

## Investigation Steps

1. **Check loss_cooldowns.json** — see if the token+direction is absent:
   ```bash
   cat /var/www/hermes/data/loss_cooldowns.json | jq '.["FIL:SHORT"]'
   ```

2. **Check the trade's close_reason** — if it's `HL_SL_CLOSED` or `PHANTOM_CLOSE`, the guardian closed it:
   ```sql
   SELECT id, token, direction, pnl_pct, close_reason, exit_reason
   FROM trades WHERE token='FIL' ORDER BY id DESC LIMIT 3;
   ```

3. **Check the guardian log** for the close:
   ```bash
   grep "HL_SL_CLOSED\|PHANTOM_CLOSE\|FIL" /root/.hermes/logs/sync-guardian.log | tail -20
   ```

4. **Verify position_manager has the call but guardian doesn't:**
   ```bash
   grep -n "set_loss_cooldown" /root/.hermes/scripts/position_manager.py
   grep -n "set_loss_cooldown\|record_loss_cooldown" /root/.hermes/scripts/hl-sync-guardian.py
   ```

## Fix Applied (2026-04-20)

Added cooldown recording **directly in `_close_paper_trade_db()`** — the single function that ALL guardian close paths call. This is the correct architectural fix because:

- Centralizes cooldown logic in one place
- Any new close reason added to `_close_paper_trade_db` automatically gets cooldown recording
- No need to remember to add cooldown calls at individual call sites

**Added to `hl-sync-guardian.py`:**
1. Cooldown constants and helper functions (`_load_cooldowns`, `_save_cooldowns`, `_is_loss_cooldown_active`, `_record_loss_cooldown`)
2. In `_close_paper_trade_db` after `conn.commit()`:
   ```python
   if final_pnl_usdt < 0:
       _record_loss_cooldown(token, direction)
   ```

## Why Not Import from position_manager?

`position_manager.py` and `hl-sync-guardian.py` are separate service entry points. Importing `set_loss_cooldown` from position_manager into guardian creates a dependency that complicates deployment (guardian can't start if position_manager has an import error). The cleanest approach is duplicating the lightweight cooldown helpers in guardian — they just read/write a JSON file.

## Prevention

When adding a new close reason to `_close_paper_trade_db` or a new close path to `hl-sync-guardian.py`, always ask: "Does this close compute a PnL? If yes, should it record a cooldown?" The cooldown recording is already in `_close_paper_trade_db` post-commit — as long as PnL is computed correctly there, cooldown is automatic.

---

## Pattern: TWO Independent Cooldown Stores (Critical Architecture)

`signal_gen.py` uses `get_cooldown()` which checks **TWO stores in order**:

1. **PostgreSQL `signal_cooldowns`** — PRIMARY for signal blocking. Checked FIRST.
2. **`loss_cooldowns.json`** — SECONDARY. Used as fallback if PostgreSQL has no entry.

**Key discovery (2026-04-22):**

`_close_paper_trade_db` writes cooldowns to BOTH stores independently:
- Lines ~2392-2393: `if final_pnl_usdt < 0: _record_loss_cooldown(token, direction)` → writes to `loss_cooldowns.json` (exponential backoff, streak-based)
- Lines ~2352-2355: Direct SQL INSERT into `signal_cooldowns` table (flat 1h cooldown)

BUT `_close_orphan_paper_trade_by_id` calls `_record_trade_outcome()` → `set_cooldown()` for PostgreSQL — a SEPARATE path from the direct INSERT at lines 2352-2355.

**Gap found:** If `_close_paper_trade_db` reaches the PostgreSQL INSERT (lines 2352-2355) but `_record_loss_cooldown` at line 2392 is NOT called (e.g., a code path where `final_pnl_usdt < 0` check fails), then PostgreSQL gets a cooldown but JSON doesn't. Then `get_cooldown()` finds PostgreSQL first and uses it — BUT the expiry times and durations differ (1h flat vs exponential 10-40min).

**Root issue:** The TWO stores have DIFFERENT expiry durations:
- PostgreSQL: flat 1 hour (from `set_cooldown` or direct INSERT)
- JSON: exponential 10-40 minutes (streak-based from `_record_loss_cooldown`)

This means the SAME losing trade creates TWO different cooldowns with different durations in two different stores. If one expires but the other doesn't, `get_cooldown()` might still block (if PostgreSQL still active) or might miss (if JSON expired but PostgreSQL was never written).

**Prevention:** After any change to `_close_paper_trade_db`, verify BOTH paths execute for ALL losing trades:
```bash
grep -n "loss_cooldowns\|signal_cooldowns\|INSERT INTO signal" /root/.hermes/scripts/hl-sync-guardian.py
```
Always check that the PostgreSQL path AND the JSON path are BOTH reached for losing trades. Any divergence causes the two stores to get out of sync.

**Correct Diagnosis (PostgreSQL primary):**

```bash
# Check PostgreSQL — what signal_gen actually respects
python3 -c "
import psycopg2
from datetime import datetime, timezone
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute('''
    SELECT token, expires_at, reason, direction,
           expires_at > NOW() as is_active
    FROM signal_cooldowns
    WHERE token LIKE \"PEOPLE%\"
    ORDER BY expires_at DESC
''')
rows = cur.fetchall()
now = datetime.now(timezone.utc)
print(f'Current UTC: {now}')
for r in rows:
    remaining = (r[1] - now).total_seconds()
    status = f'remaining={remaining/60:.1f}min' if remaining > 0 else 'EXPIRED'
    print(f'  {r[0]} | dir={r[3]} | {status} | reason={r[2]}')
conn.close()
"

# Check loss_cooldowns.json (guardian's internal tracking)
python3 -c "
import time, json
now = time.time()
with open('/var/www/hermes/data/loss_cooldowns.json') as f:
    data = json.load(f)
entry = data.get('PEOPLE:LONG')
if entry:
    remaining = entry['expires'] - now
    print(f'JSON cooldown: {remaining/60:.1f}min remaining, streak={entry[\"streak\"]}')
else:
    print('No entry in loss_cooldowns.json')
"
```

**Fix Options:**

Option A — Make `get_cooldown()` also check `loss_cooldowns.json`: Add guardian's `_is_loss_cooldown_active()` check in signal_gen alongside PostgreSQL check. If EITHER says cooldown is active, skip the token.

Option B — Consolidate: Make guardian write only to PostgreSQL with streak-based duration. Remove `loss_cooldowns.json` entirely. This is the cleanest but requires updating guardian's cooldown logic.

**Verification after fix:**

After a loss, both PostgreSQL and loss_cooldowns.json should show active cooldowns with consistent expiry times.
