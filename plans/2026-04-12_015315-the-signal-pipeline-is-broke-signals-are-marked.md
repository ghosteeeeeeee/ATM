# Signal Pipeline Repair Plan

**Date:** 2026-04-12  
**Status:** Planning only — do not execute  
**Last Session Context:** Investigated WAIT signals (SCR/SHORT hmacd-,hzscore) stuck in DB, hotset.json perpetually empty. Two fixes already applied to STEP 1 and STEP 6 queries in `ai_decider.py`. This plan covers remaining pipeline issues.

---

## 1. Goal

Fix the Hermes signal pipeline so that:
- Signals can actually be **executed** (not just marked EXECUTED at WAIT decision time)
- The **hot-set** is consistently populated and survives compaction cycles
- Signal lifecycle is **correct**: PENDING → AI review → WAIT/APPROVED → hotset → executed

---

## 2. Root Causes Identified (Session 2026-04-12 01:20)

### Bug A: `ai_decider` not defined (pre-existing fix)
- `signal_schema.py` referenced `ai_decider` module that didn't exist
- Was causing recurring `[ERROR] [ai-decider] get_pending_signals DB read error` every 10 min
- **Status:** Already fixed in prior session

### Bug B: RSI-confluence 1.5x boost (pre-existing fix)
- RSI confluence has 0% win rate but was boosted 1.5x
- **Status:** Already fixed (weight → 0.8 in prior session, later blacklisted entirely)

### Bug C: rsi-confluence blocking hot-set (pre-existing fix)
- 132 rsi-confluence signals blacklisted via `SIGNAL_SOURCE_BLACKLIST`
- **Status:** Already fixed this session (signals purged, hotset clean)

### Bug D: WAIT signals never fed to LLM for ranking (fixed)
- `mark_signal_processed()` sets `executed=1` for WAIT decisions
- `compact_signals_to_hotset()` STEP 1 query only read `PENDING/APPROVED, executed=0`
- WAIT signals were **invisible** to the LLM compaction engine
- hotset.json was empty for 30+ minutes because no "recent" PENDING signals existed
- **Status:** Fixed this session — STEP 1 and STEP 6 queries updated to include `WAIT + review_count>=1`

### Bug E: Signal lifecycle confusion — `executed=1` on WAIT
- When `decider_run.py` calls `mark_signal_processed('WAIT', ...)`, it sets `executed=1`
- `executed=1` was supposed to mean "already traded", but signals with `decision=WAIT` haven't traded
- The word "executed" conflates two concepts: (a) traded, (b) processed/decided
- This is a **design smell** — the DB has no clean way to distinguish "WAIT pending execution" from "WAIT — do not execute"
- **Status:** Not yet fixed — needs design decision

---

## 3. Current Signal State (as of 01:20 UTC)

```
signals_hermes_runtime.db:
  WAIT signals: 3 (all SCR/SHORT hmacd-,hzscore, review_count=1, executed=1)
  PENDING/APPROVED: 0 (no recent signals generated)
  EXECUTED: many (historical)

signals.json (API output):
  0 rsi-confluence signals (purged)
  113 hmacd signals
  3 SCR/SHORT WAIT signals visible

hotset.json:
  0 signals (empty since ~01:00 UTC)
  Last successful compaction: 00:52:42 (cycle=347)
```

---

## 4. Proposed Fix Plan

### Step 1: Clarify signal `executed` flag semantics

**Problem:** `executed=1` is set for BOTH traded signals AND WAIT signals. This makes it impossible to query "signals that have been traded" vs "signals that were processed."

**Option A (recommended):** Rename/repurpose `executed` column intent:
- `executed=1` → signal has been traded (position opened)
- `executed=0` → signal is available for trading consideration
- WAIT signals should keep `executed=0` — WAIT means "pause before executing" not "already executed"
- Add a new column `decision_processed` for "has been reviewed by AI"

**Option B:** Add a separate `trade_executed` boolean column

**Impact:**
- File: `signal_schema.py` — `mark_signal_processed()` logic
- File: `ai_decider.py` — all queries filtering on `executed`
- DB migration needed to fix historical WAIT signals that have `executed=1` incorrectly

**Action:** Confirm with T which approach before proceeding.

---

### Step 2: Fix `mark_signal_processed()` for WAIT signals

**File:** `/root/.hermes/scripts/signal_schema.py` line ~929-936

**Current behavior:**
```python
elif increment_rc:  # WAIT/SKIPPED
    SET executed=1, review_count+1
```

**Fix:** For WAIT, set `executed=0` so signal remains eligible for hotset:
```python
elif decision == 'WAIT':
    SET executed=0, review_count+1   # signal reviewed but not traded — stays in play
elif decision == 'SKIPPED':
    SET executed=1, review_count+1   # SKIPPED = dead signal
```

**Also fix:** SKIPPED should probably set `executed=1` to exclude from future consideration (already correct).

---

### Step 3: Fix the hot-set compaction query to use `decision` not `executed`

**File:** `/root/.hermes/scripts/ai_decider.py` line ~1116-1140 (STEP 1) and ~1462-1480 (STEP 6)

After Step 2 fix, the query becomes simpler:

```python
# STEP 1 — LLM input: signals the AI has reviewed and not yet approved for execution
c.execute("""
    SELECT token, direction, signal_type, confidence, source, created_at,
           compact_rounds, survival_score, z_score_tier, z_score
    FROM signals
    WHERE decision IN ('PENDING', 'WAIT')
      AND executed = 0
      AND created_at > datetime('now', '-30 minutes')
      AND token NOT LIKE '@%'
    ORDER BY confidence DESC
    LIMIT 100
""")
```

Key insight: with `executed=0` for WAIT signals, the filter `decision IN ('PENDING', 'WAIT') AND executed = 0` correctly captures:
- PENDING signals: not yet reviewed
- WAIT signals: reviewed but deferred (executed=0, not traded)

The `review_count >= 1` check moves to STEP 6 for the DB update, not STEP 1.

---

### Step 4: Fix hot-set write safety filters (unknown functions)

**File:** `/root/.hermes/scripts/ai_decider.py` line ~1576-1582

`is_solana_only()` and `is_delisted()` are called but imports suggest they come from `tokens` and `hyperliquid_exchange` respectively. Need to verify:

```bash
python3 -c "from tokens import is_solana_only; from hyperliquid_exchange import is_delisted"
```

If these modules/functions don't exist, the hot-set write silently crashes (exception swallowed) and hotset.json stays empty.

**Fix:** Add stub definitions or fix imports:
```python
# Fallback stubs in ai_decider.py if imports fail
try:
    from tokens import is_solana_only
except ImportError:
    def is_solana_only(tkn): return False

try:
    from hyperliquid_exchange import is_delisted
except ImportError:
    def is_delisted(tkn): return False
```

---

### Step 5: Add hot-set write error recovery

**File:** `/root/.hermes/scripts/ai_decider.py` line ~1603-1610

Currently if hot-set write fails (exception), there's no recovery. The `compact_signals_to_hotset` function silently continues and the hot-set is lost.

**Fix:** After writing hotset.json, read it back and verify:
```python
with FileLock('hotset_json'):
    with open('/var/www/hermes/data/hotset.json', 'w') as _f:
        json.dump({...}, _f, indent=2)

# Verify write succeeded
with open('/var/www/hermes/data/hotset.json') as _f:
    verify = json.load(_f)
    assert len(verify.get('hotset', [])) > 0, "hotset.json write failed — empty after write"
```

---

### Step 6: Prevent hot-set starvation (no-signals deadlock)

**Problem:** If no new signals are generated (signal_gen doesn't fire), hot-set empties and trading stops.

**Current behavior:**
- `signal_gen` fires 2x/hour (not every pipeline run)
- If no PENDING signals in 30 min, compaction skips and hotset.json goes empty
- decider_run.py finds empty hot-set and outputs "no signals survived compaction"

**Fix options:**
1. **Keep WAIT signals alive** in hot-set until they're explicitly APPROVED/REJECTED (fixes current issue)
2. **Extend 30-min window** to 2 hours for PENDING signals
3. **Preserve previous hot-set** if no new signals qualify (survival of previously APPROVED signals)

**Recommended:** Combine #1 (fix WAIT semantics) with #3 — on compaction skip, preserve existing hot-set rather than wiping it:
```python
# In compact_signals_to_hotset():
if not hotset_final:
    print("  [LLM-compaction] No new signals — keeping previous hot-set")
    # Don't overwrite hotset.json with empty
    return
```

---

## 5. Files Likely to Change

| File | Change |
|------|--------|
| `/root/.hermes/scripts/signal_schema.py` | `mark_signal_processed()` — WAIT sets `executed=0` not `1` |
| `/root/.hermes/scripts/ai_decider.py` | STEP 1 + STEP 6 queries simplified after Step 2; add safety stubs for `is_solana_only`/`is_delisted`; hot-set write verification; no-signal deadlock fix |
| `/root/.hermes/scripts/hermes-trades-api.py` | Potentially update `get_signals_from_db()` if WAIT semantics change |

---

## 6. DB Migration

After Step 2 fix, existing WAIT signals with `executed=1` need correction:
```sql
UPDATE signals
SET executed = 0
WHERE decision = 'WAIT' AND executed = 1;
```

---

## 7. Testing / Validation Plan

1. **DB query test** — verify WAIT signals show `executed=0` after migration
2. **Step 1 query test** — verify WAIT signals appear in LLM input query
3. **Compaction dry-run** — simulate full compaction cycle and verify hotset.json populated
4. **Pipeline smoke test** — run `decider_run.py` and verify hot-set written
5. **Trade lifecycle test** — generate signal → WAIT → verify stays in hotset → APPROVE → verify `executed` updates

```bash
# Quick validation commands
python3 -c "import sqlite3; c=sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db').cursor(); c.execute('SELECT COUNT(*) FROM signals WHERE decision=\"WAIT\" AND executed=0'); print('WAIT executed=0:', c.fetchone()[0])"
python3 -c "import json; print(json.load(open('/var/www/hermes/data/hotset.json')).get('hotset', []))"
```

---

## 8. Open Questions / Risks

1. **T decision needed:** `executed` flag semantic change — Option A or Option B (Section 4)?
2. **Historical signals:** Do existing EXECUTED signals have correct `executed` values? May need audit.
3. **SKIPPED vs WAIT:** SKIPPED signals set `executed=1` — should they also be kept in hot-set pool?
4. **Signal expiry:** When should a WAIT signal expire? Currently no explicit expiry — it survives until manually overridden.
5. **Hot-set size cap:** Top 20 signals — if WAIT signals flood in, they may push out PENDING signals.

---

## 9. Recommended Execution Order

1. **Step 4** (safety filters) — low risk, high value, immediate
2. **Step 2** (WAIT executed=0 fix) — core fix
3. **DB migration** — correct existing WAIT signals
4. **Step 3** (simplify queries after Step 2)
5. **Step 5** (write verification) — reliability
6. **Step 6** (no-signal deadlock) — graceful degradation
7. **Step 1** (design decision + migration) — only if needed

---

*Plan saved: `.hermes/plans/2026-04-12_015315-the-signal-pipeline-is-broke-signals-are-marked.md`*
