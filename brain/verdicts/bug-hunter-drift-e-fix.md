# Bug Hunter: DRIFT-E Fix Verification (fce5c6bb)

## Verdict: SAFE — ship it, with one hardening follow-up (MEDIUM, not blocking)

The fix is correct on every live-data path. Verified against the real PostgreSQL
schema (jsonb), real metadata rows, real imports, and a 12-case empirical
edge-case harness with fake connections. One unguarded `float()` conversion can
crash and leak a connection, but it is unreachable with today's data (0 bad rows
in 5,680) and all 3 callers wrap the call in try/except.

---

## Issues Found

### MEDIUM — Unguarded `float(_meta_rsi)` crashes AND leaks the metadata connection
Both files, `feature_recorder.py:167-169` and `hl-sync-guardian.py:2551-2553`:

```python
if _meta_rsi is not None:
    intel['rsi_14'] = float(_meta_rsi)   # <-- OUTSIDE the try/except
```

If `_signal_metadata.rsi_14` is ever a non-numeric string, list, or dict,
`float()` raises `ValueError`/`TypeError` **outside** the try block that wraps
the metadata read. Empirically confirmed with the fake-connection harness:

- `rsi_14='N/A'` → `ValueError: could not convert string to float: 'N/A'`,
  connections opened=1, closed=**0 → LEAKED=1**, UPDATE never runs.
- `rsi_14=[1,2]` → `TypeError`, same leak.

Consequences: the exception propagates to the caller (all 3 call sites catch it,
so the trade itself is unaffected and `brain.py` prints "Feature record failed"),
but the psycopg2 connection opened at line 154/2538 is never closed. In the
long-running `hl-sync-guardian` daemon, repeated leaks accumulate toward
"too many clients". Also: the entire feature UPDATE is skipped, so
`features_recorded` stays FALSE for that trade.

Mitigating facts (why it's not blocking):
- Live data check over all 5,680 trades: `rsi_14` is present in 1,799 rows and
  is a JSON **number** in **all 1,799** (string=0, json-null=0). Zero live triggers.
- All callers wrap in try/except: `brain.py:754-757`, guardian `:882-884`, `:1727-1729`.

Suggested fix: move the conversion inside the try, or wrap the whole
read+convert block in `try/finally: conn.close()`, e.g.:

```python
if _meta_rsi is not None:
    try:
        intel['rsi_14'] = float(_meta_rsi)
    except (TypeError, ValueError):
        pass  # fall back to computed RSI
```

### LOW — Silent `except Exception: pass` on the metadata read (observability)
`feature_recorder.py:164-165` / `hl-sync-guardian.py:2548-2549` swallow every
metadata-read error with zero logging. If the `_signal_metadata` column were
renamed or the SELECT started failing, every trade would silently revert to the
old drift values and nothing in the logs would show it — exactly the failure
mode DRIFT-E was meant to kill. Recommend logging the fallback at least once
per occurrence.

### LOW — Fix is a no-op for orphan-recovery trades (coverage gap, not a regression)
`hl-sync-guardian.py:855` orphan-trade INSERT does not write `_signal_metadata`
(row defaults to NULL), so `add_orphan_trade` → `record_entry_features(:884)`
always falls back to the old drift computation. Same for any trade not created
through `brain.py`'s signal path. Behavior is unchanged (safe), but entry_rsi_14
still drifts for orphan trades.

### LOW — Flip-path call site has a pre-existing wrong-row bug, but it is DEAD CODE
`hl-sync-guardian.py:1728` calls `record_entry_features(int(trade_id), ...)` where
`trade_id` still refers to the OLD closed trade — the flip INSERT at `:1692` has
no `RETURNING id` and `trade_id` is never reassigned. However,
`_check_and_execute_flip` has been **DEFUNCT since 2026-04-17** (flip moved to
position_manager CASCADE_FLIP); its only caller is commented out at `:1848-1849`.
Live flip trades are created by `brain.py` (rows show `flip_variant='signal-flip'`,
`flipped_from_trade` stored as int(bool)=0/1 — the source trade id is actually
lost, a separate data-quality nit) and get features via the correct
`brain.py` → `feature_recorder` path. Not introduced by fce5c6bb. Latent bug if
the function is ever re-enabled.

### INFO — Behavior change (arguably an improvement)
Empty `intel` + valid metadata RSI now records the trade (rsi only, other feature
columns NULL) where the pre-fix code returned False. Harness case J confirms.
More `entry_rsi_14` values captured — consistent with the fix's intent.

### INFO — Historical rows are NOT backfilled
The fix is forward-only. PURR #16026 still stores `entry_rsi_14 = 100.00` while
its metadata says `68.71` (verified live). Any analysis over pre-fix history is
still affected. A one-time backfill
(`UPDATE trades SET entry_rsi_14 = (_signal_metadata->>'rsi_14')::numeric
WHERE _signal_metadata ? 'rsi_14'`) would cure the ~1,799 rows that carry the key.
Recent coverage is healthy: 194 of the last 200 trades have `rsi_14` in metadata.

---

## Connection Leak Check

Same structure in both files; traced with a fake-connection harness that counts
open/close per path (12 cases):

| Path | Connections | Closed? | Leak? |
|------|------------|---------|-------|
| Normal (metadata rsi present) | 1 opened, reused for UPDATE | once (success branch) | No |
| Metadata NULL / `{}` / no key / rsi null | 1, reused for UPDATE | once | No |
| Invalid JSON string | 1, reused for UPDATE | once | No |
| Trade row missing (fetchone → None) | 1, UPDATE hits 0 rows, commit | once | No |
| Metadata read exception (SELECT fails) | 1 reused; real psycopg2 raises `InFailedSqlTransaction` on the UPDATE → caught → rollback+close | once | No |
| Empty intel (early return) | 1, explicit close in early-return block (`:172-174` / `:2556-2558`) | once | No |
| First `_get_db_connection()` returns None | second call only attempted when the first never opened a conn; None → return False | n/a | No |
| **`float()` crash (non-numeric rsi)** | **1 opened** | **NEVER** | **YES — see MEDIUM issue** |

- **No double-close anywhere.** Every tested path closed the connection 0 or 1
  times; the rollback/close in the exception handler is itself guarded by
  try/except, so a close-after-close cannot raise.
- **Read happens BEFORE the UPDATE** (`:154-165` vs `:184`) — ordering correct.
  (The UPDATE doesn't touch `_signal_metadata`, so ordering is belt-and-suspenders.)
- `get_token_intel` opens/closes its own connection internally (success and
  exception paths both close) — no leak feeding into the fix.
- `if conn:` truthiness is safe — psycopg2 connections define no `__bool__`/`__len__`,
  so a non-None connection is always truthy.
- `import json as _json` inside the function: harmless. `_json` avoids shadowing
  the module-level `json` in hl-sync-guardian (`:22`,`:198`); feature_recorder has
  no module-level json, so the local import is required. Negligible overhead.
- **jsonb vs string:** the column is `jsonb` (verified via information_schema),
  so psycopg2 returns a Python **dict** — the `isinstance(str)` branch never
  fires in production; the else branch handles the dict correctly. Live test on
  trade #16046 (APT): returned `dict`, `rsi_14 = 71.43`, parsed to float fine.

---

## Edge Cases Tested

Empirical harness (fake psycopg2 connection tracking open/close/execute) plus
live DB queries. Each is the actual result, not reasoning:

1. **Normal, `rsi_14=68.71`** → override applied, SELECT+UPDATE on same conn, closed once. ✔
2. **`_signal_metadata` NULL** → fallback to computed RSI, no crash. ✔
3. **Metadata `{}`** (brain.py's default when a signal has no metadata) → fallback. ✔
4. **Metadata has no `rsi_14` key** (31.7% of history / 6 of last 200 trades) → `.get()` returns None → fallback. ✔
5. **`rsi_14` is JSON null** → `.get()` returns None → `is not None` check → fallback. ✔
6. **`rsi_14='N/A'` (string)** → **unhandled ValueError + connection leak** (MEDIUM issue). 0 live rows like this.
7. **`rsi_14=[1,2]` (list)** → **unhandled TypeError + connection leak** (MEDIUM issue). 0 live rows like this.
8. **Invalid JSON string** (TEXT-column hypothetical; impossible for jsonb — Postgres validates) → exception swallowed → fallback, conn reused and closed. ✔
9. **Metadata is a JSON array/number** (`.get` on non-dict) → AttributeError swallowed → fallback. ✔ (covered by the same except path as #8)
10. **Trade row doesn't exist** → fetchone None → skip → UPDATE affects 0 rows → commit → close, no leak. Both live callers call AFTER the INSERT...RETURNING id + commit, so trade_id is always valid (brain.py ~744-756; guardian orphan path :869-884). ✔
11. **Empty intel + metadata RSI** → now records rsi-only row (behavior change, improvement). ✔
12. **SELECT fails (e.g., column renamed)** → conn reused for UPDATE; in real psycopg2 the aborted transaction fails the UPDATE → caught → rollback+close → returns False, error printed. No leak, but see LOW observability issue: silent in the metadata-read stage.

Runtime checks run:
- `python3 -c "from feature_recorder import record_entry_features"` → **import OK**
- `ast.parse(hl-sync-guardian.py)` → **syntax OK**

## Callers Verified

- **`brain.py:754-757`** — `try: from feature_recorder import record_entry_features; record_entry_features(int(trade_id), token.upper()) except → print`. Runs after INSERT with `RETURNING id` + commit; trade_id valid; caller-side try/except contains any float() crash. Works. ✔
- **`hl-sync-guardian.py:882-884`** (orphan recovery) — wrapped in try/except with `log(..., 'WARN')`; called after `RETURNING id` + commit. Works (falls back to old RSI since orphans have NULL metadata). ✔
- **`hl-sync-guardian.py:1727-1729`** (flip) — dead code (see LOW issue). Would work mechanically (wrapped in try/except) but targets the wrong trade_id. ✔/⚠
- **Guardian helpers:** local `get_db_connection()` at `:760` returns None on failure (compatible with the fix's None checks); local `get_token_intel` at `:2400`; `log` imported from `hermes_log` at `:205` with signature `log(msg, level=None)` — the new one-arg `log(...)` call is consistent with the file's usage. The guardian does NOT import feature_recorder, so no name mixing. feature_recorder correctly uses its own `_get_db_connection` (`:14`). ✔

---

## Recommendation

**SHIP.** The fix does exactly what it claims on every reachable path, is
correct against the real jsonb schema, verified working on live rows, and leaks
nothing on any normal/fallback path. Follow-up (non-blocking, do soon):

1. Guard the `float(_meta_rsi)` conversion (MEDIUM issue above) in both files —
   4-line change, removes the only crash+leak path.
2. Log (don't swallow) metadata-read failures — silent reversion to drift values
   is the exact bug class this fix exists to kill.
3. Optional: one-time backfill of historical `entry_rsi_14` from metadata
   (~1,799 rows carry `rsi_14`), or accept that pre-fix history stays dirty and
   exclude it from RSI-keyed analysis.
