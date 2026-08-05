---
name: duplicate-trades-debug
description: Debug and fix duplicate closed trades in Hermes PostgreSQL database — race conditions in guardian sync flow
triggers:
  - duplicate closed trades
  - guardian creates two closes same token
  - phantom trades in brain database
  - paper=False and paper=True duplicates
---

# Debugging Duplicate Closed Trades in Hermes

## When to Use
- Duplicate closed trades appearing (same token/direction/entry, different exit prices)
- `guardian_closed=TRUE` flag set but trade still open
- Profit-monster or guardian creating paper=False phantom closes
- Any race condition in the guardian sync flow

## Investigation Steps

### Step 1 — Find duplicate groups
```bash
sudo -u postgres psql -d brain -c "
SELECT token, direction, entry_price, COUNT(*) as cnt
FROM trades 
WHERE server='Hermes' AND status='closed'
GROUP BY token, direction, entry_price 
HAVING COUNT(*) > 1;
"
```

### Step 2 — Inspect duplicate records
```bash
sudo -u postgres psql -d brain -c "
SELECT * FROM trades 
WHERE server='Hermes' AND token='<TOKEN>' AND direction='<DIR>' 
AND entry_price=<PRICE> AND status='closed'
ORDER BY id;
"
```

### Step 3 — Read guardian close flow
File: `/root/.hermes/scripts/hl-sync-guardian.py`

Key functions to audit:
- `process_guardian_closes` (Step 8, ~line 2860)
- `_close_paper_trade_db` (~line 890)
- `add_orphan_trade` (~line 545)
- `_close_orphan_paper_trade_by_id` (~line 2140)

### Step 4 — Identify the race condition pattern

The classic bug:
```python
# BAD — separate queries = race condition
cur.execute("UPDATE trades SET guardian_closed=TRUE WHERE id=%s", (trade_id,))
cur.execute("UPDATE trades SET status='closed', exit_price=%s WHERE id=%s", (exit_px, trade_id))
# If crash happens between queries, guardian_closed=TRUE but status='open'
# Next cycle sees guardian_closed=TRUE → tries to close AGAIN → DUPLICATE

# GOOD — atomic update
cur.execute("""
    UPDATE trades 
    SET status='closed', exit_price=%s, guardian_closed=TRUE
    WHERE id=%s
""", (exit_px, trade_id))
```

### Step 5 — Apply atomic fixes

Search for all standalone `guardian_closed=TRUE` pre-UPDATEs in hl-sync-guardian.py:
```bash
grep -n "guardian_closed.*=.*TRUE" /root/.hermes/scripts/hl-sync-guardian.py
```

### Step 6 — Archive before deleting
```python
import json
import datetime
archived = {
    "archived_at": datetime.datetime.utcnow().isoformat(),
    "reason": "duplicate closed trades cleanup",
    "trades": [...]  # full trade dicts
}
with open(f"/root/.hermes/data/archive_duplicates_{timestamp}.json", "w") as f:
    json.dump(archived, f, indent=2, default=str)
```

### Step 7 — Delete duplicates, keep best exit
- LONG: keep record with higher exit price
- SHORT: keep record with lower exit price
- Same exit: prefer `paper=False` if it has real PnL
- **IMPORTANT** — trades with different entry prices are genuinely separate trades (different signals, different entries) — keep both.

### Step 8 — Restart guardian
```bash
sudo systemctl restart hermes-hl-sync-guardian
```

## Duplicate Patterns Seen

### Pattern 1: Guardian race condition (HL_SL_CLOSED/HL_CLOSED)
- **Symptom**: Same `paper=False` trade appears twice with different exit prices
- **Cause**: `guardian_closed=TRUE` pre-UPDATE runs, then crash/exception, next cycle retries
- **Fix**: Atomic update merging flag + status in one UPDATE

### Pattern 2: Orphan paper + real close (guardian_orphan)
- **Symptom**: `guardian_orphan` + `atr_sl_hit` for same token
- **Cause**: `reconcile_hype_to_paper` creates orphan paper trades without `guardian_closed=TRUE`
- **Fix**: Set `guardian_closed=TRUE` in `add_orphan_trade` INSERT

### Pattern 3: profit-monster paper=False duplicates
- **Symptom**: `paper=False` closed at entry price, `paper=True` closed with real exit
- **Cause**: Signal system creates both when `live_trading` enabled, profit-monster closes them independently
- **Fix**: Delete the phantom `paper=False` with zero PnL, keep `paper=True`

### Pattern 4: signal_gen + guardian orphan race (same entry price, different sources)
- **Symptom**: Two closed trades for same token — one with `source='hzscore,pct-hermes+'`, `paper=False`, `close_reason=HL_CLOSED`; one with `source=NULL`, `paper=True`, `close_reason=guardian_orphan`. Same entry_price, same direction. Different sizes ($10 vs $50).
- **Cause**: `signal_gen` opens a trade, guardian's Step 3 runs in the same ~1min cycle and sees the HL position but NO matching DB record. Guardian creates its own orphan paper record at the same price. Other systems then independently close the orphan.
- **Fix (2026-04-16) — THREE fixes applied**:
  1. `is_guardian_close=TRUE` in `add_orphan_trade()` INSERT — prevents downstream systems from processing guardian orphans
  2. PostgreSQL DB pre-check in Step 3 orphan detection — skip orphan creation if matching DB record exists
  3. ROOT FIX: `continue` bug — the duplicate check detected an existing orphan, updated it, then `continue`d WITHOUT closing the orphan HL position or closing the orphan paper trade. Fix: replace `continue` with full close logic.

### Pattern 5: Open positions missing from HL (429 false positive)
- **Symptom**: Real HL position exists but guardian reports it as "missing" → closes DB trade
- **Cause**: HL rate-limit 429 on `get_open_hype_positions_curl()` makes real positions invisible for 1 cycle
- **Fix**: Guardian tracks `missing_cycles` per token. Only closes after 2+ consecutive missing cycles.

### Pattern 6: Duplicate guardian PROCESSES causing double-closes
- **Symptom**: Same token closed twice within seconds — two HARD-HARD_SL fires
- **Cause**: Stale guardian process still running alongside new systemd-managed guardian
- **Fix**: `kill <STALE_PID>`. After restarting, verify: `ps aux | grep hl-sync-guardian | grep -v grep` should show exactly 1 guardian process.

## Database Connection
```python
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
```

**IMPORTANT:** SQLite DBs in `/root/.hermes/data/` do NOT contain authoritative trade data. Always query PostgreSQL `brain` database directly.

## Critical Flag Meanings
- `guardian_closed=TRUE`: Guardian has marked this trade for closure (intent set, closure may not have completed)
- `guardian_closed=FALSE`: Guardian hasn't touched this trade
- `paper=True`: Paper trade (no real execution)
- `paper=False`: Live or simulated trade tracked as live
