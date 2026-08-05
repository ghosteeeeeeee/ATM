# Archive Migration Broke the WR Filter — Burst Opening

## The Incident

On 2026-05-11, `archive-trades.py --apply --rebuild-db` moved 361 closed trades from PostgreSQL `brain.trades` to JSON gzip archives and a local SQLite analysis DB.

**Result: PostgreSQL went from 361 closed trades to 2 (0G SHORT, CAKE LONG).**

## Why This Broke the WR Filter

The per-coin WR filter in `signal_compactor.py:946` and `decider_run.py:1786` uses this condition:

```python
if wr < 50 and wr_count >= 3:
    block  # skip this token
```

**The threshold is `>= 3 trades`.** With 361 trades archived, every token in the signal universe had `wr_count = 0`. The condition `0 >= 3` is **False** — the filter never fires.

**Effect:** WR filter became completely dormant. Every token passed through as if it had a clean history.

## The Burst Opening Sequence

```
20:02:16 — AVAX LONG opened
20:02:26 — BSV LONG opened
20:02:36 — ATOM LONG opened
20:03:06 — STRK LONG opened
20:05:09 — 0G SHORT closed (atr_sl_hit)
20:05:09 — CAKE LONG closed (atr_sl_hit)
20:06:07 — SKR LONG opened (5th slot filled)
```

4 LONGs opened within 52 seconds. This was the first time the system ran with zero WR history — every token looked clean. Combined with MAX_POS=5 and the system having just closed 2 positions, it opened 5 positions within 4 minutes.

**Not a bug in the WR logic — it was the expected behavior when history is erased.**

## Why 0G SHORT and CAKE LONG Remained in PostgreSQL

The archive-trades.py uses `LIMIT 500` in its SQLite query (line 362). If the `close_time` filter missed some trades or the query didn't pick them up in the first pass, some trades remain in PostgreSQL.

```python
cur.execute("""
    SELECT id, token, direction, pnl_usdt, entry_price, exit_price,
           stop_loss, target, open_time, close_time, close_reason, exit_reason,
           amount_usdt, leverage, exchange
    FROM trades
    WHERE status = 'closed'
    ORDER BY close_time
    LIMIT 500
""", ...)
```

PostgreSQL showed 0G SHORT (1 trade, 0 wins) and CAKE LONG (1 trade, 0 wins) still in the database. Both have `wr_count=1 < 3` so they still don't trigger the WR filter.

## The Catch-22

1. Archive moved closed trades to remove WR history
2. WR filter requires 3+ trades to fire
3. New tokens (no history) pass freely — same as tokens with losing records
4. System loses the ability to distinguish fresh tokens from broken ones
5. Only fix: either lower the `>=3` threshold, or seed fresh tokens with a different mechanism

## Fix Options

### Option A: Lower the threshold to `>= 1`
```python
if wr < 50 and wr_count >= 1:
    block
```
Tokens with even 1 losing trade get blocked. But this means new tokens (count=0) still pass — need another mechanism to differentiate.

### Option B: Block tokens with ANY losing trade
```python
if wr_count >= 1 and wr < 50:
    block
```
New tokens (count=0) pass. Tokens with 1 loss pass. But this is overly strict — sample size of 1 is meaningless.

### Option C: Use the archive analysis DB for WR
The WR check could query the local archive SQLite (`/root/.hermes/archive/trades_analysis.db`) as a fallback when PostgreSQL has insufficient data. Archive has 361 trades with full signal context.

```python
def _get_token_wr(token, direction):
    # First try PostgreSQL
    wr, count = _pg_query(token, direction)
    if count >= 3:
        return wr, count  # authoritative PostgreSQL
    # Fallback to archive DB
    wr_arch, count_arch = _archive_query(token, direction)
    if count_arch >= 3:
        return wr_arch, count_arch
    # No sufficient history
    return 50.0, 0  # pass
```

### Option D: Decouple WR filter from trade count
Track token age separately — a token with 0 WR history but in the signal universe for 2+ days has "proven itself" and doesn't need the WR filter firing.

## Diagnostic Commands

```bash
# Confirm PostgreSQL closed trade count (should be ~0 after archive)
psql -h /var/run/postgresql -U postgres -d brain -c "SELECT status, COUNT(*) FROM trades GROUP BY status;"

# Confirm WR filter dormant — all tokens show 0 closed trades
psql -h /var/run/postgresql -U postgres -d brain -c \
  "SELECT token, direction, COUNT(*) as closed_trades FROM trades WHERE status='closed' GROUP BY token, direction ORDER BY closed_trades;"

# Check archive has the real history
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/archive/trades_analysis.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM trades')
print(f'Archive trades: {cur.fetchone()[0]}')
conn.close()
"

# Confirm the burst — 5 positions opened in 4 min
journalctl --since '20:00' --no-pager | grep 'OPEN' | head -10
```

## Related

- `references/wr-per-coin-filter-2026-05-11.md` — original WR gate design
- `references/decider-run-regime-disabled-2026-05-11.md` — regime filter also disabled around same time
- `references/hotset-approved-disconnect-2026-05-11.md` — WR/gate interactions