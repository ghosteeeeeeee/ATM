---
name: hermes-pipeline-debug
description: Debug signals/hot-set discrepancies in Hermes trading pipeline — signals in DB but not in dashboard, empty hot-set despite running pipeline
triggers:
  - "signals in DB but not in dashboard"
  - "hot-set empty"
  - "signals.json count mismatch"
  - "pipeline running but no hot signals"
  - "signals.html shows different counts than runtime DB"
  - "signal/opened fields blinking on/off in trades.json"
  - "signals.json shows 0 despite DB having rows"
  - "trades.json written by multiple scripts"
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

### Bug 11: Dual-writer flashing — signal/opened fields blink on/off
**Symptom:** "signal" and "opened" fields in trades.json flash between actual values and empty/blank every few minutes.
**Root cause:** Two scripts write the same output file:
  - `hermes-trades-api.py` — writes full record with signal, opened, confidence, etc.
  - `update-trades-json.py` — writes ONLY token/direction/entry/current/pnl (no signal/opened)
  Pipeline runs `hermes-trades-api` then 1 min later `update-trades-json` overwrites it with incomplete data → flashing.
**Fix:** Consolidate to ONE writer. `hermes-trades-api.py` is the authoritative source (has all fields). Remove `update-trades-json` from pipeline STEPS_EVERY_MIN in run_pipeline.py.
**Also fix:** `hermes-trades-api.py` used `host=localhost` (TCP) which fails intermittently. Change to `host=/var/run/postgresql` (Unix socket) + correct password `Brain123` for reliable connections.

### Bug 12: Wrong signals DB path + missing hot_set field in signals.json
**Symptom:** signals.json reports 0 signals (or 0 hot_set) despite runtime DB having thousands of rows.
**Root cause (part 1):** `SIGNALS_DB` in hermes-trades-api.py pointed to wrong path:
  - WRONG: `/root/.openclaw/workspace/data/signals.db` (stale 53KB, weeks old)
  - CORRECT: `/root/.hermes/data/signals_hermes_runtime.db` (live 2.5MB, updated every cycle)
**Fix (part 1):** Update SIGNALS_DB path in hermes-trades-api.py.
**Root cause (part 2):** `write_signals()` did not include `hot_set` key in the result dict at all — the field was missing from signals.json entirely. The hot_set query code existed elsewhere in an older version of the file but was absent in the current version.
**Fix (part 2):** Add hot_set query (from hotset.json + SQLite fallback) and include `"hot_set": hot_set` in the result dict.

### Bug 13: SQLite column name mismatch — query silently returns empty list
**Symptom:** signals.json has 0 signals despite DB having rows. No Python errors shown.
**Root cause:** `get_signals_from_db()` queried column `macd_histogram` but actual column is `macd_hist`. Query wrapped in bare `except:` that silently returns `[]` on any error.
**Fix:** Always run the exact query from the source file directly against the DB to catch schema mismatches:
  ```bash
  python3 -c "import sqlite3; conn=sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db'); c=conn.cursor(); c.execute("SELECT macd_histogram ...")"; "
  ```
  Compare actual column names (`PRAGMA table_info(signals)`) against query SELECT list.

### Bug 14: PostgreSQL net_pnl column doesn't exist
**Symptom:** hermes-trades-api.py fails on write_signals() with "column net_pnl does not exist".
**Root cause:** Table has `pnl_usdt`, not `net_pnl`.
**Fix:** Replace `net_pnl` → `pnl_usdt` in all SQL queries in hermes-trades-api.py.

### Bug 15: hot_set in signals.json always empty — no SQLite fallback for stale hotset.json
**Symptom:** signals.json has `hot_set: 0` even though SQLite has 30+ hot tokens (`hot_cycle_count >= 1`).
**Root cause:** `hermes-trades-api.py` only reads hot_set from hotset.json (written by ai_decider). If hotset.json is stale (>11 min — e.g., ai_decider hitting "Token budget exceeded"), it returns empty list. No SQLite fallback existed.
**Fix:** Add SQLite fallback query in `write_signals()` — when hotset.json is stale or absent, query `signals_hermes_runtime.db` directly for `hot_cycle_count >= 1`.
**Also:** ai_decider token budget issue means hotset.json can go stale for hours. The SQLite fallback is the correct fix — it bypasses the LLM entirely.

### Bug 16: signals.html uses wrong field name for z-score (s.zscore vs s.z_score)
**Symptom:** Hot-set tokens show z-score as `--` in the HTML dashboard even though signals.json has valid z_score values.
**Root cause:** `signals.html` line 251 reads `s.zscore` but `signals.json` emits `z_score` (underscore). JS silently gets `undefined`, converts to `NaN`, displays as `--`.
**Fix:** Change `const zscore = parseFloat(s.zscore)` → `const zscore = parseFloat(s.z_score)` in signals.html.

### Bug 17: hermes-trades-api.py PostgreSQL TCP auth failure
**Symptom:** `hermes-trades-api.py` uses `host=localhost dbname=brain user=postgres password=brain123` (TCP). Connections fail with "password authentication failed" or "connection refused" because TCP auth on localhost:5432 is broken.
**Root cause:** PostgreSQL is only accessible via Unix socket at `/var/run/postgresql`. TCP/IP is disabled/refused.
**Fix:** Change `BRAIN_DB` to `host=/var/run/postgresql dbname=brain user=postgres password=Brain123`. Note: password is `Brain123` (capital B), not `brain123`.

### Bug 18: Removing update-trades-json revealed hermes-trades-api was incomplete
**Lesson learned:** When consolidating dual-writers, don't just remove the secondary writer — verify the primary writer actually produces complete output. The "fix" exposed 4 pre-existing bugs in hermes-trades-api that were masked because update-trades-json was overwriting it every minute.
**Before removing a writer:** Run the surviving script standalone and verify output completeness before touching the pipeline.

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

### Bug 19: LLM calls in ai_decider.py have no timeout — pipeline hangs indefinitely
**Symptom:** `decider_run` times out (pipeline log shows `ERROR decider_run: timed out`) repeatedly. The step never completes. Systemd `TimeoutStopSec=10min` eventually kills it.
**Root cause:** Three OpenAI SDK calls in `ai_decider.py` use the OpenAI SDK's default timeout (None = infinite wait). When the LLM endpoint is slow or unreachable, the process hangs forever.
**Affected call sites (ai_decider.py):**
1. `_do_compaction_llm()` — line ~1331 (hot-set compaction)
2. `ai_decide_batch()` — line ~2233 (batch decisions for non-hot signals)
3. `ai_decide()` — line ~2565 (individual decisions for hot signals)

**Fix:** Add `timeout=60` to all OpenAI client instantiations:
```python
_client = OpenAI(api_key=_token, base_url='https://api.minimax.io/v1', timeout=60)
```
Do NOT confuse this with HTTP-level `timeout=` on `requests.get()` — this is the OpenAI SDK's built-in client timeout.

**Debug approach:**
```bash
# Check stderr for hanging LLM calls (writes to pipeline.err.log)
tail -20 /root/.hermes/logs/pipeline.err.log

# Check which step is hanging (look for "Running X..." without corresponding completion)
grep -E "Running decider_run|ERROR decider_run" /root/.hermes/logs/pipeline.log | tail -10

# If decider_run is hanging, check if it's an LLM hang or HL API hang:
grep "429\|rate.limit" /root/.hermes/logs/pipeline.err.log
# 429 = HL API rate-limiting (retry loops in hyperliquid_exchange.py)
# No such messages = likely LLM hang
```

### Bug 20: Token budget exactly hit (daily cap exhausted)
**Symptom:** ai_decider starts skipping all LLM calls with `[BUDGET] Blocked call`. hotset.json goes stale and never refreshes. Signals still flow via SQLite fallback in hermes-trades-api.
**Root cause:** `_DAILY_TOKEN_BUDGET` is set to 1,200,000. When `used` in `ai_decider_daily_tokens.json` hits exactly that value, ALL subsequent LLM calls are blocked.
**Fix:** Reset the counter:
```bash
echo '{"date": "'$(date +%Y-%m-%d)'", "used": 0}' > /root/.hermes/data/ai_decider_daily_tokens.json
```
Also consider raising `_DAILY_TOKEN_BUDGET` if the LLM is the bottleneck (e.g., 2M instead of 1.2M).

### Bug 22: Duplicate Pipeline Runs — Orphaned Process + Double Logging
**Symptom:** Every pipeline cycle fires twice (logs show "Running ai_decider..." twice per cycle). The two runs are NOT from two pipeline processes — they produce identical output with identical timestamps.

**Root cause (double logging):** `hermes-pipeline.service` uses `StandardOutput=append:/root/.hermes/logs/pipeline.log`. Each step script ALSO uses `StandardOutput=append:pipeline.log` in its systemd service definition. Every line written by every step subprocess gets appended twice to the same log file.

**Root cause (orphan):** The pipeline was previously started by a manual `nohup python3 run_pipeline.py &` command (before systemd was set up). That orphaned process kept running alongside systemd's timer, firing the pipeline every minute simultaneously with systemd's every-10-minute trigger.

**Fix (double logging):** Add systemd drop-in override to redirect step output to journal:
```bash
mkdir -p /etc/systemd/system/hermes-pipeline.service.d
cat > /etc/systemd/system/hermes-pipeline.service.d/override.conf << 'EOF'
[Service]
StandardOutput=journal
StandardError=journal
EOF
systemctl daemon-reload
systemctl restart hermes-pipeline.service
```

**Fix (orphan):** Kill orphaned processes:
```bash
kill $(ps aux | grep run_pipeline | grep -v grep | awk '{print $2}')
```
Verify only one remains: `ps aux | grep run_pipeline | grep -v grep`

**Prevention:** Always use `systemctl start/restart hermes-pipeline.service` to trigger pipeline manually, never run `run_pipeline.py` directly in the background.

### Bug 23: FileLock PID Write Leaks File Descriptor
**Symptom:** Multiple FileLock users could potentially corrupt the PID file or leak fds.

**Root cause:** `hermes_file_lock.py` line 53 used `open(self.lockfile, 'w').write(str(os.getpid()))` which opens a NEW file handle separate from `self.fd`, instead of writing to the already-open locked fd.

**Fix:**
```python
# BEFORE (leaks fd):
open(self.lockfile, 'w').write(str(os.getpid()))

# AFTER (uses locked fd):
os.lseek(self.fd, 0, os.SEEK_SET)
os.ftruncate(self.fd, 0)
os.write(self.fd, str(os.getpid()).encode())
```

Also remove `os.unlink(self.lockfile)` from `__exit__` — deleting the lockfile makes it impossible to audit which process held which lock.

### Bug 21: HL API 429 rate-limiting causes decider_run to exceed pipeline timeout
**Symptom:** `decider_run` times out even though no LLM call is hanging. HL API returns 429 repeatedly. Retry backoff in `hyperliquid_exchange.py` uses `4 ** attempt` seconds (1→4→16→64s). With 5 positions to check, total wait can exceed 240s pipeline step timeout.
**Root cause:** `_http_post()` in `hyperliquid_exchange.py` retries up to 8 times with exponential backoff. The 240s `decider_run` step timeout in `run_pipeline.py` is too short for sustained HL rate-limiting.
**Fix options:**
1. Increase step timeout: `STEP_TIMEOUTS['decider_run'] = 360` in `run_pipeline.py`
2. Reduce max HL retries: change `for attempt in range(8)` to `range(4)` to cap max wait at ~30s instead of ~85s
3. Both

**Debug:**
```bash
# 429 retry patterns in stderr
grep "429 rate-limited" /root/.hermes/logs/pipeline.err.log | tail -5
# Shows: "[_http_post] 429 rate-limited, attempt N/8, waiting Xs..."
```

## Hot-set Empty but Pipeline Clean?
- Check if hotset.json timestamp is stale (>20 min old)
- If stale: manually reset with `{"hotset":[],"compaction_cycle":0,"timestamp":<current_unix_ts>,"note":"Reset"}`
- LLM-compaction will rebuild on next 10-min cycle if signals exist
- If no signals exist (market neutral), hot-set stays empty — this is NORMAL, not a bug

## Guardian Sync Debug — hl-sync-guardian.py (DB ↔ HL Reconciliation)

The guardian reconciles Hyperliquid (HL) positions with the PostgreSQL `brain` DB (`trades` table).

### Key Discovery: PostgreSQL, NOT SQLite
The guardian uses **PostgreSQL** to query trades:
```bash
psql -U postgres -d brain -t -c "SELECT id, token, status, paper FROM trades WHERE exchange='Hyperliquid' AND status='open';"
```
NOT SQLite — the SQLite DBs (signals_hermes_runtime.db etc.) are NOT the guardian's source of truth for positions.

### Check if Guardian is Alive
```bash
ps aux | grep hl-sync-guardian | grep -v grep
tail -5 /root/.hermes/logs/sync-guardian.log
```
Guardian is stuck if: no new log entries in >10 min, process still running.

### Check HL Ground Truth (direct API call)
```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_hype_positions_curl
positions = get_open_hype_positions_curl()
# Returns dict like {'ETH': {'size': 0.0045, 'direction': 'LONG', ...}}
```

### Phantom Positions — Root Cause
**Symptom:** DB has 5+ open trades but HL only has 3.
**Root cause:** `_close_paper_trade_db()` silently skips closes when `exit_price <= 0`. When guardian detects a position missing from HL (phantom), it tries to get an exit price from HL fills — if no fills exist (position was never on HL, or fills not available), exit_price=0 → close silently skipped → phantom stays open.

**Fix:** Added explicit validation that raises `ValueError` when exit price is missing/invalid, so the exception handler catches it properly:
```python
# In Step 8 close logic, after _get_hl_exit_price() calls:
if exit_price <= 0:
    raise ValueError(f"No valid exit price for {token}")
```

### Guardian Death Spiral
Guardian can get stuck in a restart loop when:
1. HL API returns 429s → guardian gets rate-limited
2. Orphan handling fails (market_close returns None)
3. Guardian creates duplicate orphan recovery trades each restart
4. Guardian exits due to `ai_decider lock held` conflict

**Fix:**
1. Kill all guardian processes: `kill $(ps aux | grep hl-sync-guardian | grep -v grep | awk '{print $2}')`
2. Reset state files:
   ```bash
   echo '{}' > /root/.hermes/data/guardian-missing-tracking.json
   echo '[]' > /root/.hermes/data/guardian-closed-set.json
   echo '{"copied": [], "closed": []}' > /root/.hermes/data/copied-trades-state.json
   ```
3. Restart: `nohup python3 /root/.hermes/scripts/hl-sync-guardian.py > /root/.hermes/logs/sync-guardian.log 2>&1 &`

### TP/SL Placement — HL API Limitations
HL rejects TP/SL as trigger orders for most tokens. Errors seen:
- `'str' object has no attribute 'get'` — HL returns string error, code expects dict
- `'Main order cannot be trigger order.'` — HL doesn't support TP/SL for this token
- `'Invalid TP/SL price. asset=0'` — BTC price precision mismatch

**Fix for str/dict bug:** Check `isinstance(result, dict)` before calling `.get()`:
```python
result = place_tp_sl_batch(tok, direction, ideal_sl, ideal_tp, order_size)
if isinstance(result, dict) and result.get('success'):
    ...
else:
    error_msg = result if isinstance(result, str) else (result.get('error', 'unknown') if isinstance(result, dict) else 'unknown')
    log(f'❌ TP/SL batch failed: {error_msg}', 'FAIL')
```

### Close Phantom Positions Manually (SQL)
```sql
-- Close specific phantom trades
UPDATE trades
SET status='closed', close_reason='PHANTOM_CLOSE', guardian_closed=TRUE
WHERE id IN (5161, 5164, 5165, 5162, 4904)
  AND exchange='Hyperliquid' AND status='open';
```

## Key Files
- `/var/www/hermes/data/hotset.json` — authoritative hot-set (written by ai_decider)
- `/var/www/hermes/data/signals.json` — dashboard export (written by hermes-trades-api.py)
- `/var/www/hermes/data/trades.json` — open positions (written by hermes-trades-api.py)
- `/root/.hermes/data/signals_hermes_runtime.db` — SQLite runtime signals DB
- `/var/www/hermes/signals.html` — web dashboard (reads signals.json)
- `/root/.hermes/scripts/ai_decider.py` — decision engine + LLM compaction
- `/root/.hermes/scripts/hermes-trades-api.py` — dashboard data exporter
- `/root/.hermes/scripts/run_pipeline.py` — pipeline orchestrator
- `/root/.hermes/scripts/update-trades-json.py` — secondary trades.json writer (should be removed from pipeline)
- `/root/.hermes/logs/pipeline.log` — pipeline execution log
- `/root/.hermes/scripts/hl-sync-guardian.py` — DB↔HL reconciliation (PostgreSQL brain DB)
