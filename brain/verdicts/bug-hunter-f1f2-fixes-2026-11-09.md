# bug_hunter verdict — F1/F2 fix set verification (re-verification of 9cac2eb1)

**Date:** 2026-11-09
**Change set under review:** `9cac2eb1` "bug-hunter live-fill FAIL fixes: F1 state lock (CRITICAL) + F2 dynamic_sl payload (HIGH) + F3/F4/F7/F10" (files: `scripts/trade_watchdog.py`, `scripts/auto_trader.py`, `scripts/run_pipeline.py`, `skills/shared/manual-trade-override/SKILL.md`)
**Predecessor verdict being re-tested:** `brain/verdicts/bug-hunter-live-fill-2026-11-09.md` (FAIL — F1 CRITICAL double-fire/corruption, F2 HIGH inert `dynamic_sl`, plus F3/F4/F7/F10)
**Harnesses (rerunnable):** `/tmp/bh_f1f2/{harness_A_race.py, worker_race.py, harness_A_kill.py, harness_A_nesting.py, harness_B_failclosed.py, harness_C_f2.py, harness_D_claim.py, harness_E_f3.py, harness_F_f4.py, harness_F_extra.py, harness_G_lockfail.py, harness_J_regress.py, poll_watchdog.sh}`
**Live-write discipline:** every harness redirected `HERMES_DATA_DIR` + `HERMES_DATA_OVERRIDE` (+ `_PENDING_STATE_LOCK`, config, state) to temp dirs; `subprocess.run` inside trade_watchdog was monkeypatched everywhere an execute could occur (fake rc=0 / `✓ Added trade #99999`) — **zero real orders placed by me**. Live-file integrity: sha256 of `data/{pending_orders.json, pending_orders_state.json, manual_trail_state.json, auto_trader_config.json}` identical at baseline (06:24), after all harnesses (06:37) and at end of run (06:58).

---

## Verdict table

| # | Check | Result | Evidence |
|---|---|---|---|
| **A-i** | Lock correctness — no nesting path | **PASS** | AST call-site audit: wrappers called only from `trade_watchdog.py:1613` (analyze_all), `:1992` (execute_safe_actions), `pending_order_monitor.py:43/53`; `manual_exit_manager.py:185` is a comment. All 8 internal call sites are wrapper→impl/lock only; `_monitor_pending_orders_impl`/`_execute_pending_order_impl` bodies reference no wrapper/lock call (AST: NONE). Runtime depth instrumentation over monitor→execute in one process: `max_lock_depth=1`, no hang. Hazard proven real: same-process acquire on a 2nd fd **blocks** (alarm-bounded demo) → a nesting path would deadlock. |
| **A-ii** | 2-process synchronized race ≥5 rounds → exactly 1 claim | **PASS (16/16)** | `/tmp/bh_f1f2/harness_A_race.py`: 5 natural rounds + **5 adversarial rounds with 50 ms stall injected inside the locked section** → 10/10 rounds exactly 1 claim; 3 monitor+execute rounds → exactly 1 brain call, `fired`; 3 stale-steer-replay rounds (both processes call `_execute_pending_order`) → exactly 1 brain call. **Sensitivity control: wrapper bypassed (no flock) → 6/6 rounds double-claim**, so the test does detect the original bug. |
| **A-iii** | NFS/unwritable lock path | **SKIP / partial** | FS is local ext4 (`/dev/vda2 on /`), no NFS — N/A as instructed. Unwritable-path behaviour tested instead → see finding **LOW-1**. |
| **A-iv** | kill -9 while holding lock → next caller acquires | **PASS** | `harness_A_kill.py`: holder SIGKILLed mid-hold; independent probe confirmed lock genuinely held while held (blocked >3 s); next caller acquired in **0.001 s** and claimed (`steers=1`, `status=triggered`). Also cross-process mutual exclusion: prober waited **2.49 s** of holder's 2.5 s hold. Lock file survives kill (inode-based flock). |
| **B** | Fail-closed: corrupt / non-dict / empty + recovery + no brain.py | **PASS (10/10)** | 6 corruption modes (garbage, extra-data, list, string, number, empty file): monitor → `[]` + ERROR `pending orders state UNREADABLE (corrupt) … FAIL-CLOSED`; execute → `hl_result="error: one-shot state corrupt"`, **subprocess spy = 0 calls**; state file byte-unchanged. Delete file → next monitor works (`steers=1`, `status=triggered`); execute after recovery → 1 brain call, `success`. |
| **C** | F2 end-to-end + mxm gate (both directions) | **PASS (18/18)** | `dynamic_sl: false` order, crossed price → steer payload carries `dynamic_sl=False` → mocked execute → state `fired` **with** `dynamic_sl:false` **and** `manual_trail_state {99999:{dynamic_sl:false}}` (trade_ref parsed from `#99999`). `mxm.update_trail` on matching pos → **False, 0 psycopg2 connects, 0 SQL, state-file hash unchanged**. Absent key → payload `None` → bridge does not write the flag (`99999` entry untouched, no new flag) → unflagged trade reaches `decide_sl` → CAS write recorded (`UPDATE trades SET stop_loss…`, `rowcount=1`, returns True). |
| **D** | Claim semantics + orphan | **PASS (10/10)** | `triggered` → **PROCEEDS** (handoff); `fired` → refuses `skipped: already fired`, 0 brain calls; `error` → refuses `skipped: already error`; missing entry → proceeds. Monitor does not re-emit fresh `triggered`; orphan (>15 min) surfaced as urgent steer with `auto_executable:False`, **no action payload, 0 executions**; monitor does not rewrite state in that path. Orphan code untouched by the commit (diff has no hunk over lines 1323–1341). |
| **E** | F3 4 branches + price-side guard | **PASS (7/7)** | SHORT R1 97→100.5 + R2 50→96.5; LONG R1 100.5→99.5 + R2 200→103.5 (CAS params, rowcount, logged). **Guard blocked**: SHORT candidate TP 96.5 ≥ price×0.999=95.904 → **zero SQL**; LONG candidate 103.5 ≤ 104.104 → **zero SQL**; just-inside case (96.9 < 96.903) → R2 fires. Unflagged trade → zero SQL; missing structure → no connect. |
| **F** | F4 dedupe 5 cases | **PASS (8/8)** | `fired`→**armed**, `error`→**armed**, `triggered`→**covered**, absent→**covered**, far→**armed**; wrong-direction unaffected; armed order shape valid (`dynamic_sl:false`, trigger/SL/TP ordered). See **LOW-2** (robustness) and **LOW-3** (fail-open). |
| **G** | F7/F10 + step order | **PASS** | `run_pipeline.py:56` `'pending_order_monitor': 180` with F7 comment vs brain inner `trade_watchdog.py:1498 timeout=120`; `:38` monitor still **first** in `STEPS_EVERY_MIN`; `SKILL.md:221-227` states cross-process flock + fail-closed **and** "temp state AND temp config path — never the live ones" with the #16832 incident. |
| **H** | Live health post-fix | **PASS** | pipeline.log since 06:14 (fix) → **43/43 `pending_order_monitor` cycles rc=0**, 0 Tracebacks, 0 `[ERROR]`, 0 FAILED/timed-out steps, 0 state-unreadable/corruption/drop events. `data/pending_orders_state.json.lock` exists (0 bytes, mtime refreshed each cycle), state file valid JSON (20 entries). Watchdog cycles on new code: **06:19:17** and **06:49:17** — deterministic part of both: 0 Tracebacks, 0 `[ERROR]`, `[DONE]`; `watchdog.json.auto_trader` = `mode:live, decision:BRACKET, live_armed:[], tweaks:[]` (auto_trader ran live cleanly). 4 Tracebacks in the 06:49 section are inside the **opencode agent** block (after `> build · mimo-v2.6-flash` banner), not trade_watchdog paths. No `JSONDecodeError` anywhere after line 2805358 (fix predates it). |
| **I** | Closed-trade sanity | **PASS (1 cosmetic gap)** | PG: #16831 `closed / manual_sl_hit / exit 74644 / entry 74613.5 = hl_entry 74613.5 / pnl −0.01 / closed 06:07:46`; #16832 `closed / manual_sl_hit / exit 74644 / entry_price 74613.5` (hl_entry 74587 = its own original fill of the merged pair; `hl_exit_price=0` matches every other recent closed row — normal). **Open BTC rows = 0** (only #16830 WLFI open). pending state: `btc-auto-…-short` has `dynamic_sl:false` retro-flag; **`probe` (#16832) does NOT** → see **LOW-4**. mxm state: `16831` and `16832` both `dynamic_sl:false`; last real `[MANUAL-TRAIL]` for them = 05:29:27, i.e. **no trail writes after the 06:07 close** (only post-close line is my harness artifact, disclosed below). |
| **J** | Regression | **PASS (3/4 green + 1 harness artifact)** | `analysis/test_manual_exit_manager.py` → **20 passed, 0 failed**; `py_compile` on trade_watchdog/auto_trader/run_pipeline/pending_order_monitor → OK; dry `auto_trader.run_cycle()` on a **copy** of live data: rc=0, `mode=live, decision=BRACKET, live_armed=[], shadow_armed=[], tweaks=[], pause_flag=null`, **temp config byte-identical**, and live config byte-identical. The 4th J sub-check (`no candles.db-wal/shm`) failed but is a **wrong harness expectation**: those files are owned by the live collectors (open fds, rewritten every cycle); `candles.db` itself unchanged across the run window. |

---

## Findings

### LOW-1 — An unusable lock path is an UNCAUGHT exception: it kills the pipeline step and would abort a whole watchdog cycle (previously the monitor was exception-proof)
**Where:** `scripts/trade_watchdog.py:1246` (`open(_PENDING_STATE_LOCK, "w")`) called from `:1266` (monitor wrapper) and `:1440` (execute wrapper); unprotected call sites `scripts/pending_order_monitor.py:43`, `scripts/trade_watchdog.py:1613` (`analyze_all`).
**Proven** (`harness_G_lockfail.py`, non-crossed order, temp dir, lock path replaced by a directory): `pending_order_monitor` exits **rc=1 with `IsADirectoryError` traceback** — i.e. `pending_order_monitor: FAILED in … (rc=1)` in pipeline.log. Same class applies to `FileNotFoundError` (missing data dir) and `EMFILE`.
**Blast radius:** fail-closed for trading (no steer, no execution) but (a) the pipeline step is reported FAILED and its output/visibility for that minute is lost, and (b) in the watchdog, `analyze_all:1613` is not inside a try, so the exception escapes `main()` and — because `run_watchdog.sh` runs `set -euo pipefail` — the **entire cycle aborts** (no steers at all, no `[DONE]`, agent skipped) until the FS issue clears. Every other I/O path in the monitor (config read, state read, state write) catches and degrades gracefully; the lock is now the only raising path.
**Suggested fix:** wrap `_acquire_pending_lock()` in the wrappers — on `OSError`, log the same `ERROR … FAIL-CLOSED` line as the corrupt-state path and return `[]` / a failure dict instead of raising.

### LOW-2 — F4 state read is not `isinstance(..., dict)`-guarded: a truthy non-dict state entry raises and aborts the auto_trader cycle
**Where:** `scripts/auto_trader.py:246-248` — `_st = (pstate.get(ex.get('id')) or {}); _st.get('status')`.
**Proven** (`harness_F_extra.py`): state entries `"fired"` (str), `1` (int), `[1,2]` (list) → `AttributeError: 'str'/'int'/'list' object has no attribute 'get'` from `_arm_real_leg`. `None` is harmless (`or {}`).
**Impact:** the raise escapes `_arm_real_leg` → escapes `run_cycle` (arming block is not inside a try) → caught only by `trade_watchdog.py:2043-2047` (`auto_trader cycle failed (watchdog continues)`) → **that cycle's remaining auto_trader work is skipped** (learn, pause checks, dashboard summary), repeated every cycle until the entry is repaired. The monitor's equivalent code guards correctly (`trade_watchdog.py:1322` uses `isinstance(prev, dict)`), so this is an inconsistency in the new code, not a trading-safety hole.
**Suggested fix:** `pstate.get(...) if isinstance(pstate.get(...), dict) else {}`.

### LOW-3 — F4 fails OPEN on a corrupt one-shot state while the fire path fails CLOSED (inconsistent posture)
**Where:** `scripts/auto_trader.py:235-241` (`except Exception: pstate = {}`).
**Proven** (`harness_F_f4.py`, corrupt state): a consumed (`fired`) order **covers again** → returns `covered` → shadow hypothetical stays `armed` with no live order = the F4 shadow/live divergence reappears — exactly in the corrupted-state situation where the monitor/execute path goes fail-closed. Not a money-safety issue (no execution), but the two halves of the feature now disagree about what "unreadable state" means.
**Suggested fix:** decide explicitly — e.g. on unreadable state, still record the divergence (`armed` + WARN) or defer the arm; do not silently revert to the pre-F4 behaviour.

### LOW-4 — "Retro-applied to #16831/#16832" is only half true for the pending state (cosmetic — the field has no reader)
**Where:** `data/pending_orders_state.json` — `btc-auto-1794190756-19b405-short` (trade **#16831**) carries `"dynamic_sl": false` + retro note; the **`probe` entry (trade #16832)** has **no** `dynamic_sl`. mxm state is correct for both (`16831`, `16832` → `dynamic_sl:false`).
**Impact:** none functionally — grep shows `state[oid]["dynamic_sl"]` (`trade_watchdog.py:1523`) is **write-only**; every functional gate reads the config/payload (`:1409`, `:1522`) or mxm state (`manual_exit_manager.py:186`, `auto_trader.py:320`). Flagged because the commit message asserts both.

### INFO-1 — Hand-rolled blocking flock instead of the codebase's own `hermes_file_lock` helper; no PID, no timeout
**Where:** `scripts/trade_watchdog.py:1241-1259`. `scripts/hermes_file_lock.py` docstring: *"All Hermes scripts should import this instead of hand-rolling fcntl locks"* (it also writes the holder PID for operator visibility). The new lock blocks indefinitely with `flock(LOCK_EX)` — no deadline. In practice the holder is bounded (brain.py subprocess `timeout=120` at `:1498` + state write), and the pipeline side is bounded by the new **180 s step timeout**, which kills the process group and thereby releases the lock (run_pipeline.py:86-99). The watchdog side (`analyze_all`) has no such bound: a hypothetical wedged holder would stall both callers until systemd/service cleanup. Consistency/robustness note only.

### INFO-2 — The lock is held across the whole brain.py execution (≤120 s): the other caller can block ~2 min
Design consequence of putting execute under one lock: the 1-minute pipeline monitor can be blocked for up to ~125 s by a watchdog fill in progress. **This is exactly what F7's 60→180 s step timeout covers** — the two fixes are coupled; if brain's inner timeout ever rises above ~175 s, the pipeline step will start timing out (killed, `rc` failed) while the fill is legitimately in flight. Worth keeping both constants in view together.

### INFO-3 — F4 changes future live behaviour (intended): a consumed order no longer blocks a new arm
With both short orders in `pending_orders.json` in state `fired`, a future **kept short hypothetical** will now take `_arm_real_leg` → `'armed'` → a **new real conditional order written** (previously `'covered'`). That is the point of F4 (shadow/live parity) and it is still gated by ITM-skip, shape and real-R:R ≥ 1.0. Observed today: `live_armed=[]` in my dry run and in both live watchdog cycles (06:19, 06:49) because there are no `armed` hypotheticals and the short levels are already ITM — **no config change happened**. Flagging so the CEO knows the first kept short after this fix will arm live rather than report `covered`.

### INFO-4 (pre-existing, not this change set) — opencode agent pass WARN/timeout
`[WARN] Opencode agent failed or timed out` at 05:57, 06:27, 06:57. Started with the 05:49 cycle (**before** the fix commit at 06:14) and only affects the LLM deep-analysis step; the deterministic watchdog part completes `[DONE]` every cycle. No action needed for this verdict; worth a look separately.

### Sideways find (INFO) — working-tree `scripts/hermes_constants.py` diff is *not* part of this commit
`git status` shows uncommitted changes: `FAVORITES_LONG` dropped `'CAKE'` and `LOSERS = {'ETH'}`. Both are the **sanctioned automated rewrites** (`favorites_updater.py` daily rewrite; `daily_git_commit.py:18-60` explicitly whitelists the `LOSERS = …` block as the losers_tracker daily rewrite). Not a finding against this fix set — recorded so the working-tree state isn't mistaken for fix-set scope.

---

## Harness self-disclosure (bug_hunter artifacts, no live data/ damage)

1. **One spurious line in the live `logs/pipeline.log`** at `2026-11-09 06:34:58`: `[MANUAL-TRAIL] BTC SHORT: $74700 → $74600 (BE-LOCK, profit 0.13%)`. Source: `harness_C_f2.py` case C8 — `manual_exit_manager` logs through `hermes_log.log`, which **appends to `logs/pipeline.log`**; my harness did not patch that logger. **LOG-ONLY**: no DB row (psycopg2 stub), no state-file mutation (`manual_trail_state.json` sha256 unchanged), no trade. Do not read it as a real trail event on a real position.
2. `harness_J_regress.py` asserted `candles.db-wal/-shm` absence → false alarm: those are live-collector artifacts (open fds, rewritten every cycle). `candles.db` itself was unchanged across the harness window; live JSON/DB watched files sha256-identical.
3. Live config/state/config-path protection: all harnesses used `HERMES_DATA_DIR`/`HERMES_DATA_OVERRIDE` → temp, plus explicit asserts that `PENDING_ORDERS_CONFIG`, `PENDING_ORDERS_STATE`, `_PENDING_STATE_LOCK`, `mxm._STATE_FILE`, `at.HERMES_DATA` all start with the temp dir (the predecessor's config-clobber incident class is now checked at process start).
4. E3/E4/E6 and one F case initially "failed" — those were **my test-data arithmetic errors** (candidate TP was not actually crossed; the connect-before-gate ordering); corrected after recomputation. The shipped code was right in all four.

---

## Verdict summary (claims vs proof)

| Claim | Verdict |
|---|---|
| F1 cross-process flock, whole read→claim→write under one EXCLUSIVE lock (monitor + execute) | **VERIFIED** — 16/16 race rounds = 1 claim (control 6/6 double without lock), mutual exclusion measured, kill -9 release OK, no nesting path (AST + runtime depth) |
| F1 fail-closed `_load_orders_state` → None; monitor `[]`+ERROR; execute failure dict, no brain.py | **VERIFIED** — 6 corruption shapes, 0 subprocess calls, state untouched, recovery works |
| F1 execute claims under lock, refuses fired/error, reuses claim-time load | **VERIFIED** — code `:1459-1473/:1506-1515` + tests; `triggered` proceeds, missing proceeds |
| F2 `dynamic_sl` in steer payload + fire-path bridge + mxm flag | **VERIFIED end-to-end** with mocked brain; gate blocks `update_trail` (0 connects) |
| F3 price-side guarded R2 TP (both sides) | **VERIFIED** — crossed candidate ⇒ zero SQL |
| F4 fired/error do not cover | **VERIFIED** — plus 2 LOW findings on robustness/consistency |
| F7 step timeout 60→180 | **VERIFIED** (`run_pipeline.py:56`) |
| F10 skill warns temp state AND config | **VERIFIED** (`SKILL.md:221-227`) |
| Live health post-fix | **VERIFIED** — 43/43 pipeline monitor cycles rc=0, 2/2 watchdog cycles clean, auto_trader live `tweaks:[]`, no corruption events, live files byte-identical |

---

## Overall verdict: **PASS WITH FINDINGS**

The predecessor's two FAIL items are genuinely fixed and provable in both directions: with the lock the 2-process race produces exactly one claim in **16/16** rounds (including 50 ms stall-injected and stale-steer-replay variants), and with the lock bypassed the same harness double-claims **6/6** — the fix, not the test, is what changed. Fail-closed behaves exactly as specified across 6 corruption shapes with zero `brain.py` invocations, `dynamic_sl` now crosses payload→state→mxm gate end-to-end, claim/orphan semantics are correct, the F3 guard issues zero SQL for crossed TPs, F4/F7/F10 land as described, the regression suite is 20/20, and the live system has run 43 clean pipeline monitor cycles plus 2 clean full watchdog cycles (auto_trader live, `tweaks=[]`) since the commit with no state corruption and no live-file mutation by this verification.

Remaining findings are LOW/INFO: an uncaught lock-path failure can kill a pipeline step or a whole watchdog cycle (LOW-1), F4's new state read lacks the `isinstance` guard the monitor has (LOW-2) and fails open on corrupt state (LOW-3), the #16832 pending-state retro-flag is missing though harmless (LOW-4), plus INFO notes on the hand-rolled blocking flock vs `hermes_file_lock`, the ≤125 s lock hold that only F7's 180 s covers, and F4's first future live re-arm. None is money-unsafe today; none should block shipping. Suggested next pass: 5-line hardening (catch `OSError` in the two wrappers, `isinstance` in F4) rather than a re-open of the fix set.
