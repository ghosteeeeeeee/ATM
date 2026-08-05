---
name: closed-trades-eval
description: Audit closed trades for bogus zero-PnL entries, delete them, then run blocklist-decision on all remaining loss tokens. Produces a cleaned trade history and updated blacklist.
---

# Closed Trades Eval Skill

## Prerequisites
- SQLite signals DB: `/root/.hermes/data/signals_hermes_runtime.db`
- PostgreSQL brain DB: `host=/var/run/postgresql, dbname=brain, user=postgres, password=Brain123` (for blocklist lookups only)
- Constants file: `/root/.hermes/scripts/hermes_constants.py`
- The canonical `signal_outcomes` table is in SQLite — NOT in PostgreSQL brain DB
- The `signal_outcomes` table does NOT have a `close_reason` column — do not look for one

## Critical Bug: BRAIN_DB typo in hl-sync-guardian.py

**ALWAYS check and fix first:** Line 312 of `hl-sync-guardian.py` has a typo that breaks phantom close retry:

```python
# WRONG (BRAIN_DB is not defined):
conn = psycopg2.connect(**BRAIN_DB)

# CORRECT:
conn = psycopg2.connect(**BRAIN_DB_DICT)
```

This typo causes phantom close backfill to fail every cycle, creating new zero-PnL rows on each retry instead of updating the original trade. Fix it before auditing.

## Process

### Phase 1: Audit Zero-PnL Phantom Entries

**Zero-PnL entries are NOT duplicates — they are phantom close retries.**

The guardian's `_close_orphan_paper_trade_by_id` is called each cycle for phantom positions. If no HL fill is found (`hl_exit_px == 0.0`), the function returns early, but other code paths can still fire and create zero-PnL rows. Each guardian retry cycle adds another row.

**Step 1a — Identify zero-PnL entries:**
```python
c.execute("""
    SELECT id, token, direction, signal_type, pnl_pct, pnl_usdt, created_at
    FROM signal_outcomes
    WHERE pnl_pct = 0 AND pnl_usdt = 0
    ORDER BY created_at
""")
```
Print count and list. These are phantom entries.

**Step 1b — Delete zero-PnL entries:**
```python
c.execute("DELETE FROM signal_outcomes WHERE pnl_pct = 0 AND pnl_usdt = 0")
conn.commit()
```

### Phase 2: Signal Type Performance Analysis

After cleanup, run:
```python
c.execute("""
    SELECT signal_type,
           COUNT(*) as n,
           SUM(is_win) as wins,
           ROUND(100.0*SUM(is_win)/COUNT(*), 1) as wr,
           ROUND(SUM(pnl_usdt), 4) as net_pnl
    FROM signal_outcomes
    GROUP BY signal_type
    ORDER BY net_pnl ASC
""")
```

**Dangerous signals to flag:**
- `hzscore,pct-hermes`: 20% WR or below over 5+ trades → candidate for SIGNAL_SOURCE_BLACKLIST
- Any signal with negative net PnL over 10+ trades → investigate

### Phase 3: Blacklist Candidates

```python
c.execute("""
    SELECT token, direction,
           COUNT(*) as n,
           SUM(is_win) as wins,
           ROUND(SUM(pnl_usdt), 4) as net
    FROM signal_outcomes
    GROUP BY token, direction
    HAVING SUM(pnl_usdt) <= -0.50
    ORDER BY net ASC
""")
```

Check each candidate against hermes_constants.py SHORT_BLACKLIST and LONG_BLACKLIST before adding.

### Phase 4: Root Cause Analysis

Calculate directional split:
```python
c.execute("""
    SELECT direction, COUNT(*) as n, SUM(is_win) as wins, SUM(pnl_usdt) as net
    FROM signal_outcomes GROUP BY direction
""")
```

**Common loss patterns:**
1. **Risk/reward imbalance**: avg loss > avg win despite good WR
2. **Directional bias**: one direction dominates and loses
3. **hl_reconcile noise**: many small losses from guardian reconciliation

### Phase 5: Update Constants

Add to SHORT_BLACKLIST or LONG_BLACKLIST with format:
```python
# YYYY-MM-DD: systematic SHORT losses (net loss, phantom trades excluded)
'TOKEN',  # SHORT net: -$X.XX (N losses: sig1 $Y.YY, sig2 $Z.ZZ)
```

Verify: `python3 -m py_compile /root/.hermes/scripts/hermes_constants.py`

### Phase 6: Report

Print summary with signal type performance, directional split, root cause, and blacklist changes.

## Key Insight: Why "Duplicates" Appear

Zero-PnL entries are **multiple INSERT attempts for the same phantom close** across guardian retry cycles — NOT duplicates from concurrent writes. The BRAIN_DB typo makes the backfill fail, so each retry creates a new row instead of updating the original trade. IMX/LONG had 6 entries because the guardian retried 6 times before the HL fill propagated.
