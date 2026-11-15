# bug_hunter verifier — BE-cap (6d6a2138) + F-6/docs (dcae3611)

**Commits under review:** `6d6a2138` "lag: breakeven-cap in profit (BE-lock) — #16915's pummel root-caused" + `dcae3611` "verifier bf763207 closures: F-6 tighten-only guard + F-3/F-4/F-9 docs".
**Verified:** 2026-11-15 03:30–04:45 UTC, adversarial, no fixes applied.
**Harnesses (all /tmp, SELECTs + mocks, zero production writes except ONE task-sanctioned `run_cycle`):**
`/tmp/bh5_contract.py` (35 checks, 0 FAIL — drives REAL `tweak_structure_fixed` HEAD vs `c345c11c` copy A/B), `/tmp/bh5_replay.py` (F-7 oracle validation + both trades, 3-way, rc=0), `/tmp/bh4_tpgate.py` (22 checks FAILS NONE — managed-TP spy re-run post-doc-edits), `/tmp/bh4_lag.py` (23/27 — 4 stale expectations, see F-6r), `/tmp/bh4_box.py` (OK), PG SELECTs, `data/candles.db` (ro), archived `pipeline.log.20261115000915.gz`, `auto_trader.db` events/decisions, `data/tweak_struct_state.json`.

## Verdict table

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| **A(i)** | BE-cap 7-case contract: birth BE-lock (S+L), in-profit adverse capped, underwater byte-identical vs `c345c11c`, breach-first, trail-below-BE continues, CAS-miss retry, + F-6/BE interplay | **PASS 35/35** | `/tmp/bh5_contract.py` A1–A11, A-iv, P1 |
| **A(ii)** | entry plumbing: `pos.get('entry_price')` exists (get_open_btc SELECT :44-48), call sites `float(pos.get('entry_price') or 0)` (:616 gate, :638/:644 args) → Decimal never reaches `_be`; real Decimal pos (entry/stop/target/price) through REAL tweak → **no exception, correct BE-lock**; entry=0/None → gated/no-SQL or byte-identical `_be=0`; run_cycle try/except backstop :921-922 | **PASS** | A16/A16b/A17/A17b/A18; PG entries 16913=64929, 16915=62911, 16918=64712 all real (pnl math matches) |
| **A(iii)** | LONG mirror: birth BE-lock raises sub-BE stop to entry×0.999 (63000→63936); adverse floor-capped at `_be`; favorable never targets below BE (raw 62846 → capped UP to 63936, F-6 then allows the tighten) | **PASS** | A2/A8/A9 |
| **A(iv)** | F-6 × BE interplay: cap is ceiling (S)/floor (L), F-6 blocks only the loosening side; **target==stop after cap → `abs<=1` → record-only, NO write** (proven); adverse raise-to-BE (≤BE) allowed per doctrine; no disagreement path found | **PASS** | A6b/A10/A-iv/B1-B5 |
| **A(v)** | Money replays, all mechanisms (TP-gate+v3+BE-cap+F-6), oracle candles | **PASS — see tables** | `/tmp/bh5_replay.py` |
| **B** | F-6: loosen attempt → no write + state still records; next cycle re-evaluates clean; control tighten applies (clamp ≥price×1.001 noted); LONG mirror; legit-path walk (adverse-raised stop → favorable target below stop → tighten, NOT blocked); does F-6 ever block a legitimate path? **No** — target on the loose side IS the definition of loosening; the legitimate raise lives in the ADVERSE branch (not F-6-guarded, shakeout intact A6/A7) | **PASS** | B1–B5, A6/A7 |
| **C** | Docs: regime-claim grep = **1 stale line left** (F-3r :371); structure_governed "ALL THREE" + exactly 3 sites (pm:644/3969/3990); both skills' manual_tp_hit suppression present; "disaster" across skills = only arm-time TP depth line (no close claim); F-4 branch comment present + trace confirms unreachable | **FAIL (1 doc line, LOW)** | findings F-3r |
| **D** | F-2 stale-birth-pin root cause | **ROOT CAUSE NAMED** — see D | below |
| **E** | Regression: suite (author's inline "20/20" not persisted — substituted harnesses), py_compile, fresh imports, ONE live run_cycle, logs, TP spy | **PASS** | below |
| **F** | Scope = exactly 4 files across the two commits; constants/watchdog/mxm untouched | **PASS** | `git diff 6d6a2138~1..dcae3611 --name-only` = auto_trader.py, position_manager.py, 2 skills |
| **G** | Current pre-structure exit inventory | **PASS — nothing NEW** | list below |

## A(v) — the 3-way money tables (the CEO numbers)

### #16915 — SHORT 62911, TP 62286, open 01:05:15 (UTC 2026-11-15)

| column | mechanism | exit | pnl @10x |
|--------|-----------|------|----------|
| **actual (live)** | v2-era birth + v3 steps + TP-gate (c345c11c live that night) | 02:30:32 `manual_sl_hit` @ 64453 (stop 64408.84) | **−24.5108%** |
| **bf763207's v3 replay** (same code, oracle structure) | gate+v3, no BE-cap | 02:12 @ 63978.41 | −16.97% (F-7-bracketed vs live; production structure ran staler) |
| **ungated TP counterfactual** | gate OFF | TP first crossed 01:39 (fill 62286) | **+9.93%** |
| **now (BE-cap+F-6+gate)** | HEAD | **02:04 @ 62973.911** | **−1.00%** |

- Stop sequence now: 64265 → (01:20 birth) 64666.95 oracle / 65058.98 production-faithful → **(01:50 favorable-cap) 62973.911** → (02:20 record-only, no write) → V tags 02:04.
- **BE-cap saves +23.5pp vs actual (−24.51 → −1.00); still −10.9pp vs ungated TP (+9.93)** — the gate's cost (F-1) is untouched by this commit; the CEO decision on F-1 remains open.
- Commit-message corrections (F-4msg): birth at 01:20:27 was **NOT in profit** (decision price 62961.0 > entry 62911; 1m close 62859.68 a minute later) — BE-lock binds at 01:50 via the favorable-cap, not at birth; and the tag is **−0.10% price = −1.00% @10x**, not "+~0.1%". End state unaffected.

### #16913 — SHORT 64929, TP 63111, open 21:42:59 (UTC 2026-11-14)

| column | mechanism | exit | pnl @10x |
|--------|-----------|------|----------|
| **actual (live)** | v2 lag + **ungated TP** (pre-gate) | 01:04:20 `manual_tp_hit` fill 62873 | **+31.6654%** |
| **bf763207's v3 replay** (prior method: seed fresh@22:20 + production pin 66265.056) | gate+v3 | 02:12 @ 63978.41 | **+14.6404%** (reproduced exactly — harness validated) |
| **now (BE-cap+F-6)** prior-method, same seed | HEAD | 02:12 @ 63978.41 | **+14.6404%** (identical) |
| **now full-path** from 21:50 birth (2 unknown-stale-sh15 bounds × 2 versions = 4 runs) | HEAD + v3 | 02:12 @ 63978.41 | **+14.6404% all four** |

- BE-cap changes only intermediate stops — **66265.056 → 64993.929 @22:20** (pin eliminated) and 65058.98 → 64993.929 @23:50 — neither was ever tagged (price stayed < 64955 through 00:50).
- **HONEST ANSWER: BE-cap does NOT recover #16913's 17pp.** That loss is the TP-gate (F-1) — unchanged by these commits; gate OFF on the same trail exits at the TP (+28.0% at TP price / +31.67% actual fill).

## D — F-2 root cause (stale-birth-pin, NOW NAMED)

**The pin 66265.056 = `prev_sh1h + 0.1·atr1h@22:20` — v2's CHOP-favorable branch (source=1h) targeting the swing high RECORDED AT THE 21:50:25 BIRTH.**

- **prev_sh1h = 66189.88 = the 17:00 1h bar's high.** The whole 21:50:25 snapshot = the **closed-1h series through the 19:00 bar** — 3/3 cross-validated against the SAME-cycle ladder event: sh 66189.88 (implied by the event arithmetic), sl **65363.04** = ladder's printed "1h major floor 65363", atr **576.036** = ladder TP 62286 = round(64014 − 3×576.036) ✓. The 20:00 bar (closed 21:00) and forming 21:00 bar were **both absent at read time** (≥50 min stale 1h series; `load_candles` = `is_closed=1` rows, and price_collector's upsert writes `is_closed=1` on every write → rows themselves were missing, i.e. collector insert gap; collector logs for that window rotated away at 00:09 — no further mechanism separable).
- At **22:20:27** the snapshot refreshed (through the forming 22:00 bar): state row **reproduces oracle mode-A 4/4** (64896.01/63326.43/64981.44/63944.0), atr1h = **751.667** (same-cycle ladder TP: round(65041+3×751.667)=67296 ✓). The favorable step then computed 66189.88 + 75.17 ≈ **66265.056** — a **+945 loosening to a swing high that was 4 hours stale when recorded and never re-validated** (the birth froze it; the next cycle trusted `prev` blindly).
- **Explicitly ruled out (the prior verdict's two hypotheses):** NOT the `max(line, price×1.001)` clamp — fresh decision price 63869.45 makes both clamps non-binding (63933 / 67062); NOT a 17× ATR — production atr1h@22:20 = 751.667 (ladder TP arithmetic); NOT a different-TF sl/sh — the through-19:00 window matches all three printed values.
- Class: **stale-birth-pin** — a stale structure snapshot enters the lag state at birth and is consumed one cycle later as if fresh. The 15m side was stale too at 21:50 (ladder-derived sl15 64074 matches no as-of window), so the staleness was whole-snapshot, not TF-specific. Under HEAD the pin cannot recur in this form: the BE-cap bounds any in-profit step at `entry×1.001` regardless of how stale `prev` is (full-path runs: 22:20 stop → 64993.929 under both sh15 bounds).

## E — regression

- **Suite:** the author's inline "20/20" is not persisted (no file in repo//tmp from the commit window). Substituted: **bh5_contract 35/35**, **bh4_tpgate 22/22 (FAILS NONE)** — `check_atr_tp_sl_hits` spy: managed TP still suppressed after the doc edits (control non-managed still closes `atr_tp_hit`), **bh4_lag 23/27** (4 stale expectations — F-6r), bh4_box OK, replays rc=0.
- **py_compile:** all scripts OK except pre-existing F-10 `scripts/tpsl_utils_debug.py:561` (unchanged, not imported). **Fresh imports OK** (auto_trader, position_manager, structure_analysis, auto_analysis).
- **ONE live `run_cycle`** (`python3 scripts/auto_trader.py`) **rc=0, stderr empty**: `decision=MANAGE_ONLY, scores {long:-20, short:10, regime:CHOP}, price 64815.19, tweaks=[16918 stop 65706.90→65395.39 R1 tighten (sanctioned write)], shadow_armed=[], live_armed=[], armed_detail=[], hypo=0, stats n=58 wr=44.8 pnl=+$0.775`. **BTC open: YES — 16918 SHORT entry 64712 lev10 TP 61754 stop 65395.39 (opened 04:12:10)**; 16916 (ladder LONG) closed 04:10:21 `manual_sl_hit` −12.81% (structure stop, normal). **Armed book both sides: 33 BTC rungs (21 short 59940→73940 / 12 long 65041→75630) + HYPE short 70.6**; prices.json BTC 64772.5 age 28s.
- **Logs:** `pipeline.log` **0 Tracebacks**. `trade-watchdog.log` 3574 Tracebacks total, **0 reference auto_trader/position_manager** — composition: psycopg2-connect/json load (agent SQL), `<stdin>`/`/tmp/opencode` heredoc noise (F-6 class, named not counted), 13 × `ai_trader_precheck.py` module-level (agent-invoked CLI), 1 × `paths.py:112`.

## C — docs

- **F-3r:** `auto_trader.py:371` still reads (present tense): "# 1h structure for the lag's MAJOR targets (adverse raises always, **favorable steps when regime=CHOP**) — CEO 2026-11-13 shakeout fix." — stale regime claim in the lag path; the prior verdict named this exact line and it was not rewritten (the `_lag_stop` docstring :431-443 and inline comment :459-465 WERE rewritten — those now say "Regime no longer selects anything" / "old regime-split" (historical, fine)).
- `structure_governed` docstring = "Gates **ALL THREE** non-structure exit clocks" (pm:191-206) ✓; exactly **3 call sites** — pm:644 (TP gate), pm:3969 (stale), pm:3990 (maxhold) ✓.
- Skills: `full-analysis:112` and `manual-trade-override:155` both carry the 2026-11-15 suppression note; the disaster-circuit-breaker line replaced at `manual-trade-override:344-351` (target = validation-only, BE-cap trail owns profits) ✓. Grep "disaster" across skills = only `manual-trade-override:369` (arm-time TP depth for ladder rungs — no close claim) + `python-gotchas:91` (unrelated) — **no skill still claims TPs close structural trades**.
- **F-4 marked-unreachable branch (pm:660-668): trace confirms unreachable** — pm:619 `if not sl or not tp: continue` removes stop-less before hit detection; for stop-bearing managed, `structure_governed(sig, sl)` at pm:644 is always True (is_managed_signal already true in that branch + sl truthy) → gate fires first → `elif hit=='atr_tp_hit'` never reached. Kept as fail-open relabel, correctly documented.

## G — current pre-structure exits for a managed structural trade (nothing NEW)

1. **Structure stop** — hit check pm:614-624 (`manual_sl_hit`); moved only by the **lag trail**: favorable = 15m tighten-only + BE-cap + F-6, adverse = 1h line capped at BE, birth = re-anchor or BE-lock (auto_trader `_lag_stop` :430-606).
2. **Guardian HL-side stop mirror** (SL side; TP side skipped for managed rr_engine — `hl-sync-guardian.py:2065-2087`).
3. **Guardian CUT_LOSER ≤ −3.0%** — `hl-sync-guardian.py:286` const, `:1919-1930` fire, **BTC exempt :1922-1925** (non-BTC only).
4. **Weather-vane shield 30-min force-close** — `pm:3068-3076` (`WEATHER_VANE_SHIELD_MAX_HOLD`); no structure_governed/is_ceo gate (carried).
5. **wave_turn** z±1.5 + accel — `pm:3677-3690+`; no is_ceo gate (carried LOW).
6. **MACD `should_exit`** — `pm:3721+`; token-gated {TRB,IMX,SOPH,SCR} → BTC N/A (carried LOW).
7. **`should_cut_loser` priority-3** −4/lev% latent — `pm:509-556` (carried LOW).
8. **UGB-PT giveback ≥0.45% from peak** — `pm:174-182` consts, close `pm:4568` (carried LOW).
9. **Capital/structural closes** — guardian stale-rotation `:1901`/`:2227`, MAX_POSITIONS `:2821`, NOT_HOTSET `:2858`, HL_CLOSED mirror `:3032` (carried INFO).
10. **Floors:** HML twin (stop twin — gated), staleness-of-PRICES (prices.json age — named in structure_governed "safety retained", pm:201-206).
- **Gated (do NOT fire for stop-bearing managed):** UNIVERSAL_MAX_HOLD pm:3990, stale_exit pm:3969, at-target TP pm:644.
- **NEW this round: none** — BE-cap/F-6 only move stops; the diffs add no close path.

## Findings

| ID | Severity | Finding | Location |
|----|----------|---------|----------|
| **N-1** | **MEDIUM (money, not a code defect)** | **BE-cap does not help #16913** — 3-way: actual +31.67 / v3 +14.64 / now +14.64 (identical, 6 replay runs). The −17pp is the TP-gate (prior F-1) — still open for CEO decision. BE-cap only cures the intermediate pin (66265→64993.93), never tagged. | `/tmp/bh5_replay.py` |
| **N-2** | **MEDIUM (root cause closed; class remains)** | F-2 pinned: `prev_sh1h`=66189.88 (17:00 bar) frozen by the 21:50:25 birth from a **through-19:00 stale 1h snapshot** (3/3 vs ladder), consumed one cycle later by v2's CHOP-1h-favorable → 66265.056. Price-clamp and 17×-ATR hypotheses disproven. Whole-snapshot staleness (15m also stale). Collector insert-gap is the probable mechanism; window logs rotated — beyond available evidence. | `auto_trader.py:551-572` (v2), events 1794694827.02496, archived pipeline.log |
| **N-3** | **MEDIUM (invariant hole in the new safety)** | **BE-cap birth fall-through is uncapped**: BE-lock only fires when `stop > _be` (:506). If the stop is already ≤ `_be` at birth (tight/hand-armed rung in profit, or a >72h state-prune re-birth of a live structural trade — maxhold is gated so trades CAN outlive the 72h prune), the mid-box re-anchor (:529-532) applies `line` with NO BE cap — proven: stop 64900 → **65056.66 > _be 64993.929** (up to price×1.05). Adverse and favorable are capped; this path is not. Reachability narrow but the invariant "never looser than BE while winning" is violated on it. | `auto_trader.py:506-533` (probe P1) |
| **N-4** | LOW (doc) | Commit 6d6a2138 message: "01:20 birth ... in-profit!" is wrong (decision price 62961.0 > entry 62911 at 01:20:27) — BE-lock binds at 01:50 via favorable-cap instead; "tags it at +~0.1%" is actually −0.10% price = **−1.00% @10x**. Outcome claim (≈breakeven) holds; mechanism text does not. | commit msg / `auto_trader.py:502-510` |
| **N-5** | LOW (doc — F-3 incomplete) | `auto_trader.py:371` present-tense "favorable steps when regime=CHOP" — stale regime claim; prior verdict named this line, fix missed it. | `auto_trader.py:371` |
| **N-6** | INFO (F-7) | Oracle bracketing: 16913@22:20 **4/4 match**; 16915@02:20 1h 2/2 match but 15m **2/4 mismatch** (oracle 64154.01/62485.54 vs prod 63809.08/62006.0); production 1h@01:20 (16915) = 64981.44 vs oracle 64574.27 — production structure snapshots ran staler than as-of reconstruction on both trades (same class as N-2). Replays bracketed, both columns reported. | `/tmp/bh5_replay.py` |
| **N-7** | INFO (stale harness) | bh4_lag 23/27 — 4 FAILs are expectation drift, verified not defects: E3/E4 signature arity 6→7 (entry added, by design); C7b/C7d assert v3's LOOSENING clamps apply (price×1.05 raise / price×0.95 long floor) — F-6 now blocks them **by design and correctly** (C7d would have loosened a LONG stop 69000→66215). | `/tmp/bh4_lag.py:206,222` |
| carried | INFO | F-10 `tpsl_utils_debug.py:561` syntax error pre-existing; F-5 guardian config-coupled skip unchanged. | — |

## Overall verdict

**PASS on implementation — every mechanical claim verifies: BE-cap contract 35/35 (birth/adverse/favorable caps, underwater byte-identical, breach-first, CAS-retry, LONG mirror, Decimal-safe entry plumbing, F-6×BE interplay incl. the target==stop record-only path), F-6 tighten-only correct on both sides and never blocks a legitimate path (state still records on the None path), docs/skills structurally fixed with ONE leftover stale line (:371), scope exactly 4 files, regression clean (py_compile/imports/TP-spy/logs), ONE sanctioned live run_cycle rc=0 with a healthy armed book and BTC open. D: the F-2 pin is root-caused to a through-19:00 stale 1h snapshot frozen at birth and trusted one cycle later — price-clamp and ATR hypotheses disproven.**

**Three things the CEO should see:** (1) the money — #16915 −24.51% → **−1.00%** under BE-cap (vs +9.93% ungated; the gate still costs ~11pp), but **#16913 unchanged at +14.64% vs +31.67% actual — the −17pp is F-1, not fixed by this round**; (2) N-3 — the BE-cap's birth re-anchor fall-through can still raise a sub-BE stop past BE (one-line fix candidate: apply the same `_be` clamp to the birth `line`); (3) N-5 — one stale regime comment line (:371) left from F-3. No code defect blocks shipping; N-3 is the one to close before the next in-profit birth.

---

## Acceptance addendum — fix commit `57da3401` (N-3 + N-5), verified 2026-11-15 04:55 UTC

**PASS — both findings closed on my own numbers, zero delta elsewhere.**

- **N-3 (birth clamp, both branches):** my proven hole case now writes **64993.929 = _be exactly** (pre-fix 65056.66) — `/tmp/bh5_contract.py` P1 flips to "no violation (invariant holds)". LONG mirror probed independently: stop 64500 / entry 64000 / price 65000 / raw line 63877.11 → writes **63936.0 = _be** (never past BE). BE-lock-first path unchanged (A1/A2/A5b PASS), breach-first/CAS-retry unchanged (A4/A5), **underwater byte-parity to `c345c11c` holds** (A3/A3b/A7 PASS — clamp inert at `_be=0`).
- **No behavioral delta:** full 35-check re-run = only P1 flipped (that IS the fix); money replays byte-identical — #16915 now −1.00% @02:04, #16913 +14.6404% ×6 runs, F-7 validations unchanged (16913 4/4, 16915 15m 2/4 as before).
- **N-5:** `auto_trader.py:370-371` rewritten (adverse=1h / birth line / favorable=15m-always, no regime-favorable claim). Grep over lag/tweak region 333-670: remaining "regime" mentions = "Regime no longer selects anything" (docstring, correct) + "old regime-split CHOP->1h source" (historical, correct) — **zero present-tense stale claims**.
- **Scope:** `git diff 57da3401~1..57da3401 --name-only` = `scripts/auto_trader.py` only.
