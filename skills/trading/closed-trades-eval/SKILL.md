---
name: closed-trades-eval
description: Audit closed trades for bogus zero-PnL entries (non_hoted_removed/orphan_sync/phantom_sync), delete them, then run blocklist-decision on all remaining loss tokens. Produces a cleaned trade history and updated blacklist.
---

# Closed Trades Eval Skill

## When to Use
Run during session wrap, weekly audit, or whenever the user asks to "clean up" or "evaluate" closed trades.

## Prerequisites
- PostgreSQL brain DB: `host=/var/run/postgresql, dbname=brain, user=postgres, password=Brain123`
- SQLite signals DB: `/root/.hermes/data/signals_hermes_runtime.db`
- Constants file: `/root/.hermes/scripts/hermes_constants.py`

## Process

### Phase 1: Audit Bogus Trades

**Step 1a — Identify bogus zero-PnL trades**
```python
cur.execute("""
    SELECT id, token, direction, pnl_pct, pnl_usdt, close_reason, close_time
    FROM trades
    WHERE (pnl_pct IS NULL OR pnl_pct = 0)
      AND close_reason IN ('non_hoted_removed', 'orphan_sync', 'phantom_sync')
      AND status = 'closed'
    ORDER BY close_time
""")
bogus = cur.fetchall()
```
Print count and list. These represent tokens that were never actually filled.

**Step 1b — Delete bogus trades**
```python
ids = [r[0] for r in bogus]
if ids:
    cur.execute(f"DELETE FROM trades WHERE id IN ({','.join('%s' for _ in ids)})", ids)
    conn.commit()
    print(f"Deleted {len(ids)} bogus trades")
```
Also delete corresponding rows from `signal_outcomes` (SQLite) for these bogus entries:
```python
# In SQLite - match by token+direction+close_reason timing
cur.execute("""
    DELETE FROM signal_outcomes
    WHERE token = ? AND pnl_pct = 0 AND pnl_usdt = 0
""", (token,))
```

### Phase 2: Cross-Reference with signal_outcomes

For each remaining token with losses, query `signal_outcomes` (SQLite) alongside brain DB trades to get the complete trade history:
```python
sqlite_conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
# Get directional net from signal_outcomes
cur.execute("""
    SELECT direction, signal_type, is_win, pnl_pct, pnl_usdt, confidence
    FROM signal_outcomes WHERE token=? ORDER BY created_at
""", (token,))
```

### Phase 3: Calculate Directional Net PnL

Group all trade data by token+direction:
- Wins = trades where `is_win=True` or `pnl_pct > 0`
- Losses = trades where `is_win=False` or `pnl_pct < 0`
- Net = sum of all `pnl_usdt` values

### Phase 4: Apply Blocklist Rules

Rules from `hermes_constants.py`:
- **SHORT_BLACKLIST**: `net_loss_on_direction <= -$2.50` OR `3+ consecutive losses`
- **LONG_BLACKLIST**: `net_loss_on_direction <= -$2.50` OR `3+ consecutive losses`

**Exclusions — DO NOT blacklist based on these:**
- Any trade with `confidence=0` or `confidence=None` alongside `pnl_pct` < -50% — these are phantom/sync errors
- Any trade with close_reason in `('phantom_sync', 'orphan_sync', 'non_hoted_removed')` — these are the bogus entries already deleted
- Any trade where entry_price == exit_price (no actual fill)

### Phase 5: Update Constants

```python
patch(hermes_constants.py,
      old_string="    # 2026-04-02: persistent losing LONG directions (loss cooldown streaks)\n    'AERO', 'CHILLGUY', 'LIT', 'DOT', 'ANIME',  # LONG losing streaks",
      new_string="    # 2026-04-02: persistent losing LONG directions (loss cooldown streaks)\n    'AERO', 'CHILLGUY', 'LIT', 'DOT', 'ANIME',  # LONG streaks\n    # YYYY-MM-DD: SHORT blacklist additions\n    'TOKEN',  # SHORT net: $X.XX (N losses: ...)\n    # YYYY-MM-DD: LONG blacklist additions\n    'TOKEN',  # LONG net: $X.XX (N losses: ...)")
```
Verify syntax: `python3 -m py_compile /root/.hermes/scripts/hermes_constants.py`

### Phase 6: Report

Print a final summary table:
```
=== CLOSED TRADES CLEANUP ===
Deleted: N bogus trades (zero-PnL, no fill)

=== BLACKLIST UPDATES ===
SHORT_BLACKLIST added:  TOKEN ($X.XX, N losses)
LONG_BLACKLIST added:   TOKEN ($X.XX, N losses)

=== FINAL BLACKLIST (as of YYYY-MM-DD) ===
SHORT_BLACKLIST: ...
LONG_BLACKLIST: ...
```

## Output
- Cleaned brain DB (no bogus entries)
- Updated hermes_constants.py with new blacklist entries
- Complete audit report
