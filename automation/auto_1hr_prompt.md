# Hourly Trade Analysis + Auto-Tune

You are analyzing Hermes trades and **making fixes** every hour. Be concise, data-driven, and actionable.

**IMPORTANT: Do NOT query OpenMemory during this task. The OpenMemory queries are failing with tenant_mismatch errors and causing timeouts. Skip all OpenMemory calls entirely.**

## Step 1: Read Context

```bash
cat automation/trading_log.md | tail -50  # Past learnings
cat automation/recent_changes.log | tail -20  # Recent changes (don't revert)
cat data/vacation_size_reduce.json 2>/dev/null  # size-reduce status — FILE IS TRUTH
```

**Size-reduce reporting:** quote `size_multiplier` from `data/vacation_size_reduce.json` (e.g. 0.5 → "0.5x"). Never infer the multiplier from past log entries — it changes without history rewriting.

## Step 2: Query Last Hour's Trades

```python
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='[BRAIN_DB_PASSWORD]')
cur = conn.cursor()

# Trades closed in last hour
# pnl_pct is ALREADY in percent units (5.0 = +5.0% account return = raw move × leverage).
# Do NOT multiply by 100 — that produced fake "nonsense" like CFX -585% (= -5.85% × 100).
# hard_max_loss ~1% PRICE move becomes ~3-5% account loss at 3-5x leverage — expected, not a bug.
cur.execute("""
    SELECT token, signal, direction, exit_reason,
           ROUND(pnl_usdt,2) as pnl, ROUND(pnl_pct,2) as pnl_pct
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

### 3b. Signal Inversion Check (PORTED from signal-reporter 2026-10-27)

The LLM signal-reporter was retired (a deterministic
`signal_performance_report.timer` already writes `signal_report.md` every 6h).
Its two DECISION rules — which the deterministic report does not act on — now
live here. Run this every hour:

```python
# Direction mismatches — a signal named *long* that fired SHORT (or vice versa)
# is a CRITICAL bug, not a bad trade.
cur.execute("""
    SELECT token, signal, direction, exit_reason, ROUND(pnl_usdt,2) AS pnl
    FROM trades
    WHERE close_time > %s
      AND ((signal LIKE '%%long%%' AND direction = 'SHORT')
        OR (signal LIKE '%%short%%' AND direction = 'LONG'))
    ORDER BY close_time DESC LIMIT 10
""", (h24,))
```

If any rows return → **CRITICAL**: a signal is wired to the wrong direction.
Find it in `scripts/signals/`, fix the direction logic, and log to the CEO
kanban. Do NOT silently flip the trades.

### 3c. Boost Candidates (PORTED from signal-reporter 2026-10-27)

**Boost only if ALL are true (24h):**
- WR > 55% with 5+ trades
- Net PnL > $0.05
- Consistent across multiple tokens (not one lucky coin)

Boost by raising the confidence weight in `signal_compactor.py` or adding to
hot-set priority. Log the change + numbers to `trading_log.md`. One boost max
per hour (same stability rule as kills).

## Step 4: Fix Issues

### If atr_sl_hit is >40% of all closes:
Check if `tpsl_utils.py` fix is deployed. If not, alert CEO.

### If a signal has 0% WR with 3+ trades in last hour:
**DO NOT blanket-kill (`SIGNAL_ENABLED = False` is banned without CEO approval).** Mandatory regime-based kill policy:
1. Query regime performance first:
```sql
SELECT volatility_regime, COUNT(*),
       ROUND(100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1) wr,
       ROUND(SUM(pnl_usdt),2) pnl
FROM trades WHERE signal LIKE '%X%' AND close_time > NOW() - INTERVAL '14 days'
GROUP BY volatility_regime;
```
2. Signal wins in ANY regime → keep it alive; block only the losing regime(s) via `scripts/volatility_gate_v2.py` (0.0x multiplier for that regime) + `scripts/market_phase_gate.py` FAMILY_MAP entry.
3. Signal loses in ALL regimes (n≥20) → write the kill recommendation to the CEO kanban with the numbers; disable in `hermes_constants.py` only after CEO approval (or an explicit pre-registered kill criterion being met).

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

### After ANY hermes_constants.py change, log the version:
Audit store is `data/signal_versions.json` (NOT a Python script — scripts/signal_version.py does not exist; CEO 2026-09-30).
Append an entry under the signal key:
```bash
python3 - <<'PY'
import json
from datetime import datetime, timezone
path = "/root/.hermes/data/signal_versions.json"
signal = "SIGNAL_NAME"  # e.g. volume-breakout
entry = {
    "version": 1,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "params": {"PARAM": "value"},
    "metrics": {},
    "changed_by": "auto_1hr",
    "reason": "brief reason",
    "prev_version": None,
}
data = json.load(open(path))
cur = data.get(signal, {}).get("current_version", 0)
entry["version"] = cur + 1
entry["prev_version"] = cur or None
data.setdefault(signal, {"versions": [], "current_version": 0})
data[signal]["versions"].append(entry)
data[signal]["current_version"] = entry["version"]
json.dump(data, open(path, "w"), indent=2)
print(f"Logged {signal} v{entry['version']}")
PY
```
This creates an audit trail of all parameter changes. Without this, we lose track of what changed and why.
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

## CRITICAL: Bash Quoting for $ Amounts

When writing money amounts via bash `echo`/`printf`/heredoc, SINGLE-QUOTE the string. Unquoted `$0` expands to the shell path and corrupts the audit trail (`-$0.14` becomes `-/usr/bin/bash.14`):
- ✅ `echo "- [time] 24h -$0.14 (WR 41%)"`
- ❌ `echo - [time] 24h -$0.14 (WR 41%)`

## CRITICAL: SQL Rules

PostgreSQL treats `"double quotes"` as column identifiers, NOT string literals. Always use `'single quotes'` for string values:
- ✅ `WHERE status = 'closed'`
- ❌ `WHERE status = "closed"` ← this means "find a column named closed"

**Correct column names for `trades` table:**
- `open_time` (NOT `entry_time` or `entry_timing` for the trade open timestamp)
- `close_time` (trade close timestamp)
- `status` ('open' or 'closed')
- `signal` (signal name)
- `direction` ('LONG' or 'SHORT')
- `exit_reason` (close reason: 'atr_sl_hit', 'tp_hit', etc.)
- `pnl_usdt`, `pnl_pct` (PnL columns)
- `entry_price`, `exit_price`, `stop_loss`, `target`
- `amount_usdt` (position size)

**Two more gotchas (PORTED from signal-reporter 2026-10-27 — hard-won, do not lose):**
- Signal metadata JSON column is **`_signal_metadata`** (leading underscore) — NOT `signal_metadata`. Wrong name → `column "signal_metadata" does not exist`. Example: `_signal_metadata->>'source'`, `(_signal_metadata->>'rsi_14')::numeric`.
- RSI from metadata is `(_signal_metadata::json->>'rsi_14')::float` — the `entry_rsi_14` column is unreliable (median error ~13 points). Prefer `meta_rsi` semantics.

If a query fails with `UndefinedColumn`, check column names against this list before retrying.

## Key File Paths
- Trades: PostgreSQL at `/var/run/postgresql/brain`
- Constants: `scripts/hermes_constants.py`
- TPSL logic: `scripts/tpsl_utils.py`
- Trading log: `automation/trading_log.md`
- Recent changes: `automation/recent_changes.log`
- Signal versions: `data/signal_versions.json` (append after every constants edit — no scripts/signal_version.py)
