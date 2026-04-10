# Profit Monster — Plan

## Goal
Create a `profit_monster.py` cron job that randomly (10-30 min intervals) closes 1-2 open positions that are in moderate profit (2-5%), locking in medium gains before momentum fades. A/B testable fire intervals.

---

## Current Context
- Hermes runs on cron: every minute (`hermes-pipeline`)
- `decider-run.py` handles entry/execution
- Positions stored in PostgreSQL `brain.trades` with `status`, `pnl_pct`, `entry_price`, `exit_price`
- Positions have `server='Hermes'` and `status='open'`
- Existing take-profit runs per-trade via SL/TP set at entry — this is a *global override* that pre-emptively closes medium-profit positions

---

## Design

### Core Logic
```
ON WAKE (every X mins, random 10-30):
  1. Query open positions WHERE pnl_pct BETWEEN 2.0 AND 5.0
  2. Exclude top 20% most profitable (leave the winners running)
  3. Randomly select 1-2 positions from the filtered set
  4. Close each via brain.py trade close command
  5. Log which tokens closed and at what profit
```

### A/B Test: Fire Interval
- Test group A: fire every 10-15 min
- Test group B: fire every 20-30 min
- Stored in `/root/.hermes/data/profit_monster_config.json`
- Can be switched via config file without redeploy

### Profit Range
- Min: **2.0%** (below this = not worth the trade cost)
- Max: **5.0%** (above this = let winners run, we want "medium profit" only)
- Configurable via `PROFIT_MIN_PCT` and `PROFIT_MAX_PCT` constants

### Position Selection
- Get all open positions with `pnl_pct` in range
- Sort by `pnl_pct DESC`
- Skip the top 20% most profitable (don't touch the best ones)
- Randomly pick 1-2 from the remaining pool
- If fewer than 1 qualify, do nothing

---

## Files to Create/Modify

### New File: `/root/.hermes/scripts/profit_monster.py`
Main script. Implements the logic above.

Key constants at top:
```python
PROFIT_MIN_PCT = 2.0
PROFIT_MAX_PCT = 5.0
MAX_CLOSE_PER_WAKE = 2
CONFIG_FILE = '/root/.hermes/data/profit_monster_config.json'
LOG_FILE = '/root/.hermes/logs/profit_monster.log'
```

### New Cron: `profit-monster`
Schedule: `*/1 * * * *` (every minute — script itself decides whether to act)
The script uses its internal random timer to decide when to actually fire.

Or better: schedule at both 10min and 20min intervals and let A/B config decide which is active.

### Modify: `update-git.py` or `brain/trading.md`
Document the feature under a new `## Profit Monster` header.

---

## Step-by-Step Plan

1. **Create `profit_monster.py`**
   - Connect to PostgreSQL `brain` DB
   - Read config from `profit_monster_config.json` (AB test group, enabled flag)
   - Query open positions: `SELECT token, direction, pnl_pct, entry_price FROM trades WHERE status='open' AND server='Hermes' AND pnl_pct BETWEEN 2.0 AND 5.0`
   - Apply top-20% filter (skip most profitable)
   - Randomly select 1-2 from remainder
   - Call `brain.py trade close <token>` for each
   - Log results

2. **Create `profit_monster_config.json`**
   ```json
   {
     "enabled": true,
     "ab_group": "B",         // "A" = 10-15min, "B" = 20-30min
     "min_profit_pct": 2.0,
     "max_profit_pct": 5.0,
     "max_closes_per_wake": 2,
     "skip_top_pct": 20
   }
   ```

3. **Add cron job**
   - `mcp_cronjob create` for `profit-monster`
   - Script: `python3 /root/.hermes/scripts/profit_monster.py`
   - Schedule: `*/1 * * * *` (runs every minute, internal random gate)

4. **Document in `brain/trading.md`**
   - Add `## Profit Monster` section
   - Include config path, AB test groups, known behavior

5. **Initial validation**
   - Run manually: `python3 profit_monster.py --dry-run` (add `--dry-run` flag to preview closes without executing)
   - Check logs: `cat /root/.hermes/logs/profit_monster.log`

---

## A/B Test Design

| Group | Fire Interval | Hypothesis |
|-------|--------------|------------|
| A | 10-15 min | More frequent small wins, higher total win rate |
| B | 20-30 min | Let positions run longer, bigger wins per close |

- Split by `ab_group` in config
- Track in `brain.trades` via `--experiment profit-monster-A/B` flag
- Or add a `profit_monster_closes` table to track separately

---

## Risks / Open Questions

1. **Conflict with existing TP/SL**: Positions already have TP at ~5%. Profit monster closing at 2-5% is a subset. This is fine — TP still fires if price reaches it. Profit monster is just an early exit option.
2. **Brain.py close command**: Need to verify `brain.py trade close <token>` syntax and that it works for open positions.
3. **PostgreSQL password**: Should read from env or `_secrets.py`, not hardcode. Check existing scripts for the pattern.
4. **A/B test stats**: Need a way to measure which group performs better. Could add a simple JSON log file or DB table.
5. **Should it close in loss?** No — only profitable trades. Unprofitable positions should be left for the existing SL/TP system.

---

## Config File Schema

`/root/.hermes/data/profit_monster_config.json`:
```json
{
  "enabled": true,
  "ab_group": "B",
  "min_profit_pct": 2.0,
  "max_profit_pct": 5.0,
  "max_closes_per_wake": 2,
  "skip_top_pct": 20,
  "dry_run": false
}
```

---

## `close_reason` Field —closes should log as `"profit-monster"`

### Why
The `trades.close_reason` column exists in the DB but is never populated. Every profit-monster close should set `close_reason = 'profit-monster'` so we can filter and analyze these exits separately.

### Changes Required

#### 1. `/usr/local/bin/brain.py` — 4 edits

**1a. Function signature** — add `close_reason=None` param:
```python
def close_trade(trade_id: int, exit_price: float, pnl_usdt: float = None,
                 notes: str = None, close_reason: str = None):
```

**1b. UPDATE SQL** — add `close_reason = %s` to the SET clause:
```sql
        UPDATE trades SET
            exit_price = %s,
            pnl_usdt = %s,
            pnl_pct = %s,
            status = 'closed',
            close_time = NOW(),
            notes = COALESCE(notes, ''),
            close_reason = %s
        WHERE id = %s
```
Then add `close_reason` to the params tuple (goes between `pnl_pct` and `trade_id`).

**1c. Argument parser** — add `--close-reason` flag:
```python
    close_parser.add_argument("--close-reason", help="Close reason tag")
```

**1d. Call site** — thread `args.close_reason` through:
```python
    close_trade(args.id, args.exit_price, args.pnl, args.notes, args.close_reason)
```

#### 2. `/root/.hermes/scripts/profit_monster.py` — 1 edit

**2a. Pass `--close-reason profit-monster` to brain.py close command:**
```python
    cmd = [sys.executable, BRAIN_CMD, "trade", "close", str(trade_id), exit_price,
           "--notes", f"profit-monster({pnl_pct:.2f}%)",
           "--close-reason", "profit-monster"]
```

### Validation
```bash
# Syntax check
python3 -c "import ast; ast.parse(open('/usr/local/bin/brain.py').read())" && echo "syntax OK"

# Dry-run preview
python3 /root/.hermes/scripts/profit_monster.py --dry-run

# Query closed profit-monster trades
psql -h /var/run/postgresql -U postgres -d brain \
  -c "SELECT id, token, close_reason, notes FROM trades WHERE close_reason='profit-monster' LIMIT 5"
```