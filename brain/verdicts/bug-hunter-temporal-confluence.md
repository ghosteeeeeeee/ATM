# Bug Hunter: Temporal Confluence Shadow Mode (d2a19277)

**Verified:** 2026-10-13 03:39–04:05 UTC by bug_hunter (diff read, code read, runtime executed, live data queried)

## Verdict: ISSUES FOUND

The feature is **100% inert as shipped** (dead code — collects zero shadow data) and carries a **latent compactor-killer NameError** that fires the moment the dead code is fixed. Shadow safety itself is intact: zero behavior change confirmed. Do not treat this as "collecting data" — it is not.

## Issues Found

### 1. HIGH — Temporal confluence branch is unreachable (dead code)
The shadow/enforce block was placed inside the **final `else`** of the confluence chain (signal_compactor.py:3345-3366), but every single-source signal is already swallowed by the earlier `elif` at **line 3320**:

```python
elif unique_signal_types == 1 and source_parts:      # line 3320 — matches ALL single-source signals
    ...
    if _part_bypass:
        pass_gate = True; gate_msg = ...
    # (no else — on miss, gate_msg stays '' and the chain ENDS; no fall-through)
...
else:                                                  # line 3338 — temporal branch lives HERE
    ...
    if TEMPORAL_CONFLUENCE_ENABLED and unique_signal_types == 1:   # line 3355 — impossible here
```

`unique_signal_types` is computed **from** `source_parts` (line 2648: `len(set(...) for p in source_parts)`), so `unique_signal_types == 1` implies `source_parts` is non-empty ⇒ the line-3320 `elif` is **always taken** for single-source signals ⇒ the final `else` only runs when `unique == 0`, where the inner `unique == 1` guard fails. **The temporal block can never execute.**

**Live evidence:**
- 2,544 `unique_types=1 -> BLOCK` events in pipeline.log; message distribution: 1,630 **empty** (part-bypass miss) + 914 NEUTRAL-relax (`single-type not in standalone bypass (regime=…)`). **Zero** `need 2+` messages — the final else has never executed once.
- Shadow DB (`brain/temporal_confluence_shadow.db`): **0 events**; `--report` → `blocks=0`. Zero `TEMPORAL-CONFLUENCE-SHADOW` lines in pipeline.log.
- The spec (plans/temporal-confluence-spec.md:36) explicitly says: *"Add a new bypass branch **before** the final `else` block"* — the implementation did the opposite.
- The spec's motivating signal `return_exhaustion-short` is among the blocked-with-empty-message sources (146 blocks) — exactly the case this feature was built for, and it is not covered.

**Fix:** relocate the temporal block into an `else:` of the part-bypass branch (i.e., when `unique_signal_types == 1` and no part matched) or as an `elif unique_signal_types == 1:` before line 3320.

### 2. HIGH (latent) — NameError: `TEMPORAL_CONFLUENCE_WINDOW_MIN` not imported
Lines **3359** (shadow log) and **3362** (enforce `gate_msg`) reference `TEMPORAL_CONFLUENCE_WINDOW_MIN`, but the enclosing `try` (3352-3354) imports only `ENABLED, SHADOW, MIN_FIRES`, and the name is not a module global (verified: `hasattr(signal_compactor, 'TEMPORAL_CONFLUENCE_WINDOW_MIN') → False`; no star import; only other reference is a function-local import at line 760). Reproduced the exact `NameError` in isolation.

`except ImportError` does **not** catch `NameError` → it propagates out of `run_compaction` → `__main__` catches it, prints `FATAL ERROR`, **exit 1**. The compactor runs every 1 min via `hermes-signal-compactor.timer`; while a token+direction holds ≥3 fires in the 30-min window (common — e.g., BTC SHORT already at 3 fires; APT/CFX/CHIP hit 5–6 fires/ha in the last 72h), **every cycle crashes → ALL signal compaction halts for up to ~30 min**, affecting every token, not just the triggering one.

Currently latent only because issue 1 keeps the branch unreachable. **Fixing issue 1 without issue 2 turns a dead feature into a recurring pipeline outage.**

**Fix:** add `TEMPORAL_CONFLUENCE_WINDOW_MIN` to the import at 3352-3354.

### 3. MEDIUM — `gate_msg` fallback in the wrong scope
`if not pass_gate and gate_msg == ''` (3365-3366) sits inside the final `else` and is therefore dead too. The real source of the **1,630 empty `BLOCKED — ` messages** is the part-bypass miss at line 3320-3330 (pre-existing since ≥2026-10-11, not introduced by this commit) — this commit apparently attempted to address it but the fix landed in an unreachable scope. Block-census lines remain reasonless.

### 4. MEDIUM — NEUTRAL-regime gap
When 4h regime == `NEUTRAL` (`_neutral_relax`, line 2683), single-source signals are decided at line 3301 and never reach any temporal evaluation. A large share of blocked repetition volume (914 of 2,544 observed blocks) routes through this branch — the feature does not cover repetition that occurs in NEUTRAL regimes.

### 5. LOW — systemd units not stored in repo
`/etc/systemd/system/hermes-tc-shadow.{service,timer}` exist, are enabled and active (timer: `OnCalendar=*:00/30`, `Persistent=true`; first service run 2026-10-13 04:00 UTC). But sibling units (`hermes-gate-shadow`, `hermes-t5-shadow`) are copied into `config/` for durability — **no `hermes-tc-shadow` copies exist in the repo** → lost on host rebuild. Unit files are also mode 600 (works since systemd runs as root; 644 is convention).

### 6. LOW — forward-return horizon doc mismatch
`close_events()` docstring: *"close events >24h old … with would-be outcome"* — the 24h is only the wait-before-close; the measured counterfactual is a **30-minute forward return** (`entry_ts + 1800`). Math verified correct (see below), but confirm 30-min is the intended decision metric (sibling `gate_shadow.py` closes with actual trade outcomes 24h later).

### 7. LOW — dedup inflates episode counts
Compactor runs every 1 min and would re-log the shadow line each cycle; the 10-min bucket dedup still yields ~3 events per 30-min episode. The `n>=15` enforce-decision threshold can be reached with ~5 real episodes. Consider episode-level aggregation before the enforce flip.

### 8. LOW — rotation/first-run edges
- Rotation reset only triggers when `offset > file_size`; rotation to a new file smaller than the old one but larger than the offset silently skips the head of the new file.
- First run (offset=0) parses only the last 20 MB of pipeline.log (file is currently 51 MB) — fine today since the feature shipped today; would drop older events later.
- `--since-hours 6` cutoff also applies to incremental reads: if the timer is down >6h, shadow lines older than 6h at catch-up are dropped.

### 9. NIT
- `close_events()` opens a **new** CANDLES_DB connection per event (each properly closed in `finally` — no leak, just inefficient; open once outside the loop).
- `SHADOW_DB`/`PIPELINE_LOG`/`OFFSET_FILE` derived via `os.path.dirname(HERMES_DATA)` string surgery instead of `paths.py` constants — works, fragile.

## Shadow Mode Verification
- **Constants** (`hermes_constants.py:3851-3854`): `TEMPORAL_CONFLUENCE_ENABLED=True`, `TEMPORAL_CONFLUENCE_SHADOW=True`, `WINDOW_MIN=30`, `MIN_FIRES=3`. Import test passed. (Constants were committed in the batched config commit `2e0e5f08`, not in d2a19277 — commit touched only `signal_compactor.py` + new tracker; the file list in the task brief overstates the commit's contents.)
- **Shadow branch** (3358-3359) only calls `log()` — it does **not** set `pass_gate`. ✅ semantics correct.
- **Enforce branch** (3360-3362) **does** set `pass_gate = True` + sets `gate_msg`. ✅ semantics correct.
- **As shipped, neither branch can execute** (issue 1), and both would crash if reached (issue 2). Actual behavior change: **none**. Verified: zero shadow lines in log, tracker DB 0 events, compactor journal clean (all `Deactivated successfully` through 03:51, no FATAL).
- **Flipping `SHADOW=False` today changes nothing** (dead code). Do NOT fix issue 1 without simultaneously fixing issue 2 — that flip-by-fix is what arms the crash.

## SQL Query Check
- Uses `decision IN ('PENDING', 'EXPIRED')` — ✅ matches spec (spec line 57: `executed=0` is explicitly wrong; expired signals have `executed=1`). SKIPPED is excluded by design.
- **Parameterized** throughout: `token = ? AND direction = ?` and `datetime('now', ?)`. The only f-string is the window modifier `f'-{TEMPORAL_CONFLUENCE_WINDOW_MIN} minutes'` — a controlled int constant, not user input. Safe.
- **Tested against the real function** (monkeypatched `RUNTIME_DB` to a temp DB): PENDING/EXPIRED counted (3/3), EXECUTED/SKIPPED excluded, direction mismatch → excluded, 31-min-old fire excluded, lowercase→upper normalization harmless (signals table stores uppercase, e.g. `KPEPE`).

## Connection Leak Check (all paths traced)
| Path | Connect | Close | Error path | Result |
|---|---|---|---|---|
| `_temporal_confluence_count` | `sqlite3.connect(RUNTIME_DB, timeout=3)` inside try | inner `finally: cur.close(); conn.close()` | outer `except Exception → return 0` | **No leak.** Tested: locked DB (EXCLUSIVE from 2nd conn) → returns 0 in exactly 3.0s; missing DB → returns 0 |
| tracker `record/close/report` | `get_db()` | `finally: conn.close()` in each | propagates (systemd captures) | No leak |
| tracker `close_events` per-event candles conn | `connect(CANDLES_DB, timeout=5)` **before** inner try | inner `finally: cconn.close()` | connect failure → outer `except` (inner finally not yet armed — no NameError) | No leak |
- Fail-open semantics: DB error → 0 → "no bypass" → signal stays blocked. Fails toward the **safe** direction. Comment "fail-open" is accurate.

## Edge Cases
| Case | Result |
|---|---|
| Signals DB locked/unavailable | Helper returns 0 after 3s timeout (tested) — shadow: no log; enforce: no bypass. Safe direction ✅ |
| `pipeline.log` missing | `record()` logs `pipeline.log missing` and returns 0 (tested) ✅ |
| Log rotation | Detected (`offset > size`), offset reset, tail re-parsed, dedup absorbs duplicates (tested: +1 event, no dup) ✅; partial blind spot = issue 8 |
| Same-event re-parse (idempotency) | Re-run with same offset → +0 events (tested) ✅ |
| Shadow flag flipped mid-cycle | Constants imported at first gate evaluation per process; running cycle keeps old value; next 1-min timer run picks up new value. No restart needed ✅ |
| `gate_msg` fallback when temporal doesn't fire | Correct logic but dead scope (issue 3) ⚠️ |
| Forward returns | Verified against raw candles: LONG +0.625% / SHORT −0.625% match hand-computed values exactly; no-candle token → closed with `would_trade=NULL` ✅ |
| Timezone | pipeline.log stamps are server-local = UTC (verified vs systemd); tracker appends `+00:00` — consistent. Python 3.12.3 `fromisoformat` handles space separator (verified) ✅ |
| DB schema on first run | `events` + `meta` created via `CREATE TABLE IF NOT EXISTS` (verified live) ✅ |
| `--report` aggregation | Correct on synthetic data (wr/pnl/per-direction all match hand-check) ✅ |

## Recommendation
**FIX FIRST — this is not "shipped and collecting."** Three fixes, in this order, as one commit:
1. `signal_compactor.py:3352-3354` — add `TEMPORAL_CONFLUENCE_WINDOW_MIN` to the import (kills the latent crash).
2. Relocate the temporal block out of the final `else` into the part-bypass miss path (an `else:` under the line-3320 branch) so it actually evaluates single-source signals (spec: "before the final else").
3. Move the `gate_msg` fallback so it also covers the part-bypass miss (fixes the 1,630 empty `BLOCKED — ` census lines — pre-existing, but this commit's stated neighbor).

Then: run one compactor cycle manually, confirm a `[TEMPORAL-CONFLUENCE-SHADOW]` line appears for a token with 3+ fires (BTC SHORT qualifies right now), and confirm `--record` picks it up. Keep `SHADOW=True`; ship enforce flip only after the tracker shows n≥15 real episodes (not deduped events — see issue 7). Also copy the two systemd units into `config/` (mode 644).

**Do not flip `SHADOW=False` until fixes 1+2 are in — that sequence arms a recurring full-compactor outage.**
