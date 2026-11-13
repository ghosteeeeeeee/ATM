# bug_hunter verdict — SL placement fix (CEO 2026-11-13 → commit `114711f4`)

**Commit:** "SL placement fix (CEO 2026-11-13): structure-widened guardian cap + regime/major lag + 1h keeper anchors"
**Verified:** 2026-11-13 ~18:30–19:05 UTC by bug_hunter verifier (adversarial, no fixes applied)
**Harnesses (all /tmp, SELECT + mocks only, zero production writes except one task-mandated live run_cycle):**
`/tmp/hml_harness.py` (A), `/tmp/bhv2_lag.py` (B + D), `/tmp/bhv2_keeper.py` (C), plus SELECTs against brain PG, `data/auto_trader.db`, `data/candles.db`.

## Verdict table

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| A(i) | hml_threshold 7 case families (struct wider→widens; >floor→floor; tighter→cap stays; non-managed/wrong-side/missing→unchanged; LONG mirror; lev scaling) | **PASS** | `/tmp/hml_harness.py` 35/35, exit 0. e.g. struct 1.5%@lev5 → −1.5; struct 5%@lev5 → −1.6; struct 0.42% → −0.80 stays |
| A(ii) | Blast radius of floor: `is_managed_signal` = substring tags `('ai-trader-manual','ai-trader-pending','ai-trader-auto')` (manual_exit_manager.py:67-73) | **PASS** | 30d distinct signals (64): managed = only `ai-trader-pending` (40) + `ai-trader-manual` (16). `ai-trader+`/`ai-trader-`/`jup_yolo_mirrored`/`pump-chain+` → NOT managed → unchanged. No accidental tag substrings. T1 xmirror trades `continue` at position_manager.py:3214 BEFORE the HML fire → never reach hml_threshold |
| A(iii) | Adversarial: entry=0 / stop=None / stop=0 / signal=None → unchanged; lev=0/None/−5 → treated lev1 (call site guarantees ≥1, position_manager.py:4026); floor-import failure → falls back to hard_pct (tested by deleting the constant); mixed-case dir upper()'d works; mixed-case signal unchanged (safe side); negative entry → unchanged (min() picks hard) | **PASS** | hml_harness |
| A(iv) | Call-site bindings + ordering: `_pos_signal` bound :3917, `_hml_lev` :4026, `HARD_MAX_LOSS_PCT = CUT_LOSER/lev` :4027, vol-block :4076 (no-op, see F-5), reassignment :4191 **before** fire :4196 | **PASS** | code trace |
| A(v) | Other HML-adjacent paths unchanged: vol-floor block :4060-4077, xmirror catastrophic floor :3163-3214 | **PASS** | position_manager diff = exactly 2 hunks (@184 fn, @4184 call) |
| A(vi) | Floor really binds: struct 5% @lev5 → −1.6% price (= −8% acct); @lev3 → −2.667% (= −8% acct); 7-lev × 8-dist grid: threshold never < floor/lev; result never tighter than caller cap | **PASS** | hml_harness grid checks |
| B(i) | Lag-split cases: birth 4-key seed/no-move; CHOP ignores 15m-only change; CHOP favorable 1h-step (prev sh1h+0.1·atr1h); CHOP adverse → raise to sh1h+0.1·atr1h (only-raise gate); adverse-below-stop → keep+record; TREND favorable 15m-step; TREND adverse → 1h-major (not 15m); migration old→re-seed NO stop move; breach guard; F-4 clamps both ends; CAS-miss records nothing; LONG mirror; malformed-row re-seed | **PASS** | `/tmp/bhv2_lag.py` 35/35 (incl. 8 regime variants), real `tweak_structure_fixed`, fake psycopg2, state in /tmp |
| B(ii) | f-string key sweep of whole function | **PASS** | only one construct: `prev[f'{fld}{sfx}']` :464; keys `sh15/sl15/sh1h/sl1h` written at seed :459-460 and record :470-471; F-1 guard :440-444 requires all 4 numeric → no KeyError path. No other key construction anywhere in file |
| B(iii) | Regime values | **PASS (with note F-4)** | producer auto_analysis.py:232 = `'CHOP'/'TREND'/'UNKNOWN'` only; all-time decisions DB: CHOP 1059 / TREND 48 / UNKNOWN 18. `.upper()` covers case variants; 'CHOPPY' does not exist. **UNKNOWN (18 rows) is unreachable by _lag_stop**: UNKNOWN ⇒ `flips is None` ⇒ STAND_DOWN branch auto_analysis.py:260-265 returns WITHOUT `structure_detail` ⇒ tweak early-return :374. None/missing regime → 15m source is therefore a dead-in-practice default, not a live exposure |
| B(iv) | State migration at scale | **PASS** | `data/tweak_struct_state.json`: 10 entries, **all old 2-key**, ids 16873–16896 — all CLOSED (open trades = 0, PG SELECT) → nothing to migrate live today; spy (B7) proves re-seed writes 4 keys with **zero** stop UPDATE; 72h prune (unchanged) drops them |
| B(v) | 1h-present freeze path | **FAIL (finding F-3, LOW)** | structure_detail missing → early-return :374-375 → no lag, no seed, **no log** — stop frozen at armed level. BTC live OK now (all 5 TFs present; 171 1h candles/7d vs limit 150); silent (unlogged) |
| C(i) | Keeper derivation uses 1h with deliberately-different 15m | **PASS** | bhv2_keeper 17/17: short trig 66940 = sl1h−60 (15m would give 68840), SL 67180 = sl1h+0.6·atr15 (15m 69080); long trig 70060 = sh1h+60 (15m 68560), SL 69820 |
| C(ii) | Reach / ITM / idempotency / fired-rung guards | **PASS** | C2 (no duplicate), C3 (trig<reach_lo → no arm), C4 (trig≤price → no long), C5/C5b (unfired in-reach = ready; fired ≠ ready) |
| C(iii) | Notes match | **FAIL (finding F-2, LOW)** | order notes updated ✓ ("1h MAJOR-floor/ceiling") but **event-log detail strings still print `15m sl/sh {sl15/sh15}` while trig/SL derive from 1h** — auto_trader.py:680, :716; keeper docstring :577-584 and comment :651-655 still say "15m swing floor/ceiling". Commit claim "notes/docstring updated" = partially false |
| C(iv) | Current real book read-only | **PASS (keeper = no-op)** | price 68899.0, 1h sh 69134.01 / sl 68530.29 / atr 676.3; reach [66870, 70928]. Would-derive: short trig 68470 SL 68710 TP 66441; long trig 69194 SL 68955 TP 71223. Actual: short-ready (unfired rung @68073 in reach) + long-ready (CEO rungs 69560/70060) → **next cycle arms NEITHER side**. Old-15m anchors for contrast: 68730/68969 and 69038/68799 |
| D | #16896 end-to-end under fixed system | **FAIL (finding F-1, MEDIUM — outcome gap, not a code defect)** | see D section: trade dies identically |
| E(i) | Suites | **PASS (with caveat)** | my suites: hml 35/35, bhv2_lag 35/35 (+D), bhv2_keeper 17/17 — all exit 0. Author's claimed "Suite 20/20" file NOT found; stale `/tmp/lag_harness.py` is pre-commit (expects 2-key state, `KeyError: 'sh'` against HEAD) → cannot verify author's exact suite; independent suites substitute |
| E(ii) | py_compile + fresh imports | **PASS** | `auto_trader.py`, `position_manager.py`, `hermes_constants.py` compile; fresh import exposes `hml_threshold` + `HML_STRUCT_FLOOR_ACCT=-8.0` |
| E(iii) | ONE live run_cycle | **PASS** | rc=0 (`exit=0`): decision BRACKET, regime CHOP, price 68928.42, `shadow_armed=[]`, `live_armed=[]`, **`tweaks=[]` — tweak not invoked: 0 open positions (auto_trader.py:789 guard)** → HML/lag no-op this cycle; keeper: no ladder key in summary → no arm (matches C(iv) readiness calc). 0 open managed trades (PG SELECT) |
| E(iv) | pipeline/watchdog logs 0 Tracebacks from shipped code | **PASS** | pipeline.log since 18:29: 0 Traceback; watchdog 18:20/18:50 post-deploy cycles complete `[DONE]`; 2 Tracebacks near log tail = **another agent's interactive SQL heredoc errors** interleaved in trade-watchdog.log (sqlite `?` / PG syntax), not shipped code (F-6) |
| F | Scope: exactly 3 files; state-format migration contained; no mxm/pending-order changes | **PASS** | `git diff HEAD~1 --name-only` = auto_trader.py, hermes_constants.py, position_manager.py; `manual_exit_manager.py` + `pending_order_monitor.py` diff = 0 lines; state keys `sh15/sl15/sh1h/sl1h` referenced only in auto_trader.py; prune block unchanged |

## D — #16896 honest end-to-end walk

Ground truth (PG SELECT + auto_trader.db events):
- #16896 SHORT entry 68,661, armed stop 68,950 → DB `stop_loss=68953.9019`, opened 15:25:08, **exit 17:42:26 fill 69,027, −2.6653 % acct**, `manual_sl_hit`. Stop distance **0.4266 % price** (cap −0.80 % = 69,210.3).
- **Regime = CHOP at every decision** 15:20→18:31 (auto_trader.db, flips=2).
- Price facts (candles.db): 1m crossed 68,953.9 first at **17:41**; max 1m high after 17:20 = **69,134.01**; HML 69,210.3 never reached (guardian never fired — the SL did); the 69,818 print was **13:46, before the trade opened**; box (15:00→now) = 68,103–69,134.
- **Old-code actual stop path (events table):** seed ≤15:50 → **16:20:05 R1 tweak 68,950 → 69,161.82** (15m favorable trail) → **16:50:05 R1 tweak 69,161.82 → 68,953.90** (**interior re-arm**) → no further write → died 17:41. Price never again ≥69,161.82 (max 69,134.01): **the 16:50 interior re-drop alone caused the death — even old code survived had it held 69,161.8.**

Fixed system, cycle-by-cycle (as-of reconstruction: closed buckets + forming-bucket partial from 1m; 1h-oracle validated: atr1h 828.6 vs keeper-note 826.3):

| cycle | price | sh1h | stop | action |
|---|---|---|---|---|
| 15:50 | 68,694.6 | 69,583.1 | 68,953.9 | birth seed 4-key, no move |
| 16:20 | 68,506.1 | 69,583.1 | 68,953.9 | sh1h unchanged → no touch |
| 16:50 | 68,630.7 | 69,583.1 | 68,953.9 | unchanged → no touch (**no interior re-drop possible — CHOP source=1h**) |
| 17:20 (last cycle before death) | 68,609.6 | 69,583.1 | **68,953.9** | unchanged → no touch |
| 17:41 | — | — | — | **price crosses 68,953.9 → dies same fill ~69,027, same −2.67 %** |
| 17:50 | 68,995.3 | 69,134.0 | (breach) | first sh1h step arrives 33 min too late; breach guard returns |
| 18:20 | 68,917.4 | 69,134.0 | →69,650.5 | raise to prev-sh1h+0.1·atr1h (post-mortem; protects later trades) |

hml_threshold along the way: with stop 68,953.9 → struct 0.4266 % < 0.80 % → **cap stays −0.80 %** (widening does not bind — exactly the "hmm" in the task). With a structure-anchored stop 69,653.4 → thresh −1.4454 % → fire at **69,653.4** (guardian matches the stop instead of pre-empting at 69,210.3) — verified.

**Verdict on the CEO's "we should have still been in": NOT achieved for #16896 — partial at best.**
- What the commit DOES fix (proven): (1) the actual kill mechanism — the 15m interior re-drop at 16:50 — is structurally impossible now (CHOP→1h source; adverse→1h raise-only); (2) any 1h-ceiling step before price reaches the armed stop lifts the stop to ≥ former ceiling + buffer (here ≥69,6xx → survives 69,134 max); (3) once the stop sits at structure, hml_threshold widens the guardian to match (verified numerically); (4) future keeper rungs arm with 1h-major anchors from birth.
- What is MISSING: **birth re-anchor.** Seed-only policy (auto_trader.py:457-463) keeps the armed interior stop until the FIRST sh1h step. With a static 1h ceiling through the shakeout window (sh1h 69,583.1 static 15:50→17:20), the trade still dies interior exactly as it did, and the HML widening never binds (stop never ≥0.8 % from entry). To actually deliver "still been in", a managed loss-side trade would need re-anchoring to the 1h major at/before birth (or keeper-level anchors at arm time for orders armed pre-fix — #16896's order predates the keeper change).

Data caveat: exact historical replays cannot be certified — production's own recorded structure values don't exist in current candles.db (keeper note sl15=68,133/atr15=380 vs current-data 68,103/403.7; state sh15=68,819.5 in no current 15m row) → candle rows were rewritten post-hoc. The D conclusion rests on the parts robust to this: sh1h static 69,583.1 across every window ending 15:00–16:00 (corroborated by the 1h ATR oracle), the events-table old-code path, and the 1m price path.

## Findings

| ID | Severity | Finding | Refs |
|----|----------|---------|------|
| F-1 | **MEDIUM** | #16896-class trades still die at the armed interior stop when the 1h ceiling never steps before price arrives: seed-only (no birth re-anchor to 1h major) + HML widening not binding for struct < cap ⇒ CEO's cited outcome not delivered for the cited trade. Commit mechanics are correct; the outcome gap is a missing behavior, not a defect. | auto_trader.py:457-463, :451; position_manager.py:4191-4196; events 16:50:05 |
| F-2 | LOW | Keeper event-log detail strings still label `15m sl/sh {sl15/sh15}` while trig/SL derive from 1h — misleading forensics (the exact confusion class behind this incident); docstring/comment also stale. Order notes themselves are correct. | auto_trader.py:680, :716, :577-584, :651-655 |
| F-3 | LOW | Silent freeze: missing `1h` in structure_detail (structure_summary skips TF <50 candles or on exception) → tweak early-returns with no seed, no lag, **no log**; stop frozen at armed level indefinitely. BTC currently safe (all TFs, 171 1h candles/7d); matters if coin spin-off runs auto_trader. | auto_trader.py:374-375; auto_analysis.py:112-127, :240-244, :260-265 |
| F-4 | LOW (info) | `regime=None`/'UNKNOWN' → 15m (TREND) source. Currently dead-in-practice (UNKNOWN ⇒ no structure_detail ⇒ early return; only producers are build_decision), but a future producer passing regime=None with structure_detail would silently degrade shakeout protection. | auto_trader.py:451; auto_analysis.py:232 |
| F-5 | LOW (pre-existing) | Vol-floor HML block is dead code since the 2026-10-10 clamp: `_hml_vol_floor` clamped ≥ account cap == HARD_MAX_LOSS_PCT, so `if _hml_vol_floor < HARD_MAX_LOSS_PCT` never fires. Unchanged by this commit — cleanup note only. | position_manager.py:4073-4077 |
| F-6 | INFO | trade-watchdog.log tail interleaved with another agent session's interactive SQL Tracebacks (sqlite `?`, PG syntax) — not shipped code; log-hygiene observation. | trade-watchdog.log ~L3147319, ~L3149864 |
| F-7 | INFO (sideways) | candles.db historical rows drifted post-hoc (2 oracles fail vs production-time records) — any postmortem replay from candles.db must validate against events/keeper-note oracles first. | candles.db vs keeper event 15:50:05 + state ts16:50 |

## Uncertainties
- Exact sh1h at production read times is bracketed, not certified (F-7). The death conclusion holds under every non-lookahead variant: no sh1h step between seed (15:50) and the 17:41 cross; the only variant showing an earlier step used the not-yet-closed 17:00–18:00 bar (lookahead — excluded).
- Author's claimed 20/20 suite file not located; substituted three independent suites (87 checks, all green).
- Current-book keeper numbers recomputed at ~19:00; structure moves → re-derive on next cycle (readiness currently suppresses both arms anyway).

## Overall verdict

**PASS with findings — ship stands, one MEDIUM outcome gap.**
All safety-critical mechanics verified adversarially: the widened guardian cap cannot exceed −8 % account, cannot tighten, cannot touch non-managed/wrong-side/absent-stop trades, and fails safe on every bad input; the lag split, migration (zero stop movement), guards, and keeper 1h derivation all behave as specified; scope is exactly the 3 claimed files; regression is green (3 suites, compile, fresh imports, one live run_cycle rc=0, zero shipped-code tracebacks).
**But:** for the exact incident cited (#16896), the fixed system would still have exited at 69,027 — the commit removes the interior re-drop whipsaw and protects once the 1h ceiling steps, yet ships no birth re-anchor, and the HML widening is inert while the stop sits interior. CEO decision: accept (protection arrives with the first 1h step + future 1h-anchored arms) or add a birth re-anchor to the 1h major.
