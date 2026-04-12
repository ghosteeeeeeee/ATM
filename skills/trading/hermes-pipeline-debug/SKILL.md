---
name: hermes-pipeline-debug
description: Debug signals/hot-set discrepancies in Hermes trading pipeline — signals in DB but not in dashboard, empty hot-set despite running pipeline
triggers:
  - "signals in DB but not in dashboard"
  - "hot-set empty"
  - "signals.json count mismatch"
  - "pipeline running but no hot signals"
  - "signals.html shows different counts than runtime DB"
---

# Hermes Pipeline Debug — Signals/Hot-set Discrepancy

## Core Principle: 4-Layer Data Flow

```
Layer 1: signal_gen.py          → writes → signals_hermes_runtime.db (SQLite)
Layer 2: ai_decider.py          → reads DB → writes → /var/www/hermes/data/hotset.json
Layer 3: hermes-trades-api.py   → reads hotset.json → writes → /var/www/hermes/data/signals.json
Layer 4: signals.html          → fetch(/data/signals.json) → renders dashboard
```

**Critical path knowledge:**
- `ai_decider.py` writes hotset to `/var/www/hermes/data/hotset.json` (NOT `/root/.hermes/data/`)
- `hermes-trades-api.py` reads from whichever path — CHECK LINE 324 on any discrepancy
- `signals.json` is NOT the runtime DB — it's a derived export with filters (e.g., excludes `source='rsi-confluence'`)
- The dashboard signals.html reads ONLY from `signals.json`, NOT from `signals_hermes_runtime.db` directly

## Debugging Steps

### Step 1: Check hotset.json directly (authoritative source)
```bash
cat /var/www/hermes/data/hotset.json
```
If this is empty/stale, the problem is Layer 2 (ai_decider not writing).

### Step 2: Check signals.json (dashboard feed)
```bash
cat /var/www/hermes/data/signals.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('hot_set:', len(d['hot_set']), '| total:', d['total'])"
```
Compare hot_set count vs hotset.json tokens. If DIFFERENT → path mismatch (Layer 3).

### Step 3: Check hermes-trades-api.py path
```bash
grep -n "HOTSET_FILE\|hotset\.json" /root/.hermes/scripts/hermes-trades-api.py
```
Must match where ai_decider writes: `/var/www/hermes/data/hotset.json`.

### Step 4: Check runtime DB signals
```bash
python3 -c "
import sqlite3
db = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('SELECT decision, COUNT(*) FROM signals GROUP BY decision')
for r in cur.fetchall(): print(r)
conn.close()
"
```

### Step 5: Check why signals.json total ≠ DB total
```bash
# signals.json excludes rsi-confluence (0% WR)
python3 -c "
import sqlite3
db = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM signals')
total = cur.fetchone()[0]
cur.execute(\"SELECT COUNT(*) FROM signals WHERE source != 'rsi-confluence'\")
filtered = cur.fetchone()[0]
print(f'DB total: {total} | signals.json (non-rsi): {filtered}')
conn.close()
"
```

### Step 6: Check pipeline logs for ai_decider errors
```bash
grep -E "ERROR|NameError|Exception|traceback" /root/.hermes/logs/pipeline.log | tail -30
```

### Step 7: Verify SIGNAL_SOURCE_BLACKLIST is not bypassed
```bash
# Check what signal_type and source are actually stored in DB
python3 -c "
import sqlite3
db = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
# Show unique signal_type + source combinations
cur.execute('SELECT DISTINCT signal_type, source, COUNT(*) FROM signals GROUP BY signal_type, source ORDER BY COUNT(*) DESC LIMIT 20')
for r in cur.fetchall(): print(f'{r[0]!r:30} {r[1]!r:30} {r[2]}')
conn.close()
"
# Compare against hermes_constants.SIGNAL_SOURCE_BLACKLIST
python3 -c "from hermes_constants import SIGNAL_SOURCE_BLACKLIST; print('Blacklist:', SIGNAL_SOURCE_BLACKLIST)"
```
⚠️ If a blacklisted source appears in the DB with EXECUTED=1, the bypass is active.

## Quick Zero-Signal Triage (First 5 Minutes)

When `signal_gen.run()` returns 0 added signals, check these in order:

```bash
# 1. Is add_signal() being called at all? (fastest check)
cd /root/.hermes && python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.signal_schema import add_signal
r = add_signal('BTC','LONG','test','test',confidence=85,value=1,price=70000)
print('add_signal works:', bool(r))
"

# 2. Are tokens reaching signal_gen with valid data?
cd /root/.hermes && python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.signal_gen import get_momentum_stats
mom = get_momentum_stats('BTC')
print('BTC rsi_14:', mom.get('rsi_14'))
print('BTC pct_short:', mom.get('percentile_short'))
"

# 3. Check add_signal return value (is it truthy?)
cd /root/.hermes && python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.signal_schema import add_signal
# Test each signal_type this token would use
for stype in ['mtf_macd','rsi_individual','velocity','mtf_zscore']:
    r = add_signal('BTC','LONG',stype,'test',confidence=85,value=1,price=70000)
    print(f'{stype}: sid={r}')
"

# 4. Check MIN_CONFIDENCE_FLOOR — signals below this are silently dropped
grep -n "MIN_CONFIDENCE_FLOOR" /root/.hermes/scripts/signal_schema.py
```

## Common Bugs Found

### Bug 6: avg_z vs z_1h z-score filter (critical — causes zero signals)
**Symptom:** No signals from `_run_mtf_macd_signals()`. BTC has z_1h=-0.503 (good for LONG) but avg_z=0.621 (blocks entry).
**Root cause:** Line 1577 checked `avg_z > LONG_1H_Z_MAX` where `avg_z` is the AVERAGE across all 6 TFs (1m through 4h). A single elevated sub-1H TF inflates avg_z and blocks entries that should pass on 1H z.
**Fix:** Use `z_1h` from `get_tf_zscores()` instead:
```python
zscores = get_tf_zscores(token)
z_1h = zscores.get('1h', (None, None))[0] if zscores else None
if z_1h is not None and z_1h > LONG_1H_Z_MAX:
    continue
```
**Verification:**
```bash
cd /root/.hermes && python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.signal_gen import get_momentum_stats, get_tf_zscores
for tok in ['BTC','ETH','SOL']:
    mom = get_momentum_stats(tok)
    zs = get_tf_zscores(tok)
    z1h = zs.get('1h',(None,None))[0] if zs else None
    print(f'{tok}: avg_z={mom[\"avg_z\"]:.3f} z_1h={z1h} filter_pass={z1h <= 0.5 if z1h else True}')
"
```

### Bug 7: Percentile confidence below MIN_CONFIDENCE_FLOOR (critical — causes zero signals)
**Symptom:** `add_signal()` returns falsy (None/0) for percentile signals. Token clearly has elevated percentile (e.g., `pct_short=74.4`) but no signal written.
**Root cause:** Old formula: `(pct_val - 70) * 4.0`. At pct_val=74.4 → 17.6. `MIN_CONFIDENCE_FLOOR = 50` in `signal_schema.add_signal()` silently drops signals below 50.
**Fix:** Ensure confidence reaches floor:
```python
# pct_val 72→50pts, pct_val 100→75pts. Now passes MIN_CONFIDENCE_FLOOR at pct_val=72.
pct_conf = min(80, max(50, (pct_val - 72) * 3.5 + 50))
```
**Verification:**
```bash
cd /root/.hermes && python3 -c "
pct_val = 74.4
old = min(75, (pct_val - 70) * 4.0)
new = min(80, max(50, (pct_val - 72) * 3.5 + 50))
print(f'pct_val={pct_val}: old_conf={old:.1f} (dropped!), new_conf={new:.1f} (passes)')
"
```

### Bug 8: `rsi_14` column missing from momentum_cache
**Symptom:** `get_momentum_stats()` computes RSI (via `get_price_history()` then `rsi()`) but `momentum_cache` table has no `rsi_14` column. All signals using `rsi_val = mom.get('rsi_14')` return None.
**Root cause:** `_persist_momentum_state()` INSERT never included `rsi_14` column. The function didn't accept the parameter. Column didn't exist in DB schema.
**Fix:**
```sql
ALTER TABLE momentum_cache ADD COLUMN rsi_14 REAL;
```
Then update `_persist_momentum_state()` signature and INSERT to include `rsi_14`.

### Bug 9: rsi_individual and mtf_macd signals never increment `added` counter
**Symptom:** `add_signal()` returns valid signal IDs but `added` stays 0.
**Root cause:** The `added += 1` was only in `_run_rsi_signals_for_confluence()`. The `mtf_macd`, `rsi_individual`, `velocity`, and `mtf_zscore` calls in `_run_mtf_macd_signals()` never had `added += 1`.
**Fix:** Wrap each `add_signal()` call in `_run_mtf_macd_signals()` with `if sid: added += 1`.

### Bug 10: Counter duplicated during debug editing
**Symptom:** `added` gets double-incremented or code breaks after patching.
**Root cause:** During inline debugging, it's easy to accidentally duplicate `add_signal()` calls or leave dangling `rsi_14=rsi_val)` lines.
**Fix:** Always verify after patching — check the full function with line numbers after any inline debug session.

### Bug 1: Path mismatch in hermes-trades-api.py
Symptom: hotset.json has tokens but signals.json hot_set is empty.
Fix: Change line 324 from `/root/.hermes/data/hotset.json` to `/var/www/hermes/data/hotset.json`.

### Bug 2: HOTSET_BLOCKLIST not imported in ai_decider.py
Symptom: ai_decider crashes on every cycle, decisions table stays empty, hotset never refreshes.
Fix: Add `HOTSET_BLOCKLIST` to the import line for hermes_constants.

### Bug 3: sig_entry referenced before assignment
Symptom: Secondary error in ai_decider, compaction skips.
Fix: Move sig_entry lookup before the source blacklist check.

### Bug 4: SIGNAL_SOURCE_BLACKLIST bypass — dash vs underscore mismatch (CRITICAL)
Symptom: rsi-confluence signals keep executing despite being in SIGNAL_SOURCE_BLACKLIST.
Root cause: `signal_schema.add_signal()` checks `signal_type` against blacklist, but signal_gen.py
passes `signal_type='rsi_confluence'` (underscore) while blacklist has `'rsi-confluence'` (dash).
Both field names are used inconsistently throughout the codebase:
  - signal_type field: `rsi_confluence` (underscore)
  - source field: `rsi-confluence` (dash)
  - add_signal() checks signal_type (underscore) → never matches blacklist (dash)
  - ai_decider checks src_val (source field, dash) → this path works
  - hermes-trades-api.py query excludes source='rsi-confluence' (dash) → this path works
Fix: Add BOTH variants to SIGNAL_SOURCE_BLACKLIST in hermes_constants.py:
  SIGNAL_SOURCE_BLACKLIST = {
      'rsi-confluence',  # source field (dash)
      'rsi_confluence',  # signal_type field (underscore)
  }
VERIFICATION: After fixing, run:
  python3 -c "from hermes_constants import SIGNAL_SOURCE_BLACKLIST; print('rsi_confluence blocked:', 'rsi_confluence' in SIGNAL_SOURCE_BLACKLIST)"

### Bug 5: Guardian creates duplicate paper trades via add_orphan_trade
Symptom: Two open trades for same token (e.g., AXS id=4525 non-paper + id=4531 paper).
Root cause: hl-sync-guardian.py `add_orphan_trade()` creates paper trades without going through
add_signal() or execute_trade(). It bypasses all signal-level blocking (HOTSET_BLOCKLIST,
SIGNAL_SOURCE_BLACKLIST, confidence floor). Guardian creates paper records when HL has a position
but brain DB doesn't.
Fix: If a guardian-created paper trade appears with a blacklisted signal source, close it manually
and add the token to HOTSET_BLOCKLIST if not already there. Check regularly:
  SELECT id, token, status, signal, paper, server FROM trades WHERE token='<token>' ORDER BY id;

## Hot-set Empty but Pipeline Clean?
- Check if hotset.json timestamp is stale (>20 min old)
- If stale: manually reset with `{"hotset":[],"compaction_cycle":0,"timestamp":<current_unix_ts>,"note":"Reset"}`
- LLM-compaction will rebuild on next 10-min cycle if signals exist
- If no signals exist (market neutral), hot-set stays empty — this is NORMAL, not a bug

## Key Files
- `/var/www/hermes/data/hotset.json` — authoritative hot-set (written by ai_decider)
- `/var/www/hermes/data/signals.json` — dashboard export (written by hermes-trades-api.py)
- `/root/.hermes/data/signals_hermes_runtime.db` — SQLite runtime signals DB
- `/root/.hermes/scripts/ai_decider.py` — decision engine + LLM compaction
- `/root/.hermes/scripts/hermes-trades-api.py` — dashboard data exporter
- `/root/.hermes/logs/pipeline.log` — pipeline execution log
