# bug_hunter verifier — stale_exit structure-gate closure (commit `99cffce6`)

**Commit:** `99cffce68cc581d2792787660bbb4aa403f81eea` — "verifier 0090d750 closures: stale_exit structure-gate (F-2) + 5 stale doc sites (F-4/F-5)" (2026-11-14 17:29 UTC). `git log -1 --name-status` = **exactly 4 files** (F check).
**Closes findings from:** `brain/verdicts/bug-hunter-hml-floor-retire-2026-11-14.md` (F-2 / F-4 / F-5).
**Verified:** 2026-11-14 17:40–18:10 UTC, adversarial, no fixes applied.
**Harnesses (all /tmp, SELECT + mocks, zero production writes except ONE task-mandated `run_cycle`):**
`/tmp/bh_stale_gate.py` (17-case spy matrix on the real `check_and_manage_positions()`), `/tmp/bh_struct_gov.py` (11/11), `/tmp/bh_hml_floor.py` (34/34, C-section re-pointed at the new signature in /tmp only), AST diff vs `HEAD~1`, PG SELECTs (brain), `data/candles.db` (1m, ro), `data/pending_orders*.json`, log scans.

## Verdict table

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| **A(i)** | Gate trace: `pos` in scope (loop var, `:3158`), `is_linreg_fade_pos` assigned `:3183`, `stale_close` `:3930`; evaluation order is left-to-right short-circuit (`stale_close and not is_linreg_fade_pos and not structure_governed(...)`) so `_pos_signal` is only touched when a non-linreg stale fires; `continue` still follows at `:3946`. **BUT `_pos_signal` is first ASSIGNED at `:3954` — 15 lines AFTER the gate at `:3939`** (grep `_pos_signal`: first hit 3939 = use, 3954 = assign) | **FAIL — N-1 (HIGH)** | grep + AST; spy run below |
| **A(ii)** | Spy matrix (17 cases, real function, `close_paper_position`/`check_stale_position`/`refresh_current_prices`/`_persist_*` mocked): managed+stop→NO close **= crash or wrong-close**; managed w/o stop→CLOSES **= crash when first**; non-managed pump/jup→CLOSES **= crash when first, wrongly BLOCKED when preceded by a managed trade**; linreg-fade→exempt ✓ | **FAIL (3 of 4 sub-claims)** | table below |
| **A(iii)** | Both stale branches reach the same gate: real `check_stale_position` returns `(True,'stalled_loser_…')` at −1.5%/9min and `(True,'stalled_winner_…')` at +1.5%/125min → `stale_close` is the single flag for both, so the gate must block both; **spy shows the winner branch ALSO stale-closes a managed trade** (`winner_managed_second`) and also crashes when first (`winner_managed_first`) | **FAIL** | `/tmp/bh_struct_gov.py` + spy |
| **A(iv)** | `check_stale_position` untouched: `ast.dump` of the function **byte-identical** to `HEAD~1` | **PASS** | AST compare |
| **A(v)** | Single caller `pm:3930`; single `stale_exit` fire site `pm:3943` (repo grep, excl. graphify/logs); `shadow_trader.py:931 _simulate_speed_stale` is shadow-simulation only, no live close | **PASS** | grep |
| **B** | `maxhold_exempt` repo-wide (excl `.git`/graphify): **only** `brain/verdicts/bug-hunter-hml-floor-retire-2026-11-14.md` (history) — zero in scripts/analysis/skills/brain/config; `structure_governed` **defined once** (`:190`) and called at **exactly 2 sites** (`:3939` stale gate, `:3960` maxhold gate); body byte-identical to `maxhold_exempt` (trailing-newline artifact only); `from position_manager import maxhold_exempt` → ImportError; `analysis/test_manual_exit_manager.py` references neither name | **PASS (6/6 cases green)** | grep + `/tmp/bh_struct_gov.py` 11/11 |
| **C** | `hml_threshold` now 6 params, **exactly one caller** (`pm:4230`, 6 positional args, no `floor_acct`); no other import/call anywhere; AST diff vs `HEAD~1` = **args + docstring only, executable body identical**; sweep grid old==new (`/tmp/bh_hml_floor.py` **34/34** after /tmp-only C re-point: `floor_acct` absent from signature, docstring records retirement) | **PASS** | AST + harness |
| **D** | `HML_STRUCT_FLOOR_ACCT` = **only** `hermes_constants.py:821` (def + RETIRED comment); `floor_acct` = only a historical echo in `logs/trade-watchdog.log:3222117` (not code); `python3 -c "import position_manager"` fresh OK; no live-floor claim left in `scripts/*.py` or either SKILL.md (only history/retirement wording); both skill texts internally consistent; pm docstring dates/numbers check out: floor **added `114711f4` 2026-11-13 18:29** ("(13th: floor added…)" ✓), retired `555b4738` 2026-11-14 16:25 ✓, #16896 entry 68661 → base −0.80% = **69,210** ✓, stop 68,953.9 ✓, #16909 stop **2.4258%** from fill ✓ | **PASS (F-4/F-5 closed)** | git log -S + PG SELECT + grep |
| **E** | Suite **20/20 rc=0**; `py_compile` OK; fresh `from position_manager import structure_governed, hml_threshold` OK (old name gone); harnesses 34/34 + 11/11 + 17-case matrix; **ONE live `run_cycle`** (`python3 scripts/auto_trader.py`) **rc=0, stderr empty**: `enabled=true, mode=live, decision=BRACKET, scores {long:0, short:10, regime:CHOP}, price 66050.17, shadow_armed=[], live_armed=[], tweaks=[], armed_detail=[], hypotheticals=0, stats n=58 wr=44.8 pnl=+$0.775`; book before **and** after = **0 open trades (BTC flat)**; last close #16911 SOL 17:57 `profit-monster-trail` +$0.11, no new BTC close since #16909 15:44; unfired rungs = **12 (11 BTC + HYPE)** incl. **short 65007 lev10 SL65320 armed, state ABSENT = unfired**, long 66933 lev10 SL66607, 67089/67583/68557/69560/70060 lev10, 72560/74840/75396/75630 lev5; price path since 17:14 (1m): low **65090.0**, high **66189.9**, last 65839 @17:59 (run_cycle read 66050 @18:01) → **never crossed 65007 or 66933 → no next break** (16:49 low 65000.0 = the pre-17:14 F-9 wick, rung still unfired); `pipeline.log` **0 Tracebacks**, `trade-watchdog.log` 6 after L3242618 — all `<stdin>`/`/tmp/opencode/wd_q.py` SQL/heredoc = known F-6-class noise, named not counted; **zero** `UnboundLocalError` in any log (bug not yet reached in production: book flat) | **PASS (with the caveat that the shipped gate is unproven-in-prod because it has not fired yet)** | run + PG + logs |
| **F** | Scope: `git log -1 --name-status` = 4 files only; `git diff HEAD~1 HEAD -- scripts/trade_watchdog.py scripts/auto_trader.py scripts/manual_exit_manager.py` = **empty**; `hermes_constants.py` numstat 1+/1− = **only line 821**, value token byte-identical `HML_STRUCT_FLOOR_ACCT = -8.0` (verified `repr` = `-8.0`, `CUT_LOSER_PNL` = `-4.0`); worktree code == shipped code for all 4 files | **PASS** | git |
| **G** | See enumeration below — **F-2 is NOT gone from the list** (gate non-functional); F-1 unchanged; nothing else new | **FAIL** | see below |

### A(ii) spy matrix — 17 cases (`/tmp/bh_stale_gate.py`, one process per case)

| Case (stale_close mocked True) | Author claim | Actual |
|---|---|---|
| managed+stop, 1st position (loser `-1%/8m`) | NO close | **`UnboundLocalError: cannot access local variable '_pos_signal'`** at `pm:3939` → whole manage cycle dies |
| managed+stop, 1st position (winner `+1.5%/125m`) | NO close | **same UnboundLocalError** |
| managed+stop, 2nd position (prev = non-managed) | NO close | **`stale_exit` FIRED** — gate read the *previous* position's signal (`pump-chain` → not governed) |
| managed+stop, 2nd position (winner branch) | NO close | **`stale_exit` FIRED** (`stalled_winner_pnl+1.5%…`) |
| managed **without** stop, 1st | CLOSES | **UnboundLocalError** (no close) |
| managed without stop, 2nd | CLOSES | closes ✓ (only because the leaked signal was non-managed; the `stop_loss` arg *is* current) |
| non-managed `pump-chain`, 1st | CLOSES | **UnboundLocalError** |
| non-managed `jup_yolo`, 1st | CLOSES | **UnboundLocalError** |
| non-managed after a managed trade (pnl isolated at −0.2 so HML can't mask it) | CLOSES | **0 closes — wrongly BLOCKED** (leaked `ai-trader-manual` + current stop → `structure_governed` True) |
| linreg-fade, 1st | still exempt | **✓ exempt** (short-circuits before `_pos_signal` — the only sub-claim that holds) |
| + 6 more mixed/iso variants | — | same two failure modes, see run log |

Root cause in one line: **`_pos_signal` is a function-local assigned at `pm:3954`; the new gate at `pm:3939` reads it first.** On the first position reached in a cycle → `UnboundLocalError` (escapes `check_and_manage_positions`; `main()` at `:5140` logs + re-raises → `position_manager` exits 1, so **the entire exit loop for every other position is skipped that cycle**). On later positions → the previous iteration's signal leaks in, so the gate is wrong **in both directions**.

## G — every exit that can still close a managed structural trade BEFORE its stop (post-commit)

1. **`stale_exit`** `pm:3939` (loser −1.0% + 8min, winner +0.6% + 120min, `hermes_constants.py:584-587`) — **F-2 STILL OPEN**: the gate exists but reads `_pos_signal` before assignment → crash-first / wrong-signal-after (N-1). Both branches affected.
2. **Guardian CUT_LOSER −3.0% price**, non-BTC only — `hl_sync_guardian.py:286` (const), `:1919-1924` (fire), **BTC exempt `:1921-1924`** — **F-1 unchanged, untouched by this commit** (file not in diff).
3. **Weather-vane shield 30-min force-close** `pm:3046-3054` (`WEATHER_VANE_SHIELD_MAX_HOLD`) — F-6 unchanged (currently gated off by `WEATHER_VANE_SHIELD_ENABLED`/window, `:2993`).
4. **`wave_turn`** z±1.5 + accel `pm:3663-3667` — F-7 unchanged, still no `is_ceo_trade` gate.
5. **MACD `should_exit`** `pm:3701` (token gate `:282` {TRB,IMX,SOPH,SCR}) / close `:3815` — F-8 unchanged (`elif` still runs with `CASCADE_FLIP_ENABLED=False`).
6. **`should_cut_loser` priority-3** −4/lev % price when `sl_distance`/`sl_group` absent — `pm:551` (latent, 0/74) — F-3 unchanged; priority-2 units mismatch `pm:534-543` still inert.
7. **`ugb_pt` giveback ≥+0.40% from peak** `pm:4538` — pre-existing profit protection (can close in small loss after a favourable excursion).
8. *Not exits / stop movers:* ATR+manual stop `pm:3632`/`check_atr_tp_sl_hits` (this IS the stop), HML twin `pm:4230` (never leads the stop — 900-cell proof), `UNIVERSAL_MAX_HOLD` `pm:3972` (gated by `structure_governed` `:3960` ✓), mxm trail + structure-lag (move the stop only), kill switch / blocklist sweep (not loss-based).
9. **NEW this commit:** none of the above, plus **N-1** — the gate itself (crash path + cross-iteration signal leak). Nothing else appeared.

## Findings

| ID | Severity | Finding | Location |
|---|---|---|---|
| **N-1** | **HIGH** | **The F-2 gate is non-functional: `_pos_signal` is read before its first assignment.** (a) First position to reach the gate with `stale_close=True` (and not linreg) raises `UnboundLocalError`, which escapes `check_and_manage_positions` → `main()` re-raises → `position_manager` exits 1 and **no exits at all run for that cycle** (stop checks included). (b) On any later position the previous iteration's signal is used, so a **managed structural trade with a stop IS still stale-closed** when the previous position was non-managed (F-2 open, both branches), and a **non-managed trade is wrongly skipped** when the previous one was managed+stop. Fix would be one line: move `_pos_signal = str(pos.get('signal','') or '')` to the loop top (next to `is_linreg_fade_pos`, `:3178-3183`). Not applied (adversarial pass). | `scripts/position_manager.py:3939` (assign at `:3954`, loop top `:3158`, `main` `:5140`) |
| **F-2** | MEDIUM (carried, **not closed**) | stale_exit can still close a managed structural trade before its stop — proven for both the −1%/8min loser branch and the +0.6%/120min winner branch (spy: `iso_managed_stop_second`, `winner_managed_second`). The commit message's "F-2 MEDIUM (closed)" claim is not true as shipped. | `scripts/position_manager.py:3939` |
| **N-2** | LOW (doc) | `structure_governed` docstring still describes only the maxhold job ("so the 8h UNIVERSAL_MAX_HOLD clock must not cut it") and asserts "staleness checks still run" — after this commit the stale close is *skipped* for managed+stop trades, so that sentence is now misleading; the second gate is undocumented. | `scripts/position_manager.py:191-199` |
| **N-3** | LOW (process) | Prior round's verdict `brain/verdicts/bug-hunter-hml-floor-retire-2026-11-14.md` is **untracked** (`git status` `??`); AGENTS.md mandates committing verdicts. | `brain/verdicts/` |
| **F-1** | MEDIUM (deferred, unchanged) | guardian CUT_LOSER −3.0% price binds non-BTC managed stops >3.0%; BTC exempt. Explicitly deferred by the commit; confirmed byte-unchanged. | `hl_sync_guardian.py:286`, `:1919-1924` |
| **F-3…F-8** | LOW (unchanged) | cut_loser prio-3 units/latent, weather-vane 30min, wave_turn, MACD elif, — all pre-existing, none touched. | see G list |
| **N-4** | INFO (task premise) | The brief's "stale-WINNER **+1%/30min**" is not what the code does: winner = **+0.6% / 120min** (`hermes_constants.py:584,586`), loser = −1.0% / 8min (`:585,587`). Gate coverage conclusion is unaffected (both return the same `stale_close`). | `hermes_constants.py:584-587` |

Closed as claimed: **F-4** (docstring, call-site comment, constants RETIRED comment, both SKILL.md texts, dead `floor_acct` param) and **F-5** (`1.58%` → `2.43% from the fill`) — all verified, plus zero live `HML_STRUCT_FLOOR_ACCT`/`floor_acct` references and a byte-identical `-8.0`.

## Overall verdict

**FAIL — F-2 is not closed; the commit ships a broken safety gate (N-1 HIGH).**

Proven green: rename completeness (6/6 + 2 call sites + zero old-name residue), `hml_threshold` param removal with **byte-identical behavior** (AST body equal, 34/34 sweep), F-4/F-5 doc closure (all 5 sites + wrong-number fix, dates/numbers cross-checked against `114711f4`/`555b4738`/PG), scope exactly 4 files with constants value untouched, regression clean (20/20, py_compile, fresh imports, ONE live `run_cycle` rc=0, 0 Tracebacks from shipped code, book flat, 12 unfired rungs incl. 65007 lev10 still armed and unfired, no break since 17:14).

Not proven: the headline safety claim. The gate at `pm:3939` reads `_pos_signal` before its first assignment (`:3954`), so it **crashes the manage cycle on the first stale position and mis-gates every later one** — a managed trade with a stop still gets `stale_exit`d (both branches), and a non-managed trade can be wrongly protected. One-line fix (hoist the `_pos_signal` assignment to the loop top) + rerun of this matrix is what a follow-up round needs; nothing else in the commit should change.
