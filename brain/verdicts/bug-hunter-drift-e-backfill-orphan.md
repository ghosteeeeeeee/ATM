# Bug Hunter: DRIFT-E Backfill + Orphan INSERT Verification

## Verdict: SAFE — code verified correct on live DB; one MEDIUM deployment gap (restart required)

Both changes are correct as written and as executed. Every claim below comes from
live PostgreSQL queries against dbname=brain and from reading the actual code/diff.
The only real issue: the guardian daemon was NOT restarted after the commit, so the
orphan-INSERT fix is committed but not yet live in the running process.

---

## Backfill Verification

### 1. NULL count — reduced, confirmed by arithmetic against a recorded baseline
- Current: `SELECT COUNT(*) FROM trades WHERE entry_rsi_14 IS NULL` → **1,315**
- Baseline: the earlier verdict `brain/verdicts/bug-hunter-drift-e-fix.md` recorded
  **1,799** trades carrying `rsi_14` in `_signal_metadata` pre-backfill.
- Claimed backfill: 657 mismatched + 1,140 NULL = 1,797 rows.
- Consistency check: 1,799 (rows with key) − 1,797 (claimed updated) = **2 rows
  already matching within 0.01** (skipped by the WHERE clause, as intended).
- NULL arithmetic: 1,315 now + 1,140 claimed NULL-backfilled = 2,455 before —
  consistent. Live check confirms **0 trades opened with NULL RSI after the
  backfill timestamp** (`open_time > 2026-10-10 23:09:13 UTC` → 0), so 1,315 is
  the genuine residual, not a fresh influx.
- Residual composition (why 1,315 remain): **0** of them have an `rsi_14` key.
  1,214 have empty `{}` metadata; 101 have metadata without `rsi_14` (keys like
  z_score/macd/momentum — older schema). These are legitimately un-backfillable.
  → **Backfill is complete. 0 rows remain that the UPDATE could fix.**

### 2. PURR #16026 spot check — PASS
```
 id   | token | entry_rsi_14
------+-------+--------------
 16026 | PURR |        68.71
```
Metadata `rsi_14` = 68.71. Prior verdict documented this row stored 100.00 before —
now exactly 68.71. Fixed.

### 3. Three random trades with metadata — PASS (exact matches)
```
  id   | entry_rsi_14 | meta_rsi |  diff
-------+--------------+----------+--------
 14439 |        82.61 |    82.61 | 0.0000
 15367 |        25.00 |     25.0 | 0.0000
 15657 |        50.00 |     50.0 | 0.0000
```
Table-wide re-check: rows with key + entry_rsi_14 both present and
differing by > 0.01 → **0 mismatches**.

### 4. No trades lost their entry_rsi_14 — PASS
- Rows with `rsi_14` in metadata but `entry_rsi_14 IS NULL` → **0**.
- Rows opened after the backfill with NULL → **0**.
- The UPDATE statement can only SET non-NULL values (guarded by
  `(t._signal_metadata->>'rsi_14')::float IS NOT NULL`); it is structurally
  incapable of creating NULLs. Populated count now: 4,365 of 5,680.
- All 1,799 `rsi_14` metadata values are JSON type **number** (verified via
  `jsonb_typeof`) → the `::float` cast could never raise mid-UPDATE. No partial
  failure possible.

### Backfill SQL review (cosmetic notes only)
- The self-join (`UPDATE trades ... FROM trades t WHERE trades.id = t.id`) is
  valid but redundant — equivalent to a single-table UPDATE. No correctness impact.
- `::float IS NOT NULL` is always true when the cast succeeds (a bad string would
  RAISE, not return NULL). Harmless, misleading guard. All data is numeric so it
  never mattered here.

---

## Orphan INSERT Verification (commit 6c5fd8e3)

### 1. Diff — matches the description exactly
`git show 6c5fd8e3` adds `_orphan_meta` (source/z_score/vol_regime) and the
`_signal_metadata` column with `%s::jsonb` to `add_orphan_trade`, plus the DRIFT-E
comment block. No other files touched.

### 2. `%s::jsonb` with psycopg2 — PASS (live-tested)
Ran the exact guardian INSERT through psycopg2 against the real brain DB with a
test token, inside a transaction that was **rolled back**:
- INSERT executed cleanly, `RETURNING id` gave #16047, and psycopg2 returned the
  stored `_signal_metadata` as a proper Python **dict** (`{'source': 'bughunter_test', ...}`).
- `%s::jsonb` is the standard psycopg2 cast pattern: param sent as text, cast
  server-side. Works.

### 3. Column — PASS
`\d trades` + information_schema: `_signal_metadata` exists, type **jsonb**,
default `'{}'::jsonb`.

### 4. `import json as _json` — PASS (no issues)
Function-local import; binds only the local name `_json`. Module-level `json`
exists (line 1 and line 198) and is NOT shadowed. The same local-import pattern
already exists at lines 2202 and 2543 in other functions — established file
convention. No conflict, negligible overhead.

### 5. `float(signal_z_score)` crash risk — PASS today, LOW defensive concern
Live-tested: `float('abc')` and `float('')` raise **ValueError**; `float(None)` is
guarded by the `is not None` conditional.
- **Reachability: none today.** The sole caller (`hl-sync-guardian.py:1509`) passes
  only 7 positional args, so `signal_z_score` defaults to `None` → conversion
  skipped. Verified repo-wide: no other callers exist.
- **If ever triggered:** the whole function body sits in `try/except Exception` →
  rollback + `add_orphan_trade FAILED` log + orphan trade NOT created. Visible
  degradation, not a silent corruption. Recommend wrapping the conversion in a
  defensive try/except as hardening (see Issues).

### 6. `WHERE NOT EXISTS` — PASS (live-tested both paths, rolled back)
- Test token with no open Hermes trade → INSERT proceeded, row returned. ✓
- Test token `ETH` (has an open Hermes trade) → **no row returned, INSERT skipped**. ✓
- The added column is in the INSERT column list only; the NOT EXISTS subquery is
  untouched and its semantics are unchanged.

### 7. Downstream behavior — PASS (by design)
Orphan metadata intentionally has **no** `rsi_14` key. Verified:
`record_entry_features` (hl-sync-guardian.py:2533) reads metadata, `_meta.get('rsi_14')`
→ `None` → falls back to the price_history computed RSI. Exactly what the code
comment promises. Current DB has **0** rows with `source='orphan_recovery'` — the
new path hasn't fired yet (see deployment gap below).

---

## Issues Found

### MEDIUM — Fix is committed but NOT loaded in the running guardian daemon
`hermes-hl-sync-guardian.service` main process started **2026-10-10 06:29:11 UTC**;
commit 6c5fd8e3 landed **23:09:13 UTC**. The service is a long-running daemon
(`Type=simple`, internal `sleep 60` loop) — the 5-minute timer re-triggers an
already-active unit, which is a no-op, so **no code reload has happened**. The
running process still has the pre-fix `add_orphan_trade` (no `_signal_metadata`).
Corroboration: 0 `orphan_recovery` metadata rows in the DB. No data harm meanwhile
(old behavior was safe), but the fix is inert.
**Action: `systemctl restart hermes-hl-sync-guardian.service`** (not performed by
this audit — flagged for the orchestrator since it touches the live sync daemon).

### LOW — Defensive hardening for `float(signal_z_score)`
Unreachable via the only current caller, and contained by the outer try/except if
it ever fires, but a non-numeric string would abort orphan recovery for that
trade. Suggested: `try: float(signal_z_score) except (TypeError, ValueError): None`.

### INFO — Backfill SQL style (no action needed)
Redundant self-join and an always-true `::float IS NOT NULL` guard. Cosmetic.

### INFO — Sideways find: prior verdict's MEDIUM/LOW issues are already fixed
The earlier `bug-hunter-drift-e-fix.md` flagged an unguarded `float(_meta_rsi)`
(possible crash + connection leak) and a silent metadata-read swallow. Both are
**now fixed** in `hl-sync-guardian.py:2550-2555` and `feature_recorder.py:171-176`
— the float conversion is inside try/except (TypeError/ValueError) and read
failures are logged. Verified in code today.

---

## Recommendation

**SHIP.** Both changes are correct, verified against live data and live psycopg2
execution: the backfill fully exhausted its target set (0 backfillable rows
remain, 0 mismatches, 0 data loss, PURR #16026 = 68.71), and the orphan INSERT is
syntactically and semantically sound with the NOT EXISTS guard intact.

Two follow-ups before considering this closed:
1. **Restart `hermes-hl-sync-guardian.service`** so the orphan-INSERT fix is
   actually live (MEDIUM).
2. Optional hardening: guard `float(signal_z_score)` (LOW).
