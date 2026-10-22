# Bug Hunter Verification: Shadow Signals Runner Pipeline Integration

## Summary
Commit `0747cdd3` wires the step in correctly (flag exists, step runs every 10 min with a 180s timeout, observed live rc=0 in 6.9s) and the `add_signal()` monkey-patch does prevent writes to the live signals DB — but the runner still **writes live cooldowns (proven in production)**, **half of the registry entries silently never execute**, and **every signal it records is in a date format `shadow_trader.close_events()` can never parse**, so the stats T asked for will not materialize.

## Verdict: FAIL

## Shadow-Mode Flag Verification
- `SHADOW_SIGNALS_RUNNER_ENABLED = True` exists — `scripts/hermes_constants.py:3240`. ✅
- Flag checked first thing in `main()` — `scripts/shadow_signals_runner.py:240-247`. ✅
- Flag **False** ⇒ immediate `return 0`, no registry load, no detector executed — tested in-process (`hc.SHADOW_SIGNALS_RUNNER_ENABLED=False` → `rc=0`, log line `SHADOW_SIGNALS_RUNNER_ENABLED is False — exiting`). ✅
- Flag is referenced only by `hermes_constants.py` + `shadow_signals_runner.py` (repo-wide grep) ⇒ no live trading code reads it. ✅
- Flag never modifies `hermes_constants.py`: `strace` of a full run shows `hermes_constants.py` is never even opened (only the `.pyc` is read) and `git diff scripts/hermes_constants.py` is empty after all test runs. ✅
- ⚠️ `except ImportError: pass` = **fail-open** (see LOW-7): renaming the constant silently disables the switch while the runner keeps running.
- ⚠️ `SHADOW_SIGNALS_RUNNER_STAGES = ('A','C')` (`hermes_constants.py:3241`) is **dead config** — never read anywhere (see MEDIUM-6).

## Pipeline Integration Verification
- In `STEPS_EVERY_10M` — `scripts/run_pipeline.py:43`. ✅
- Timeout 180s — `scripts/run_pipeline.py:56`; enforced via `proc.communicate(timeout=…)` + `killpg` on expiry (`run_pipeline.py:75-89`). ✅
- Script path correct — `run()` builds `{SCRIPTS}/shadow_signals_runner.py` (`run_pipeline.py:63-66`, `SCRIPTS` = dir of `run_pipeline.py` = `/root/.hermes/scripts`). ✅
- **Observed live in `logs/pipeline.log`:** `2026-10-22 00:20:26 Running shadow_signals_runner...` → `done in 6.9s (rc=0)` → `DONE: 1 signals recorded, 6 skipped, 9 errors`. Step is genuinely executing from the pipeline. ✅
- Runtime margin: 6.9s / 7.2s / 8.2s measured vs 180s budget; peak RSS 83.7 MB (`/usr/bin/time -v`), fresh process per cycle ⇒ no memory leak. ✅

## No Live-Trading Impact Verification
- **No signal rows written to the live signals DB** ✅ — (a) `capture_add_signal` replaces `signal_schema.add_signal` and module-level references before `run()` is called; (b) grep of all 8 mapped detectors found **zero** `INSERT INTO` / `UPDATE` / `DELETE FROM` statements (they write only through `add_signal`); (c) synthetic detector test: `add_signal()` fired once, live `signals` row count stayed `0 → 0`, shadow row recorded; (d) `signals` count/`MAX(id)` unchanged across a full 8s run (`8867 / 1684357` before and after).
- **Flags not changed permanently** ✅ — overrides are in-process `setattr` only; restored after each signal and die with the process. Restorations verified for `signal_schema.add_signal`, module-level `mod.add_signal` (mtf_macd) and the `*_ENABLED` value (tests T1/T2: restored `True`).
- **No protected flags touched** ✅ — `git diff scripts/hermes_constants.py` empty; `LIVE_TRADING_ENABLED` untouched; `SHADOW_BYPASS_SIGNALS`/`SHADOW_BYPASS_ENABLED` are consumed only by `shadow_trader.py`, `shadow_signals_runner.py`, `hermes_constants.py` (no live gate consumer).
- **Cannot trigger a live trade** ✅ — captured signals go only to `brain/shadow_trades.db` with `decision='SHADOW_BYPASS'`; only 3 files read that DB (`shadow_trader.py` = paper trading, no exchange/order code; `shadow_mode_analysis.py` = read-only; the runner itself). Nothing copies shadow rows into `signals_hermes_runtime.db`, and `signal_compactor`/deciders never see them.
- ❌ **BUT the runner DOES modify live trading state — cooldowns.** See HIGH-1. The code comment "ZERO impact on live trading" (`shadow_signals_runner.py:16`, `hermes_constants.py:3236`) is false as written.

## Findings

### HIGH — Shadow run writes live cooldowns (suppressed live signals + defeated loss backoff)
- **Location**: `scripts/shadow_signals_runner.py:176-190` (capture returns a truthy fake id) → detector code e.g. `scripts/signals/rs.py:1125-1126`; writer `scripts/signal_schema.py:3978-4026`
- **Issue**: detectors call `set_cooldown(token, direction, hours=…)` in the `if sid:` branch. The capture function returns a truthy `shadow_…` id, so shadow fires take that branch and `set_cooldown` writes the **shared live cooldown stores**: `data/loss_cooldowns.json` and PostgreSQL `signal_cooldowns`.
- **Evidence (production pipeline run, not my test)**: run at `00:20:30` recorded `LDO / SHORT / rs-s-broken` (a path whose live flag `RS_BROKEN_SHORT_ENABLED=False`) and created `LDO:SHORT` in `loss_cooldowns.json` plus a `signal_cooldowns` row expiring **2026-10-22 10:20:30 UTC = run time + RS_COOLDOWN_HOURS(10)**. My runs produced the same for `GOAT:SHORT` (10:23:03) and `CAKE:SHORT` (10:30:36). 3/3 shadow rows have a matching cooldown stamped exactly run_time+10h.
- **Secondary evidence**: synthetic detector calling `set_cooldown('HERMESBUGTEST','LONG')` wrote the live store while its `add_signal` write was blocked (0 live rows).
- **Impact**:
  1. `get_cooldown()` is called by **100 signal modules** — `LDO`, `GOAT`, `GOAT`/`CAKE` SHORT entries are now blocked for every generator until ~10:20–10:30 UTC today, and the pipeline recreates these blocks every time a shadow signal fires (≈3 in 11 minutes of observation).
  2. Cooldowns created from **live-disabled paths** (`rs-s-broken`) would never exist in live trading → pure shadow-created suppression.
  3. `signal_schema.py:4002` overwrites the entry's `reason` with `'signal'` → I proved a synthetic active guardian cooldown (`reason:'loss'`) becomes `active: False` after `set_cooldown()`. So a shadow fire on a token in guardian **loss backoff silently cancels that guard** and re-allows live entries early.
- **Fix**: in `run_shadow_signal`, also monkey-patch `signal_schema.set_cooldown` (and `clear_cooldown`, `record_cooldown_start`) to no-ops and restore them in `finally`; keep the capture returning a truthy id so detector-side counting still works. Add a regression test asserting that a full shadow run leaves `loss_cooldowns.json` and `signal_cooldowns` byte-identical.

### HIGH — 6 of 12 registry entries never actually execute (flag override doesn't reach the gate)
- **Location**: `scripts/shadow_signals_runner.py:154-170` (override only `setattr(mod, flag, True)` when `hasattr(mod, flag)`) + `ENABLED_FLAG_MAP` at `:67-80`
- **Issue** (proven by building the reachability table with `hasattr()`/`inspect` on each mapped module):
  | key | mapped flag | `hasattr(mod, flag)` | real gate | result |
  |---|---|---|---|---|
  | bb-bounce-v3-long | `BB_BOUNCE_V3_LONG_ENABLED` | True | `:501` module attr | **WORKS** |
  | hmacd_mtf-+ | `HMACD_MTF_PLUS_ENABLED` | True | `:357` module attr | **WORKS** |
  | rs-broken-short / -resistance-long | `RS_BROKEN_*_ENABLED` | True | `:840/:924` module attr (masters True) | **WORKS** |
  | bb-squeeze- | `BOLLINGER_SQUEEZE_MINUS_ENABLED` | **False** | `bollinger_squeeze.py:183` reads `hc.…` dynamically | **no-op** |
  | volume-breakout-long | `VOLUME_BREAKOUT_LONG_ENABLED` | **False** — flag **does not exist anywhere in the repo** | `volume_breakout.py:232-235` reads `hc.VOLUME_BREAKOUT_PLUS/MINUS` at call time | **no-op (typo)** |
  | doji-bottom-long | `DOJI_BOTTOM_LONG_ENABLED` | **False** — flag **does not exist anywhere in the repo** | `doji_bottom.py:178` `DOJI_BOTTOM_ENABLED` (=False, untouched) | **no-op (typo)** |
  | open-skies+ | `OPEN_SKIES_PLUS_ENABLED` | True | `open_skies.py:286` also requires master `OPEN_SKIES_ENABLED` (=False, untouched) | **no-op (master gate)** |
  | squeeze-cross+ / - | `SQUEEZE_CROSS_PLUS/MINUS_ENABLED` | True | `squeeze_cross.py:243` `if not SQUEEZE_CROSS_ENABLED` (=False, untouched) | **no-op (master gate)** |
- **Impact**: half the target set produces zero shadow data, and the log reports `0 signals (detector ran but found nothing)` — **indistinguishable from a genuine no-detection**, so the missing stats would never be noticed. T's "give us the stats we need" is only half-delivered.
- **Fix**: (1) correct the two non-existent flag names; (2) override the module's master flag too (`OPEN_SKIES_ENABLED`, `SQUEEZE_CROSS_ENABLED`, `DOJI_BOTTOM_ENABLED`, `VOLUME_BREAKOUT_PLUS/MINUS`); (3) set the value on the `hermes_constants` module object as well (covers `hc.`-style reads), restoring both in `finally`; (4) add a self-check to `--dry-run` that asserts each mapped gate actually evaluates `True` after override.

### HIGH — Every runner-created row can never be closed ⇒ zero exit stats
- **Location**: `scripts/shadow_signals_runner.py:178/186` writes `created_at = datetime.now(utc).isoformat()` (`2026-10-22T00:20:30.111040+00:00`) vs `scripts/shadow_trader.py:1178` (also `:1531`, `:1664`, `:1884`, `:1968`) `datetime.strptime(created, '%Y-%m-%d %H:%M:%S')` inside `except (ValueError, TypeError): continue`
- **Issue**: verified directly — `strptime('2026-10-22T00:20:30.111040+00:00', '%Y-%m-%d %H:%M:%S')` raises `ValueError: time data … does not match format`. The row is skipped and stays `closed=0` forever.
- **Impact**: the signals the runner captures get **no exit-engine simulation, no WR, no PnL** — exactly the stats requested. Rows accumulate as permanently-pending (`closed=0`); once their date string is older than the cutoff they are returned by the `LIMIT 1000` pending query (`shadow_trader.py:1164-1171`) every run forever and will crowd out legitimate rows. Currently `shadow_*` rows: 3, all `closed=0`.
- **Fix**: write `created_at` as `datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')` (what `shadow_trader.record()` uses), and backfill the 3 existing rows. Then confirm `close_events()` actually closes one.

### MEDIUM — Monkey-patch not restored on error path (no try/finally)
- **Location**: `scripts/shadow_signals_runner.py:154-236` — restore at `:215-222` is only reached on the happy path; the outer `except Exception` at `:234` skips it.
- **Issue / proof**: (a) detector raising `SystemExit` → propagates out, `signal_schema.add_signal` still patched; (b) forced `record_to_shadow` failure (`SHADOW_DB` → bad path) → `ERROR: unable to open database file` → returns 0 but **`add_signal` still patched** (test T4/T7).
- **Impact**: process-local but real — every subsequent detector in the same run gets fake ids and its shadow rows are silently dropped (stats loss); `SystemExit` from a detector aborts the whole run (pipeline logs FAILED) with the flag left `True` in-process. Note the live cooldown side effect already happened *before* the failure in case (b).
- **Fix**: `try: … finally:` restoring `signal_schema.add_signal`, `mod.add_signal`, and the `*_ENABLED` flag — for every early-exit path.

### MEDIUM — Mis-attributed / duplicated shadow rows (whole module runs per registry key)
- **Location**: `scripts/shadow_signals_runner.py:267-293` + `SIGNAL_MODULE_MAP:60-61` (both `rs-broken-short` and `rs-broken-resistance-long` → `signals.rs`)
- **Issue**: each registry key runs the **entire** module, so the runner captures *all* signals the module emits, not the disabled path's. Proven: my `rs-broken-short` entry recorded `GOAT / source rs-r31` — `rs-r31` comes from `rs.py:962` (`f'{RS_SOURCE_PREFIX}-r{touch_count}'`), the **live-enabled** `RS_MINUS` path — yet it was tagged with the broken-short reason ("DISABLED 2026-07-21 — broken support SHORT = 26.5% WR"). The module is also scanned twice per cycle (~4s wasted).
- **Impact**: shadow stats mix live-eligible signals with shadow-only signals, attribute them to the wrong registry reason, and duplicate what `shadow_trader.record()` already snapshots from the live DB (double counting in reports).
- **Fix**: run each module once, then filter captured signals by expected `source`/`direction` for each registry key (e.g. only `rs-s-broken` / `rs-r-broken` count for the Stage C rs keys).

### MEDIUM — `SHADOW_SIGNALS_RUNNER_STAGES` is dead configuration
- **Location**: `scripts/hermes_constants.py:3241`
- **Issue**: `('A','C')` is never read anywhere (repo-wide grep: definition only). Stage filtering is hard-coded as `if stage == 'B': skip` at `shadow_signals_runner.py:277`.
- **Impact**: T flipping it to `('A',)` changes nothing — a switch that silently does nothing is worse than no switch, and it is in the DO-NOT-EDIT file so it reads as authoritative.
- **Fix**: consume it in `main()` (`if stage not in SHADOW_SIGNALS_RUNNER_STAGES: continue`) or delete the constant.

### LOW — Fail-open flag check
- **Location**: `scripts/shadow_signals_runner.py:246-247` (`except ImportError: pass`)
- **Issue**: if `SHADOW_SIGNALS_RUNNER_ENABLED` is renamed/removed, the check silently falls through and the runner always executes. (Note: a *missing file* is not the risk — `paths.py:112` imports `hermes_constants` first and would crash at import; this is specifically the missing-attribute case.)
- **Impact**: safety switch can be silently lost during a refactor.
- **Fix**: fail closed (`return 0`) with a loud log when the flag cannot be resolved.

### LOW — `errors` counter counts normal zero-detection runs
- **Location**: `scripts/shadow_signals_runner.py:295-296` (`if n == 0: total_errors += 1`)
- **Impact**: every run reports `10 errors` for benign "found nothing" outcomes, which buries real import/exception failures → alert fatigue. Observed on all runs: `DONE: 1 signals recorded, 6 skipped, 9 errors`.
- **Fix**: have `run_shadow_signal` return a status enum (RECORDED / NO_SIGNAL / SKIPPED / IMPORT_ERROR / RUN_ERROR) and report them separately.

### LOW — Shadow process runs DDL against the live signals DB
- **Location**: `scripts/signals/mtf_macd.py:308` → `signal_schema.init_db()` → `signal_schema.py:170-176` (`CREATE TABLE IF NOT EXISTS signals …`) on `signals_hermes_runtime.db`; `strace` shows the runtime DB opened `O_RDWR` during a shadow run.
- **Impact**: no signal rows are written (proven above), and the DDL is idempotent and identical to what the live `signals_runner` runs — but the shadow process does hold the live DB read-write.
- **Fix (defence in depth)**: open live DBs read-only in the shadow context / skip `init_db()`.

### INFO — Concurrency
- No lock of its own; `run_pipeline.py` holds `/tmp/hermes-pipeline.lock`, but a manual invocation can overlap the pipeline step (I ran two instances in parallel deliberately): both completed `rc=0`, `PRAGMA integrity_check = ok`, no `database is locked`. Dedup in `record_to_shadow` keys on `shadow_id` = second-resolution timestamp + token, so the *same* setup detected by two overlapping runs 1s apart records once, 10s apart records twice → possible shadow-stat inflation. The pipeline step itself runs synchronously inside the cycle, so pipeline-vs-pipeline overlap is already excluded.

## Verified Working
- Flag exists, defaults `True`, is checked first in `main()`, exits `rc=0` with no side effects when `False` (tested in-process).
- Flag is read by no live trading code; `hermes_constants.py` byte-unchanged after all tests (git diff empty, strace shows no write open of the file).
- Step present in `STEPS_EVERY_10M` with 180s timeout; script path resolves; **observed executing from the pipeline at 00:20:26, rc=0 in 6.9s** (well inside timeout).
- `--dry-run` works (0.03s, lists 10 mapped + 2 skipped entries).
- Full run works: 7-8s, exit 0, records signals to `brain/shadow_trades.db` with `shadow_bypass` context (production rows: `LDO/SHORT/rs-s-broken`, `GOAT/SHORT/rs-r31`, `CAKE/SHORT/rs-s-broken`).
- `add_signal()` patching effective: synthetic detector produced **0 rows in the live signals DB** while 1 shadow row was recorded; live `signals` table unchanged across a full run; no `INSERT/UPDATE/DELETE` in any mapped detector.
- Patch + flag restoration on the happy path and on import failure (tests T1, T2, T3).
- Missing/broken detector module is handled: logged `Could not import …`, run continues, `rc=0`.
- No live-trade path: shadow rows live only in `brain/shadow_trades.db`; `shadow_trader.py` is paper-only (no exchange/order code); `signal_compactor`/deciders read only the runtime DB.
- Memory: peak RSS 83.7 MB over a full run; fresh process each cycle ⇒ no cross-cycle leak.
- Integrity after concurrent runs: `PRAGMA integrity_check = ok`.

## Recommendations
1. **Patch `set_cooldown` (and friends) to no-op inside the shadow run and restore in `finally`** — highest priority; today every 10 minutes the pipeline can suppress live signals and cancel guardian loss backoffs. Afterwards, re-run a full cycle and assert both cooldown stores are byte-identical before/after.
2. **Fix the flag-override reachability** (2 typo flags, 4 master gates, `hc.`-style reads) and add a `--dry-run` self-check that proves each gate evaluates `True` — otherwise half the registry silently yields nothing.
3. **Fix `created_at` format** to `%Y-%m-%d %H:%M:%S` and backfill the 3 existing rows, or the recorded signals produce no stats at all.
4. **Wrap the patch/restore in `try/finally`** so a detector crash cannot strand `signal_schema.add_signal`.
5. **Filter captured signals per registry key** (source/direction) so shadow stats aren't polluted with live-eligible signals; run each module once.
6. Either consume `SHADOW_SIGNALS_RUNNER_STAGES` or delete it; make the flag check fail closed; split "no signal" from "error" in the summary.
7. Decide what to do about the three cooldowns already written by production runs (`LDO:SHORT` → 10:20:30 UTC, `GOAT:SHORT` → 10:23:03 UTC, `CAKE:SHORT` → 10:30:36 UTC). I left them in place as evidence (they self-expire and the pipeline would recreate them); clearing them is a one-line `clear_cooldown` + `DELETE FROM signal_cooldowns` per token if T wants the block lifted now.
8. Sideways find (pre-existing, not from this commit): `shadow_trader.py` parses `created_at` in five places (`:1178`, `:1531`, `:1664`, `:1884`, `:1968`) with a single hard-coded format — worth centralising so a second writer can't break it again.

## Test Log (what was run)
- `git show 0747cdd3` — full diff read.
- `python3 scripts/shadow_signals_runner.py --dry-run` (0.03s).
- `python3 scripts/shadow_signals_runner.py` ×4 (8.2s / 7.2s / 7.2s×2 concurrent), plus 1 pipeline-native run at 00:20:26.
- Flag-off harness, ImportError harness, restoration/leak harness (T1–T7, synthetic detectors in `/tmp/shadowtest`, all test artifacts cleaned up: shadow rows deleted, `HERMESBUGTEST*` cooldowns removed from JSON + PostgreSQL).
- `/usr/bin/time -v` (RSS 83,672 KB, exit 0), `strace -f -e trace=openat` (no writes to `hermes_constants.py`, live DB opened read-write but no row writes), `PRAGMA integrity_check`, before/after snapshots of `signals` (count/MAX id), `loss_cooldowns.json`, PostgreSQL `signal_cooldowns`, `shadow_trades`.
