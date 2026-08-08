# Hourly Trade Analysis + Auto-Tune

You are analyzing Hermes trades and **making fixes** every hour. Be concise, data-driven, and actionable.

## Step 1: Read Context

```bash
cat automation/trading_log.md | tail -50  # Past learnings
cat automation/recent_changes.log | tail -20  # Recent changes (don't revert)
```

## Step 2: Query Last Hour's Trades

```python
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
cur = conn.cursor()

# Trades closed in last hour
cur.execute("""
    SELECT token, signal, direction, exit_reason, 
           ROUND(pnl_usdt,2) as pnl, ROUND(pnl_pct*100,2) as pnl_pct
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '1 hour' AND status = 'closed'
    ORDER BY close_time DESC
""")
trades = cur.fetchall()
print(f"Last hour: {len(trades)} trades closed")
for t in trades:
    print(t)

# Win rate by close reason (last 24h)
cur.execute("""
    SELECT exit_reason, COUNT(*) as trades, 
           ROUND(SUM(pnl_usdt),2) as pnl,
           ROUND(AVG(pnl_usdt),3) as avg_pnl
    FROM trades 
    WHERE close_time > NOW() - INTERVAL '24 hours' AND status = 'closed'
    GROUP BY exit_reason ORDER BY trades DESC
""")
print("\n24h by close reason:")
for r in cur.fetchall():
    print(r)
conn.close()
```

## Step 3: Diagnose

Answer these:
1. **Entry quality**: Did winners have low adverse excursion (<0.5%)?
2. **SL behavior**: Is `atr_sl_hit` the dominant close reason? → SL too tight
3. **Signal quality**: Which signals are losing money?
4. **Trade frequency**: Overtrading or over-filtered?

## Step 4: Fix Issues

### If atr_sl_hit is >40% of all closes:
Check if `tpsl_utils.py` fix is deployed. If not, alert CEO.

### If a signal has 0% WR with 3+ trades in last hour:
Kill it immediately:
```python
# Edit hermes_constants.py
SIGNAL_ENABLED = False  # Kill the signal
```

### If avg_pnl is negative for 3+ consecutive hours:
Check market regime. If NEUTRAL, consider reducing position size.

### If trade count is >20/hour:
Overtrading — increase minimum signal confidence.

## Step 5: Implement Changes

You can edit:
- `scripts/hermes_constants.py` — enable/disable signals, tune params
- `scripts/signals/*.py` — fix signal logic bugs

Rules:
- Max 1 change per hour (don't destabilize)
- Only change non-locked params
- Git commit each change
- Log to `automation/trading_log.md`
- **Report to CEO kanban:**
```markdown
## TEAM UPDATES
- [YYYY-MM-DD HH:MM] auto_1hr: [what was changed] — [why]
```

## Step 6: Document

Append to `automation/trading_log.md`:

```markdown
## [YYYY-MM-DD HH:MM] Hourly Analysis

**Trades:** X closed (Y wins, Z losses)
**PnL:** $X.XX (WR: XX.X%)

**Changes:**
1. [Change] — [why]

**No Change Needed:**
- [What was checked and why it's OK]

**Open Questions:**
- [Anything unclear]
```

## Key File Paths
- Trades: PostgreSQL at `/var/run/postgresql/brain`
- Constants: `scripts/hermes_constants.py`
- TPSL logic: `scripts/tpsl_utils.py`
- Trading log: `automation/trading_log.md`
- Recent changes: `automation/recent_changes.log`
