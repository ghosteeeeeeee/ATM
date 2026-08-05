# Ghost Trade Root Cause — add_orphan_trade() Silent Failure (2026-05-18)

## Pattern

HL shows open/close pairs ~10s apart, ~$10 USDC notional, real loss -$0.01 to -$0.13.

## Root Cause Chain

```
reconcile_hype_to_paper() → HL orphan detected
  → add_orphan_trade(token, direction, amount_usdt, entry_px)
    → INSERT INTO trades ... WHERE NOT EXISTS (SELECT 1 FROM trades WHERE token=X AND status='open')
    → condition FALSE (open trade already exists from previous failed cycle)
    → INSERT returns 0 rows (didn't execute)
    → cur.fetchone() returns None
    → function returns None
  → trade_id = None
  → _close_orphan_paper_trade_by_id(None, token, ...)
    → WHERE id=NULL → no match → UPDATE does nothing
    → DB trade stays open, HL position already closed by market_close()
  → Next cycle: orphan recovery runs again → same pattern → ghost trades accumulate
```

## The Core Problem

`add_orphan_trade()` returns `None` for THREE very different situations:
1. INSERT executed successfully → `cur.fetchone()` returns row → return `trade_id`
2. INSERT didn't execute (WHERE NOT EXISTS was false) → `cur.fetchone()` returns None → return `None`
3. Database error / connection failure → exception raised → return `None`

The caller can't distinguish case 2 (intentional non-creation) from case 3 (failure).

## Why It's Not the PnL Inflation Bug

Ghost trades are a **record-keeping bug** — positions opened on HL are never recorded in DB.
PnL discrepancy was a **calculation bug** — DB had records but used wrong notional.

The two bugs are independent. Fixing the PnL calculation doesn't fix the ghost trades.

## Fix Options

### Option A — Return tuple from add_orphan_trade()
```python
def add_orphan_trade(...):
    ...
    if cur.rowcount == 0 and cur.fetchone() is None:
        # Either INSERT didn't run OR it ran and returned no row
        # Check existence explicitly
        cur.execute("SELECT id FROM trades WHERE token=%s AND direction=%s AND status='open'", (token, direction))
        existing = cur.fetchone()
        if existing:
            return (existing[0], "already_exists")  # ← distinguish this case
        return (None, "insert_failed")
    return (trade_id, "created")
```

### Option B — _close_orphan_paper_trade_by_id fallback
When `trade_id is None`, close by `(token, direction, status='open')` instead of `id=NULL`.

### Option C — reconcile_hype_to_paper pre-check
Before calling `add_orphan_trade()`, check if open trade already exists for that token.
If yes, use the existing trade_id directly instead of calling `add_orphan_trade()`.

**Recommended: Option C** — simplest, only adds one query before the insert attempt.

## Key Insight

The `WHERE NOT EXISTS` pattern is a anti-pattern when combined with silent None returns.
If the INSERT doesn't run, the function should either:
- Raise an exception (caller handles it)
- Return a distinguishable sentinel (caller knows to skip close)
- Do nothing and let caller handle the existing record

Returning `None` for both "created" and "not created" is the bug.