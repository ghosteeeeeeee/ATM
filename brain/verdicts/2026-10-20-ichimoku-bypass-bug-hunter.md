# Bug Hunter Verification: ichimoku LONG bypass (a1b80950)

## Summary
The bypass itself works — `'ichimoku'` in `STANDALONE_BYPASS_SIGNALS` is live at every confluence-gate stage and both new compactor blocks are correctly scoped. But the pre-registered kill switch the CEO conditioned approval on is **inert**: the auto-revert flips `ICHIMOKU_LONG_BYPASS_ENABLED`, which **nothing in the trading path reads** — the actual gate is tuple membership, which the revert never touches. The kill alert is also silently dropped (Decimal not JSON-serializable).

## Verdict: FAIL

The loosening is live and tradeable, but the auto-revert safety mechanism does not disable it. "Approved LONG-only with kill switch" — the kill switch does not kill. Must-fix before the 40% WR criterion can be considered enforced.

## Findings

### [SEVERITY: CRITICAL] — Auto-revert is a no-op: kill flag gates nothing, bypass stays active after "revert"
- **Location**: `scripts/vacation_guardrail.py:303-319` (revert) vs `scripts/signal_compactor.py:3399,3448` (actual gate)
- **Issue**: The compactor enforces the bypass via `'ichimoku' in STANDALONE_BYPASS_SIGNALS` (imported at module top, line 26, plus 10 other consumption sites). `ICHIMOKU_LONG_BYPASS_ENABLED` is read ONLY inside `vacation_guardrail.py` itself (line 278 — to decide whether to check). Repo-wide grep confirms zero trading-path readers. The revert sets the flag False but never removes `'ichimoku'` from the tuple.
- **Verified by simulation** (copied live `hermes_constants.py`, ran the exact replace, imported the result): after revert, `ICHIMOKU_LONG_BYPASS_ENABLED = False` **and** `'ichimoku' in STANDALONE_BYPASS_SIGNALS = True`. The compactor gate stays fully active. Additionally the reverted file logs "Auto-reverted" while the system keeps trading loosened ichimoku — operator believes bypass is off.
- **Secondary consequence**: after a revert, if the CEO manually re-enables the bypass (re-adds tuple membership) but leaves the flag line as AUTO-REVERTED False, the guardrail returns early at line 278 forever — **no kill monitoring for the re-enabled bypass at all**.
- **Impact**: On a live trading system, the single safety condition the CEO attached to approving the loosening provides zero protection. A bad WR cohort keeps trading indefinitely.
- **Fix**: In `check_ichimoku_bypass_kill()`, revert the actual gate: remove `'ichimoku',` from `STANDALONE_BYPASS_SIGNALS` (and/or add an explicit direction-aware check in the compactor gate: `bare_source == 'ichimoku' and direction == 'LONG' and ICHIMOKU_LONG_BYPASS_ENABLED`). The flag must be consulted at the gate, or the gate must be the tuple. Also assert the replace actually changed content before logging success.

### [SEVERITY: HIGH] — Kill alert silently dropped: Decimal not JSON-serializable in write_alert
- **Location**: `scripts/vacation_guardrail.py:317-319` → `write_alert` (line 241 `except Exception: pass`)
- **Issue**: `wr` and `pnl` come straight from `ROUND(...)` → psycopg2 `Decimal`. `json.dump` raises `TypeError: Object of type Decimal is not JSON serializable` (verified live). `write_alert`'s blanket except swallows it — the WARNING never lands in `vacation_alerts.json`, the CEO/T-facing channel. `check_guardrails()` correctly wraps every metric in `float()`; the new function doesn't.
- **Impact**: When the kill fires, the structured alert vanishes. "No alert" is read as "all good" — the one event this feature exists to surface is invisible except as one log line.
- **Fix**: `wr = float(row[3] or 0)`, `pnl = float(row[2] or 0)` before use (also fixes the alert payload).

### [SEVERITY: HIGH] — Bypass is direction-agnostic: ichimoku SHORT loosened everywhere except LONG_BIAS
- **Location**: `scripts/hermes_constants.py:3089` + `scripts/signal_compactor.py:2943,3366-3371,3399`
- **Issue**: CEO verdict approved **LONG-only** loosening. But tuple membership grants the standalone bypass regardless of direction, and `ICHIMOKU-SHORT-BLOCK` only fires when `_regime_4h == 'LONG_BIAS'`. Single-source ichimoku SHORT therefore bypasses the confluence gate in NORMAL, SHORT_BIAS, and NEUTRAL regimes (NEUTRAL additionally via the SHORT-NEUTRAL-BYPASS at line 2943 and NEUTRAL-relax at 3366 — both consult the tuple). The kill criteria monitor LONG WR only, so a bleeding SHORT cohort in those regimes can never trigger a revert.
- **Impact**: Un-approved scope expansion on the SHORT side of a live trading system, with no monitoring attached.
- **Fix**: Make the gate direction-aware (see CRITICAL fix), or add `ICHIMOKU_SHORT_BYPASS_BLOCK`-style protection, and extend kill criteria to SHORT if SHORT loosening is actually intended.

### [SEVERITY: MEDIUM] — Kill query measures the wrong cohort: confluence + pre-bypass trades
- **Location**: `scripts/vacation_guardrail.py:284-293`
- **Issue**: `signal LIKE 'ichimoku%' AND direction='LONG'` counts ALL closed ichimoku LONG trades in 24h — including 2+ source confluence trades (the pre-existing legal path; live PG shows `ichimoku+,rs_s` LONG rows) and trades opened **before** the bypass shipped (close_time window ≠ open cohort). The pre-registered criterion targets the *loosened* cohort. Verified live: the query runs clean (0 rows in 24h right now), and historical ichimoku LONG rows are all confluence — so the first evaluation windows will be dominated by non-loosened trades. A strong confluence cohort masks a bad loosened cohort (no revert when required) and vice versa.
- **Fix**: Isolate single-source trades, e.g. `AND signal IN ('ichimoku','ichimoku+','ichimoku-')` (stored single-source value is bare `'ichimoku'`, confirmed in PG), or filter `signal_metadata` for source count == 1; anchor on open_time >= bypass-activation timestamp.

### [SEVERITY: MEDIUM] — Shadow log fires pre-gate and lists reasons that aren't real gates
- **Location**: `scripts/signal_compactor.py:3236-3248` (shadow) vs gate at 3359-3481
- **Issue**: Two accuracy problems polluting the counterfactual data the CEO will use to judge the bypass:
  1. **Ordering**: the shadow block runs *before* the confluence gate (3359+) and before the VOL-GATE-BYPASS check (3473-3479). It logs "bypass active" for ichimoku LONGs that subsequently fail the gate or get vol-gate-blocked — trades that never fired counted as loosened activity.
  2. **Reasons are hypothetical**: there is no vol HIGH/EXTREME block for ichimoku anywhere in the compactor (verified — per-signal vol blocks are pump-chain/accel-300/volume-breakout/coil-spring only; `volatility_gate_v2` has zero ichimoku overrides), and the NEUTRAL gates (2956-3054) already ran upstream — a trade reaching the shadow log in NEUTRAL *survived* those gates via explicit exceptions. "would have been blocked by: 4h=NEUTRAL" is false for a trade the real NEUTRAL gate already allowed.
- **Impact**: Kill-criteria support data is misleading in both directions (false "active" entries, fabricated blocker reasons).
- **Fix**: Move the shadow block to after `if not pass_gate: continue` (post line 3462), and label the reasons as policy-criteria flags, not "would have been blocked".

### [SEVERITY: MEDIUM] — Non-atomic auto-revert write races the every-minute compactor import
- **Location**: `scripts/vacation_guardrail.py:308-315`
- **Issue**: `open(path,'w')` truncates `hermes_constants.py` then writes. `hermes-signal-compactor.timer` runs **every minute** (`*:0/1`) and imports the file at module top (line 26 — hard import, SyntaxError not ImportError). An import landing in the truncate→write window crashes that compactor run.
- **Impact**: ~ms window, 30-min guardrail cadence — low probability, but the failure mode is a dead compaction cycle with a SyntaxError, on a file AGENTS.md marks CEO-protected. (Verified: the replacement itself is precise — target string occurs exactly once — and the reverted file compiles.)
- **Fix**: Write temp file + `os.replace()` (atomic on same filesystem).

### [SEVERITY: LOW] — PG connection not closed on exception (no try/finally)
- **Location**: `scripts/vacation_guardrail.py:282-296`
- **Issue**: `conn`/`cur` are closed only on the success path. An exception in `execute`/`fetchone` skips both (the outer except only logs). CPython refcounting closes it at function exit in practice, but that's GC-dependent, and it violates the house convention (AGENTS.md: close in `finally`); the sibling `check_guardrails()` does it correctly with try/finally.
- **Fix**: Wrap in try/finally like `check_guardrails()`.

### [SEVERITY: LOW] — Regime fallback conflates "NEUTRAL" with "no data"
- **Location**: `scripts/signal_compactor.py:423-442` (get_regime_4h fallback) → 3228, 3243
- **Issue**: `get_regime_4h` returns `'NEUTRAL'` on missing row / NULL / any error (verified: `momentum_cache.regime_4h` contains NULLs). `_regime_4h` is never None (good — no crash), but: (a) ichimoku SHORT is **not blocked** when regime data is absent (fail-open); (b) the shadow logs `4h=NEUTRAL` for tokens that simply have no regime data.
- **Impact**: Data-gap tokens silently exempt from the SHORT block; shadow data mislabeled.
- **Fix**: Distinguish 'UNKNOWN' (None) from 'NEUTRAL' in the fallback, or treat UNKNOWN as non-bypassable for the loosened directions.

### [SEVERITY: INFO] — Minor cleanups
- `scripts/vacation_guardrail.py:306` — `import re` is unused. Line 299 — `n_wins` computed, never used.
- Matching asymmetry: the new blocks use substring `'ichimoku' in bare_source` while the bypass uses exact tuple membership. Today both are consistent (`ichimoku_cloud.py` emits exactly `ichimoku+`/`ichimoku-`, bare → `'ichimoku'` — verified). A future rename (e.g. `ichimoku-cloud`) would block SHORTs while never bypassing LONGs.
- Side effect of tuple addition (by mechanism, but flag for CEO awareness): ichimoku now also (a) skips the chop detector (`signal_compactor.py:1415-1423`), (b) passes the SHORT-NEUTRAL block in 4h NEUTRAL (line 2943), (c) bypasses the hotset final guard/pending-approve/safety-filter gates (4908/4927/5015/5524/5699/6101). All direction-agnostic.
- The auto-revert edits the CEO-protected `hermes_constants.py` unattended — sanctioned by the verdict, but it's the first unattended writer of that file; worth an explicit note in AGENTS.md.
- `close_time` is `timestamp without time zone` compared to `NOW()` — same pattern as every other query in the file; consistent, not a new bug.

## Verified Working
- `python3 -m py_compile` passes on all three files.
- All 5 new constants import with correct types/values; `'ichimoku' in STANDALONE_BYPASS_SIGNALS` = True.
- Source matching: `ichimoku_cloud.py` emits `SOURCE_LONG='ichimoku+'`/`SOURCE_SHORT='ichimoku-'`; compactor `bare_source` derivation (line 2706) → `'ichimoku'` → exact tuple match. Bypass is wired at **all** 11 gate/confluence-check stages (2379, 3366-3371, 3399, 3448, 4908, 4927, 5015, 5524, 5699, 6101).
- Scope: `_regime_4h` (assigned line 2721), `_vol_regime` (2734), `token`, `direction`, `bare_source` (2706) all defined before the new blocks at 3225/3236 — no NameError risk.
- Regime variable choice correct: block uses `_regime_4h` (4h scanner), consistent with sibling regime blocks, not the noisy 1m `_regime`.
- Guardrail PG query executes clean against live brain DB (verified): returns (0, None, None, None) currently; `signal LIKE 'ichimoku%'` matches actual stored values (`ichimoku`, `ichimoku+,rs_s`, `ichimoku_,rs_r`); `direction='LONG'` case matches.
- `check_ichimoku_bypass_kill()` ran live in isolation: logged `⏳ Collecting data: 0/5 trades (WR 0%)`, returned cleanly, no side effects.
- `log(msg, 'ERROR')` and `write_alert(level, msg, dict)` signatures match usage; imports (`os`, `datetime`, `timezone`, `psycopg2`) all present.
- Revert string replace is precise (target occurs exactly once), idempotent after first revert, and the reverted file compiles (verified by simulation).
- Fail-safe behaviors: PG down → outer except logs ERROR, no bad revert happens (fail-open on kill criteria — acceptable); constants module import failure in compactor blocks → `except ImportError: pass` (fail-open, consistent with siblings).

## Recommendations
1. **Must-fix before this feature can be called safe**: wire the kill switch to the actual gate (CRITICAL finding #1) — the tuple is the switch; either remove `'ichimoku'` on revert or make the compactor gate direction-aware AND consult `ICHIMOKU_LONG_BYPASS_ENABLED` at the gate. Add a post-revert assertion that the bypass is truly dead (e.g., re-import + assert, or unit test).
2. Fix the Decimal alert drop (one-line `float()` casts) — the kill event must reach `vacation_alerts.json`.
3. Get an explicit CEO ruling on the SHORT-side scope: the shipped behavior loosens ichimoku SHORT in all non-LONG_BIAS regimes; the verdict said LONG-only. If unintended, tighten now.
4. Narrow the kill cohort to loosened (single-source, post-activation) trades so the 40% WR criterion measures what it was registered against.
5. Move shadow logging post-gate so counterfactual data counts only trades that actually fired.
6. Housekeeping: atomic file write (temp + os.replace), try/finally on the PG connection, drop unused `import re`/`n_wins`.
7. Restart note per AGENTS.md: after the fix ships, confirm the compactor timer picks up new code (fresh process per run — automatic — but verify the gate behavior in the next compaction log).
