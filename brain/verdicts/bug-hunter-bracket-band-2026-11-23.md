# bug_hunter verdict — §17 bracket band (keeper enforcement)

**Commit under review:** `edc9e636` ("keeper §17: the first (closest) bracket sits in a 1-2% band")
**Plus scope addenda:** `1fa0acbf` (band_exempt + equal $11.10 sizing), `1d440698` (add-to-winners gate + skill restore)
**Verifier:** agent-8 (bug_hunter), 2026-11-23 ~06:30 UTC
**Harness:** `/tmp/bh17/harness.py` — all keeper I/O against `/tmp/bh17/data` (paths.HERMES_DATA patched), `DB.log_event` mocked, zero production writes except ONE sanctioned live `run_cycle`.
**Harness result: 60/65 PASS — the 5 FAILs are findings F1/F2 below.**

---

## Verdict table

| Area | Verdict | Evidence |
|---|---|---|
| A. Clamp math (safety) | **PASS** (1 LOW nit) | 12/12 clamp probes: 5 probes (60591→60500, 62402→62250, fresh-air→59000, long-too-close→62000, in-band untouched both sides), short-too-far→60000, exact 1.0% edge untouched at pre-pass level (computed pct = 1.000000000000000), both-rounds-in-band→nearest wins, no-round-in-band→edge survives (price 20,161.62), mirror ✓, price=0→0, trig=None→TypeError (caught by keeper's outer try), constants-missing→fallback 0.01/0.02 ✓ |
| B. Pre-pass re-level | **PASS** (2 LOW findings) | push-out short: SL stays/TP follows/shape preserved; pull-in long: SL+TP follow; in-band byte-identical; nearest-selection both directions (only the first/closest bracket is governed — matches skill §17 wording); idempotent (2nd run: no event, bytes identical); exempt survives write + control re-levels; state file untouched; flock proven to block (3s timeout) and release; REVERT-0 behavior = F3 |
| B(ii) Oscillation | **PASS** | re-levelled config → 2nd keeper run = zero changes; derived rung in band → untouched (C7) |
| B(iii) State walk | **PASS** (1 LOW design note) | monitor `crossed` uses CONFIG trigger; `state['price']` is write-only (grep: zero reads in trade_watchdog); keeper never writes state (B8); first_break+uncrossed-new-trigger → retested on next cycle; retested+crossed → momentum-gated single fill (id-keyed, serial one/cycle → no double-fill). Design note: multi-touch history earned at the OLD trigger is inherited by the NEW trigger → first-touch fill possible (momentum still required) |
| B(iv) Write path | **PASS** (1 LOW) | tmp+os.replace atomic, under EX flock for the whole function (B10 blocking test); flock covers only flock-aware writers (`_arm_real_leg` L287 ✓, keeper L860 ✓) — hand-apply scripts are outside it (F9) |
| C. Derivation clamps | **FAIL → F1, F2** | clamp-before-reach-guard order correct (L1006→L1007; L1075→L1078); out-of-reach → no arm, 2nd cycle identical (no dup loop — keeper recomputes each cycle but writes nothing); ITM guard subsumed by band (clamp output always < price short / > price long, 15-point sweep ✓); fresh-air "→ band-clamped" note ✓; clamped trig1h note = "1h MAJOR-floor break" ✓ — **but `_src1h` is constant-True → fallback/fresh-air SL sources and the 15m note branch are broken (F1), and the clamp fabricates triggers from degenerate structure (F2)** |
| D. Dictated rungs | **PASS** (design question F7) | Commit-time verified from 05:47 UTC dump: short 60,250/60,801/59,067 (R:R 2.15 ✓), long 62,250/62,061/64,091 (R:R 9.74 ✓); dictation #3: long 61,750/61,561/63,591 + `band_exempt:true` (R:R 9.74 ✓); my live run_cycle @ price 61,549.69 → config **byte-identical** (short 1.30% in band, exempt long skipped) ✓. NOTE: at 06:09:48 (watchdog cycle, not mine) the live keeper **re-levelled the dictated short 60,250 → 60,750** (price 61,766 made it 2.46% too far; SL 60,801→61,301, TP 59,067→59,567, R:R kept 2.15) → F7 |
| E. Regression | **PASS** | py_compile (auto_trader, hermes_constants, trade_watchdog) OK; `test_pending_machine.py` ALL PENDING-MACHINE TESTS PASS; `test_manual_exit_manager.py` 20/20; skill §17 present (SKILL.md:1043, 6 markers, 1,310 lines — post-incident restore verified); constants revert comment present (but false → F3); ONE live run_cycle **rc=0**, exact summary: `enabled=True mode=live decision=BRACKET price=61549.69 shadow_armed=[] live_armed=[] tweaks=[]`, legs skipped by the pre-existing R:R≥1.0 gate (0.74<1.0), **0 §17 re-levels logged by my run**, config untouched; pipeline.log 0 Tracebacks; trade-watchdog.log: 448 Tracebacks — ALL interactive-agent heredoc/tmp-script noise (0 frames from trade_watchdog.py/auto_trader.py cycle code, 0 `cycle failed`/`ladder_keeper:` failure markers); scope: edc9e636 = auto_trader.py + hermes_constants.py ONLY (skill untouched there, committed in 484d7a2b prior ✓, working tree clean) |
| F. Cross-cutting | **PASS** (design question F7) | Only 2 writers of pending_orders.json (keeper + `_arm_real_leg`), both under the same EX flock; ladder_api reads config fresh per request (L57) → re-level displays correctly, no band assumptions; state keys id-based ✓ (orphan keys from consumed ids harmless — monitor iterates config ids); hand-arms: no other code path writes triggers; addendum: exempt check ONLY in pre-pass (L929), `_band_clamp` has no exempt logic, derivations never flagged (C6c) ✓; §6 BRACKET DISTANCE = skill-template only (no code) → exempt rungs still reported with distance+flag ✓; `_side_mult` callers = derivation sites only (L1047/L1087), trade-add path uses the rung's configured amount ✓; 82/82 rungs = $11.10 ≥ HL_MIN 11.0 (brain.py:716 accepts) ✓; config rewrite preserved notes/entry_style/band_exempt ✓; add-to-winners gate verified (below) |
| Addendum: add-to-winners gate | **PASS** | 3-col SELECT `id, direction, pnl_pct` matches schema; open-row pnl_pct is live-maintained unleveraged price-% by position_manager (`compute_live_pnl`, pnl_utils:47, persisted per cycle position_manager:2919) ✓; defer `continue` happens before ANY state write (state neutrality) ✓; IndexError in the parse except (L1998) ✓; D2.3 `prearmed_add` flag set ONLY inside the `pnl > 0` branch ✓; flat (`_open` None) skips the block → fills normally ✓; NULL/0/negative → defer ✓; residual: stale pnl_pct if position_manager hasn't cycled (LOW) |
| Addendum: skill incident | **PROCESS FINDING** | SKILL.md wiped to 0 by `open(p,'w').write(tuple)`; restored from 1fa0acbf + §7 re-applied, amended as 1d440698 (+50/−14). Verified now: 1,310 lines, §17 (L1043), band_exempt (L1059), §7 winner-condition (L684), §12 sizing (L853) all present. No other file written with the bad pattern (lead's claim; all my reads used strings). Note: write-then-verify (wc/grep) after every skill write |

---

## Findings (severity + line refs)

### F1 — HIGH — `_src1h` is constant True: wrong SL on two live arm paths + lying notes
`scripts/auto_trader.py:975` captures `_src1h = (trig == trig1h)` **immediately after `trig = trig1h`** — i.e. *before* the sl15-fallback reassignment (~L989) and the fresh-air reassignment (~L1001). The expression is therefore **always True** and the later branches dead:
- SL branch `:1013` `sl = (sl1h+0.6·atr15 if _src1h else (sh1h+0.1·atr1 if fresh_air else sl15+0.6·atr15))` → always `sl1h+0.6·atr15`.
- note branch `:1034` `elif _src1h` → the `else` ("15m fresher-low") is **unreachable**.

Proven (harness C1/C4):
- **sl15-fallback arm** (1h floor ITM, fresh 15m low): got SL `sl1h+0.6·atr15 = 61590`, pre-§17/expected `sl15+0.6·atr15 = 60940`; note says "1h MAJOR-floor break … (sl1h 61500−60)" while trigger is 60250 — the reclaimed level is wrong (stop sits 1,340pts away instead of just above the broken 15m low) and the note contradicts itself (the F7 class the commit claimed to fix).
- **fresh-air arm**: got SL `61590`, doctrine `sh1h+0.1·atr1 = 61840`; note prints "SL 61590 = sh1h+0.1·ATR1h" — value and formula disagree in the same sentence.
- Live proof these paths fire: config contains "15m fresher-low break" arms and many `entry_style: continuation` arms.

The commit message states `_src1h` was captured to survive the *clamp* breaking `trig==trig1h` — but the capture point also precedes the *fallback/fresh-air* reassignments, which broke the same identity pre-§17 (old code evaluated `trig == trig1h` at SL time). Fix = capture after fallback+fresh-air, before the clamp at `:1006`. One line.

### F2 — HIGH — clamp fabricates a trigger from degenerate structure → malformed rung + dark short side
`auto_trader.py:1006` `trig = _band_clamp(price, trig, 'short')` runs **unconditionally**, including when `trig ≤ 0` (no usable structure). `_band_clamp` turns any `t < far_edge` into the far edge — so `0` (or `-20`) becomes a band-edge trigger, and the guard `:1007 if trig and reach_lo <= trig < price` can no longer reject it (its falsy check is dead post-clamp). Pre-§17 the falsy/reach guard rejected this class (the F2 comment documents exactly this "dark side" failure mode).
Reachability: `classify()` returns `sl=None` when <2 swings (`structure_analysis.py:205-206`) → `structure_summary` stores None → keeper `float(None or 0)` = 0; also `<50` 1h candles drops the key entirely. Two sub-paths proven (harness C8/C9):
- all structure zero → arm at band edge with `sl = 0.6·atr15` (e.g. 90);
- `sl1h` undefined + real `sl15` → fallback fires but `_src1h`=True → `sl = 0.6·atr15` (90–300) << trigger → **shape-wrong**.
Consequence: the monitor's shape guard rejects the rung every cycle (`trade_watchdog.py` ~L1687, before `seen_ids.add` → no state ever set) → the rung is permanently "unfired" → `short_ready` stays true forever → **keeper never derives a proper short** + WARN spam + a malformed live pending order on display. Rare trigger (1h UNDEFINED), but it is precisely the class the old guards existed to prevent.

### F3 — MEDIUM — documented REVERT (both constants → 0) is not a no-op; it is destructive
`hermes_constants.py:2214` "REVERT: set both to 0 (the clamp becomes a no-op)" is false. Proven (A11/A11b/B11/B12):
- pre-pass: every nearest rung's trigger is slammed to **exactly price** (out of `[0,0]` band → clamp → price), i.e. an instant-cross level the CEO never chose (SL/TP shift with it so shape survives, but the rung sits AT price);
- derivation: clamp pins trig at price → `trig < price` / `price < trig` guards fail → **ladder replenishment goes dark entirely**.
Correct revert semantics would need the clamp to no-op (return `trig` unchanged when both constants are 0).

### F4 — MEDIUM — skill §17.2 contradicts the shipped SL/TP mechanics, and promises a check that doesn't exist
`skills/shared/full-analysis/SKILL.md:1063-1066`: "the SL moves by the SAME delta … **the TP stays** — the R:R is re-checked ≥1.0 after the move".
Code (`auto_trader.py:944-953`): **TP always moves** (3·ATR distance preserved — consistent with the F-2 doctrine), **SL moves only on a pull-in** (`_pull_in` L949). And **no R:R re-check exists anywhere in the pre-pass** — a large push-out grows risk while reward stays fixed and can push planned R:R below 1.0 (e.g. risk 551→1,161 vs reward 1,183 ≈ 1.02, worse for thin-reward rungs). The skill is the rule-of-record ("add to the skill first") — either the skill or the code must change; today they disagree on both numbers.

### F5 — MEDIUM — skill §12 sizing table still instructs the retired 2× rule
`SKILL.md:853-857`: "rungs size at **2× base ($22.20)** when the side's last-5 net positive … The keeper enforces it (`_side_mult`); apply the same table when deriving by hand." After `1fa0acbf`, `_side_mult` returns 1.0 always (`auto_trader.py:883-892`). manual-trade-override was updated; full-analysis §12 was not. An analyst following the skill would hand-arm $22.20 rungs.

### F6 — MEDIUM — clamped derivations produce self-contradicting notes; re-levels never update the note
- New notes print the **clamped** trigger next to the **old** arithmetic: "trigger 60250 (sl1h 60650−60)" (`:1035-1038`), "trigger 61750 (sh+60)" (`:1090-1093`) — 60650−60 = 60590 ≠ 60250. The fresh-air branch got the "→ band-clamped" treatment (`:1024-1026`, verified C4a) but the structure branches did not — same F7 class the commit message claims to have fixed (harness C5c/C6d).
- The pre-pass re-level (`:1100-1111`) logs to DB but **never appends to the rung's note**: live config's dictated short note still says "trigger 60591 → 60250" while the config now reads 60,750 (F7 evidence below).

### F7 — MEDIUM (design question for CEO) — a CEO-dictated level is re-levelled as soon as price drifts it out of band
Skill §17.2 protects CEO levels **only while in-band**. Live proof: dictation #2 set short 60,250 at price ≈61,152 (1.48% ✓ in band); at 06:09:48, price 61,766 made it 2.46% too far and the watchdog's keeper executed
`§17 re-level short btc-auto-ladder-1795401586 trigger 60250.0 → 60750 (band 1.0-2.0% from price 61766, SL/TP moved by the same delta)` — SL 60,801→61,301, TP 59,067→59,567 (R:R preserved 2.15, deltas all correct).
The long got the third dictation + `band_exempt`; the short did not — so the CEO's 60k-psychological level silently became 60,750 within an hour. **My read:** mechanically this is intended (the band is a distance rule, exempt is the opt-out), but the CEO dictated *levels*, not distances — he should either (a) flag the short `band_exempt` too, or (b) accept drift and be told when a dictated level moves. Recommend surfacing this to him; the skill sentence "CEO-dictated levels are never touched" is true only with the unstated "while in-band" qualifier.

### F8 — LOW — re-level log line lies on push-outs
`auto_trader.py:1110-1111` always logs "SL/TP moved by the same delta" — on a push-out the SL deliberately does **not** move (B1: trigger/TP −450, SL stayed 60,900). Log should reflect the pull-in/push-out split.

### F9 — LOW (design) — hand-applied dictations are outside the flock
Only `_arm_real_leg` (`:287`) and `_ladder_keeper` (`:860`) take `pending_orders.json.lock`. Today's dictation #2/#3 writes were hand-applied — no evidence they took the lock; a concurrent keeper RMW could in principle lose them (didn't happen today). Hand-apply scripts should take the same lock.

### F10 — LOW — add-gate reads a possibly-stale pnl_pct
`trade_watchdog.py:1998` trusts `trades.pnl_pct`, refreshed by position_manager's cycle; if that step is delayed the gate can defer (or add) on a stale sign. Fail direction is benign-ish (stale positive → add on a now-red trade); the belt (NULL→defer) covers missing data only.

### F11 — LOW — in-band non-round derivation triggers get snap-moved anyway
Skill §17.1 says only **out-of-band** derivations snap; `_band_clamp` also snaps in-band non-round triggers (e.g. 60,620 → 60,500 at price 61,500). Stays in band, note prints the moved value — cosmetic divergence only. (The snap-selection logic itself is correct: the "nearest in-band of 3 candidates" always wins; the `else t` fallback at `:786-791` is unreachable dead code — verified by probe A7a/A7b.)

### F12 — LOW (process) — agent interactive sessions pollute trade-watchdog.log
448 Tracebacks in `logs/trade-watchdog.log`, all `<stdin>`/`/tmp/opencode/*.py` heredocs from analysis sessions (0 cycle-code frames, 0 failure markers, pipeline.log clean). Makes "any Traceback?" checks noisy — keep agent shells out of the service log.

---

## Addendum spot-checks (detail)

- **band_exempt placement:** read only at `auto_trader.py:929` (pre-pass, after nearest-selection, before the band test). `_band_clamp` has no exempt branch — correct: a derivation is never flagged (C6c). Exempt-on-nearest skips the whole side for that cycle — consistent with first-bracket-only governance. Flag survives keeper round-trip (B7c: forced a write via the other side, flag present in JSON). Unflagged control re-levels (B7d).
- **§6 reporting:** no code computes closest-bracket distance (grep BRACKET DISTANCE → skill template only, SKILL.md:1250) → exempt cannot hide anything; the analyst reports distance + out-of-band flag from the config regardless of the flag.
- **Equal sizing:** `_side_mult` → `return 1.0` with revert documented in docstring (`:883-892`); callers = `:1047`/`:1087` only (grep); trade-add/fill path uses the order's configured `amount_usdt` (`trade_watchdog.py` steer → brain); HL floor: `HL_MIN_NOTIONAL_USDT = 11.0` (hermes_constants:632), brain.py:716 rejects `<11.0` → 11.10 passes; 82/82 BTC rungs = 11.1 (odd 11.0 gone); notes/entry_style/band_exempt intact after rewrite (spot-checked dictated rungs + continuation/retest styles).
- **Gate state-neutrality:** the defer `continue` (`trade_watchdog.py:2015`) fires before the fill path's `state[oid] = fired` and after every earlier state-writing branch has already `continue`d → no state burn, rung stays armed ✓.

## Overall verdict

**CONDITIONAL PASS.** The §17 core — band math, nearest-bracket selection, re-level deltas (SL pull-in-only / TP always), idempotency, flock/atomic write, exempt flag, equal sizing, add-to-winners gate, and the two dictated rungs' R:R — all verified correct under test, and the one sanctioned live `run_cycle` was clean (rc=0, config byte-identical, no re-level). But the same commit introduced **two HIGH regressions in the derivation path** — F1 (`_src1h` constant-True → wrong SL + self-contradicting notes on fallback/fresh-air arms, live-firing paths) and F2 (clamp fabricates a band-edge trigger from degenerate structure → malformed rung, dark short side, the exact F2 class the old guards prevented) — plus the false REVERT doc (F3) and three skill↔code divergences (F4/F5/F6). Fix F1 (move the capture below fallback/fresh-air) and F2 (guard `trig > 0` before clamping / skip clamp on falsy trig), correct the REVERT comment, and reconcile skill §17.2 + §12 with the code before this is a full pass. F7 needs a CEO call, not a code change.

*Reproduce: `python3 /tmp/bh17/harness.py` (60/65; the 5 FAILs are F1×2, F2×2, and D1's documented live-move).*
