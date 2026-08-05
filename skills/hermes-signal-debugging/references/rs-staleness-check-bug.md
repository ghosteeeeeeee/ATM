# RS Staleness Check Bug — `rows[-1]` vs `rows[0]`

## Bug Description

**Symptom**: RS signals completely stop firing. Every token shows:
```
[rs] SUI: stale price_history (last ts 1778335785, skipping)
```
But `signals_hermes.db` has fresh data (price_history rows <2 minutes old).

**Root cause**: `signals/rs.py` line 609 — staleness check uses `rows[-1][0]`
(the OLDEST row in the lookback window) instead of `rows[0][0]` (newest).

```python
# WRONG — checks oldest row in 4700-row window (~78 hours of data)
most_recent_ts = rows[-1][0]
if (time.time() - most_recent_ts) > 120:  # always True, always skips

# CORRECT — checks newest row (fresh price)
most_recent_ts = rows[0][0]
if (time.time() - most_recent_ts) > 120:
```

## Verification Script

```python
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
lookback = 4700  # RS_LOOKBACK_CANDLES
c.execute('SELECT timestamp FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT ?', ('SUI', lookback))
rows = c.fetchall()
now = time.time()
print(f"Newest: {rows[0][0]} (age={now-rows[0][0]:.0f}s)")    # should be <120s
print(f"Oldest: {rows[-1][0]} (age={now-rows[-1][0]:.0f}s)")  # always >>120s
print(f"Bug confirmed (rows[-1] staleness): {now-rows[-1][0] > 120}")
```

Expected output for a fresh token:
- Newest: age <120s ✓
- Oldest: age >>120s (e.g., 230,000s) 
- Bug confirmed: True ← proves the bug

## Fix

Line 609 of `/root/.hermes/scripts/signals/rs.py`:
```python
most_recent_ts = rows[-1][0]  # OLD — wrong
most_recent_ts = rows[0][0]   # NEW — correct (newest row)
```

## Key Insight

Not caused by direction flags (RS_PLUS/RS_MINUS). Those were already in place when RS was working. The staleness check was always logically wrong but became critical once the lookback window was large enough that the oldest row's timestamp exceeded the 120s threshold. The bug was introduced when the lookback window grew (or the threshold tightened) — investigate the commit history around the time RS stopped firing (02:35 UTC 2026-05-12).