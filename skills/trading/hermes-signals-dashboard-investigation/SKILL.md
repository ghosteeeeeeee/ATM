---
name: hermes-signals-dashboard-investigation
description: Investigate and fix Hermes signals.html (signals.json) dashboard issues — stale hot-set data, wrong decision states, missing tabs, and schema mismatches between hotset.json and signals.json
trigger: "When signals.html shows tokens in wrong tabs (e.g. APPROVED + EXPIRED simultaneously), hot-set entries appear stale, SKIPPED/EXPIRED tabs are empty or wrong, or the signals API needs debugging"
---

# Hermes Signals Dashboard Investigation Pattern

## Critical Data Paths

```
signal_gen scripts → signals_hermes_runtime.db (signals table)
signal_compactor.py → hotset.json + signals DB (decision='APPROVED')
                         ↓
hermes-trades-api.py (write_signals function) → signals.json
                         ↓
nginx :54321 → /data/signals.json → signals.html (JS fetch every 30s)
```

**Two key files:**
- `/var/www/hermes/data/hotset.json` — authoritative hot-set, updated every minute by signal_compactor
  - Structure: `{timestamp, compaction_cycle, hotset: [{token, direction, source, confidence, ...}, ...]}`
  - **NOT** a flat list — accessing `hs[0]` gets the dict wrapper, not a token entry
- `/var/www/hermes/data/signals.json` — API output served to signals.html, regenerated on HTTP request
  - NOT on a timer — only regenerates when someone hits the HTTP endpoint

## The Staleness Window Problem

**Symptom:** A token (e.g. CAKE) appears in hot-set APPROVED tab AND in EXPIRED tab simultaneously.

**Root cause:** `signals.json` regenerates only on HTTP request, but `hotset.json` updates every minute. If signal_compactor evicts a token from hotset.json between two API calls, `signals.json` still shows the old hot-set entry as APPROVED while the DB already recorded the EXPIRED transition.

**Diagnosis:**
```python
import json, os

# Compare hotset.json mtime vs signals.json mtime
hs_stat = os.stat('/var/www/hermes/data/hotset.json')
sig_stat = os.stat('/var/www/hermes/data/signals.json')
print(f"hotset.json mtime: {hs_stat.st_mtime}")
print(f"signals.json mtime: {sig_stat.st_mtime}")
print(f"hotset.json age: {os.time.time() - hs_stat.st_mtime:.0f}s")

# Check current state
with open('/var/www/hermes/data/hotset.json') as f:
    hs = json.load(f)
hotset_tokens = {e['token'] for e in hs.get('hotset', [])}

with open('/var/www/hermes/data/signals.json') as f:
    sigs = json.load(f)
hs_in_signals = {t.get('token') for t in sigs.get('hot_set', []) if isinstance(t, dict)}
overlap = hotset_tokens & hs_in_signals
print(f"hotset.json tokens: {hotset_tokens}")
print(f"signals.json hot_set tokens: {hs_in_signals}")
print(f"In both: {overlap}")
```

**Fix in hermes-trades-api.py write_signals():** When building approved_list, demote hot_set entries where the DB has a newer EXPIRED entry:
```python
from datetime import datetime
for s in hot_set:
    c_d.execute(
        "SELECT created_at FROM signals WHERE token=? AND direction=? AND decision='EXPIRED' ORDER BY created_at DESC LIMIT 1",
        (s['token'], s['direction'])
    )
    row = c_d.fetchone()
    if row:
        expired_ts = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timestamp()
        hotset_ts = float(s.get('last_seen', 0))
        if expired_ts > hotset_ts:
            s['decision'] = 'EXPIRED'
            s['time'] = row[0]
            # Remove from hot_set so it doesn't appear in APPROVED tab
            hot_set.remove(s)
```

## Decision State Taxonomy

| Decision | Meaning | Tab |
|----------|---------|-----|
| `APPROVED` | Signal in hot-set, awaiting execution | APPROVED |
| `PENDING` | Signal generated but not yet approved | PENDING |
| `EXECUTED` | **Real trade placed on Hyperliquid** — must cross-check with trades.json | EXECUTED |
| `SKIPPED` | Blocked by guardian (price suspicious, speed=0%, already open, single-source, etc.) — valid signal that didn't trade | SKIPPED |
| `EXPIRED` | Signal was in hot-set but exited (stale, de-escalated, replaced) | EXPIRED |

**Critical:** `EXECUTED` should ONLY mean a real Hyperliquid trade. Any blocked signal should be `SKIPPED`, NOT `EXECUTED`. If phantom `EXECUTED` entries exist (no corresponding trade in trades.json), they corrupt `signal_outcomes` and can trigger false loss cooldowns.

## Common Schema Bugs

### 1. hotset.json accessed as flat list
```python
# WRONG — hotset.json is {hotset: [...], not a flat list}
entries = data  # data is the dict wrapper

# CORRECT
entries = data.get('hotset', [])
```

### 2. Unix timestamp vs SQLite datetime string comparison
```python
# WRONG — string comparison always fails
hotset_ts = float(e.get('timestamp', 0))  # e.g. '1777350120.64' (string)
expired_ts = row[0]  # e.g. '2026-04-28 04:15:36' (SQLite date string)
if expired_ts > hotset_ts:  # Always True — string '2' > '1' lexicographically

# CORRECT — parse SQLite datetime to Unix timestamp
from datetime import datetime
expired_ts = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timestamp()
hotset_ts = float(s.get('last_seen', 0))
if expired_ts > hotset_ts:
```

### 3. Blocked signals marked EXECUTED
The guardian/decider must call `mark_signal_executed(..., 'SKIPPED')` for blocked signals, not `mark_signal_executed(...)` which defaults to `'EXECUTED'`. This corrupts `signal_outcomes`.

## Investigation Checklist

1. **Check file staleness:** `os.stat()` mtime comparison between hotset.json and signals.json
2. **Check hotset.json structure:** `data.get('hotset', [])` not flat list
3. **Check decision cross-contamination:** Tokens appearing in multiple tabs simultaneously
4. **Check EXECUTED cross-reference:** Every `decision='EXECUTED'` must have a corresponding entry in trades.json
5. **Check SKIPPED accumulation:** After Bug-1 fix, SKIPPED tab should show blocked signals
6. **Check signals.json top-level keys:** Must include `skipped` and `expired` lists (added in 2026-04-28)

## SQL Diagnostic Queries

```sql
-- Check EXECUTED signals not in trades.json (phantom EXECUTEDs)
SELECT s.id, s.token, s.direction, s.source, s.created_at
FROM signals s
WHERE s.decision = 'EXECUTED'
  AND NOT EXISTS (SELECT 1 FROM trades t WHERE t.coin = s.token AND t.direction = s.direction);

-- Check signals appearing in multiple decision states
SELECT token, direction, decision, COUNT(*) as cnt
FROM signals
WHERE created_at > datetime('now', '-24 hours')
GROUP BY token, direction, decision
ORDER BY token, direction, created_at DESC;

-- Check EXPIRED distribution
SELECT decision, COUNT(*) FROM signals GROUP BY decision;
```

## Related Skills

- `hermes-dashboard-investigation` — covers trades.html/trades.json pipeline (different from signals.html)
- `signal-compaction` — hot-set compaction via signal_compactor.py (what writes hotset.json)
- `hermes-signature-change-audit` — before changing signal_schema.py functions like `mark_signal_executed()`
