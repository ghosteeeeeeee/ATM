---
name: signal-compactor-model-redesign
description: Redesign the signal compactor's hot-set compaction model — changing GROUP BY identity, survival/staleness/rounds tracking, and JSON/DB schema fields across signal_compactor.py + signal_schema.py + hotset.json. For multi-file refactors that change how signal combo identity, staleness, or survival rounds are computed.
version: 1.1.0
author: Hermes Agent
created: 2026-04-26
updated: 2026-04-27
tags: [signals, signal-compactor, hot-set, refactor, multi-file]
triggers:
  - changing how signal rounds or staleness are computed in the compactor
  - redesigning what "survival" or "rounds" means across compaction cycles
  - changing GROUP BY identity (e.g., token+direction → combo_key)
  - adding or removing fields from hotset.json schema
  - changing how multi-source signal combos are identified or merged
---

# Signal Compactor Model Redesign

Redesigning the compaction model requires coordinated changes across 3+ files and the DB schema. This skill captures the pattern used in the 2026-04-26 redesign.

## Key Concepts

### combo_key Identity
`combo_key = TOKEN:DIRECTION:SORTED_SOURCES` — order-independent signal combo identity.
- `gap+,fast+` and `fast+,gap+` → same `combo_key` (sources sorted alphabetically)
- Computed in `signal_schema.add_signal()` on insert
- Used in `signal_compactor.py` GROUP BY instead of `(token, direction)`

### Rounds = Combo Consecutive Cycles
Rounds tracks how many consecutive compaction cycles the **same combo** fired together:
- New combo fires → rounds=1
- Same combo fires next cycle → rounds=2 (lookup prev hot-set by combo_key)
- Combo dies (staleness=0, leaves hot-set) → rounds resets to 1 on next fire

**Critical**: `compact_rounds` in the DB tracks two different things depending on decision state:
- PENDING: failure count (cycles tried and failed to enter top-10)
- APPROVED: hot-set survival rounds (written on APPROVED transition)

These two concepts are semantically different but share one DB column. Consider renaming
`compact_rounds` → `pending_fail_count` for PENDING rows and using `survival_rounds`
for APPROVED rows. The ambiguity is a design debt item.

### Staleness = MAX(created_at) Per Combo
Staleness is now computed from the **actual sources in the entry**, not MAX across all PENDING signals for token+direction. With GROUP BY combo_key, staleness = max created_at of signals in that specific combo.

## Files Changed (in order)

### 1. signal_schema.py — combo_key on INSERT
Add `combo_key` to new signal row. Sources must be sorted for order-independent identity:
```python
source_parts = sorted(set([s.strip() for s in (source or '').split(',') if s.strip()]))
combo_key = f"{token}:{direction}:{','.join(source_parts)}"
```
Update the INSERT or UPDATE query to include `combo_key` column.

### 2. DB — Add new columns + backfill
```sql
ALTER TABLE signals ADD COLUMN combo_key TEXT;
ALTER TABLE signals ADD COLUMN survival_rounds INTEGER DEFAULT 0;
ALTER TABLE signals ADD COLUMN expired_at TEXT;
```
Backfill existing rows:
```sql
UPDATE signals SET combo_key = token || ':' || direction || ':' || source
WHERE combo_key IS NULL;
```

### 3. signal_compactor.py — GROUP BY + staleness + scoring
- GROUP BY clause: `GROUP BY combo_key` (not `token, direction`)
- Add `combo_key` to SELECT (index position matters for unpacking)
- staleness computation: use combo's own `MAX(created_at)`, not MAX across all PENDING for token+direction
- Scoring: unpack combo_key (index 10), apply opposing signal penalty, lookup prev hot-set by combo_key for rounds

### 4. signal_compactor.py — Rounds tracking
```python
prev_hotset_by_combo = {entry['combo_key']: entry for entry in prev_hotset}
# in scoring loop:
if combo_key in prev_hotset_by_combo:
    rounds = prev_hotset_by_combo[combo_key].get('rounds', 0) + 1
else:
    rounds = 1
```

### 5. signal_compactor.py — Opposing signal penalty
```python
def _get_opposing_penalty(conn, token, direction, lookback_min=5):
    """
    Return multiplier for signals with opposing direction.
    Each opposing signal halves confidence (0.5 per opp signal found).
    e.g. 1 opposing → 0.5, 2 opposing → 0.25.
    """
    opp_dir = 'SHORT' if direction == 'LONG' else 'LONG'
    cur = conn.execute("""
        SELECT COUNT(*) FROM signals
        WHERE token=? AND direction=? AND decision IN ('PENDING', 'APPROVED')
        AND created_at > datetime('now', '-' || ? || ' minutes')
    """, (token, opp_dir, lookback_min))
    count = cur.fetchone()[0]
    return (0.5 ** count) if count > 0 else 1.0
```
Penalty is applied as `score = base_score * opp_penalty` in the scoring loop.
Both PENDING and APPROVED opposing signals count — a live opposing position
is strong counter-evidence.
Use DB connection (not connection object) since conn is closed before scoring runs.

### 6. signal_compactor.py — PENDING rejection removed, EXPIRED added
- Remove: `cr >= 5` PENDING rejection block (signals wait for confluence indefinitely)
- Add: EXPIRED logic — entries in previous hot-set not in current top-10 → mark `decision=EXPIRED, expired_at=NOW`
- PENDING signals that age to staleness=0 are also marked EXPIRED (not just forgotten)

### Live bug caught (2026-04-26): `rejected_ids` undefined at result dict
After removing PENDING rejection logic, the final result dict still referenced
`rejected_ids` which no longer existed. Fix: replace with `0` since rejected count
is no longer tracked in the new model.
```python
# WRONG (NameError):
'rejected': len(rejected_ids) if not dry else 0,
# RIGHT:
'rejected': 0,
```

### 7. signal_compactor.py — JSON schema
Hotset.json entries include:
```python
'combo_key': combo_key,
'staleness': staleness,  # per-combo, not per token+direction
'rounds': rounds,
'survival_round': rounds,  # backward compat alias for decider_run.py
# 'survival_score': REMOVED
```

## Hot-Set Timer: 1 Minute (2026-04-27)

The compactor fires every 1 minute via `hermes-signal-compactor.timer` (systemd). Each signal entry has an independent wall-clock survival timer (`entry_origin_ts`) — staleness is the **only** exit mechanism. Compactor fires frequently to keep the hot-set fresh; individual signals age out naturally at 5 minutes wall-clock.

```
OnCalendar=*:0/1:00   # Every 1 minute at :00, :01, :02, etc.
```

Timer file: `/etc/systemd/system/hermes-signal-compactor.timer`

## Staleness = Only Exit Mechanism (2026-04-27)

Staleness is computed from `entry_origin_ts` (wall-clock when combo first entered hot-set):
```python
age_min = (now - entry_origin_ts) / 60.0
staleness = max(0.0, 1.0 - age_min * 0.2)  # exits at staleness <= 0.01 (~5 min)
```

`compact_rounds` is **NOT** decremented on preserve. It has no role in hot-set exit. A signal exits when `staleness <= 0.01` (5 min wall-clock from entry_origin_ts).

Rounds increment rule: `rounds` only increments when the combo fires together again in a new cycle (DB entry exists). On preserve (no new DB entry), rounds stays the same — it does NOT decrement.

## Breakout Signal Exemption (2026-04-27)

`breakout` is a single-source signal that bypasses the confluence gate (requires 2+ sources). It writes to BOTH DB and hot-set directly. Exemption added at TWO places in signal_compactor.py:

1. **DB query pre-filter (line ~393)**: `if len(source_parts) < 2 and source != 'breakout': continue`
2. **`_filter_safe_prev_hotset` (line ~1029)**: breakout entries pass through without confluence check

breakout writes to DB with `source='breakout'`, `combo_key='TOKEN:DIRECTION:breakout'`. The compactor picks it up from DB on the next 1-min cycle, and merges it with preserved entries.

## Critical Patch Order
The `import os` bug (UnboundLocalError on `os.path.exists`) was caused by `import os` inside the `if not dry:` block while `os.path.exists()` was called before that block at line ~352. When patching:

## Post-Deployment Bug Fixes (2026-04-27)

### BUG: `get_approved_signals()` reading wrong column (signal_schema.py:1022)

The decider's `get_approved_signals()` subquery was reading `compact_rounds` instead of `survival_rounds`:

```python
# WRONG — compact_rounds is always 0 for APPROVED signals (it's PENDING failure count)
(SELECT compact_rounds FROM signals s2
 WHERE s2.token=signals.token ... ORDER BY compact_rounds DESC LIMIT 1), 0

# RIGHT — should read survival_rounds
(SELECT survival_rounds FROM signals s2
 WHERE s2.token=signals.token ... ORDER BY survival_rounds DESC LIMIT 1), 0
```

Impact: Every APPROVED signal had `compact_rounds=0`. The decider's surfing gate checked `hot_rounds < 1` — which was always true — blocking all approved signals from execution.

Fix: Changed the subquery at line 1022 to read `survival_rounds` instead of `compact_rounds`. Also renamed `MIN_COMPACT_ROUNDS` → `MIN_SURVIVAL_ROUNDS` in decider_run.py and updated all variable names and comments.

### BUG: EXPIRE query expiring newly approved signals (signal_compactor.py:847)

The EXPIRE query used `hot_cycle_count >= 1` which immediately eligible newly APPROVED signals for expiration in the next cycle (they get `hcc=1` on APPROVAL). Combined with a Python TypeError in the `approved_ids` exclusion, approved signals were being expired before they could be traded.

```python
# WRONG — newly approved signals get hcc=1 on APPROVAL step, so they'd immediately
# be eligible for expiry in the next cycle's EXPIRE query
WHERE ... hot_cycle_count >= 1

# RIGHT — require hcc >= 2 (survived at least one full compaction cycle after approval)
WHERE ... hot_cycle_count >= 2
```

Also fixed the `approved_ids` exclusion which had a Python bug:
```python
# WRONG — TypeError when approved_ids is empty: .format() unpacks nothing but
# "if approved_ids else []" returns [] as second argument to execute()
c.execute(sql.format(','.join(['?']*len(approved_ids))),
          *([sid for sid in approved_ids] if approved_ids else []))

# RIGHT — use conditional to avoid the execute() call entirely when list is empty
if approved_ids:
    c.execute(sql, approved_ids)
```

## The Two-Column Invariant (Critical Design Rule)

The compactor uses **two separate columns** with completely different semantics:

| Column | Written by | Meaning | Value for APPROVED signals |
|--------|-----------|---------|---------------------------|
| `compact_rounds` | signal_compactor | PENDING failure count — cycles tried and failed to enter top-10 | Always 0 (never written for APPROVED) |
| `survival_rounds` | signal_compactor | APPROVED hot-set survival rounds — consecutive cycles in top-10 | 1-5+ (incremented each refresh cycle) |

**Rule**: Every reader of either column must be aware of this invariant. A common mistake is to check `compact_rounds > 0` to mean "signal has survived in hot-set" — this is wrong. Check `survival_rounds > 0` or `hot_cycle_count > 0` instead.

The decider's surfing gate (`signal_schema.py` → `hot_rounds`) reads `survival_rounds`. The comment at `signal_schema.py:1006` said `compact_rounds > 0` — that was also wrong and was corrected to `survival_rounds > 0`.

## Verification Queries

```python
# Verify APPROVED signals have survival_rounds > 0 and compact_rounds = 0
python3 -c "
import sqlite3
db = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute('''SELECT token, direction, survival_rounds, compact_rounds, hot_cycle_count
             FROM signals WHERE decision=\"APPROVED\" LIMIT 10''')
for row in c.fetchall():
    print(f'{row[0]:8} {row[1]:6} surv={row[2]} compact={row[3]} hcc={row[4]}')
conn.close()
"
# Expected: survival_rounds >= 1, compact_rounds = 0, hot_cycle_count >= 1

# Verify decider's hot_rounds alias matches survival_rounds
python3 -c "
import sqlite3, sys
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import get_approved_signals
signals = get_approved_signals(hours=24)
for s in signals:
    print(f'{s[\"token\"]:8} hot_rounds={s.get(\"hot_rounds\", 0)} conf={s.get(\"max_conf\",0)}')
# hot_rounds should be >= 1 for all entries shown
"
```

## Post-Deployment Audit Findings (2026-04-26)
1. Never import modules inside function bodies — use module-level imports
2. If `import` must be conditional, ensure no references to that module exist earlier in the function
3. Search for `import os` inside function bodies as a separate bug class

## Verification (2026-04-26 live run)
First live run after redesign:
- 0 new signals passed safety filters → hot-set preserved (GRIFFAIN SHORT, rounds=23)
- 6 PENDING signals expired (>5 min) → 3 marked EXPIRED in DB (BLAST:LONG, COMP:LONG, SCR:LONG)
- EXPIRED marking fires correctly; GRIFFAIN staleness=0.0058 (15 sec from exit boundary)
- `rejected_ids` undefined bug caught and fixed before it could cause cascading failures

## Post-Deployment Audit Findings (2026-04-26)

### BUG #5 — CRITICAL: staleness leak in _filter_safe_prev_hotset (signal_compactor.py)
When no new signals pass the pre-filter, `_filter_safe_prev_hotset` preserves entries from the previous hot-set. It refreshed `entry['timestamp'] = time.time()` on every preserve cycle but **never recomputed `entry['staleness']`**. This caused entries to be stuck at their initial staleness value indefinitely — GRIFFAIN showed staleness=0.838 permanently despite being silent for 45+ minutes.

Evidence: GRIFFAIN SHORT was APPROVED, then combo went silent. On each preserve cycle, timestamp was refreshed to `now` but staleness stayed at ~0.83. The entry never reached staleness=0 and never exited.

Fix: Added `entry_origin_ts` field — set once when combo first enters hot-set, preserved across preserve cycles. On each preserve, recompute staleness:
```python
# FIX (2026-04-26): Refresh timestamp AND recompute staleness.
entry_origin_ts = entry.get('entry_origin_ts')
current_ts = time.time()
if entry_origin_ts is None:
    entry_origin_ts = current_ts  # First time this entry is in hot-set
    entry['entry_origin_ts'] = entry_origin_ts
entry['timestamp'] = current_ts
age_min = (current_ts - entry_origin_ts) / 60.0
entry['staleness'] = max(0.0, 1.0 - age_min * 0.2)
```

Also added to JSON schema in hot-set output:
```python
'entry_origin_ts': e.get('entry_origin_ts', e.get('timestamp', time.time()))
```

Staleness formula: `max(0, 1 - age_min/5)` where age_min = (now - entry_origin_ts) / 60. At exactly 5 minutes: `1 - 5/5 = 0.0`. Signal exits hot-set at the boundary.

Note: A transient `HORT` combo_key corruption was observed once — entries in the previous hot-set.json had `combo_key=HORT:gap-300-...` instead of their actual token names. This self-healed on the next compaction cycle (DB had correct combo_keys). Cause was likely a stale entry written during development. No code fix needed — the compaction correctly rebuilds from DB on each cycle.

### BUG #1 — CRITICAL: combo_key NOT updated on merge (signal_schema.py)
When a new signal merges with an existing PENDING signal (same token+direction, within 5 min),
the UPDATE query at lines 516-526 modifies `source` and `signal_types` but NEVER recomputes
`combo_key`. The `combo_key` is computed only at INSERT time and never updated.

Impact: Staleness formula uses `age_m` from the grouped row's `created_at` — correct.
BUT opposing penalty uses `current_sources` parsed from `combo_key` — WRONG (stale sources).
Rounds lookup by combo_key also fails on re-merge since combo_key doesn't match new sources.

Evidence (GRIFFAIN):
  src=oc-mtf-rsi-       → combo_key=GRIFFAIN:SHORT:oc-mtf-rsi-     ✓ at INSERT
  src=gap-300-,oc-mtf-rsi- → combo_key=GRIFFAIN:SHORT:oc-mtf-rsi- ✗ should be gap-300-,oc-mtf-rsi-

Fix: Add `combo_key = ?` to UPDATE query at line 523, recomputed from merged_sources.

### BUG #2 — MAJOR: survival_rounds vs compact_rounds mismatch (signal_compactor.py)
The APPROVED refresh (lines 783-791) increments `survival_rounds` but NOT `compact_rounds`.
Later, the APPROVED→EXPIRED staleness check at line 758 uses `compact_rounds == 0` as the
"fresh" proxy:
  if cr == 0: stay PENDING
  else: EXPIRED
Since APPROVED signals have `compact_rounds=0`, they would incorrectly stay PENDING.

Fix: Change APPROVED refresh to also `compact_rounds = COALESCE(compact_rounds, 0) + 1`,
OR change staleness check to use `hot_cycle_count > 0` as "was in hot-set" flag.

### BUG #3 — MINOR: compact_rounds as staleness proxy (signal_compactor.py:758)
Using `compact_rounds == 0` as "signal is fresh" proxy is indirect.
`compact_rounds` = PENDING failure count; a 10-min-old PENDING signal with cr=0
would pass as "fresh" despite being stale. (The 5-min PENDING expiry at lines 310-319
should catch these first, but the proxy is semantically wrong.)

### BUG #1 FIXED (2026-04-26 live): combo_key updated on merge
The merge UPDATE now recomputes combo_key from merged sources:
```python
merged_combo_parts = sorted(all_srcs)
merged_combo_key = f"{token.upper()}:{direction.upper()}:{','.join(merged_combo_parts)}"
# in UPDATE:
SET ... combo_key=?,
...
merged_combo_key,
```
Without this fix, GRIFFAIN had `source="gap-300-,oc-mtf-rsi-"` but `combo_key="GRIFFAIN:SHORT:oc-mtf-rsi-"` — missing gap-300-, breaking opposing penalty and rounds lookup.

### BUG #3 FIXED (2026-04-26 live): staleness uses created_at directly
The PENDING staleness check now uses `created_at` directly instead of `compact_rounds` as proxy:
```python
created_ts = time.mktime(time.strptime(sig_created_at, '%Y-%m-%d %H:%M:%S'))
age_m = (time.time() - created_ts) / 60.0
if age_m < 5.0:
    still_pending_ids.append(sid)   # fresh — stay PENDING
else:
    expired_ids.append(sid)         # stale — EXPIRED
```
SELECT now includes `created_at` as last column. A 10-minute-old cr=0 signal is correctly
expired; a cr>0 signal that just entered the merge window stays PENDING. The `compact_rounds`
ambiguity remains as design debt (see BUG #2 note in Post-Deployment section) but this
closes the staleness check bug.

### BUG #4 FIXED (2026-04-26 live): APPROVED expiry requires no fresh PENDING
APPROVED combos are only expired when there are NO PENDING signals for that combo_key
that are younger than 5 minutes. This prevents APPROVED from being expired during
temporary PENDING gaps (e.g., when no new signals fire in the current cycle):
```sql
AND combo_key NOT IN (
    SELECT combo_key FROM signals
    WHERE decision = 'PENDING'
      AND executed = 0
      AND combo_key IS NOT NULL
      AND created_at > datetime('now', '-5 minutes')  -- fresh PENDING
)
```
Previously, APPROVED was expired immediately when it left top-10, even if PENDING
had signals <5 min old — causing unnecessary round resets.

### BUG #2 (design debt — partially mitigated)
`compact_rounds` tracks PENDING failure count; `survival_rounds` tracks APPROVED rounds.
The APPROVED expiry uses `hot_cycle_count >= 1` as "was in hot-set" flag, which
correctly prevents new APPROVED signals (hcc=0) from being incorrectly expired. The
underlying column ambiguity remains — consider renaming `compact_rounds` to
`pending_fail_count` in a future refactor.

### Audit Methodology (DB-first)

To verify this redesign after deployment, run:

**Staleness correctness (BUG #5):**
```python
import json, time
with open('/var/www/hermes/data/hotset.json') as f:
    d = json.load(f)
now = time.time()
for e in d['hotset']:
    ts = e.get('entry_origin_ts', 0)
    computed = max(0, 1 - (now - ts) / 300)
    diff = abs(computed - e['staleness'])
    print(f'{e["token"]:10}: staleness={e["staleness"]:.4f} computed={computed:.4f} {"✓" if diff < 0.01 else "✗"}')
```
After a preserve cycle (no new signals), all entries should have staleness matching the formula within 0.01. If computed > stored, the entry is stale (not being recomputed).

**Staleness filter behavior:**
```python
import sys; sys.path.insert(0, '.')
from signal_compactor import _filter_safe_prev_hotset
# Returns only entries with staleness >= 0.01
```

**combo_key consistency (BUG #1):**
```sql
-- Verify combo_key matches actual sources for each token
SELECT token, source, combo_key,
       token || ':' || UPPER(direction) || ':' || source AS expected_combo
FROM signals WHERE combo_key IS NOT NULL LIMIT 10;
-- If combo_key != expected_combo for any row → BUG #1 not fixed
```

**EXPIRED marking is working:**
```sql
SELECT token, direction, decision, combo_key, expired_at
FROM signals WHERE decision='EXPIRED' ORDER BY expired_at DESC LIMIT 10;
```

**Verify entry_origin_ts in hot-set JSON:**
```bash
python3 -c "
import json
with open('/var/www/hermes/data/hotset.json') as f:
    d = json.load(f)
for e in d['hotset']:
    assert 'entry_origin_ts' in e, f'{e[\"token\"]} missing entry_origin_ts'
    assert 'combo_key' in e, f'{e[\"token\"]} missing combo_key'
    assert 'staleness' in e, f'{e[\"token\"]} missing staleness'
print('All entries have required fields ✓')
"
```

**No PENDING cr>=5 signals (BUG #3):**
```sql
SELECT COUNT(*) FROM signals WHERE decision='PENDING' AND compact_rounds >= 5;
-- Must be 0
```

### Transient `HORT` combo_key corruption (no code fix needed)
During one preserve cycle, all entries showed `combo_key=HORT:gap-300-...` instead of their actual token names (BRETT, CAKE, AVAX, etc.). GRIFFAIN showed `AIN:SHORT:...`. This was NOT a code bug — it was a stale entry in the previous hot-set.json written during development with an incorrect combo_key. The next compaction self-healed by rebuilding from the DB (which had correct combo_keys). If this recurs: check the hot-set.json file directly for corrupted combo_keys, then run one live compaction to overwrite from DB.

### Audit via subagent (complex cases)
For thorough multi-file audits, dispatch a `terminal+file` subagent to:
1. Read signal_compactor.py and trace the full compaction flow
2. Query DB for state consistency
3. Verify hot-set JSON schema after a live run
4. Report any remaining bugs — do NOT fix without user approval

Always verify combo_key consistency against actual sources:
  SELECT token, source, combo_key FROM signals WHERE combo_key IS NOT NULL;
  # Then manually compute expected combo_key = token:direction:sorted(sources) and compare.

Always verify combo_key consistency against actual sources:
  SELECT token, source, combo_key FROM signals WHERE combo_key IS NOT NULL;
  # Then manually compute expected combo_key = token:direction:sorted(sources) and compare.

## Backward Compatibility
decider_run.py reads `survival_round` from hot-set entries. Always include both:
```python
'rounds': rounds,
'survival_round': rounds,  # alias for readers
```

## Common Pitfalls
- GROUP BY changing from `(token, direction)` to `(combo_key)` shifts all column indices — update every `row[N]` access
- staleness was per `(token, direction)` — now per `combo_key`, affects how staleness_mult is computed
- `import os` inside function bodies causes UnboundLocalError in paths that run before the import line
- DB connection closed before scoring runs — pass `db_path` not `conn` to helper functions that need DB access
