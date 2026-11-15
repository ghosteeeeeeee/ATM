# bug_hunter verifier — TP gate + lag v3 (commit `c345c11c`)

**Commit:** `c345c11c` "exits: structure-trail owns profits — TP gated + favorable steps always 15m (CEO 2026-11-15)" (2026-11-15 01:15:27 UTC), `git show --stat` = **exactly 2 files** (`scripts/position_manager.py` +15/−1, `scripts/auto_trader.py` +13/−10). Later commit `b8436f9b` touched only `automation/`; `git diff c345c11c -- scripts/` empty → worktree == shipped.
**Verified:** 2026-11-15 01:38–02:45 UTC, adversarial, no fixes applied.
**Harnesses (all /tmp, SELECTs + mocks, zero production writes except ONE task-mandated `run_cycle`):**
`/tmp/bh4_tpgate.py` (19 direct + 3 spy checks, FAILS NONE), `/tmp/bh4_lag.py` (27 checks, FAILS NONE, A/B against HEAD~1 copy at `/tmp/auto_trader_v2_c345.py`), `/tmp/bh4_replay16913.py` (real `_lag_stop` over oracle-calibrated as-of structure × 2 visibility modes + 1m walk), `/tmp/bh4_box.py` (box A/B both branches), AST-extracted guardian matcher, PG SELECTs, `data/candles.db` (ro), `data/tweak_struct_state.json`, `auto_trader.db` events/decisions, log scans.

## Verdict table

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| **A(i)** | 5 author cases rerun+extended: managed TP suppressed LONG+SHORT; managed SL → `manual_sl_hit`; profit-side SL → `manual_trail_hit` (both directions); non-managed TP → `atr_tp_hit` unchanged; + stop-less/missing-TP/wrong-side/ai-trader-auto/SL-precedence | **PASS 19/19** | `/tmp/bh4_tpgate.py` direct |
| **A(ii)** | Every other TP-close path (inventory below): **NO second live at-target path for managed trades** | **PASS** (2 latent couplings: F-5, F-4) | inventory + AST matcher + 0 resting HL orders |
| **A(iii)** | Suppression semantics: `hit=None` → caller loop over `[]` → no close, no crash, no double-count | **PASS** | spy run of real `check_and_manage_positions`: `(1,0,0)` closes `[]`; control non-managed still closes `atr_tp_hit` |
| **A(iv)** | "stop-less managed → TP still closes" | **PASS with premise correction (F-8)** | `structure_governed(sig,None)=False` proven, but `pm:619` already skips stop-less before hit detection (pre-existing, unchanged) — TP never closed stop-less managed trades here |
| **A(v)** | Target stays in DB; no `target=NULL` side effect for managed | **PASS** | diff adds no writes; xmirror NULLer requires `hl_copy` in signal (`trust_tiers.py:94`) = disjoint from managed tags; #16913 closed row keeps target 63111, #16915 keeps 62286; rungs still carry `tp` |
| **B(i)** | 7 lag cases rerun (birth-raise / CHOP-15m step NEW / TREND identical / 1h-only no-move / adverse→1h line / breach / clamps) + migration + freeze | **PASS 27/27** (3 initial FAILs were my expectation bugs, corrected: v2 target uses *prev* sh1h; v2-CHOP blind to 15m-only adverse) | `/tmp/bh4_lag.py` |
| **B(ii)** | `regime` gone from lag path; arity 6 vs both callers | **PASS** | AST: signature `['pid','side','s15','s1h','price','stop']`, exactly 2 calls × 6 args (auto_trader:602,607); body has no `regime_state`/`src_1h` (only prose comment :461); other `regime_state` uses (:853,:997,:1041) = decision/summary/scorecard, not lag |
| **B(iii)** | State format: all-4-keys on seed/record/migration; 3-regime-era 4-key rows load | **PASS** | harness E1/E2; live file rows 16902–16915 all `sh15/sl15/sh1h/sl1h` |
| **B(iv)** | Box-shakeout A/B numbers | **PASS — premise corrected (F-7)** | see box table: 0.5-ATR bounce tags **neither** stop (gap 1.85–2.10 ATR one-swing-behind); UP branch +9.3pp to v3, DOWN branch −19.0pp to v3 |
| **B(v)** | #16913 replay: stepped-stop sequence + exit | **PASS — honest answer: does NOT bank ≥ TP (F-1)** | see replay table; stop tagged **02:12 @63978 → +14.64% @10x** vs actual TP **+31.67%** (−17.0pp), both visibility modes agree |
| **B(vi)** | #16915 projection | **superseded by LIVE outcome** | trade closed during verification — see F-1: TP gated at 01:42–01:46, stopped out **02:30:32 `manual_sl_hit` −24.5108% @10x** |
| **C** | 3 `structure_governed` sites, scope at each, no N-1, current G-list | **PASS** | sites `pm:642` (`pos.get`+`sl`:614 ✓), `pm:3963` (`_pos_signal` assigned loop-top `:3204` + `is_linreg_fade_pos` `:3206` ✓ — N-1 fixed by 39bce62e), `pm:3984` (re-assign `:3978` ✓); G-list below |
| **D** | Regression | **PASS** | suite **20/20 rc=0**; `py_compile` 245 scripts OK (1 pre-existing broken debug file, F-10); fresh imports OK; **ONE live `run_cycle` rc=0, stderr empty**: `decision=BRACKET, scores {long:0, short:-40, regime:CHOP}, price 64781.16, tweaks=[], shadow_armed=[], live_armed=[], armed_detail=[], hypo=0, stats n=58 wr=44.8 pnl=+$0.775`; book **FLAT** (BTC NOT open — #16915 closed 02:30); 33 armed rungs (shorts 59940→73940, longs 65041→75630, HYPE 70.6; lev 5/10, $11.1/$22.2); prices.json age 20s BTC 64791.5; `pipeline.log` **0 Tracebacks**; watchdog 8 Tracebacks all `<stdin>`/heredoc agent SQL (F-6, named not counted) |
| **E** | Scope = exactly 2 files; constants/mxm/skills untouched; skill doc staleness | **PASS + F-9 (doc staleness)** | `git show --stat` 2 files; worktree clean for hermes_constants/mxm/skills; skill texts still describe TP-as-exit |

## A(ii) — TP-path inventory (who can close a managed trade AT ITS TARGET)

| Path | Location | Verdict |
|------|----------|---------|
| **1. `check_atr_tp_sl_hits` → `atr_tp_hit` → `manual_tp_hit`** | `pm:627/632` → gate `pm:642-654` → caller `pm:3655-3662` | **GATED (the change)** — single caller, closes only what the list returns |
| 2. Guardian `_check_hard_stops` `hard_tp` → relabel `manual_tp_hit` | `hl-sync-guardian.py:2075-2087` (skip), `:2110` (relabel), `:2196` (close) | **SKIPPED for managed** — `is_rr_engine` from AST-extracted real matcher: all live managed shapes (`ai-trader-pending/manual/auto/±/compound`) → `rr_engine` → `if not is_rr_engine` false → never sets `hard_tp`. Historical: trades **16075/16078 (`ai-trader-manual`, `hard_tp`, 2026-10-12)** fired BEFORE the config key landed (`979e9643` 2026-10-12) → path was live then, closed since |
| 3. RR engine `TAKE_PROFIT` | `pm:3552` (`not is_ceo_trade`), close `pm:3581` | **excluded for managed** ✓ (non-managed at-target = allowed, out of scope) |
| 4. ride_it EXIT / pump_exit / sl-zone tighten / MFE / soft-trail | `pm:3522/3344/3299/4594/4023` | all `not is_ceo_trade` ✓ |
| 5. mxm TP authority | `manual_exit_manager.py` (whole file, 290 lines) | **NO close anywhere** — `decide_sl`/`update_trail` only write `stop_loss`; labels applied by pm/guardian |
| 6. Exchange-side TP trigger orders | `hyperliquid_exchange.place_tp/replace_tp/place_tp_sl_batch` | **zero live callers** (only commented-out refs: `cascade_flip.py:457`, `pump_hunter.py:663`; `reconcile_tp_sl` disabled `hl-sync-guardian.py:4410`; `_place_or_replace_tp` never called); **live `open_orders` = 0** → no resting TP |
| 7. `tpTriggerPx`/`take_profit` fields in scripts | grep | **none** (only order-construction `triggerPx` inside uncalled `place_tp`) |
| 8. hl_fill_monitor `trader_exit` | `hl_fill_monitor.py:648` | copy-trader trades only, not target-based |
| 9. Other pm closes (wave_turn/MACD/cut_loser/HML/maxhold/stale/UGB-PT/TAT/weather) | see G-list | **not at-target** (clocks, stops, capital) |

**Conclusion: no second live at-target path.** Two latent couplings recorded (F-4 dead relabel, F-5 config-coupled guardian skip).

## B(v) — #16913 stepped-stop replay (v3 lag + TP-gate)

Oracle calibration: as-of `ts<=T, is_closed=now` reproduces the production state row at 22:20:27 **4/4** (sh15 64896.01 / sl15 63326.43 / sh1h 64981.44 / sl1h 63944.0). F-7 caveat: state-*tags* mismatch production (prod `EXPANSION` vs computed `DOWNTREND`), and the v2 reconstruction steps at 00:20 where production events show **zero** steps → replay is **bracketed**; both visibility modes (A = forming-inclusive, B = bar-end) reported, they agree on the exit.

| cycle | sh15 / atr15 (mode A) | direction | stop after | note |
|-------|----------------------|-----------|-----------|------|
| 22:20 | 64896.01 / 538.1 | birth | **66265.056** | production re-anchor (oracle; anomalous — F-2) |
| 22:50 | 64320.00 / 590.3 | FAVORABLE | **64955.04** | −1310 |
| 23:20 | 63926.88 / 616.5 | FAVORABLE | **64381.65** | −573 |
| 23:50 | 63966.01 / 646.8 | ADVERSE | **65058.98** | +677 loosened to 1h line (64981.44+0.1·775.4) |
| 00:20 | 64574.27 / 662.2 | ADVERSE (line ≤ stop+1) | 65058.98 | no move |
| 00:50 | 64544.37 / 621.3 | FAVORABLE | **64636.40** | −422 |
| 01:20 | 63918.82 / 642.4 | FAVORABLE | **64608.61** | −28 |
| *01:04* | *TP 63111 crossed* | *gated* | — | *suppressed (price 62931.5 at hit time)* |
| 01:50 | 63066.15 / 595.9 | FAVORABLE | **63978.41** | −630 |
| 02:20 (proj) | 64154.01 / 696.5 | ADVERSE (line ≤ stop+1) | 63978.41 | no move |

- **Exit: stop tagged 02:12 @63978.41 → +14.64% @10x** (mode B: 63979.18 → +14.63%). Gate-OFF control on the same trail: TP at 01:02 (+28.0% at TP price; actual fill +31.67%).
- **Max unrealized +45.02% @01:45** (low 62106) — never banked.
- **HONEST ANSWER: v3 does NOT bank ≥ the TP on #16913 — it gives back 17.0pp** (−17.0pp vs +31.67%). Production v2 (old): zero steps after 22:20 (events table) = the pinned-stop incident confirmed.
- Caveat: unmodeled pre-structure clocks (wave_turn has no CEO gate) could exit earlier in the counterfactual; stop/TP paths modeled exactly.

## B(iv) — box-shakeout A/B (same path, both versions, own state each)

| event | v3 (favorable=15m) | v2 (favorable=1h in CHOP) |
|-------|--------------------|---------------------------|
| cycle A: LH 69500→69000, px 68700 | stop 69680 → **69540** | **69680 unchanged** |
| cycle B: LH 69000→68700, px 68300 | → **69040** | 69680 |
| cycle C: LH 68700→68300 | → **68740** | 69680 |
| cycle D: LH 68300→68100 | → **68340** | 69680 |
| gap-to-tag after A/B | 840 / 740 pts = **2.10 / 1.85 ATR** | 980 / 1380 pts = 2.45 / 3.45 ATR |
| **0.5-ATR bounce (200 pts)** | tags **neither** stop — task premise corrected: one-swing-behind puts the stop at prev-swing-high+0.1 ATR, so only a break of the *previous* 15m swing (a real structure break) tags it | same |
| **Branch UP** (ceiling retest/break) | exit 69040 = **+0.87% @10x** | exit 69680 = **−8.39% @10x** → **+9.3pp to v3** |
| **Branch DOWN** (floor break to 66800 then reclaim) | TP 67030 suppressed; trail steps → reclaim tags 68340 = **+11.00% @10x** | TP cuts 67030 = **+29.96% @10x** → **−19.0pp to v3** |

Intended tradeoff per CEO priority: UP/shakeout side yes (+9.3pp, structure-break exit in profit); the down-ride side pays −19pp to the disaster-TP — same class as F-1.

## B(vi) — #16915: actual live outcome (supersedes projection)

| t (UTC) | event | stop |
|---------|-------|------|
| 01:05:15 | open SHORT 62911 (rung armed 21:50, trig 64014) | 64265 |
| 01:20:28 | birth re-anchor (v2, unchanged) — reproducible: sh1h 64981.44 + 0.1·775.4 | 65058.98 (**loosened +794**) |
| 01:42–01:46 | **TP 62286 crossed — six 1m closes ≤62286 (low 62006); PM ran every minute, "1 open \| 0 closed" → GATE SUPPRESSED** (live proof; only two `[ATR HIT]` lines in the window: 01:04 pre-commit TP, 02:30 SL) | 65058.98 |
| 01:50:27 | FAVORABLE 15m step (64430.5 + 0.1·590.7) | **64489.57** |
| 02:20:29 | FAVORABLE step raw ≈63933 → clamp `price*1.001` (pos px 64344.5) | **64408.8445** |
| 02:30:32 | stop tagged → `manual_sl_hit` −24.5108% @10x (guardian `HARD-MANUAL_SL_HIT` 02:30:24 + pm `[ATR HIT]` 02:30:32) | — |

Ungated counterfactual: TP ≈ **+9.94% @10x** (fill 62286; the 62006 low worth +12.8%). **Gate swing ≈ −34.5pp.** State now: sh15 63809.08 / sl15 62006 / sh1h 64574.27 / sl1h 62006.

## C — current pre-structure exit list (post-`c345c11c`)

Gated this round (removed from the list): **`stale_exit`** `pm:3963` (gated; N-1 read-before-assign fixed by hoist to `:3204`), **`UNIVERSAL_MAX_HOLD`** `pm:3984`, **TP `manual_tp_hit`/`atr_tp_hit`** `pm:642` (this commit — third gated clock). Still open:

1. **Guardian CUT_LOSER −3.0% price, non-BTC only** — `hl-sync-guardian.py:286` (const), `:1919-1924` (fire), BTC exempt `:1921-1924` — carried MEDIUM.
2. **Weather-vane shield 30-min force-close** — `pm:3064-3071` (`WEATHER_VANE_SHIELD_MAX_HOLD`); needs suppression + LOSING_ONLY + age; **no structure_governed / is_ceo_trade gate** — carried.
3. **`wave_turn`** z±1.5 + accel — `pm:3690`; no `is_ceo_trade` gate — carried LOW (skill `manual-trade-override:157` still lists it as OPEN ITEM).
4. **MACD `should_exit`** — `pm:3721+`/close ~`:3815`; token gate `pm:285` {TRB,IMX,SOPH,SCR} → **BTC N/A** — carried LOW.
5. **`should_cut_loser` priority-3** −4/lev % price, latent (0/74) — `pm:551` area — carried LOW.
6. **`ugb_pt` giveback ≥+0.40% from peak** — `pm:~4565` — profit-side protection — carried LOW.
7. **Capital/structural (non-loss) closes** — guardian stale-rotation `:2227`, MAX_POSITIONS `:2821`, NOT_HOTSET `:2858`, HL_CLOSED mirror `:3041` — carried INFO.

Verified NOT applicable: cascade flips disabled (`hermes_constants.py:591/597`); TAT matches only bb-squeeze/pump-chain/bb-bounce/`ai-trader+` (never `-pending`/`-manual`, `pm:4276/4314`); PM-trail bypass uses `signal LIKE '%ai-trader%'` → covers all managed (`profit_monster.py:89`, list `hermes_constants.py:2273-2275`) and **0/31** PM-trail closes were managed in 7d; HML = stop twin (gated); mxm/lag move stops only.

## Findings

| ID | Severity | Finding | Location |
|----|----------|---------|----------|
| **F-1** | **HIGH (behavioral, doctrine-as-built)** | **The gated TP has already cost real money on both incident trades.** #16915 LIVE: TP crossed 01:42–01:46 (six 1m closes ≤62286, low 62006, PM evaluating every minute → suppressed), then round-trip to the structure stop → **−24.5108% @10x** vs ungated **+9.94%** (≈**−34.5pp**). #16913 REPLAY (both F-7 modes): stepped stops 66265→64955→64382→(adverse +677)→65059→64636→64609→63978, TP suppressed at 01:04, tagged **02:12 @63978 → +14.64% @10x** vs actual **+31.67%** (≈**−17.0pp**); max unrealized +45.02% never banked. Mechanism: one-swing-behind steps lag price 600–900pt in straight-line moves, 30-min watchdog cadence, adverse branch *loosens* to the 1h line (23:50: +677), clamp floor `price*1.001` pins the stop just above price — **nothing banks profit when price crosses the target and reverses**. This IS the shipped CEO doctrine; the finding is the quantified cost (−17pp / −34.5pp in the first two instances) — CEO decision point before more live victims. | `position_manager.py:642-654`; `auto_trader.py:430-577` |
| **F-2** | MEDIUM (pre-existing, sideways) | **#16913's 66265.056 pin is arithmetically unreproducible** — birth `line = sh1h + 0.1·atr1h` with the *state-recorded* sh1h 64981.44 ⇒ atr1h = **12836** (17× realistic); or clamp `price*1.001` ⇒ pos price **66200.855** (a price BTC last traded ~13:00, 9h stale) while decision price = 63869 and DB `current_price` at 22:24:35 = **64227.5**. No candles.db reconstruction yields it (best 65051–65057). The stop sat **1214pt above the 1h structure line** — the incident has TWO causes: this anomalous re-anchor (F-1 birth re-anchor, commit `202f7b5`, untouched by c345c11c) + the no-step half (fixed by v3). | `auto_trader.py:470-505` (birth), evidence `auto_trader.db` events 22:20:27 |
| **F-3** | LOW (doc, shipped code) | Lag docstrings/comments still describe the **removed regime split**: `_lag_stop` docstring "REGIME/MAJOR split … 1h in CHOP" (`auto_trader.py:431-446`) and `:371` "favorable steps when regime=CHOP" are now false; `structure_governed` docstring says "**BOTH** non-structure exit clocks" (`position_manager.py:191`) — now **three** (TP added). | `auto_trader.py:371,431-446`; `position_manager.py:191` |
| **F-4** | LOW (dead code / fail-open note) | The F-3 wrong-side-TP relabel `elif hit=='atr_tp_hit'` → `_tp_loss` (`pm:655-668`) is **unreachable for ALL managed trades**: inside the managed branch `sl` is guaranteed truthy (`pm:619`) and signal truthy ⇒ `structure_governed`=True ⇒ the gate at :642 always fires first. Guardian's `hard_tp→manual_tp_hit` relabel (`hl-sync-guardian.py:2110`) likewise unreachable for managed (rr skip). Consequence: `manual_tp_hit` now has **no live producer** for stop-bearing managed trades; wrong-side-TP artifacts can no longer book a loss via TP (target fully inert) — acceptable under doctrine; branch survives only as fallback when `structure_governed` import fails (fail-open to old relabel). | `position_manager.py:642,655-668`; `hl-sync-guardian.py:2110` |
| **F-5** | LOW (latent coupling) | Guardian's TP skip is **config-coupled, not doctrine-coupled**: it keys off `SIGNAL_EXIT_CONFIG` prefix → `rr_engine` (`hl-sync-guardian.py:2065-2087`, keys `hermes_constants.py:2319-2322`), while the pm gate keys off `is_managed_signal`+stop. All current managed shapes match (AST-verified), but the keys were only added `979e9643` 2026-10-12 — before that, trades 16075/16078 closed `hard_tp` as `ai-trader-manual`. Re-scoping those keys would reopen a guardian at-target path that bypasses the pm gate. | `hl-sync-guardian.py:2074-2087`; `hermes_constants.py:2317-2322` |
| **F-6** | LOW | Favorable step has **no never-loosen guard**: `target = prev_sh ± 0.1·atr` + clamps, but no comparison against the current stop (adverse branch has `t2 > stop+1`, favorable doesn't) → a favorable step whose target exceeds the stop **raises (loosens)** it. Reachable when another actor tightened the stop without the lag state knowing (mxm coexistence admitted at `auto_trader.py:584-586`) or with a stale state row; also seen live: #16915 02:20:29 raw target ≈63933 was lifted by the `price*1.001` clamp to 64408.84 (net tighten only because price had run above the raw target). | `auto_trader.py:541-557` |
| **F-7** | INFO (task-premise correction) | "Box prints a 15m LH, price bounces ~0.5 ATR → stop tightens then gets tagged" does **not** happen at 0.5 ATR: one-swing-behind leaves a **1.85–2.10 ATR** gap at step time (tag requires a break of the *previous* 15m swing high +0.1 ATR = a real structure break). Real tradeoff (both branches) in the box table: **+9.3pp UP / −19.0pp DOWN** for v3. | `/tmp/bh4_box.py` output |
| **F-8** | INFO (task-premise correction) | "Managed + stop-less → TP still closes" is unreachable: `pm:619` `if not sl or not tp: continue` skips stop-less positions **before** hit detection (pre-existing, unchanged by the commit); guardian's SELECT also requires `stop_loss>0` (`hl-sync-guardian.py:2017`). `structure_governed(sig,None)=False` holds as a unit predicate but is moot at this call site. Stop-less managed trades get no TP/SL close from these engines (other clocks unchanged — zombie protection intact). | `position_manager.py:619,642` |
| **F-9** | LOW (doc staleness, report-only per task) | Skill texts still describe TP-as-exit for structural CEO trades: `skills/shared/manual-trade-override/SKILL.md:155` ("`manual_tp_hit` — your predefined target hit") and `:342-346` ("a TP … is a DISASTER circuit breaker set at ≥3·ATR1h depth" — now validation-only, never closes); `skills/shared/full-analysis/SKILL.md:112` same label contract. Not fixed (adversarial pass). | see lines |
| **F-10** | INFO (sideways) | `scripts/tpsl_utils_debug.py` fails `py_compile` (line 561, pre-existing, not in diff, **not imported** by pipeline/scripts) — dead debug file, cleanup candidate. | `scripts/tpsl_utils_debug.py:561` |
| **N-1 closed** | — | Prior round's HIGH (`_pos_signal` read-before-assign at the stale gate) is **fixed**: assigned at loop top `pm:3204` (N-1 note `:3198-3203`), stale gate `:3963` reads it; maxhold re-assigns `:3978`; TP site uses `pos.get` + `sl:614` — **no read-before-assign at any of the 3 sites** (spy matrix from that round now green by inspection + this round's spy run). | `position_manager.py:3204,3963,3978,3984` |

Closed as claimed: TP gate 5/5+ (A(i), A(iii)), lag v3 7 cases + migration/freeze/clamps (B(i) 27/27), regime removal AST-clean (B(ii)), 4-key state (B(iii)), suite 20/20, py_compile, fresh imports, ONE live `run_cycle` rc=0, 0 shipped-code Tracebacks, scope exactly 2 files, worktree==shipped.

## Overall verdict

**PASS on implementation — every mechanical claim of the commit verifies (gate single-path & correct, suppression semantics safe, lag v3 exactly as specified, regime fully removed, 3 gated clocks properly scoped, regression clean, scope exact) — WITH ONE HIGH BEHAVIORAL FINDING (F-1): the doctrine as shipped has already lost −34.5pp live (#16915: TP crossed at 62286 = +9.94% @10x ungated → gated → −24.51% stop-out) and −17.0pp in replay (#16913: +31.67% → +14.64%), because the structure trail lags too slow/loose to bank what the TP crossed. F-2 (the 66265 anomaly) is a pre-existing re-anchor defect the commit did not touch. Recommend CEO review of F-1's numbers before the next structural trade; no code defect blocks this commit.**
