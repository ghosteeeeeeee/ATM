# HL-First DB Insert Failure + Signal Rollback Gap

## Pattern

`brain.py` opens position on HL first (`mirror_open()`), then inserts into `brain.trades`. If the DB INSERT raises an exception after `mirror_open()` succeeds:
1. Exception propagates to `decider_run` → logged as "FAILED: Traceback (most recent call last): File brain.py"
2. BUT `mark_signal_executed()` was already called at `decider_run.py:1688` (BEFORE brain.py via atomic `WHERE executed=0`) → signal is **permanently consumed**
3. On retry, `update_signal_decision()` finds `executed=1` → 0 rows affected → signal never retried
4. Guardian orphan detection finds HL has a position with no DB record → closes HL position
5. ORPHAN GUARD skips writing any DB record → **trade exists only in HL fill history**

Result: round-trip HL fill with zero local trace.

**Trigger**: Max positions (5/5) — PostgreSQL connection pool under pressure → INSERT raises connection exception even though `mirror_open()` on HL succeeded.

## Implemented Fix (brain.py add_trade())

### 1. Stale orphan check BEFORE mirror_open

```python
# Query for zombie open trades (failed writes leave hl_entry_price=0 or NULL)
cur_orphan.execute("""
    SELECT id, paper, hl_entry_price, open_time
    FROM trades
    WHERE token=%s AND server=%s AND status='open'
      AND (hl_entry_price IS NULL OR hl_entry_price = 0)
    LIMIT 1
""", (token, server))
orphan_row = cur_orphan.fetchone()
if orphan_row:
    oid, paper_val, hl_ep, open_time = orphan_row
    age_hrs = (datetime.now() - open_time).total_seconds() / 3600
    print(f"[brain.py] {token} stale orphan trade #{oid} "
          f"(paper={paper_val}, hl_ep={hl_ep}, age={age_hrs:.1f}h) — rejecting")
    return None
```

Catches tokens like **ADA #8409** (`hl_entry_price=Decimal('0E-8')`) — a zombie from a prior failed write that would otherwise re-open on HL creating a double-entry.

**Query that catches it**: `WHERE hl_entry_price = 0` correctly finds `Decimal('0E-8')` in PostgreSQL.

### 2. DB INSERT with rollback

```python
try:
    cur.execute("""INSERT INTO trades (...) VALUES (...) RETURNING id""", (...))
    trade_id = cur.fetchone()[0]
    conn.commit()
    print(f"[brain.py] ✅ {hype_token} trade #{trade_id} confirmed on HL")
except Exception as e:
    # mirror_open already succeeded — HL has live position, DB doesn't
    print(f"[brain.py] ❌ DB INSERT FAILED for {hype_token}: {e}")
    conn.rollback()
    from hyperliquid_exchange import mirror_close
    mc = mirror_close(hype_token)
    return None
finally:
    cur.close(); conn.close()
```

**Key**: If DB INSERT fails after `mirror_open()` succeeds, we MUST call `mirror_close()` to undo the HL position. Otherwise HL has a live position with no DB record → phantom trade.

### 3. Connection cleanup on duplicate-check return path (pre-existing bug fixed)

```python
if cur_check.fetchone():
    print(f"[brain.py] {token} already open — rejecting duplicate")
    cur_check.close(); conn_check.close()  # was AFTER unreachable return — now fixed
    return None
cur_check.close(); conn_check.close()
```

## Still Needed

- **`decider_run` rollback on brain.py failure**: When `brain.py add_trade()` returns `None`, `decider_run` should call `rollback_signal_executed()` to restore the signal to APPROVED state so it can be retried on the next cycle. **Not yet implemented.**

## Guardian Step 6 Orphan Close — Now Implemented (2026-05-05)

When guardian orphan detection runs Step 6 to close a true orphan, it now creates a minimal DB record if none exists.

**The problem**: ORPHAN GUARD prevented any INSERT when the orphan was first detected. Step 6 `SELECT id FROM trades WHERE token=%s AND status='open'` found nothing. `close_position_hl()` succeeded on HL but no DB record was created → untraced close.

**Fix — `hl-sync-guardian.py` Step 6 `else` branch (lines 3617-3669)**:
```python
orphan_row = cur_orphan.fetchone()
if orphan_row:
    # Existing record found — close normally
    orphan_id = orphan_row[0]
    close_ok = _close_orphan_paper_trade_by_id(orphan_id, coin, ...)
else:
    # No DB record — brain.py INSERT failed silently. Create minimal guardian_orphan
    # record using HL trade_id (encoded from leverage), then close it.
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
    """, (coin.upper(), direction, entry_px, entry_px, int(lev), trade_id_encoded))
    orphan_id = cur_orphan.fetchone()[0]
    conn_orphan.commit()
    log(f'  Created guardian_orphan trade #{orphan_id} for {coin}', 'WARN')
    close_ok = _close_orphan_paper_trade_by_id(orphan_id, coin, ...)
```

**Verify the record was created**:
```sql
SELECT id, token, guardian_reason, status, exit_price, pnl_pct
FROM trades
WHERE guardian_reason = 'guardian_orphan'
ORDER BY close_time DESC LIMIT 10;
```

## Detection

```sql
-- Stale orphans: open trades with zero/missing HL entry price
SELECT id, token, hl_entry_price, open_time, paper, status
FROM trades
WHERE status='open'
  AND (hl_entry_price IS NULL OR hl_entry_price = 0 OR hl_entry_price::text LIKE '0E%');

-- Pipeline.log signature
grep "FAILED: Traceback (most recent call last):" /root/.hermes/logs/pipeline.log | grep brain.py
```

## Related

- `phantom-trade-debug` SKILL.md section 8 — full ETC/LTC/FET case timeline and remaining gaps
