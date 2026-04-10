# Plan: Add `close_reason` Field to Profit Monster Exits

## Goal
When profit-monster closes a trade, the `close_reason` column in the `trades` table should read `"profit-monster"`.

## Current State
- `trades.close_reason` column exists but is never populated
- `brain.py close_trade()` updates `notes` but not `close_reason`
- profit-monster.py passes `--notes profit-monster(...)` but no `--close-reason`

## Changes

### 1. `/usr/local/bin/brain.py`

#### 1a. Function signature — add `close_reason=None`
```python
# Line ~328
def close_trade(trade_id: int, exit_price: float, pnl_usdt: float = None, notes: str = None, close_reason: str = None):
```

#### 1b. UPDATE SQL — add `close_reason` column
```python
# Line ~355-363 — change UPDATE SQL from:
    notes = COALESCE(notes, '')
# to:
    notes = COALESCE(notes, ''),
    close_reason = %s
# then add close_reason to the tuple of query params at line ~363

# The full SQL block should end:
    """, (exit_price, pnl_usdt, pnl_pct, trade_id))
# becomes:
    """, (exit_price, pnl_usdt, pnl_pct, close_reason, trade_id))
# AND the params tuple needs to include close_reason before trade_id
```

**Verify the exact param ordering.** The SQL uses positional `%s` bindings — `exit_price, pnl_usdt, pnl_pct, close_reason, trade_id` in that order in the params tuple, matching the SET clause order.

#### 1c. Argument parser — add `--close-reason`
```python
# Line ~557 — after --notes arg:
    close_parser.add_argument("--close-reason", help="Close reason tag")
```

#### 1d. Call site — pass `args.close_reason`
```python
# Line ~591 — change from:
    close_trade(args.id, args.exit_price, args.pnl, args.notes)
# to:
    close_trade(args.id, args.exit_price, args.pnl, args.notes, args.close_reason)
```

### 2. `/root/.hermes/scripts/profit_monster.py`

#### 2a. Append `--close-reason profit-monster` to brain.py close command
```python
# Line ~126 — change from:
    cmd = [sys.executable, BRAIN_CMD, "trade", "close", str(trade_id), exit_price,
           "--notes", f"profit-monster({pnl_pct:.2f}%)"]
# to:
    cmd = [sys.executable, BRAIN_CMD, "trade", "close", str(trade_id), exit_price,
           "--notes", f"profit-monster({pnl_pct:.2f}%)",
           "--close-reason", "profit-monster"]
```

## Validation
```bash
# 1. Check brain.py syntax
python3 -c "import ast; ast.parse(open('/usr/local/bin/brain.py').read())" && echo "syntax OK"

# 2. Dry-run profit-monster to preview the command it would fire
python3 /root/.hermes/scripts/profit_monster.py --dry-run

# 3. After deploying, look for the field in a closed trade:
psql -h /var/run/postgresql -U postgres -d brain \
  -c "SELECT id, token, close_reason, notes FROM trades WHERE close_reason='profit-monster' LIMIT 5"
```

## Risks
- None significant — adds an optional column, all changes are additive
- Make sure param ordering in the SQL matches the `%s` bindings exactly
