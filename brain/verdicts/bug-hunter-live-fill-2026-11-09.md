# bug_hunter verdict — 1-minute fills + auto_trader LIVE phase 1

**Date:** 2026-11-09
**Change set under review:** `29369097` "trading: 1-minute fills + auto_trader LIVE phase 1 + structure-fixed stops"
**Also verified (landed during this run):** `4b531826` (back-fill kept shadow legs + sqlite3.Row .get fix), `60fad1e0` (HL min-notional size floor) — both are part of live behavior now.
**Harnesses:** `/tmp/bh_live_fill/harness_{A,B,C,E,F,J}.py` (+ inline A3b/A3c/A5/A6b/A7, E10–E14, F-extra, D-extra)
**Live event during verification:** trade **#16831** filled at 05:03:09 UTC via the new 1-minute path (details in G).

---

## Verdict table

| Check | Result | Evidence |
|---|---|---|
| **A. Double-fire proof** | **FAIL — CRITICAL** | No inter-process lock on `pending_orders_state.json`. Barrier race: both callers load pre-write copy → both execute. 5 ms stall → **6/6 double-fire**; natural synchronized starts → **1/40 double-fire** + 4/40 ENOENT steer-drops. Concurrent writers share ONE fixed `.tmp` path → corrupted state observed → `_load_orders_state` returns `{}` (A6b) → **already-fired, still-crossed order re-emits and would execute with `--force` (dup guard bypassed)**. Restart mid-fire: **PASS** (A2: state `triggered` persists, 0 re-executions, fill lost/orphaned by design). |
| **B. Mode gating** | **PASS** | B1 `WATCHDOG_MODE=recommend` → rc 0, state file never created; B2 `autopilot` → `triggered` persisted; B3 fresh deploy → recommend (no state touch); B4 deploy >48 h → autopilot. Env override read inside `get_watchdog_mode` (trade_watchdog.py:133) so pipeline path respects it; pipeline gates before `monitor_pending_orders` (pending_order_monitor.py:36-41) ⇒ recommend never touches state (PENDING_ORDERS_CAN_PERSIST semantics preserved). |
| **C. `_execute_pending_order` contract** | **FAIL (bridge inert)** | cmd verified: `--force` ✓, `--signal ai-trader-pending` ✓, **no `--manual`** ✓ (vacation/kill gates apply: `is_live_trading_enabled(is_manual=False)`), `--sl/--target/--real` ✓. Failure → state `error`, one-shot holds (C2, `monitor_refires=false`) ✓. trade_ref parse `#16827→16827` ✓ (C5). Bridge failure logged, not raised ✓ (C4). Keying: order-id in pending state, trade-id digits in manual state ✓ (C1: `mstate_keys=['16999']`). **BUT: `monitor_pending_orders` rebuilds the steer payload without `dynamic_sl` (trade_watchdog.py:1350-1356) → `order.get("dynamic_sl") is False` is always False → bridge NEVER runs on any path.** Proven in payload probe + live on trade #16831 (finding F2). |
| **D. manual_exit_manager gate** | **PASS** | Gate at manual_exit_manager.py:186-187 returns `False` **before** `decide_sl`/any DB write (poisoned-psycopg2 test: flagged trade never touches DB; flag absent/None/True → normal stack reached DB ✓). Cannot poison peak/last_sl of normal trades (keyed per trade id; gate only trips on explicit `False`). `python3 analysis/test_manual_exit_manager.py` → **20 passed, 0 failed**. |
| **E. tweak_structure_fixed math** | **PASS (1 MED finding)** | 4 branches reproduced: E1 short R1+R2 (`95→100.4`, `84→90.2`), E2 long R1+R2 (`105→99.5`, `106→99.8`); past-cap skips E3/E4 (no SQL); dynamic-skip E5; signal-skip E6; missing structure E7 (no connect). CAS param order `(new, id, old)` ✓ (params `[100.4, 5001, 95.0]` vs `SET stop_loss=%s WHERE id=%s … stop_loss=%s`). rowcount 0 → **no commit, no log** ✓ (E8); R1 rowcount 0 + R2 rowcount 1 → only R2 commits/logs ✓ (E9). Price-side guards: short stop `≥ price×1.001` ✓, long stop `≤ price×0.999` ✓. ±0.5 % cap ✓. R2 thresholds: short `target < sl−atr`, long `target > sh+atr` ✓. **MED: R2 has no price-side guard (R1 does) — can write an already-crossed TP → instant TP close (E14: long entry 101, price 100.6, TP written 99.8 → `manual_tp_hit` at −0.40 % next minute). Latent: tweak never runs today (F2).** |
| **F. _arm_real_leg** | **PASS (1 MED finding)** | Temp-dir: arm ✓ (shape ok, `dynamic_sl: False` present, no `.tmp` leftover); dedupe same-dir <0.3×ATR → `covered` ✓, opposite dir → `armed` ✓, distance == dedupe → `armed` ✓ (strict `<`), under → `covered` ✓; engine accepts all written orders (F6: crossing orders → steers, state untouched) and rejects hand-crafted bad shape (F7). **MED: dedupe does NOT check one-shot state — a FIRED order within 0.3×ATR returns `covered` for a new live arm (F-extra proven), while DB hypothetical says `armed` → shadow/live divergence; docstring says "unfired", code doesn't.** Concurrent append: config writers = `auto_trader._arm_real_leg` (inside watchdog main only) + manual/agent edits; pipeline monitor never writes config; two watchdog cycles can't overlap (bash lock + 30 min timer) → **LOW** (agent-edit vs cycle = last-writer-wins). |
| **G. run_cycle live end-to-end** | **PASS** | Ran `python3 scripts/auto_trader.py` twice (live config). Both cycles: `decision=BRACKET`, `live_armed=['short-kept:covered','long-kept:covered']`, `tweaks=[]` (BTC flat), `pause_flag=None`, config **byte-identical before/after** (dedupe idempotent). Summary fields all present (mode/live_armed/tweaks/shadow_armed). Gates on armed legs: shape ✓, ITM-skip live-proven by WARN events (`already crossed — leg skipped`), real R:R short **2.16**, long **5.21** (≥1.0), no duplicates. **Bonus: at 05:03 the live 1-min path filled the short → #16831 in 6.8 s (within the 1-min promise); post-fill re-read with live state → 0 steers (one-shot holds).** |
| **H. Pipeline wiring** | **PASS** | `run_pipeline.py:38` `pending_order_monitor` is **FIRST** in STEPS_EVERY_MIN; `:56` timeout 60 s. Direct run → exit 0, quiet, 0.0 s. Fresh-process import chain safe: `pending_order_monitor → trade_watchdog` (module level; auto_trader only imported inside `main()` try, trade_watchdog.py:1960); isolated imports prove `auto_trader→auto_analysis→structure_analysis` never imports back into `trade_watchdog` — **no cycle**. |
| **I. Logs** | **PASS** | pipeline.log since monitor went live (01:56): **0 Tracebacks**, every `pending_order_monitor: done (rc=0)`, no FAILED/timed-out. trade-watchdog.log post-commit cycles 02:19/02:49/03:19/03:49/04:19 all `[DONE]`, **0 Tracebacks after 02:19** (older tracebacks are opencode-agent ad-hoc SQL, pre-change). profit_monster.log: no errors since 02:05. watchdog.json `auto_trader: {mode: live, decision: BRACKET, live_armed: covered×2, tweaks: []}` at 04:19. auto_trader events: only expected `WARN size 7.33 < HL min — floored` (follow-up fix working). The 05:03 fill ran clean: `FILLED #16831`, rc=0. |
| **J. Scoring parity (spec gate)** | **FAIL — flag divergence** | n=54 resolved hypotheticals; 29 windows had **no** real BTC trade; matched n=25 (outcome n=24). **Direction agreement 12/25 = 48.0 %; outcome agreement 11/24 = 45.8 %** (long 8/13, short 3/11) — i.e. at/below coin-flip, no positive parity between shadow scorecard and real BTC outcomes in the same armed→expiry windows. Single-trade windows: 7/17 = 41 %. Caveat: small n (95 % CI ≈ 28–65 %), windows mix unrelated CEO/pipeline trades — but the gate asked for a flag and this is one. |

---

## Findings

### F1 — CRITICAL — Cross-process TOCTOU on the one-shot state file: double-fire + corruption → state wipe → re-fire with `--force`
**Where:** `scripts/trade_watchdog.py:1217-1227` (`_load_orders_state` swallows JSON errors → `{}`), `:1257` (load), `:1358-1360` (write `triggered`), `:1369-1378` (write + fail-closed drop), `:188-193` (`atomic_write_json` uses a **fixed** `path + ".tmp"`), `:1424-1450` (write `fired`).
**No lock anywhere:** grep for `flock/LOCK_EX/lockf` in `trade_watchdog.py`, `pending_order_monitor.py`, `auto_trader.py` → none. Pipeline holds `/tmp/hermes-pipeline.lock` but `run_watchdog.sh` never takes it → **pipeline monitor and watchdog monitor run concurrently by design**.

Two proven failure modes:

1. **Double-fire (check A).** The one-shot check (`:1274`) is read-then-write with no mutual exclusion. If both callers `_load_orders_state` before either writes `triggered`, both emit steers and both run `brain.py`:
   - barrier + 5 ms stall between load and write: **6/6 runs → 2 executions**;
   - 20 ms / 100 ms: **6/6** each;
   - natural synchronized starts (no stall): **1/40 → 2 executions** (plus 4/40 ENOENT "dropping steers" — the fail-closed path, which delays but does not prevent the race).
   Sequential same-window is safe (A1: 1 execution) and restart mid-fire is safe (A2: 0 re-executions) — the hole is purely concurrent processes. `--force` (trade_watchdog.py:1412) bypasses brain.py's dup guard (brain.py:560-565), so a double-fire = **two real BTC positions**.

2. **State-file corruption → one-shot wipe → re-fire of filled orders (proven A3/A6b).** Concurrent `atomic_write_json` calls share the same fixed `pending_orders_state.json.tmp`; interleaved writes produced a **corrupt state file in a real harness run** (`JSONDecodeError: Extra data`) and ~25 % ENOENT failures under 4-writer contention (A5). `_load_orders_state` swallows the decode error and returns `{}` → *all* one-shot memory lost → any still-crossed, already-fired order re-emits (A6b: fired order re-steered) → `--force` executes it. **Live ammunition right now:** `btc-ceo-short-74888` (fired → #16827) and `btc-auto-1794190756-19b405-short` (fired → #16831, price 74573 ≤ trigger 74604) are both still in config and still crossed — a wipe today opens a duplicate short alongside open #16831.

**Natural window:** mean 0.13 ms / max 0.37 ms for the load→write section (harness `window_natural`) — small but non-zero, and it widens with the 10 KB state file, logging, GC and disk latency; the corruption vector only needs two *writes* to overlap (execute-vs-monitor), not two loads. Rare per day, not impossible; consequence is duplicate real money. Per the task spec ("find the race → CRITICAL").
**Fix direction (not applied):** `fcntl.flock` on the state file around load→write in both callers, plus per-writer unique tmp names (`tempfile.mkstemp` in the same dir) — or a single serialized executor process.

### F2 — HIGH — `dynamic_sl: False` is silently dropped from the steer payload: structure-fixed stop feature is inert on the live path (live-proven on #16831)
**Where:** payload built at `scripts/trade_watchdog.py:1350-1356` omits `dynamic_sl`; gate read at `:1438` (`order.get("dynamic_sl") is False`); tweak gate at `scripts/auto_trader.py:307` (`mstate…get('dynamic_sl') is not False → continue`).

Config carries the flag (`auto_trader.py:250`, e.g. `btc-auto-1794190756-19b405-short … "dynamic_sl": false`), but `monitor_pending_orders` rebuilds the `action.order` dict from an explicit key list **without** `dynamic_sl`, and both callers (pending_order_monitor.py:53, trade_watchdog.py:1908) pass that rebuilt dict. Payload probe:

```
config order keys:   [..., 'dynamic_sl', ...]
steer payload keys:  [...]                       # dynamic_sl absent
payload.get('dynamic_sl') is False: False       # bridge gate never true
```

Consequences, all confirmed on the live fill:
- `pending_orders_state.json` entry for `btc-auto-1794190756-19b405-short` has **no `dynamic_sl` key** (state[oid]["dynamic_sl"]=False at :1439 also never written);
- `manual_trail_state.json` → `{"16831": {"ts": …, "last_sl": 74640.0}}` — **no flag**;
- **05:17:49 `[MANUAL-TRAIL] BTC SHORT: $74975 → $74640 (BE-LOCK, profit 0.11%)`** — BE/trail ran on a structure-fixed order, exactly the #16827 premature-stop behavior the change was built to prevent;
- **0 `tweak` events** in auto_trader.db — the tweak gate (:307) sees no flag → `tweak_structure_fixed` skips → R1/R2 never applied either. Both halves of change item 3 are dead.

Fix direction: include `"dynamic_sl": order.get("dynamic_sl")` in the payload dict at trade_watchdog.py:1350-1356 (single-line), or read the flag from the config file by id inside `_execute_pending_order` as a fallback.

### F3 — MED — R2 TP snap has no price-side guard → can write an already-crossed TP → instant (possibly losing) close
**Where:** `scripts/auto_trader.py:338-348` (short) and `:367-377` (long) — R1 has `max(want, price×1.001)` / `min(want, price×0.999)`; R2 writes `sl+0.05×atr` / `sh−0.05×atr` with no comparison to live price.
Reproduced (E14): long entry 101, sh=100, atr=4, target=106, **price 100.6** → R2 writes TP **99.8** → position_manager LONG rule (`price ≥ TP`) fires `manual_tp_hit` next minute → close at 100.6 = **−0.40 %**, mislabeled as a TP. Short mirror (E11): TP written above price → immediate hit books profit early. Latent today only because F2 blocks the tweak entirely; it activates the moment F2 is fixed. Fix: skip R2 (or clamp) when `new_tp` is on the wrong side of `current_price`.

### F4 — MED — Dedupe counts FIRED orders → consumed order silently blocks a new live arm
**Where:** `scripts/auto_trader.py:232-237` — iterates all config orders, never consults `pending_orders_state.json`; docstring (:219-220) says "unfired".
Reproduced (F-extra): new short arm 72 pts from a **fired** order (dedupe 120) → `covered`, no order written, while `record_order`/`upsert_hypothetical` already logged `armed` → shadow/live divergence (shadow tracks a fill live can never take). Aggravated by F5. Fix: skip entries whose state status is `fired`/`triggered`.

### F5 — MED — Scoring parity gate: shadow hypotheticals show no positive parity with real BTC outcomes
n=54 resolved; matched windows n=25; **direction 48.0 %, outcome 45.8 %** (see table above) — coin-flip. The 18 d / 54-hyp / 877-decision evidence cited as the live-flip justification does not positively correlate with what real BTC trades did in the same windows. Small n and mixed-strategy windows caveat applies, but the spec gate says flag it. Suggest re-running parity on same-signal windows only before extending beyond phase 1.

### F6 — LOW — Fired orders are never pruned from `pending_orders.json`
No removal code anywhere (`grep` over scripts: only read paths). Config accumulates consumed orders forever → grows the F4 dedupe pollution and enlarges the re-fire blast radius after any state wipe (F1). Suggest pruning `fired` entries (or moving them to an archive) at execute time.

### F7 — LOW — Pipeline step timeout (60 s) < inner brain.py timeout (120 s); kill mid-brain leaves `triggered` state
`run_pipeline.py:56` (60 s) vs `trade_watchdog.py:1415` (`timeout=120`). On timeout, `run_pipeline.run` kills the whole process group → state stays `triggered`, brain may have opened HL before dying (phantom-position class) → after 15 min the ORPHANED steer (:1280-1292) tells the CEO "never executed — delete state entry to re-arm"; re-arming with `--force` duplicates an existing position. Observed fill took 6.8 s so it is not imminent, but the two timeouts should be aligned (e.g. step 130 s) and the orphan message should tell the CEO to check for an open position first.

### F8 — LOW — `get_watchdog_mode()` called from the pipeline can create `watchdog_deploy_time.json`
pending_order_monitor.py:36 calls `get_watchdog_mode()`, which writes the deploy marker on first run (trade_watchdog.py:155-163). If the marker is ever deleted, the *pipeline* (not the watchdog) would set deploy time. Side effect only; note for completeness.

### F9 — LOW (observation) — back-fill logs `armed` but leaves `orders_log.action='shadow_armed'`
`btc-auto-1794181754-69e683-long` has a real config order (back-filled 02:30, event `live back-fill → armed`) while orders_log row 118 still says `shadow_armed` (row written at arm time, append-only). Cosmetic ledger inconsistency; also row 119 still shows size 7.326 while the floor fix raised live size to 11.10 (hypotheticals were synced, orders_log not).

---

## What is live-armed right now (G report for the CEO)

`data/pending_orders.json` after my runs — **unchanged by my cycles (both legs `kept:covered`, config byte-stable)**; 4 orders total:

| Order id | Side / trigger | SL | TP | Size / lev | dynamic_sl | Status |
|---|---|---|---|---|---|---|
| `btc-auto-1794190756-19b405-short` | SHORT below **74604** (re-shelved from 74430 per CEO `60fad1e0`) | 74975 | 73477.19 | $11.10 / 5x | false (dropped — F2) | **FIRED 05:03:09 → trade #16831** (open, entry 74640, real R:R 2.16) |
| `btc-auto-1794181754-69e683-long` | LONG above **75779.3** | 75510.57 | 77959.02 | $11.10 / 5x | false (dropped — F2) | unfired (real R:R 5.21; back-filled to real config 02:30) |
| `btc-ceo-long-76400` (CEO, pre-existing) | LONG above 76464 | 76060 | 77800 | 11.1 / 5x | n/a | unfired |
| `btc-ceo-short-74888` (CEO, pre-existing) | SHORT below 74828 | 75180 | 73350 | 11.1 / 5x | n/a | **fired → #16827 (closed)**; still in config, still crossed — skipped by one-shot, exposed to F1 wipe |

My two `run_cycle` invocations (03:34, 03:36): `decision=BRACKET`, `live_armed=['short-kept:covered','long-kept:covered']` — both kept legs already had real orders inside the 0.3×ATR dedupe, so **nothing new was written**; `tweaks=[]` (BTC flat at the time), `pause_flag=None`, `shadow_armed` = the two auto ids.

**Live E2E fill (the feature working):** 05:03:03 pipeline step started → 05:03:09 `FILLED #16831` (6.8 s, within the 1-minute promise) → PG row: SHORT 11.1 USDT @ 74640, SL 74975, TP 73477.19, 5x, `ai-trader-pending`, status open. Then F2 manifested: 05:17:49 BE-LOCK moved SL to 74640 despite `dynamic_sl: false`.

---

## Overall verdict: **FAIL**

The fill path itself works end-to-end (live fill in 6.8 s, one-shot held on re-read, mode gates clean, logs clean, test suite 20/20, tweak math correct, arm/dedupe/atomicity correct). But two shipped defects must be fixed before this is safe to leave running:

1. **F1 (CRITICAL):** the dual-caller design has no cross-process lock — double-fire is provable, and the fixed-tmp corruption → state-wipe → `--force` re-fire chain has two live filled orders as ammunition right now.
2. **F2 (HIGH):** `dynamic_sl` never crosses the steer payload, so the structure-fixed stop feature is dead — live trade #16831 already got the exact BE-LOCK premature stop the change was meant to eliminate, and the companion tweak never runs.

Plus F3/F4/F5 (MED) and four LOWs. Rollback lever if needed: `data/auto_trader_config.json` `mode: "shadow"` (zero live effect), and `pending_order_monitor` can be removed from `STEPS_EVERY_MIN`.

---

## ⚠️ INCIDENT (bug_hunter self-inflicted, disclosed in full)

**What happened:** my payload-probe harness (F2 proof) monkeypatched `tw.PENDING_ORDERS_STATE` to a temp path but **forgot to monkeypatch `tw.PENDING_ORDERS_CONFIG`**. Its `json.dump(..., open(tw.PENDING_ORDERS_CONFIG,'w'))` therefore **overwrote the live `data/pending_orders.json`** at 05:26:14 UTC with a single `probe` order (SHORT below 74604, SL 74975, TP 73477.19, `dynamic_sl: false`). The live pipeline monitor ran ~40 s later, saw the crossed probe, and filled it → **real duplicate trade #16832** at 05:26:52.

**Damage & cleanup performed:**
- `data/pending_orders.json` **restored** from the pre-G backup (`/tmp/bh_live_fill/pending_orders.before.json`, 03:34 snapshot) — back to the correct 4 orders (2 CEO + 2 auto), byte-level verified. The backup was valid because every `run_cycle` in between reported `kept:covered` (config unchanged).
- `data/pending_orders_state.json` retains the factual `probe: fired` entry (left in place — deleting it would be a second edit; it is inert).
- **Open position impact:** HL merged #16831 (filled 74640) and #16832 (filled 74587) into **one** BTC SHORT 0.00032 BTC @ entry **74613.5** (exact average — verified via `get_open_hype_positions_curl`, unrealized +0.04 USDT at check time). Both PG rows were rewritten to entry 74613.5 by hl-sync-guardian (normal merge-sync behavior). Net effect: **~2× intended size (≈22.2 USDT margin instead of 11.1)** on the same thesis.
- No other live files polluted (checked: `manual_trail_state.json`, `auto_trader_config.json`, `watchdog_deploy_time.json` untouched by harnesses; `probe`/`bh_` greps only hit `pending_orders_state.json` (factual record) + unrelated pre-existing files).

**CEO decision needed:** trade **#16832 is a duplicate created by my test, not by the change set**. Recommend closing one of the merged halves (or the whole position if the thesis is stale) at your discretion — I did not take a trading action. The underlying change-set verdicts (F1/F2) are unaffected; if anything the incident is a live rehearsal of F1's `--force` dup-guard-bypass consequence (the probe filled *because* the config said so and `--force` skipped the duplicate check against open #16831 — brain.py:564).

**Lesson recorded:** any harness touching `trade_watchdog` paths must monkeypatch **both** `PENDING_ORDERS_CONFIG` and `PENDING_ORDERS_STATE` (the SKILL.md line "verify … on a temp state path" says *state* only — it should say config too; noted as F10-LOW in the change-set review).

### F10 — LOW — SKILL.md temp-path guidance covers state but not config
`skills/shared/manual-trade-override/SKILL.md:222-223` says "verify any armed order with the engine on a temp state path — never the live state file". A verifier following that literally can still clobber the live **config** (exactly what happened here). Should read "temp config **and** state paths (monkeypatch `PENDING_ORDERS_CONFIG` + `PENDING_ORDERS_STATE`)".
