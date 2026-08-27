# Bug Report: Guitar Tuning Regime Capture — Audit Date: 2026-08-27

## Summary

Audited the regime capture changes in `signal_schema.py` and `position_manager.py`. Found **6 issues** (1 HIGH, 3 MEDIUM, 2 LOW), zero SQL injection vectors, and no data corruption. The core logic is sound but has connection leak paths and an incomplete backfill.

---

## ISSUE 1: `_get_volatility_regime()` Connection Leak

**SEVERITY: HIGH**
**FILES:** `signal_schema.py:3287-3297`

### ROOT CAUSE

`_get_volatility_regime()` opens a SQLite connection to `candles.db` on line 3287, but `conn.close()` on line 3297 is NOT in a `finally` block. If `cur.execute()` or `cur.fetch()` throws (e.g., DB locked, corrupt data), the connection leaks.

```python
# signal_schema.py:3284-3297
try:
    conn = _sqlite3.connect(f'{HERMES_DATA}/candles.db', timeout=10)
    cur = conn.cursor()
    cur.execute(...)    # ← If this throws...
    rows = cur.fetchall()  # ← ...or this...
    conn.close()        # ← ...this never runs
    ...
except Exception:
    return 'UNKNOWN'    # ← catches error, but conn is leaked
```

### EVIDENCE

- Line 3297: `conn.close()` is inside `try` but NOT in `finally`
- Line 3323: `except Exception: return 'UNKNOWN'` catches the error but doesn't close `conn`
- Python's sqlite3 connections don't auto-close on GC reliably (they hold file descriptors)

### IMPACT

Each leaked connection holds a file descriptor on `candles.db` (734MB, WAL mode). The pipeline runs every minute; if `_get_volatility_regime()` fails once per run, that's 1440 leaked FDs/day. SQLite's WAL checkpointing may be affected. Eventually: "database is locked" or "too many open files".

### FIX

```python
def _get_volatility_regime(token: str) -> str:
    conn = None
    try:
        from paths import HERMES_DATA
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(f'{HERMES_DATA}/candles.db', timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT open, high, low, close
            FROM candles_1h
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC
            LIMIT 20
        """, (token.upper(),))
        rows = cur.fetchall()
        if len(rows) < 15:
            return 'UNKNOWN'
        candles = list(reversed(rows))
        trs = []
        for i in range(1, len(candles)):
            h, l, pc = candles[i][1], candles[i][2], candles[i-1][3]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trs.append(tr)
        if len(trs) < 14:
            return 'UNKNOWN'
        atr = sum(trs[-14:]) / 14
        close = candles[-1][3]
        if close <= 0:
            return 'UNKNOWN'
        atr_pct = (atr / close) * 100
        if atr_pct < 0.48:
            return 'FLAT'
        elif atr_pct < 1.0:
            return 'NORMAL'
        elif atr_pct < 1.5:
            return 'HIGH'
        else:
            return 'EXTREME'
    except Exception:
        return 'UNKNOWN'
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
```

### VERIFICATION

- After fix: `python3 -c "from signal_schema import _get_volatility_regime; _get_volatility_regime('BTC')"` should leave no dangling connections
- Check with: `lsof +D /root/.hermes/data/candles.db` after multiple calls

---

## ISSUE 2: `_ensure_signal_outcomes_table()` Connection Leak

**SEVERITY: MEDIUM**
**FILES:** `position_manager.py:525-569`

### ROOT CAUSE

Same pattern as Issue 1. `conn.close()` on line 567 is NOT in a `finally` block:

```python
def _ensure_signal_outcomes_table():
    try:
        conn = sqlite3.connect(SIGNAL_DB)
        c = conn.cursor()
        # ... CREATE TABLE, ALTER TABLE, CREATE INDEX ...
        conn.commit()
        conn.close()  # ← line 567: not in finally
    except Exception as e:
        log(...)  # ← conn leaked if exception occurred after connect()
```

If any `CREATE INDEX` or `ALTER TABLE` fails, the `except` block catches it but `conn` is never closed.

### EVIDENCE

- Line 567: `conn.close()` is inside `try` but NOT in `finally`
- Line 568: `except Exception as e: log(...)` — no `conn.close()`
- This function is called at the start of every `_record_signal_outcome()` call (line 735)

### IMPACT

Lower than Issue 1 because this only writes to `signals_hermes_runtime.db` (WAL mode, 10s timeout). But repeated leaks accumulate.

### FIX

Add `finally: conn.close()` pattern, or better yet use the existing `_db_cursor()` context manager.

---

## ISSUE 3: `idx_sigout_regime` Index NOT Created in Database

**SEVERITY: MEDIUM**
**FILES:** `position_manager.py:564`, Database: `signals_hermes_runtime.db`

### ROOT CAUSE

The migration code at `position_manager.py:564` creates the index:
```python
c.execute("""
    CREATE INDEX IF NOT EXISTS idx_sigout_regime ON signal_outcomes(regime)
""")
```

But this index **does not exist** in the database:

```
=== Indexes on signal_outcomes ===
  idx_sigout_token: CREATE INDEX idx_sigout_token ON signal_outcomes(token, direction)
  idx_sigout_stype: CREATE INDEX idx_sigout_stype ON signal_outcomes(signal_type)
  [idx_sigout_regime: MISSING]
```

Most likely cause: `_ensure_signal_outcomes_table()` was called, the `ALTER TABLE ADD COLUMN regime` succeeded, but the function errored BEFORE reaching the `CREATE INDEX` line (or the call never happened after the code change).

### EVIDENCE

```sql
sqlite> SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='signal_outcomes';
idx_sigout_token
idx_sigout_stype
-- idx_sigout_regime is absent
```

Manually creating the index works fine:
```sql
CREATE INDEX IF NOT EXISTS idx_sigout_regime ON signal_outcomes(regime);
-- OK (1.65s on 9966 rows)
```

### IMPACT

Any query filtering or grouping by `regime` does a full table scan. Currently 9,966 rows — negligible. But at scale (100K+ rows), regime-based analytics will be slow.

### FIX

Run the index creation manually now, and ensure `_ensure_signal_outcomes_table()` uses `finally` for conn cleanup (Issue 2 fix addresses the root cause).

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
conn.execute('CREATE INDEX IF NOT EXISTS idx_sigout_regime ON signal_outcomes(regime)')
conn.commit()
conn.close()
print('idx_sigout_regime created')
"
```

---

## ISSUE 4: `hl-sync-guardian.py` INSERT Missing Regime Column

**SEVERITY: MEDIUM (dormant)**
**FILES:** `hl-sync-guardian.py:3253`

### ROOT CAUSE

`hl-sync-guardian.py` has its own `_record_trade_outcome()` function (line 3227) that INSERTs into `signal_outcomes` WITHOUT the `regime` column:

```python
# hl-sync-guardian.py:3252-3256
cur_s.execute("""
    INSERT INTO signal_outcomes (token, direction, signal_type, is_win, pnl_pct, pnl_usdt, confidence, trade_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (token.upper(), direction.upper(), 'unknown',
      1 if is_win else 0, pnl_pct, pnl_usdt, None, trade_id))
```

Compare with the correct INSERT in `signal_schema.py:3370-3373`:
```python
INSERT INTO signal_outcomes
    (token, direction, signal_type, is_win, pnl_pct, pnl_usdt, confidence, trade_id, regime)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
```

### EVIDENCE

- `_record_trade_outcome` is currently **dead code** (defined but never called — only 1 reference in the file, the definition itself)
- When the function was active, it would have inserted rows with `regime=NULL`

### IMPACT

Currently zero (dead code). BUT: if anyone re-enables this function, it would silently produce NULL-regime rows. It's a landmine.

### FIX

Update the INSERT to include `regime` (with a `_get_volatility_regime()` call), or better yet, make the function call `record_signal_outcome()` from `signal_schema.py` instead of having its own INSERT. Consolidate to a single INSERT path.

---

## ISSUE 5: Double `conn.close()` on Dedup Path

**SEVERITY: LOW**
**FILES:** `signal_schema.py:3368-3369, 3397-3398`

### ROOT CAUSE

When the dedup check hits (line 3367-3369):
```python
if c.fetchone():
    conn.close()       # ← explicit close on line 3368
    return False       # ← return exits try block
                       # ← finally runs: conn.close() AGAIN on line 3398
```

`conn.close()` is called twice: once explicitly, once in `finally`.

### EVIDENCE

```python
# Line 3367-3369:
if c.fetchone():
    conn.close()        # first close
    return False
# ...
# Line 3397-3398:
finally:
    conn.close()        # second close (redundant)
```

### IMPACT

Harmless in practice (Python sqlite3 handles double-close gracefully), but it's a code smell and violates the principle of single-responsibility for connection cleanup.

### FIX

Remove the explicit `conn.close()` on line 3368. Let `finally` handle all cleanup:

```python
if c.fetchone():
    return False  # dedup hit — finally closes conn
```

---

## ISSUE 6: 1,654 Rows (16.6%) Have NULL Regime — Incomplete Backfill

**SEVERITY: LOW (data quality, not a code bug)**
**FILES:** Database: `signals_hermes_runtime.db`

### ROOT CAUSE

The backfill updated 8,312 rows with regime data, but 1,654 rows remain NULL. Analysis of the NULL rows:

| Metric | Value |
|--------|-------|
| Total NULL regime rows | 1,654 (16.6%) |
| NULL with trade_id | 71 |
| NULL without trade_id | 1,583 |
| Date range | 2026-03-11 to 2026-08-27 |
| Most recent NULL | id=9996, 2026-08-27 15:01:44 |

The 8 most recent NULL rows (9989-9996) were created **before** the regime code was deployed (signal_schema.py modified at 15:08, last NULL row created at 15:01). These are normal pre-deployment rows.

### EVIDENCE

- Zero rows have `regime='UNKNOWN'` — all backfilled rows have real regime values
- NULL rows span the full history (March-August 2026)
- The 8 most recent NULL rows have real signal types (not 'unknown'), confirming they're from `record_signal_outcome` before the regime code was live

### IMPACT

Any regime-based analysis (WR by regime, signal performance per regime) silently excludes 16.6% of trades. This biases results toward post-deployment data.

### FIX

Run a one-time backfill to fill NULL regime rows:

```sql
-- For each NULL regime row, look up the token and compute regime from candles_1h
-- at the trade's close time (created_at)
```

Or accept NULL as "unknown era" and filter them out in analysis queries with `WHERE regime IS NOT NULL`.

---

## POSITIVE FINDINGS

### SQL Injection: ✅ CLEAN

All SQL queries use parameterized `?` placeholders. No f-string SQL, no string interpolation in queries.

### Error Handling: ✅ ADEQUATE

`record_signal_outcome()` has proper try/except/finally with rollback on error. `_get_volatility_regime()` catches all exceptions and returns 'UNKNOWN' (except for the connection leak noted in Issue 1).

### Performance: ✅ ACCEPTABLE

`_get_volatility_regime()` opens a new connection per trade close. Since the pipeline runs sequentially (not threaded), this is fine. SQLite WAL mode handles concurrent reads well. The query (20 rows from indexed `candles_1h`) is fast.

### Data Correctness: ✅ MOSTLY SOUND

The regime computation logic (14-period ATR, threshold classification) matches `volatility_gate.py`. The thresholds (0.48%, 1.0%, 1.5%) are reasonable for crypto. Computing regime at close time rather than entry time is a known tradeoff documented in the spec.

### Concurrency: ✅ WAL MODE PROTECTS

Both `signals_hermes_runtime.db` and `candles.db` use WAL mode with 10s busy timeout. Multiple processes (pipeline, hl-sync-guardian) can safely read concurrently. Writes are serialized by SQLite's built-in locking.

---

## UNCERTAINTIES

1. **Why the index wasn't created**: Could be a silent failure in `_ensure_signal_outcomes_table()`, or the function was never called after the code change. Without logs from the exact time of deployment, I can't determine which.

2. **Whether regime at close time is "good enough"**: For short-duration trades (< 4h), regime is likely stable. For longer holds (> 24h), regime may shift. The spec chose close-time as "best-effort fallback" — this is acceptable but not ideal. Future improvement: capture regime at trade entry time and pass it through.

3. **Whether `_record_trade_outcome` in hl-sync-guardian will be re-enabled**: The docstring says it "records signal_outcomes" but it's never called. If re-enabled without the regime fix, it would produce NULL regime rows.

4. **1,654 NULL rows backfill priority**: These 16.6% of rows affect analysis accuracy but not live trading. Low priority unless regime-based analytics become critical.
