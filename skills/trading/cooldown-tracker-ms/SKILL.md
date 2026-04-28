---
name: cooldown-tracker-ms
description: 'CRITICAL cooldown investigation guide for Hermes trading system. Covers the TWO
  separate cooldown stores, which code paths write to which store, and which functions READ
  from which store. The most common bug: one store has the cooldown but the reader function
  checks a DIFFERENT store.'
version: 6.0.0
author: Hermes Agent
created: 2026-04-20
updated: 2026-04-23
tags: [cooldown, signal-schema, bug-fix, time-units, signal-gen, paths-py, orphan-trades, postgresql, hot-set, signal-compactor]
notes:
  - "BUG FIX (2026-04-27): accel_300_signals.py cooldown bug — wrote to loss_cooldowns.json via set_cooldown() but checked TRADE_LOG_FILE via recent_trade_exists() before firing. Fixed by adding get_cooldown() check before firing. Symptom: accel-300+ signals fired every ~2min for 40min while price collapsed from +0.3% to -1.8% vs EMA300."
  - "BUG (2026-04-23): set_cooldown fix was half-done — wrote to loss_cooldowns.json with reason=signal but _is_loss_cooldown_active() blocked ALL entries regardless of reason — hot-set empty until purged 182 signal-gen entries and fixed reader to skip reason=signal"
  - BUG FIX (2026-04-22): is_loss_cooldown_active() now checks BOTH loss_cooldowns.json AND PostgreSQL
  - BUG FIX (2026-04-22): get_cooldown() purges stale entries from loss_cooldowns.json on every call
  - BUG FIX (2026-04-22): get_cooldown() periodically purges expired rows from PostgreSQL signal_cooldowns
  - BUG FIX (2026-04-22): decider_run.close_position() now writes to BOTH stores (was missing entirely)
  - BUG FIX (2026-04-22): _close_orphan_paper_trade_by_id() now calls _record_loss_cooldown() for losing orphan trades
  - BUG FIX (2026-04-22): signal_compactor.py scoring loop now checks get_cooldown() before adding to hot-set
  - BUG FIX (2026-04-22): _filter_safe_prev_hotset() now checks get_cooldown() — was BCH's exact re-entry path
  - signal_compactor is the AUTHORITY on hot-set.json — it writes every compaction run (~1 min interval via cron)
  - Constants in paths.py (SINGLE SOURCE) — imported by hl-sync-guardian, position_manager, cascade_flip, signal_schema
  - DEBUG (2026-04-22): signal_compactor outputs to /var/www/hermes/logs/signals.log NOT pipeline.log
  - DEBUG (2026-04-22): tokens with open positions are BLOCKED from hot-set by OPEN-POS-FILTER in signal_compactor
  - DEBUG (2026-04-22): PostgreSQL signal_cooldowns stores token='XRP:SHORT' (with colon) but decider_run is_loss_cooldown_active() queries correctly with same format
  - DEBUG (2026-04-22): hot-set can be empty because (a) only entry was blocked by cooldown, or (b) only entry was blocked by open-position filter, or (c) signal_gen generated no new signals that cycle
---

# Cooldown Systems — Complete Architecture Map

## THE GOLDEN RULE

**Every cooldown writer must be matched with a reader check. If you add a writer to a new store, find all readers and add that store to their read path.**

## Critical Log File Locations

| File | What Goes There | How to Read |
|------|----------------|-------------|
| `/var/www/hermes/logs/signals.log` | **signal_compactor output** (1m cron), hot-set iterations, OPEN-POS-FILTER, EXEC events | `tail -f /var/www/hermes/logs/signals.log` |
| `/root/.hermes/logs/pipeline.log` | Pipeline orchestrator (pipeline.py), price_collector, regime_scanner, signal_gen output | `tail -f /root/.hermes/logs/pipeline.log` |
| `/root/.hermes/logs/sync-guardian.log` | Guardian position sync with HL, rate-limit errors | `tail -f /root/.hermes/logs/sync-guardian.log` |

**Common mistake:** Looking in `pipeline.log` for signal_compactor decisions. signal_compactor runs as a separate systemd service and writes to `signals.log`. The orchestrator logs "Running signal_compactor..." to pipeline.log but the actual compaction decisions are in signals.log.

---

## The Two Active Cooldown Stores

| Store | Technology | Primary Writer | Backup Writer | Read By | Duration |
|-------|-----------|---------------|---------------|---------|----------|
| `loss_cooldowns.json` | JSON file | `_record_loss_cooldown()` (guardian paper path) | `decider_run.close_position()` | **`is_loss_cooldown_active()` — PRIMARY** | exponential (10-40min, streak-based) |
| `signal_cooldowns` | PostgreSQL | `_record_trade_outcome()` (HL live-close path) | `set_cooldown()` | **`is_loss_cooldown_active()` — fallback** + `get_cooldown()` | flat (1h) |

**SQLite `cooldown_tracker` table is DEAD — ignored by all code.**

---

## The Two Reader Functions (Different!)

### `is_loss_cooldown_active(token, direction)` — position_manager.py
Used by **`decider_run`** before executing every signal. This is the execution gate.

**What it checks (AFTER 2026-04-22 fix):**
1. `loss_cooldowns.json` — PRIMARY (guardian paper path)
2. PostgreSQL `signal_cooldowns` — FALLBACK (HL live-close path)

```python
# position_manager.py
def is_loss_cooldown_active(token: str, direction: str) -> bool:
    key = f"{token.upper()}:{direction.upper()}"
    # Check JSON first
    data = _clean_expired(_load_cooldowns())
    if key in data:
        return True
    # Fallback: PostgreSQL (written by _record_trade_outcome on HL closes)
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM signal_cooldowns WHERE token=%s AND direction=%s AND expires_at > NOW()",
            (key, direction.upper()))
        result = cur.fetchone()
        cur.close(); conn.close()
        return bool(result)
    except Exception:
        pass
    return False
```

### `get_cooldown(token, direction=None)` — signal_schema.py
Used by **`signal_compactor`** to filter hotset candidates. Checks both TOKEN-direction keys AND per-direction cooldowns.

**What it checks:**
1. `loss_cooldowns.json` — PRIMARY (guardian's authoritative source)
2. PostgreSQL `signal_cooldowns` — FALLBACK (general cooldowns)

**Note:** `get_cooldown()` is NOT called by decider_run — it uses `is_loss_cooldown_active()` instead. These are two SEPARATE functions with two SEPARATE read paths.

---

## The Three Write Paths

### Writer 1: `_record_loss_cooldown()` — hl-sync-guardian.py (guardian paper path)
Called when guardian CLOSES a PAPER trade with loss.

```python
# hl-sync-guardian.py
if final_pnl_usdt < 0:
    _record_loss_cooldown(token, direction)        # → loss_cooldowns.json
    from signal_schema import set_cooldown
    set_cooldown(token.upper(), direction.upper(), hours=1)  # → PostgreSQL
```

**Closes that trigger this:** `CUT_LOSER_CLOSE_FAILED`, `HARD_SL_CLOSE_FAILED`, `ORPHAN_PAPER`, `MAX_POSITIONS`, `HOTSET_BLOCKED`

### Writer 2: `_record_trade_outcome()` — hl-sync-guardian.py (HL live-close path)
Called when HL reports a fill (live trade closes). Writes **ONLY to PostgreSQL** (NOT to loss_cooldowns.json).

```python
# hl-sync-guardian.py — _record_trade_outcome()
if not is_win:
    from signal_schema import set_cooldown
    set_cooldown(token.upper(), direction.upper(), hours=1)  # → PostgreSQL ONLY
```

**Closes that trigger this:** `HL_SL_CLOSED`, `HL_CLOSED`, `atr_sl_hit`, `histogram_zero_cross`, `profit_monster`, `cascade_flip`

**THE BUG (pre-2026-04-22):** `_record_trade_outcome()` wrote PostgreSQL only. `is_loss_cooldown_active()` read JSON only. HL-live closes were invisible to the execution blocker. **FIXED: `is_loss_cooldown_active()` now also checks PostgreSQL.**

### Writer 3: `decider_run.close_position()` — decider_run.py (manual/counter-signal close)
Called when decider_run closes a position manually or via counter-signal.

**THE BUG (pre-2026-04-22):** Did NOT write any cooldown. Counter-signal closes were invisible to the execution blocker. **FIXED: now writes to BOTH stores.**

---

## Cooldown Duration Rules

| Event | Store | Duration |
|-------|-------|----------|
| Guardian paper loss (`_record_loss_cooldown`) | JSON | Exponential: `10min * 2^(streak-1)`, cap 40min |
| HL live loss (`_record_trade_outcome`) | PostgreSQL | Flat 1 hour |
| Manual close (`decider_run.close_position`) | BOTH | JSON: streak-based, PostgreSQL: flat 1h |

Formula: `hours = min(LOSS_COOLDOWN_BASE * 2^(streak-1), LOSS_COOLDOWN_MAX)` where `LOSS_COOLDOWN_BASE=10/60` and `LOSS_COOLDOWN_MAX=40/60`.

---

## Correct Investigation — Check Both Stores

```python
# Check BOTH stores side-by-side for any token
import json, time, psycopg2
from _secrets import BRAIN_DB_DICT

TOKEN = 'ETH'
DIRECTION = 'LONG'

# Store 1: JSON
json_path = '/root/.hermes/data/loss_cooldowns.json'
with open(json_path) as f:
    jdata = json.load(f)
key = f"{TOKEN}:{DIRECTION}"
entry = jdata.get(key)
if entry:
    remaining = (entry['expires'] - time.time()) / 60
    print(f"JSON: {key} — {remaining:.1f}min left, streak={entry.get('streak')}")
else:
    print(f"JSON: {key} — NOT FOUND")

# Store 2: PostgreSQL
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("""
    SELECT token, direction, expires_at, expires_at > NOW() as active
    FROM signal_cooldowns
    WHERE token = %s AND direction = %s
""", (key, DIRECTION))
row = cur.fetchone()
if row:
    remaining = (row[2] - datetime.now(timezone.utc)).total_seconds() / 60
    print(f"PostgreSQL: {key} — {remaining:.1f}min left, active={row[3]}")
else:
    print(f"PostgreSQL: {key} — NOT FOUND")
conn.close()
```

---

### Pattern 8: Half-Done Refactor — Writer Fixed, Reader Not Updated (2026-04-23)
**Symptom:** Hot-set is empty. `loss_cooldowns.json` has 150+ entries with `reason='signal'`. Compactor finds multi-source signals with high scores (100-170) but every single one hits `LOSS-COOLDOWN skip`. `_is_loss_cooldown_active()` returns `True` for everything.
**Root cause:** A previous fix updated `set_cooldown()` to write to `loss_cooldowns.json` with `reason='signal'`. But `_is_loss_cooldown_active()` was NOT updated — it checks ALL entries regardless of `reason`. Since all 150+ entries have `reason='signal'` (signal-generator cooldowns, not guardian losses), ALL signals get blocked.
**Fix applied (`signal_schema.py` `_is_loss_cooldown_active`):**
```python
# Added reason check:
entry = loss_data.get(key)
if not entry:
    return False
reason = entry.get('reason') if isinstance(entry, dict) else None
if reason and reason != 'loss':   # ← NEW: skip signal-generator cooldowns
    return False
expiry = entry.get('expires') if isinstance(entry, dict) else entry
return bool(expiry and expiry > time.time())
```
**Also:** Purged all `reason='signal'` entries from `loss_cooldowns.json` (182 entries removed, 0 actual guardian losses were present).

### Pattern 9: _is_cooldown_key_active() Missing reason Check (2026-04-23)
**Symptom:** Tokens with `reason='signal'` cooldowns still appear in hot-set via `_filter_safe_prev_hotset()`. The main scoring loop uses `_is_loss_cooldown_active()` (which correctly skips `reason='signal'`), but `_filter_safe_prev_hotset()` calls `get_cooldown()` → `_is_cooldown_key_active()` which had **no reason check**. A token with score=0 but `reason='signal'` would bypass the filter and cycle back into hot-set.
**Root cause:** `_is_cooldown_key_active()` is a shared helper used for both `loss_cooldowns.json` (where reason should be checked) and the legacy `cooldowns.json` fallback (which doesn't use reason). The fix in `_is_loss_cooldown_active()` was not propagated to the shared helper.
**Fix applied (`signal_schema.py` `_is_cooldown_key_active`):**
```python
def _is_cooldown_key_active(key: str, data: dict) -> bool:
    entry = data.get(key)
    if not entry:
        return False
    reason = entry.get('reason') if isinstance(entry, dict) else None
    if reason and reason != 'loss':   # ← NEW: skip signal-generator cooldowns
        return False
    expiry = entry.get('expires') if isinstance(entry, dict) else entry
    return bool(expiry and expiry > time.time())
```
**Key lesson:** When fixing a bug in a shared helper function, audit ALL callers to ensure the fix is applied consistently across all code paths.

## Common Bug Patterns

### Pattern 1: Writer writes Store A, Reader checks Store B
**Symptom:** Cooldown "doesn't work" — token re-enters immediately.
**Root cause:** `recent_trade_exists()` in `signal_gen.py` reads `TRADE_LOG_FILE`. `set_cooldown()` writes `loss_cooldowns.json` (via signal_schema). These are completely separate stores — a cooldown is written but the reader looks in the wrong file.

**Common variant (NEW signal scripts):** A new signal generator imports BOTH `recent_trade_exists` (from signal_gen) AND `set_cooldown` (from signal_schema/signal_gen re-export). It sets cooldown correctly but checks the wrong store before re-firing. Result: signal fires every ~2 minutes as long as conditions persist — the cooldown is written but never checked.

**Example (accel_300_signals.py bug, 2026-04-27):** `scan_accel_300_signals()` calls `set_cooldown()` after firing (line 342, writes loss_cooldowns.json), but line 291 checks `recent_trade_exists()` which reads `TRADE_LOG_FILE`. The cooldown is set but never blocks re-entry. Fix: add `get_cooldown()` check before firing.

**Fix:** When adding cooldown to a signal script — use ONE read function consistently. The safe pattern: read from `get_cooldown()` (signal_schema) which checks the authoritative store. Do not mix `recent_trade_exists()` with `set_cooldown()` unless you are deliberately using separate stores (and you are sure both readers are checked).

### Pattern 2: No cooldown written for a close reason
**Symptom:** Specific close reason (e.g., `HL_SL_CLOSED`) doesn't block re-entry.
**Fix:** Find the close reason handler and add `set_cooldown()` or `_record_loss_cooldown()`.

### Pattern 3: Per-direction cooldown queried without direction
**Symptom:** `get_cooldown('APE')` returns None but `get_cooldown('APE','SHORT')` returns True.
**Fix:** `get_cooldown()` now checks both `TOKEN:LONG` and `TOKEN:SHORT` when direction=None.

### Pattern 4: signal_compactor bypasses cooldowns entirely
**Symptom:** Token is in cooldown (written to PostgreSQL or JSON) but still appears in hotset.json.
**Root cause:** `signal_compactor.py` scoring loop never calls `get_cooldown()`. A token with zero signals gets score=0 but bypasses the cooldown check.
**Fix (2026-04-22):** Added `get_cooldown()` check in main scoring loop BEFORE computing final_score. If token is in cooldown, set score=0 immediately.

### Pattern 5: _filter_safe_prev_hotset preserves cooldown'd tokens from previous hotset
**Symptom:** Token appears in hotset every compaction cycle despite being in cooldown. The token survives because it has no fresh signals (score=0) so `_preserve_previous_hotset()` calls `_filter_safe_prev_hotset()` to re-add it — without checking cooldowns.
**Root cause (2026-04-22):** `_filter_safe_prev_hotset()` had no `get_cooldown()` call. A cooldown'd token with score=0 would cycle back into hotset forever.
**Fix (2026-04-22):** `_filter_safe_prev_hotset()` now calls `get_cooldown(tkn, direction)` and skips any token that returns True.

### Pattern 6: OPEN-POS-FILTER — token with open position blocked from hot-set
**Symptom:** Token appears in hot-set briefly then vanishes. Log shows: `[OPEN-POS-FILTER] Tokens with open positions: ['bch']` and `🚫 [HOTSET-FILTER] BCH: blocked — already has open position`.
**Root cause:** `signal_compactor.py` checks `get_open_positions()` and excludes tokens that are already open. This prevents double-entry but can make hot-set appear empty if the only surviving token already has a position.
**Investigation:**
```bash
tail -100 /var/www/hermes/logs/signals.log | grep -E "OPEN-POS|HOTSET-FILTER|hot-set"
```

### Pattern 7: Empty hot-set because all entries blocked at different layers
**Symptom:** Dashboard shows empty hot-set but signals.log shows entries being generated. Common blocking layers:
1. `[OPEN-POS-FILTER]` — token already has open position
2. `get_cooldown()` in compactor scoring loop — token in loss cooldown
3. `is_loss_cooldown_active()` in decider_run — token in loss cooldown (execution gate)
4. `_filter_safe_prev_hotset()` — token in cooldown but would otherwise survive
**Debug command (check all layers at once):**
```python
import json, sys, psycopg2
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import get_cooldown

hotset = json.load(open('/var/www/hermes/data/hotset.json'))
open_tokens = json.load(open('/root/.hermes/data/trades.json')).get('open_positions', [])

conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
cur = conn.cursor()
cur.execute("SELECT token, direction, expires_at FROM signal_cooldowns WHERE expires_at > NOW()")
active_cooldowns = {(r[0], r[1]): r[2] for r in cur.fetchall()}
conn.close()

for e in hotset.get('hotset', []):
    tok, direction = e['token'], e['direction']
    key = f"{tok}:{direction}"
    in_pg_cooldown = key in active_cooldowns
    in_signal_cooldown = bool(get_cooldown(tok, direction))
    is_open = tok.lower() in [p['token'].lower() for p in open_tokens]
    print(f"  {tok} {direction}: open={is_open} pg_cooldown={in_pg_cooldown} get_cooldown={in_signal_cooldown}")
if not hotset.get('hotset'):
    print("  HOT-SET IS EMPTY — check signals.log for why compactor produced nothing")
    print("  tail -200 /var/www/hermes/logs/signals.log | grep -E 'COMPACT|hot-set|blocked'")
```

**Investigation command:**
```bash
# Check if a token in hotset is actually in cooldown
import json, sys
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import get_cooldown

hotset_path = '/var/www/hermes/data/hotset.json'
with open(hotset_path) as f:
    hs = json.load(f)
for e in hs.get('hotset', []):
    tok = e.get('token', '')
    direction = e.get('direction', '')
    cooldown = get_cooldown(tok, direction)
    print(f"  {tok} {direction}: cooldown={cooldown}")

## Constants — SINGLE SOURCE (paths.py)

## Constants — SINGLE SOURCE (paths.py)

**LOCATION:** `/root/.hermes/scripts/paths.py`

```
LOSS_COOLDOWN_BASE      = 10 / 60   # 10 min for 1st consecutive loss
LOSS_COOLDOWN_MAX       = 40 / 60   # cap at 40 min after 3+ consecutive losses
WIN_COOLDOWN_MINUTES    = 5         # block same direction for 5 min after a win
```

**All modules import from paths.py — do NOT redefine inline.**
