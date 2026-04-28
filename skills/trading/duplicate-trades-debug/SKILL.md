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

Key fields to compare: `paper`, `guardian_closed`, `close_reason`, `exit_price`, `pnl_usdt`, `hl_entry_price`

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

Each one should be inside a closing `UPDATE trades SET ...` — not a separate query.

### Step 6 — Verify all paths set guardian_closed atomically
- `_close_paper_trade_db` — should set `guardian_closed=TRUE` in the closing UPDATE
- `add_orphan_trade` — should set `guardian_closed=TRUE` in INSERT (orphan paper trades are pre-closed)
- `_close_orphan_paper_trade_by_id` — should set `guardian_closed=TRUE` in closing UPDATE
- `process_guardian_closes` Step 8 — all three branches should use atomic updates

### Step 7 — Archive before deleting
```python
import json
import datetime
# Fetch duplicates to archive
archived = {
    "archived_at": datetime.datetime.utcnow().isoformat(),
    "reason": "duplicate closed trades cleanup",
    "trades": [...]  # full trade dicts
}
with open(f"/root/.hermes/data/archive_duplicates_{timestamp}.json", "w") as f:
    json.dump(archived, f, indent=2, default=str)
```

### Step 8 — Delete duplicates, keep best exit
Keep logic:
- LONG: keep record with higher exit price
- SHORT: keep record with lower exit price
- Same exit: prefer `paper=False` if it has real PnL, otherwise `paper=True`
- **IMPORTANT — distinguish true duplicates from genuine separate trades**: True duplicates have **identical entry prices** but different close reasons/sources. Trades with **different entry prices** are genuinely separate trades (different signals, different entries) — keep both. Example: LAYER trades at 0.0805 vs 0.0835 entry are separate trades, not duplicates. SNX trades at 0.2934 vs 0.2865 entry are separate trades.

### Step 9 — Restart guardian
```bash
sudo systemctl restart hermes-hl-sync-guardian
```

### Step 10 — Verify
```bash
# Check no duplicates
sudo -u postgres psql -d brain -c "SELECT ... HAVING COUNT(*) > 1"
# Check guardian logs
tail -50 /root/.hermes/logs/sync-guardian.log
```

## Duplicate Patterns Seen

### Pattern 1: Guardian race condition (HL_SL_CLOSED/HL_CLOSED)
- **Symptom**: Same `paper=False` trade appears twice with different exit prices
- **Cause**: `guardian_closed=TRUE` pre-UPDATE runs, then crash/exception, next cycle retries
- **Fix**: Atomic update merging flag + status in one UPDATE

### Pattern 2: Orphan paper + real close (guardian_orphan)
- **Symptom**: `guardian_orphan` + `atr_sl_hit` for same token
- **Cause**: `reconcile_hype_to_paper` creates orphan paper trades without `guardian_closed=TRUE`, then Step 8 processes them alongside real closes
- **Fix**: Set `guardian_closed=TRUE` in `add_orphan_trade` INSERT

### Pattern 3: profit-monster paper=False duplicates
- **Symptom**: `paper=False` closed at entry price, `paper=True` closed with real exit
- **Cause**: Signal system creates both when `live_trading` enabled, profit-monster closes them independently
- **Fix**: Delete the phantom `paper=False` with zero PnL, keep `paper=True`

### Pattern 4: signal_gen + guardian orphan race (same entry price, different sources)
- **Symptom**: Two closed trades for same token — one with `source='hzscore,pct-hermes+'`, `paper=False`, `close_reason=HL_CLOSED`; one with `source=NULL`, `paper=True`, `close_reason=guardian_orphan` or `ORPHAN_PAPER`. Same entry_price, same direction. Different sizes ($10 vs $50).
- **Cause**: `signal_gen` → `ai_decider` → `decider_run` → `brain.add_trade()` opens a trade. Guardian's Step 3 runs in the same ~1min cycle and sees the HL position but NO matching DB record (because signal_gen's trade hasn't been written yet). Guardian creates its own orphan paper record at the same price. The orphan has `signal=NULL` and `guardian_closed=FALSE` — which passes the hot-set filter in Step 7. Then `profit-monster` or another system independently closes the orphan, creating a duplicate.
- **Why reconciled_state doesn't catch it**: `_reconciled_state` (JSON file) only tracks guardian-opened trades. signal_gen's trades bypass guardian entirely — they're never written to reconciled_state.
- **Fix (2026-04-16) — THREE complementary fixes applied**:

  **Fix 1 — `is_guardian_close=TRUE` in `add_orphan_trade()` INSERT** (`hl-sync-guardian.py` ~line 571): Sets `is_guardian_close=TRUE` on guardian-created orphan trades. The Step 7 hot-set filter skips trades with `is_guardian_close=TRUE`, preventing downstream systems (profit-monster, etc.) from independently closing them.

  **Fix 2 — PostgreSQL DB pre-check in Step 3 orphan detection** (`hl-sync-guardian.py` ~line 560): Before creating an orphan, check the `trades` DB directly for existing open paper trades for this coin. If found, skip orphan creation and update the existing record instead.

  **Fix 3 — ROOT FIX: The `continue` bug** (`hl-sync-guardian.py` ~lines 925-962): The duplicate check detected an existing orphan paper trade, updated its entry/direction/leverage, then `continue`d — **without closing the orphan HL position or closing the orphan paper trade**. The paper trade stayed open. Other systems (`profit-monster`, `histogram_fading_fas`, `stale_bull_exhausted`) then independently closed it, creating a second closed record. Fix: replace `continue` with full close logic — call `close_position_hl()` for the orphan HL position AND `_close_paper_trade_db()` using the existing trade ID. This atomically closes both with no new record created.

- **Key insight**: This is a logical race, not a database race. signal_gen and guardian run in the same pipeline minute but write different records to the same DB table. The DB has no constraint preventing it. The `is_guardian_close` flag + the `continue` fix together form a complete solution: the flag prevents other systems from processing guardian orphans; the `continue` fix ensures orphan HL positions are properly closed instead of left dangling.

### Pattern 5: Open positions missing from HL but guardian closes them (429 false positive)
- **Symptom**: Real HL position exists but guardian reports it as "missing" → closes DB trade
- **Cause**: HL rate-limit 429 on `get_open_hype_positions_curl()` makes real positions invisible for 1 cycle
- **Fix**: Guardian now tracks `missing_cycles` per token. Only closes a trade after 2+ consecutive missing cycles (see Pattern 1 fix above)

### Pattern 6: Duplicate guardian PROCESSES causing double-closes
- **Symptom**: Same token closed twice within seconds — two HARD-HARD_SL fires, two FILL CONFIRMED entries, two signal_outcomes records
- **Cause**: A stale guardian process (pre-systemd migration, started manually/nohup) is still running alongside the new systemd-managed guardian. Both execute the same sync logic simultaneously, both see the same positions, both fire closes.
- **Detection**: `ps aux | grep hl-sync-guardian | grep -v grep` shows 2+ processes. Compare `systemctl show hermes-hl-sync-guardian.service --property=MainPID` against running PIDs — the stale one won't match the systemd MainPID.
- **Fix**: `kill <STALE_PID>` to terminate the duplicate. Systemd should be the only owner of the guardian process.
- **Prevention**: After restarting the guardian service, always verify: `ps aux | grep hl-sync-guardian | grep -v grep` should show exactly 1 guardian process (plus its wrapper bash process). The wrapper bash PID will differ from the Python MainPID reported by systemd.
- **Also check**: Other services for the same duplication pattern (`ps aux | grep -E "run_pipeline|signal_gen" | grep -v grep`). MCP servers commonly bloat too — `ps aux | grep hermes-coding-mcp/server.py | grep -v grep | wc -l` should be 1.

## Database Connection
```python
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
```
**IMPORTANT:** SQLite DBs in `/root/.hermes/data/` do NOT contain authoritative trade data. Always query PostgreSQL `brain` database directly via `sudo -u postgres psql -d brain` for trades.

## Common Issues Found
- `trades` — main trade table, `server='Hermes'` for runtime trades. **Column is `signal_reason`, NOT `signal`** — web JSON maps `signal_reason` → `signal`, so if it reads wrong column the signal shows null.
- `signal_history` — signal log
- `trailing_stops.json` — separate JSON file (not in PostgreSQL)

## Common Issues Found

### ONDO entry_price=0 (phantom fill bug)
- PostgreSQL shows `entry_price=0.00000000` but guardian log shows real entry ~$0.26062
- Guardian creates trade BEFORE writing to PostgreSQL — the HL fill record exists, DB insert has wrong price
- Fix: Update PostgreSQL manually with correct entry from guardian log
```bash
sudo -u postgres psql -d brain -c "UPDATE trades SET entry_price=<REAL_ENTRY> WHERE id=<ID>;"
```

### AAVE signal=null in web JSON
- `trades.json` served by nginx: `/var/www/hermes/data/trades.json` (NOT `/root/.hermes/data/trades.json`)
- PostgreSQL column is `signal_reason`, not `signal`
- `hermes-trades-api.py` must read `signal_reason` and map it to `signal` in JSON output
- Check: grep for `signal_reason` in hermes-trades-api.py

## Critical Flag Meanings
- `guardian_closed=TRUE`: Guardian has marked this trade for closure (intent set, closure may not have completed)
- `guardian_closed=FALSE`: Guardian hasn't touched this trade
- `paper=True`: Paper trade (no real execution)
- `paper=False`: Live or simulated trade tracked as live
