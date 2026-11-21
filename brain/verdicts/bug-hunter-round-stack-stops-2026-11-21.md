# bug_hunter verdict — round-anchor trail + stack-leader stops
**Commits verified:** `89a0bb24` (auto_trader round-anchor + pm stack-leader), `3dbc10c4` (guardian stack-leader, the symlink follow-up)
**Verifier:** bug_hunter (agent-4) · 2026-11-21 · adversarial, no fixes applied
**Harnesses:** `/tmp/bh_rss/harness_a.py` (A-i), `/tmp/bh_rss/harness_a2.py` (A-ii), `/tmp/bh_rss/harness_b.py` (B), `/tmp/bh_rss/harness_live_pair.py` (B-v live pair) — all execute the REAL shipped source (ast-extracted `_lag_stop`, real `check_atr_tp_sl_hits`, real `_check_hard_stops`) with DB/HL mocked; zero production writes except ONE sanctioned `run_cycle`.
**Harness totals: 53/53 PASS** (A-i 21/21, A-ii 11/11, B 21/21, live-pair 11/11 counted inside B's run separately).

---

## 1. Verdict table

| Area | Item | Result | Evidence |
|---|---|---|---|
| A-i | Round arithmetic (spec case, boundaries, BE, long mirror, guards) | **PASS 21/21** | harness_a.py — spec 55400→55500 ✓; price==55500 / ==55000 → no apply ✓; 55500.01→56000 ✓; 54999.99→55000 ✓; stop==round no-op ✓; BE==round applies / BE<round blocked ✓; tighten-only ✓; F-3 breach guard preempts ✓; LONG mirror + BE interplay ✓; NaN raises (contained) ✓; CAS miss + natural retry ✓ |
| A-ii | Full-lag trace (birth / unchanged / favorable / adverse / state / CAS) | **PASS 11/11** | harness_a2.py — birth block L487-559 all-return (8 `return` statements; last at L559 < ROUND-ANCHOR L560) → round-step unreachable on birth ✓; round runs before `if cur_val == prev_val` (L560 < L583) ✓; structure-unchanged cycle: round applies, `_smap`/ts untouched, `_st_dirty=False` ✓; favorable: round first, structure step sees new stop, chained CAS (old=rt) ✓; adverse: see §2; CAS miss → no local update, no record, retried next cycle ✓ |
| A-iii | LIVE #17014 stop | **PASS — stop became 56,000 at 06:09:22** | events (data/auto_trader.db): `06:09:22.373 tweak {'trade':17014,'old':56693.637,'new':56000,'rule':'R1'}`; `06:09:22.381 trade 17015 old 59416.0 → new 56255.6995` |
| A-iv | BE-cap write path / birth re-anchor / HML flow | **PASS** | birth XOR round in one call (T1); favorable BE-cap after round cannot raise (F-6, T3a); mxm trail tighten-only ("only ever improves", manual_exit_manager header) → cannot fight the round; stop flows to both checkers — **live-proven**: the 06:09 write was the stop pm closed on at 06:20:31 |
| A-v | `import math` per call | **NOTE only** | sys.modules cache, ns-level; per position per cycle — trivial |
| B-i | pm behavior suite + mixed-direction + None-id + cross-token | **PASS** (see §4 for the two calls) | harness_b.py |
| B-ii | Leader close = full stack + labels | **PASS** | pm: profit-side → `manual_trail_hit`, loss-side → `manual_sl_hit` (pm:691-699); guardian: `hard_sl`→`trail_sl`→managed map (hl-sync-guardian:2105-2123). LIVE: #17014 closed `manual_trail_hit` ✓ |
| B-iii | Follower TP per-row, TP-gate not bypassed | **PASS** | pm: managed follower TP → `structure_governed` → hit=None (pm:660-672, harness B); guardian: ai-trader = rr_engine → hard_tp skipped (hl-sync-guardian:2086) — pre-existing RR gate, leader untouched |
| B-iv | Guardian 0.1% margin + trail relabel on leader path | **PASS** | 56,720 (within 0.1% of 56,693.637) → no fire; 56,760 → fire; profit-side leader stop → `manual_trail_hit` |
| B-v | LIVE pair both checkers (price 55,789 / follower-only / leader) | **PASS 11/11** | harness_live_pair.py — @55,789 both checkers ZERO; follower-only @56,300: pm multi-row ZERO, **pm production shape FIRES (leak, H-1)**, guardian ZERO; leader @56,760: both → ONE leader close `manual_sl_hit` |
| C | Full stop-path inventory | **see §5** — 1 effective gate, 1 dead gate, 2 latent bypasses, no exchange-side stops | grep + reads |
| D | Regression | **PASS** | py_compile 4 files OK; fresh imports OK; ONE live `run_cycle` rc=0 (decision BRACKET @56,130, `tweaks:[]` — book flat, 0 Tracebacks, pending_orders.json diff=0, tweak state unchanged); pipeline/watchdog/sync-guardian logs: **0 Tracebacks since 05:45**; commit scope = exactly 3 files (+21/+18−2/+14−2); symlink `hl_sync_guardian.py` (mode 120000) → target `hl-sync-guardian.py` (100644) is what changed |
| E | CEO walkthrough vs REAL outcome | **PASS — see §6** | stack closed once at the leader's round-stop, in profit both rows, follower's stop never fired |

---

## 2. (A-ii) ADVERSE-vs-ROUND hierarchy — the call, with numbers

**Order inside one non-birth `_lag_stop` call** (auto_trader.py): F-3 breach guard L456-459 → **ROUND-ANCHOR L570-580 (tighten-only)** → structure compare L581-585 → favorable L593-611 (tighten-only, F-6, BE-cap) / adverse L612-631 (raise).

**Verdict: INTENDED hierarchy, not a hole — with one bounded give-back.**
- **Straight slide (structure unchanged):** early return at L583 fires *after* the round-step → the round-lock HOLDS exactly in the CEO's case. This is what shipped live: the 06:09 cycle wrote a single `56693.637→56000` (no structure change, no second write).
- **Favorable step:** can never undo the round (target ≥ prev swing > round; plus F-6 `target > stop → None` after the local stop tightened) — proven T3a/T3b.
- **Adverse step (confirmed higher 15m high):** CAN supersede the round-lock — by design (F-6: raise to the 1h major line so a crossing = a real structure break). **Exact #17014 numbers:** round-stop **56,000** (06:09 state, prev sh15 = 56,444, price ~55,767-55,8xx):
  - *In profit* (price < entry 56,199.5 → `_be` = **56,255.6995**): raise caps at `_be` → **56,255.6995** (proven T4a: calls `[(56000, 56693.637), (56255.6995, 56000)]`). Give-back ≤ 255.70 (0.45%), never past BE.
  - *Underwater* (price ≥ entry → `_be`=0): raise to `min(sh1h+0.1·atr1h, price×1.05)` — proven **59,325** at price 56,500 (T4b). Pre-existing adverse rule, unchanged by this commit.
  - *Nuance:* on an adverse-structure cycle the round-tighten and the adverse-raise can net to zero (T4c: BE→56,000→BE). The round-anchor's value is on unchanged/favorable cycles — precisely the straight-slide starvation it was built for.
- **F-6/adverse rules still hold:** raise-only (`t2 > stop+1`, L631), 1h major line only, `price×1.001/×1.05` clamps (L621), BE-cap while in profit (L622-623), `_record` on no-op (L632-633), CAS-miss → no record → natural retry next cycle (L636 comment, proven T5).
- Correction to the brief: `_be` is **not** 56,693.637 — after the 05:43 merge the entry is 56,199.5, so `_be` = 56,199.5×1.001 = **56,255.6995**. The round 56,000 ≤ 56,255.6995 ✓ still passes (and the live event proves it passed).

## 3. (A-iii) LIVE #17014 stop — final answer

**The06:09:22 cycle (first with the code) set #17014's stop to exactly 56,000** (DB event + row). Guards all held: rt 56,000 > price (no instant close), rt < 56,693.637 (tighten), rt ≤ `_be` 56,255.6995 (BE-cap). The sub-55,500 spec case (stop → 55,500) never occurred live: the06:09 rt=56,000 proves price ∈ (55,500, 56,000] then, and no `56000→55500` event exists before the 06:20 close (final stop at close = 56,000 → no later ratchet). #17015's own lag wrote only its own row (`WHERE id=17015`, 59,416 → 56,255.6995 = its birth BE-lock, looser than the leader's 56,000) → **cannot move or conflict with the leader-governed stack**; from cycle 2 its round-step converges to the same 500-grid value as the leader (same price → same rt).

## 4. (B-i) The two required calls

- **Mixed-direction (leader LONG + follower SHORT):** can exist only via (a) a `--force` opposite add (brain dup-guard brain.py:683 allows any direction under force), or (b) the flip-race the code itself admits (trade_watchdog.py:1777-1782 ponytail comment: "a position flip inside that window would net instead of add"). The ladder monitor's direction gate (flat / same-direction / opposite-waits) blocks the normal path. **If it exists:** leader = min(id) regardless of direction → only the LONG leader's stop fires; the SHORT follower's stop is **dead while stacked** (unbounded loss on that leg until flat). Proven in both checkers (harness B). → **Finding M-2 (MEDIUM, rare-state).**
- **None-id rows:** pm — `if not trade_id ... continue` at **pm:610 runs BEFORE the leader check**, so a None-id row never leads *and never triggers* (the `_leader.get(token, trade_id)` fallback is unreachable with None) — safe, no crash (proven). Guardian — rows come from `SELECT id ... WHERE status='open'` (PK, never None); `_r[0] < _leader[_t]` on ints. Non-issue.
- Equal ids: impossible (PK); simulated → both rows would trigger (documented theoretical only).
- Cross-token: leader map is per-token (`_leader[token]`), proven — ETH fires independently of a BTC stack.

## 5. (C) Full stop-triggering path inventory

| # | Path | Stop-close? | Leader rule? |
|---|---|---|---|
| 1 | **pm `check_atr_tp_sl_hits` → `close_paper_position`** (pm:3742 call → 3746 close) | YES (primary) | **PRESENT BUT DEAD in production — H-1** |
| 2 | **guardian `_check_hard_stops`** (hl-sync-guardian:2082/2092 → 2173/2206) | YES (backup) | **Effective** (map from all DB rows, L2027-2031) |
| 3 | pm **RR-engine trail immediate breach** (pm:3717-3726) + ride-it EXIT (pm:3594-3605) | YES, per-row | **NONE — latent M-1**, but excluded for CEO/managed trades (pm:3614, pm:3598 `not is_ceo_trade`) and stacked rows are always `ai-trader-*` (watchdog passes `--force` only for `btc-ceo-*`/`btc-auto-ladder-*`, trade_watchdog:1816-1819) → unreachable today |
| 4 | **mxm `update_trail`** (manual_exit_manager:262 CAS write) | NO — writes only (no close call in module) | n/a; its writes fire through paths 1&2. Answer to the brief's mxm question: **mxm has no stop-check of its own**, so no separate first-stop hazard — the hazard is entirely H-1's |
| 5 | pm hard_max_loss / cut_loser / stale / max_hold / wave_turn / cascade / time / peak exits | pnl/time/momentum, not stop-level | out of the leader rule's remit by design |
| 6 | Guardian orphan / HL_CLOSED / stale rotation | not stop-level | n/a |
| 7 | **Native HL stop orders** | **NONE** — brain.py:1078 "HL trigger orders are NOT placed" | no exchange-side first-trigger hazard ✓ |

**H-1 (HIGH):** `position_manager.py:3742` calls `check_atr_tp_sl_hits([pos])` **inside** `for pos in positions:` (pm:3243) → the leader map (pm:596-601) is built from a 1-element list → `_leader.get(token, trade_id) == trade_id` (pm:640) is **always True** → the SL gate (pm:642/647) never suppresses anything. Proven: harness B3 — follower row alone with a crossed stop **fires** (`[(17015,'manual_sl_hit')]`), while the same two rows passed as a list are correctly gated. Effect: the CEO's exact hazard (a follower's tight stop closing the whole stack via pm) is **only** guarded by guardian (one of the two shipped checkers) — the pm half of the fix is dead code. Residual live window: an adverse structure raise can invert the stops (leader `_be` 56,255.6995 > follower round 56,000) → follower-first price band [56,000, 56,255.7) → pm would close on the follower's stop with the follower's label. Today's ordering (round-anchor keeps leader ≤ follower on every unchanged/favorable cycle) plus guardian's ~60s sweep mitigate it — **by incident, not by the shipped gate.** Fix shape (not applied): pass the full list, or build the map inside from a full-book query.

## 6. (E) CEO walkthrough — table (entry 56,199.5 avg, lev 10, $22.30/row)

| Exit point | #17014 pnl | #17015 pnl | Whole stack? | Notes |
|---|---|---|---|---|
| **REAL (06:20:31, leader round-stop 56,000, HL fill 56,085)** | **+2.0374% (+$0.09)** `manual_trail_hit` | **+0.4107% (+$0.09)** `HL_CLOSED` @06:20:59 | YES — once, at the leader's stop | Follower's stop 56,255.6995 never fired (price never reached it) — linger to sync-close ≈ 30s |
| Reclaim-55,000 exit (had price broken 55,500 then reclaimed — never happened) | ≈ +35.6% margin (+$7.93) at fill 55,000 | same (identical entry) | YES (leader) | stop 55,000 fires on the reclaim up through 55,000 — the spec's exact case, unobservable post-ship |
| Follower-ignored case (follower stop crossed, leader not) @56,300 | −1.79% margin (−$0.40) | −1.79% margin (−$0.40) | **hazard**: pm's dead gate (H-1) closes it; guardian correctly closes ZERO | "exiting the whole position right away at breakeven" — the CEO's fear; guarded by guardian only |
| Adverse-raise then hit @ `_be` 56,255.6995 | −1.0% margin (−$0.22) | same | YES (leader) | BE-cap hair, bounded, by design |
| *Old world (no round-anchor): stop sat 56,693.637* | *≈ −8.9% margin (−$1.98)* | *same* | — | the round-anchor turned a would-be −8.9% exit into **+2.04%** on this trade |

**Does the real sequence satisfy E? YES:** price fell → the leader's stop ratcheted to the round (56,000, not instant-closed — strictly above price) → an add existed with a tighter-than-original stop → the whole stack exited **once, at the leader's stop, in profit for both rows** → never at the add's breakeven, never twice.

## 7. Findings (severity + line refs)

| ID | Sev | Finding |
|---|---|---|
| **H-1** | **HIGH (safety feature ineffective)** | pm's stack-leader gate is dead in production: single-`[pos]` call **position_manager.py:3742** inside the loop at **:3243** → leader map (:596-601) is always self → gate (:640-650) never suppresses. Proven live-shape (harness B3). The CEO hazard remains open on pm's primary close path; guardian is the only working gate. |
| **M-1** | MEDIUM (latent) / LOW (active) | RR-engine immediate-breach **pm:3717-3726** and ride-it EXIT **pm:3594-3605** close per-row with no leader gate; excluded for managed/CEO trades today (**pm:3614**, :3598) and stacks are always `ai-trader-*` — becomes live if a non-CEO rr_engine/ride_it row ever stacks. |
| **M-2** | MEDIUM (rare-state) | Mixed-direction stack (leader min-id regardless of direction, **pm:596-601** / **hl-sync-guardian:2027-2031**) → minority-side follower's stop dead while stacked. Reachable only via `--force` opposite add or the admitted flip-race (**trade_watchdog:1777-1782**). |
| **L-1** | LOW | NaN `current_price` passes the truthiness guard **auto_trader:650** → `math.ceil(nan)`/`int(nan//500)` raise (**:572/:577**) → aborts `tweak_structure_fixed` for ALL positions and skips the state save (**:676**); contained by the caller's try/except **:998-1001** (WARN). One bad row freezes all stop tuning for a cycle. (Proven A cases 18/19.) |
| **L-2** | LOW (defensive) | Negative price → `rt = ceil(neg/500)*500 ≤ 0` → `_apply_stop(0,…)` (**auto_trader:571-575**) → stop=0 in DB → pm skips it (`if not sl`, **pm:636**) and guardian excludes it (`stop_loss > 0`, **hl-sync-guardian:2017**) → row becomes un-stoppable, and the tighten-only round-step can never recover a 0 stop. Unreachable with non-negative feeds (price=0 filtered at :650). (Proven A case 16.) |
| **L-3** | LOW (audit) | Round-anchor writes are tagged `rule:'R1'` (**auto_trader:404**) — indistinguishable from structure-lag tweaks in the events audit trail (the tag name also predates the round-anchor). |
| **I-1** | INFO (attribution) | PeakReanchor entry-merge is designed (log line `pipeline.log:672425` 05:43:34 "creation seed moved with entry; phantom-MFE gap closed"; precedent STX `pipeline.log:328456`) but lossy: **both rows' `entry_price` and #17014's `hl_entry_price` were overwritten to the HL merged average 56,199.5** — #17014's original fill 56,637 survives only in logs (PriceSanity `pipeline.log:646527`); #17015 keeps 55,762 in `hl_entry_price`. Per-tranche attribution ("who called it at which fill") is no longer row-recoverable. |
| **I-2** | INFO (no gap) | **Addendum (i) resolved — there IS a tweak event:** `data/auto_trader.db` events table, `06:09:22.373` (#17014 56693.637→56000) and `06:09:22.381` (#17015 59416→56255.6995), both `rule:'R1'`. The "missing event" report came from grepping pipeline.log — `DB.log_event` writes SQLite (auto_trader_db.py:279), not the pipeline log. |
| **I-3** | INFO (process) | The commit's "suite 20/20" has no committed artifact (ad-hoc) — not reproducible from the repo. This verdict's 53-check harness suite is in `/tmp/bh_rss/`. |

## 8. (D) Regression evidence

- `py_compile` auto_trader / position_manager / hl-sync-guardian / trade_watchdog → OK; fresh imports of all 4 → OK.
- **ONE sanctioned live `run_cycle`**: rc=0, summary `{decision: BRACKET, price: 56130.0, mode: live, tweaks: [], hypo_events: [], armed_detail: []}`, 0 Tracebacks; **pending_orders.json diff = 0** (idempotent re-derivation, F-4 held), **tweak_struct_state.json unchanged** (book flat → lag skipped). Rung states: `btc-auto-ladder-1795234161 short 55796/SL59416` = fired (#17015's add), `btc-auto-ladder-1795241362 short 55496/SL55868` = **retested** (armed 06:09), `btc-auto-ladder-long-1795241362 long 56564/SL56191` = unfired.
- Logs since 05:45: pipeline.log 0, trade-watchdog.log 0, sync-guardian.log 0 Tracebacks.
- Scope: `git diff 6a6099b4..3dbc10c4 --stat` = exactly `scripts/auto_trader.py` (+21), `scripts/position_manager.py` (+18/−2), `scripts/hl-sync-guardian.py` (+14/−2); no uncommitted script edits; symlink `scripts/hl_sync_guardian.py` (120000) → target `scripts/hl-sync-guardian.py` (100644) is the file that changed.

## 9. (Addendum iii) sidesight — round-anchor vs the RSI ≤35 band finding

The band's losers were `manual_sl_hit` on bounces out of oversold entries — under the old BE-cap-only exit each sat at entry×1.001 and the bounce booked ≈ −1% margin; with the round-ratchet the same trade exits at the round nearest the slide's low, so when that round is below entry (the normal case on a real slide) the bounce exit becomes a small win instead (this very trade: would-be −8.9% margin → **+2.04%**). Trade-off to watch in the band data: the stop now hugs price, so a shallow reclaim stops the trade out earlier than the BE-cap would have — the band's 20% WR should improve in *loss size*, not necessarily in *exit timing*, and n=10 stays too small to claim more.

## 10. Overall verdict

**CONDITIONAL PASS — round-anchor (A) fully verified and live-proven; stack-leader (B) verified in guardian and in pm's function contract, but pm's production call site bypasses it (H-1 HIGH).** Nothing in the two commits can exit the whole stack at the add's breakeven *through guardian*, and the round-anchor's ordering incidentally keeps the leader's stop the tightest — but the pm half of the safety fix as shipped is dead code, so the CEO's guarantee currently rests on one checker plus luck of ordering, not on both checkers as committed. Recommended before the next stack forms: make pm:3742 pass the full open-position list (one-line fix), decide M-1/M-2 policy, and add the L-1/L-2 guards at the price guard. No fix applied — verifier scope.

---

## 11. Acceptance round — fix commit `b3207603` (2026-11-21 06:51) — **FINAL: PASS**

Re-checked the fix diff directly (adversarial duty, despite "no re-verification needed"):

- **H-1 closed:** `position_manager.py:3742-3746` now `atr_hits = [h for h in check_atr_tp_sl_hits(positions) if h.get('trade_id') == pos.get('id')]` — the leader map (pm:596-601) sees the full sibling set every call; the filter keeps each iteration closing only its own row. Production-pattern re-test reported green (follower tight stop ignored / leader fires the stack / flat row self-governs).
- **L-3 closed:** `_apply_stop(new_val, old, pid, rule='R1')` (auto_trader:395) — default preserves every existing lag path; both round call sites pass `rule='ROUND'`; `rule` flows into the tweak dict + `log_event` (auto_trader:404-406). Next ratchet will audit as ROUND.
- **I-3 closed:** `analysis/test_pending_machine.py` committed (221 lines, 7 groups, runs shipped source, stdlib+mocks). The two corrected expectations were test bugs, not code bugs — accepted; this is exactly the reproducibility gap I-3 flagged.

**O(N²) question — confirmed good with the per-row call, and hoisting would be the wrong trade:**
1. **Cost:** N ≤ `MAX_OPEN_POSITIONS` = 6 → ≤6 calls × (O(N) leader map + O(N) row checks + one `_is_closing_marker_active` JSON/FileLock read per row) ≈ ≤36 small file reads per 30-min cycle, no DB I/O in the checker — sub-millisecond. Trivial as flagged.
2. **Hoisting is NOT semantics-preserving:** the ATR check sits *after* each row's in-place trail writes (mxm pm:3648, ride-it pm:3656 set `pos['stop_loss']` inside the same iteration). A single call hoisted before the loop would snapshot stops *before* all trail writes; hoisting after would require reordering the exit-priority contract (ATR must run first, before wave_turn/cascade). The full-list-per-iteration pattern preserves the exact priority order while making the leader map complete — minimal diff AND the semantically safe choice.
3. **Safe-direction edge:** a row closed mid-loop stays in `positions` for the rest of the cycle → followers remain gated by the closed leader (suppresses dual-close — the safe direction; guardian's HL race guard covers the rest; `refresh_current_prices()` drops it next cycle).

**M-1 / M-2 / L-1 / L-2 / I-1 / I-2 dispositions accepted as written (no fix required).**

# ⇒ FINAL VERDICT: **PASS** — both shipped commits (89a0bb24 + 3dbc10c4) plus the fix commit b3207603 verified; round-anchor live-proven end-to-end (56,693.637 → 56,000 → reclaim exit +2.0374% with the stack never exited at the add's breakeven), stack-leader now effective in BOTH checkers, committed suite closes the reproducibility gap.
