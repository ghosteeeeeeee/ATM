# Guardian Orphan Closing + Closing Marker Leak (2026-05-08)

## Files Analyzed
- `hl-sync-guardian.py` — 4,092 lines (4092), UNCOMMITTED changes on disk
- `brain.py` — 937 lines, UNCOMMITTED changes on disk
- `archive-trades.py` — 515 lines, NOT in git (untracked file)
- `signal_compactor.py` — 1,489 lines, modified May 8 16:31

---

## P0: Guardian Orphan Path — Creates + Closes in One Cycle (Structural Bug)

**File:** `hl-sync-guardian.py` lines 3638–3678

When guardian finds an HL position with no matching DB record, the new orphan creation block:
1. Creates a minimal `guardian_orphan_insert` record in PostgreSQL
2. Immediately calls `_close_orphan_paper_trade_by_id()` in the SAME cycle
3. Uses `trade_id = lev * 1000000` (hardcoded encoding, not auto-increment)

```python
# Lines 3644-3662 (new block added in uncommitted changes):
cur_orphan.execute("""
    INSERT INTO trades (
        token, direction, entry_price, hl_entry_price,
        amount_usdt, leverage, status, exchange,
        signal_reason, open_time, paper,
        trade_id, is_guardian_close, guardian_reason
    ) VALUES (
        %s, %s, %s, %s,
        50.0, %s, 'open', 'Hyperliquid',
        'guardian_orphan_insert', NOW() - INTERVAL '1 second', FALSE,
        %s, TRUE, 'guardian_orphan'
    ) RETURNING id
""", (
    coin.upper(), direction, entry_px, entry_px,
    int(lev),
    int(lev * 1000000)  # trade_id from HL leverage encoding
))
```

**Problem:** This bypasses the ORPHAN GUARD at line 1145-1148 which was specifically designed to prevent guardian from creating trades. The orphan path now creates AND closes in one cycle — defeating the purpose of the guard.

**The `ORPHAN GUARD` comment (line 1145-1148) says:**
```
# ORPHAN GUARD (2026-04-16): Guardian must NOT create paper trades for orphan
# HL positions — only decider-run can open new trades. Log and skip.
log(f'  ⛔ {coin} HL position has no DB record — guardian cannot create trades (skip)')
continue
```

But the new block at 3638-3678 does the exact opposite: it creates a record when none exists. This is a direct contradiction of the ORPHAN GUARD intent.

---

## P1: Closing Marker Leak on Orphan Path

**File:** `hl-sync-guardian.py` lines 3595-3601

The closing marker is saved at line 3601 BEFORE the orphan check at line 1145-1148 runs:

```python
# Step 6 orphan close loop — line 3589:
for coin in orphans:
    _CLOSED_HL_COINS.add(coin.upper())
    p = hl_pos.get(coin, {})
    entry_px = float(p.get('entry_px', 0))
    direction = p.get('direction', 'LONG')
    lev = float(p.get('leverage', 1)) or 1

    # RACE-CONDITION FIX: Write closing marker BEFORE market_close.
    # This tells signal_compactor/decider_run "guardian is closing this token"
    _save_closing_marker(coin)  # ← SAVED HERE at line 3601

    success = close_position_hl(coin, 'guardian_orphan')
```

The orphan check (lines 1104-1148) runs much earlier in the sync cycle (Step 3: reconcile). By the time Step 6 executes, the marker has already been saved. If the orphan check did `continue` (no DB record found), the marker at line 3601 was already written for a token that will never be closed by guardian.

**However:** The orphan check at lines 1104-1148 runs in Step 3 BEFORE the orphan loop at line 3589. The `orphans` list passed to Step 6 is determined by `_find_orphan_hl_positions()` which runs in Step 3. So orphan tokens that have no DB record may not even be in the `orphans` list passed to Step 6.

The real leak path is: token IS in `orphans` → closing marker saved at line 3601 → then the DB record check at line 3617 finds no record → new INSERT block at 3638 creates record → `_close_orphan_paper_trade_by_id()` closes it → marker cleared. This works correctly.

The marker leak happens when: token IS in `orphans` → marker saved → DB record check finds no record → but the new INSERT block at 3638-3678 runs → `_close_orphan_paper_trade_by_id()` returns `False` (can't find the just-created record by the time it runs, or HL fill not available) → marker stays active → decider_run stays blocked.

---

## P1: `_close_orphan_paper_trade_by_id` Returns False on Unmatched Record

**File:** `hl-sync-guardian.py` lines 2525–2673

When `_close_orphan_paper_trade_by_id()` is called with an `orphan_id` that has no matching `id` in the `trades` table (either because the record was never created, or was created with a different ID), it returns `False`:

```python
# Line 2653: dedup check — if rowcount == 0, returns False
if cur.rowcount == 0:
    log(f'  Dedup: orphan trade #{trade_id} ({token}) already closed, skipping', 'WARN')
    conn.rollback()
    close_success = True  # Already closed is OK
else:
    conn.commit()
    close_success = True
```

If the INSERT at 3638-3678 created a record with `trade_id = lev * 1000000` but `_close_orphan_paper_trade_by_id` is called with the auto-increment `id` from the INSERT, they won't match. The function won't find the record and will return `False`, keeping the marker active.

---

## archive-trades.py — DELETE from PostgreSQL (Dangerous)

**File:** `archive-trades.py` lines 497-510

```python
if args.apply:
    print(f"\nArchiving {len(closed_trades)} trades to JSON...")
    n = archive_to_json(closed_trades, dry_run=False)
    print(f"Archived {n} trades to {ARCHIVE_DIR}/")

    # Delete archived trades from PostgreSQL
    ids = [t['id'] for t in closed_trades]
    placeholders = ','.join(['%s' for _ in ids])
    cur = conn_pg.cursor()
    cur.execute(f"DELETE FROM trades WHERE id IN ({placeholders})", ids)
    deleted = cur.rowcount
    conn_pg.commit()
    print(f"Deleted {deleted} trades from PostgreSQL.")
```

**Risk:** If run with `--apply` on a table that is the only source of truth for open positions, this wipes all position tracking. The archive to JSON is separate from the DELETE — the DELETE is what makes it dangerous.

**May 8 01:50 archive:** `trades_archive_2026-05-08.json.gz` has 4 entries (ME, ANIME, MORPHO, ADA). This was from a pre-May-8 archive run — the DELETE was already applied, leaving only PURR/XLM in the DB.

**Safe alternative:** Archive to JSON only, NEVER delete from PostgreSQL. The archive is for analysis; PostgreSQL is the system of record.

---

## Confluence Gate — Blocks Single-Source Signals

**File:** `signal_compactor.py` lines 488-498

The confluence gate requires 2+ unique signal types. Single-source signals (even high-confidence `accel-300+`) are permanently blocked.

```python
if unique_signal_types >= 2:
    pass_gate = True
else:
    gate_msg = f'only {unique_signal_types} unique types {{{source}}} — need 2+'
    pass_gate = False
if not pass_gate:
    log(f"  🔒 [CONFLUENCE-GATE-BLOCK] {token} {direction}: {gate_msg}")
    continue  # signal never enters hot-set
```

Evidence from May 8 17:09-17:37 trading.log:
```
ATOM LONG: only 1 unique types {accel-300+} — need 2+
DYM LONG: only 1 unique types {accel-300+} — need 2+
ENS LONG: only 1 unique types {accel-300+} — need 2+
```

**`_signal_type_key()` strips numeric levels** — `rs-s386` and `rs-s406` both collapse to `rs-s` (1 type). Multiple RS levels don't contribute multiple unique types toward confluence.

---

## PostgreSQL State After Incident

```
id=8774, token=XLM, status=closed, pnl=0.00, close_reason=guardian_orphan
id=8780, token=PURR, status=closed, pnl=0.00, close_reason=guardian_orphan
```

Both trades have `is_guardian_close=True`, `trade_id=3000000/5000000`. These are the PURR/XLM guardian orphans from before the May 8 incident. The PostgreSQL `trades` table has no other records — all other trades were either never recorded (orphan closes with no DB record) or were archived.

---

## brain.py Uncommitted Changes

Key additions in uncommitted `brain.py`:

1. **Loss cooldown system (lines 15-44):** `_record_loss_cooldown()` called on `close_trade()` when PnL < 0. Writes to `LOSS_COOLDOWN_FILE` with FileLock. Exponential backoff on streak.

2. **Stale orphan check (lines 413-431):** Before INSERT, checks for existing open trade with `hl_entry_price IS NULL`. If found, rejects the new trade to prevent double-entry.

3. **DB INSERT exception handler (lines 465-493):** If PostgreSQL INSERT fails after HL position opened, calls `mirror_close()` to roll back HL position. Critical safety net.

4. **14 new signal parameter fields in INSERT:** `signal_z_score`, `signal_rsi_14`, `signal_macd_hist`, etc. Added to capture signal context at entry.

---

## Diagnostic Commands

```bash
# Check PostgreSQL trades state
psql 'host=/var/run/postgresql dbname=brain user=postgres' -t -c \
  "SELECT id, token, status, pnl_usdt, close_reason FROM trades ORDER BY id;"

# Check closing markers
cat /root/.hermes/data/guardian-closing-markers.json 2>/dev/null

# Check archive directory
ls -latr /root/.hermes/archive/trades/ | tail -5

# Check guardian log
tail -20 /root/.hermes/logs/sync-guardian.log

# Check pipeline log for confluence blocks
grep "CONFLUENCE-GATE-BLOCK" /root/.hermes/logs/pipeline.log | tail -10

# Check git status of key files
cd /root/.hermes && git status --short scripts/brain.py scripts/hl-sync-guardian.py
```
