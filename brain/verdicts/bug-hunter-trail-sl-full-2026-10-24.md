# bug_hunter VERDICT — Trailing-SL for manual/CEO trades (full exit path)

**Target:** `scripts/manual_exit_manager.py` (rewritten in `5944793b`, 2026-10-24 15:36:40 UTC) + its
caller/label/state machinery in `scripts/position_manager.py`, `scripts/profit_monster.py`,
`scripts/trade_watchdog.py`, `scripts/hl-sync-guardian.py`.
**Verifier:** bug_hunter (adversarial, no fixes applied — report only)
**Date:** 2026-10-24
**Rerunnable harnesses:** `/tmp/bh_trail_A_units.py` (44/44), `/tmp/bh_trail_B_db.py` (52/52),
`/tmp/bh_trail_C_labels.py` (27/27), plus the committed suite
`python3 /root/.hermes/analysis/test_manual_exit_manager.py` (17/17).
Harness B exercises the **real** `update_trail` against **real PostgreSQL** through a psycopg2 proxy that
rewrites only the table name (`trades` → scratch `bh_trail_scratch`), so statement shape, placeholders,
rowcount and commit semantics are genuine while no production row can be touched. Scratch table dropped,
state file restored to its original (absent) state, `git status` clean of harness artifacts.

---

## ⚠️ PREMISE CORRECTION (read first)

The directive's trade facts are attached to the **wrong trade id**.

| Claim in directive | Database truth |
|---|---|
| "#16377 short entry 79,721 … closed **manual_trail_hit** +1.75%" | **#16377 = BTC SHORT entry 80,629 / SL 81,180 / TP 79,950, closed `manual_sl_hit` −3.4231%** at 2026-10-24 00:00:19 |
| the 79,721 trade | **#16381** — BTC SHORT entry 79,721, TP 79,100, closed **`manual_trail_hit` +1.7373%** at 2026-10-24 **15:22:27** (14 min *before* the rewrite commit at 15:36:40) |
| "actual manual_trail_hit exit **79,441.50**" | DB `exit_price` = **79,444.00**; `stop_loss` at close = **79,402.989** (the old-code trail write from the 15:20:24 log line) |
| "peak price **~79,283**" | actual peak ≈ **79,244.5** (log 15:20:24: `TRAIL … profit 0.60%` ⇒ price 79,244.5) |

`decide_sl` reproduces the CEO's 79,441.50 exactly (79,441.4982) **only** when fed the CEO's assumed
`peak_frac=0.005506`; the *actual* logged peak (0.60%) yields **79,402.12**, i.e. 0.87 tighter than the
old code's 79,402.989 — same tier, same exit, marginally better stop. Both numbers are verified below.

---

## Verdict table

| # | Check | Verdict | Evidence |
|---|---|---|---|
| **A** | Units — fraction space vs percent tier fn, every ×100/÷100 | **PASS** | `M.PM_BREAKEVEN_LOCK_PCT=0.001`, `M.PM_TRAIL_ACTIVATE_PCT=0.004` (fraction) while `profit_monster.PM_TRAIL_TIERS=[(0,0.2),(1.5,0.5),(3.0,0.8),(5.0,1.2)]` (percent) after `profit_monster.py:26`. Single conversion at `manual_exit_manager.py:123` `dist_frac = _trail_distance_for_peak(peak_frac*100)/100.0` — **no other ×100 or ÷100 anywhere in the module** (exhaustive read of all 220 lines; the only other `*100` are `:132` and `:204`, both log-formatting). The constants are imported **directly from `hermes_constants`**, not through profit_monster, so profit_monster's `PM_TRAIL_ACTIVATE_PCT *= 100` rebinding cannot leak (proved A1/A3). Unit probes: phase string reports `dist 0.20/0.50/0.80/1.20%` at peaks 0.6/2.0/3.5/6.0% (A5–A8); numeric floors exact to 1e-9 (A9). A missing `/100` would read `dist 20.00%`; a missing `*100` on peak would pick tier-1 for a 2% peak — both caught. |
| **B** | Sign correctness per direction + real-trade calibration | **PASS** | LONG `entry*(1+floor)` strictly above entry, SHORT `entry*(1−floor)` strictly below, over 5 entries × 6 peaks (B1/B2), intra-tier monotone (B3). **#16381 (the trade the directive calls #16377):** new code at the real 0.60% peak → SL **79,402.12** vs old code's actual `stop_loss` 79,402.989 (Δ 0.87, tighter); tier-1 dist provably identical to the old fixed 0.20% (B4a/b). CEO-stated 79,441.50 reproduced at 79,441.4982 (B4c). Full trajectory replay of #16381 through the real `decide_sl` **plus** `position_manager`'s exact hit-check ordering closes **`manual_trail_hit` @ 79,442.67** (actual 79,444) — B8. Real #16377 (entry 80,629, SL 81,180) correctly untouched below +0.10% (B4d). **#16351 TP safety:** trail SL 81,964.2 stays above TP 81,800 (B5); a monotone fall through the TP closes `manual_tp_hit` (B6); a choppy path exits either at TP or at a trail fill *above* the TP (B7). Structural argument: the trail can only fire at `peak − tier_dist`, and if peak had ever reached the TP distance the TP would already have closed the trade — so the trail can never undercut a TP. |
| **C** | Phase boundaries 0.099/0.10/0.399/0.40%; floor ≥ +0.20%; floor ≥ 0 | **PASS** | Untouched below BE; BE-LOCK at ~0.10%; still BE at ~0.399%; TRAIL at ~0.400% (C1–C3, both directions). Sweep 0.4001%→34.4% peak: worst floor **+0.2000%**, never negative (C4/C5). Trail→BE fallthrough refused (C6/C7) because BE-LOCK ratchets (`:116-118`) and a trailed stop is always better than entry. |
| **D** | Tier-boundary relaxation written for our stops, refused for CEO stops | **PASS (real DB path)** | Harness B3, real Postgres: own stop `last_sl==live` → peak 1.49→1.51 **writes 101.29 → 101.01** (B3a). CEO-tightened `live 101.40 ≠ last_sl 101.29` → **refused**, DB untouched, peak still persisted, `last_sl` unchanged (B3b–d). CEO-loosened `live 100.50` → **improved back to 101.29** (B3e). After reclaim, relaxation allowed again (B3f). Mechanism: `manual_exit_manager.py:168-178`; `decide_sl`'s trail branch deliberately has no ratchet (`:121-133`), so this guard is the *only* thing standing between a CEO stop and a relaxation — and it holds. |
| **E** | State file: concurrency, corruption, atomicity, prune, key types, growth | **PASS (2 findings)** | Only caller repo-wide is `position_manager.py:3172` (L4: 2 occurrences of `update_trail(` in all of `scripts/` = the def + that one call), and `trade_watchdog` imports only `is_managed_signal` (`trade_watchdog.py:1743-1751`) — so the pipeline lock genuinely serialises access. Corrupt JSON → `{}`, self-heals next save (B6a/b). `os.replace` atomic, no `.tmp` residue (B6g). Prune drops >72h, keeps 71h (B6e). `int` trade_id round-trips to the same `str` key via JSON — **no** silent peak loss (B6f). Growth bounded: entries only for trades `update_trail` actually saw, pruned after 72h (B6h); with `UNIVERSAL_MAX_HOLD_MINUTES = 480` (8h) an open trade can never outlive the 72h prune, so pruning cannot silently reset the peak of a live trade. ⚠️ See **F-2** (malformed sibling entry) and **F-5** (`peak_frac: null`). |
| **F** | CAS / concurrent edit / closed trade / in-memory sync / hit-check column | **PASS** | Statement byte-exact `UPDATE trades SET stop_loss=%s WHERE id=%s AND status='open' AND stop_loss=%s` with params `(new_sl, trade_id, old_sl)` (B4b/c). Stale in-memory SL → rowcount 0 → False, DB untouched (B4a). Closed trade → rowcount 0 → False (B4d). Missing/zero id → False with no query (B4e). `pos['stop_loss'] = new_sl` on success (`manual_exit_manager.py:199`) and `check_atr_tp_sl_hits` reads `pos.get('stop_loss')` from the **same dict** (`position_manager.py:503`) which was loaded from `trades.stop_loss` (`get_open_positions`, `position_manager.py:329`). Ordering: `update_trail` at **L3172** precedes `check_atr_tp_sl_hits([pos])` at **L3266** in the same iteration (J1–J3), so the trail SL is always the one the hit check sees. |
| **G** | Labels: profitable cross → `manual_trail_hit`; BE/predefined cross → `manual_sl_hit` | **PASS in position_manager / **MED finding** (guardian)** | Executed through the real `check_atr_tp_sl_hits`: 13/13 label cases (G1–G13) — profitable trail cross both directions → `manual_trail_hit`; BE-lock cross **at equality** → `manual_sl_hit` (equality is not the profit side: `sl > entry` / `sl < entry`, `position_manager.py:562-565`); predefined SL on the loss side → `manual_sl_hit`; TP → `manual_tp_hit`; non-managed signals keep `atr_sl_hit`/`atr_trail_hit`. ⚠️ `hl-sync-guardian.py:_check_hard_stops` has **no** `manual_*` relabel — see **F-1**. |
| **H** | Import chain, import-time side effects, pipeline pickup | **PASS** | Chain is a DAG: `position_manager → manual_exit_manager → profit_monster → {paths, hermes_constants, hermes_log, hermes_file_lock}`; **no back-edge** (profit_monster does not import manual_exit_manager or position_manager — full AST scan). `profit_monster` module-level statements are only three `Path(...)` constructions — no file read/write, no DB, no network at import. Fresh-process import of the whole chain succeeds and produces the correct decision (`decide_sl('SHORT', 79244.5, 79721, 79721)` → `TRAIL floor +0.40% … 79403.94`). Pipeline after the 15:36:40 commit: position_manager **rc=0 at 15:36:50, 15:37:21, 15:38:20, 15:39:21, 15:59:20, 16:00:25, 16:01:34** — zero Traceback/ImportError/SyntaxError. **Caveat (recorded, not a defect):** the live process has *not yet executed* the new code path — with 0 open positions the loop body (and therefore `import manual_exit_manager` at L2876) never runs. Live validation therefore rests on the fresh-process import + the 44+52+27 harness assertions, exactly as with the 2026-10-23 BE-lock change. |
| **I** | Committed suite + extensions (peak regression, SHORT giveback, BE→trail→tier2) | **PASS** | `python3 analysis/test_manual_exit_manager.py` → **17 passed, 0 failed**. Extended: peak never regresses across 9 `update_trail` calls against the **real file path** (B1, 9/9); SHORT 0.3%-bounce giveback never moves the SL backward and never regresses the peak (B2, 7/7); full BE→trail→tier2 walkthrough on the real DB path (B7, 7/7) — `+0.10%→SL=entry`, `+0.40%→floor +0.20%`, `1.49%→floor 1.29%`, `1.51%→floor 1.01%` (relax), `3.00%→floor 2.20%`, giveback to 2.90% leaves SL at 102.20, `4.00%→floor 3.20%`. |
| **J** | Behavior compatibility for #16381's scenario + no stale open CEO stop | **PASS** | Tier-1 distance is byte-identical to the old fixed 0.20% (B4b); the only divergence from old code is the anchor (`entry*(1−floor)` vs `price*(1+dist)`), which differs by `dist*(entry−price)` = **0.87** on #16381 — tighter, not looser. Replay closes `manual_trail_hit` exactly as the real trade did (B8). Open trades right now: **0** (`SELECT count(*) FROM trades WHERE status='open'`), and `data/manual_trail_state.json` **does not exist** → no open CEO trade carries a stale trail SL and no orphan state. |

---

## Findings

### F-1 — MED — `hl-sync-guardian.py:_check_hard_stops` has no `manual_*` relabel → CEO exits get guardian labels
`hl-sync-guardian.py:1960-2070`. The guardian's independent hard-stop check reads the **same** `trades.stop_loss`
column our trail writes, and labels a profitable cross `trail_sl`, a loss cross `hard_sl`, a TP cross `hard_tp`
(`:2046-2070`). There is no `is_managed_signal()` branch anywhere in it. `position_manager.py:547-565` was
rewritten on 2026-10-22 precisely so that "the exit-reason is unambiguous about WHO managed the trade", and
`skills/shared/full-analysis/SKILL.md:70-85` treats a non-`manual_*` label on a CEO trade as a leak — the
guardian is a second leak.

*Real evidence, not hypothetical:* the trades table already contains **2 CEO trades closed `hard_tp`**
(`SELECT close_reason … WHERE signal LIKE '%ai-trader-%'` census). `hard_max_loss` ×2 is intentional (a
safety net) but `hard_tp`/`hard_sl`/`trail_sl` are pure mislabels.
*Mitigating fact:* `atr_managed` defaults to `false` and is `false` for #16351/#16377/#16381, so the guardian's
`_margin` is `0.0` (`hl-sync-guardian.py:2043`) — it fires at the **same** threshold as position_manager, so this
is a race for the label, not a systematically worse exit price. If `atr_managed` were ever TRUE on a CEO trade
the guardian would fire 0.1% *beyond* the SL and beat us to the exit as well.
*Suggested fix (not applied):* add the same `is_managed_signal` relabel used at `position_manager.py:552-565`
inside `_check_hard_stops`, before the close.

### F-2 — MED — one malformed state entry permanently disables all state persistence
`manual_exit_manager.py:76-77` — `_save_state` prunes with `float(v.get('ts') or 0)` inside a dict
comprehension **inside** the `try`. Any non-dict value in the state file raises `AttributeError`, the whole
save is skipped, and — because nothing is ever written — the poison entry **never ages out**. Proved: B6c
(`state save failed: 'str' object has no attribute 'get'` every cycle, file unchanged) and K2 (survives
repeat save attempts).
Consequence chain, all proved: peak/last_sl stop persisting → on the next trail decision `last_sl` is stale
or absent → the CEO guard either misfires or is bypassed → **the trail silently relaxes an already-written
stop** (K1: previously written 101.29 recomputed to 101.01 with a lost peak). Only a WARN is logged.
*Suggested fix:* prune defensively (`if not isinstance(v, dict): drop it`) so one bad entry self-heals.

### F-3 — LOW — state loss silently relaxes our own stop
`manual_exit_manager.py:122-133` + `:168`. With `peak_frac` lost (corrupt JSON, deleted file, or the
F-2 lockout) the floor is recomputed from the *current* profit, which can be below the floor already on the
book; the trail branch has no ratchet, so the lower SL is written (proved K1). Bounded in practice:
`UNIVERSAL_MAX_HOLD_MINUTES = 480` means no trade outlives the 72h prune, so pruning alone can't cause this —
it needs actual state loss. Worth a belt-and-braces `new_sl` vs `old_sl` comparison for our own stops when
`last_sl is None`.

### F-4 — LOW — no-op UPDATE returns True and inflates `adjusted_count`
`manual_exit_manager.py:191-205`. While price sits inside the trail band, `new_sl == old_sl`; the CAS still
matches (Postgres reports rowcount 1 for a matched row regardless of value change), so the function issues an
identical UPDATE, syncs `pos['stop_loss']` to the same value, rewrites the state file, logs
`$100.4 → $100.4 (TRAIL floor …)` and **returns True** — which `position_manager.py:3173` counts as an
adjustment. Proved B5a/b. Cosmetic: ~30 extra UPDATEs/hour per in-band CEO trade, noisy logs, inflated
counter. A `if new_sl == old_sl: return False` short-circuit before the CAS would fix it.

### F-5 — LOW — BE-LOCK branch persists `peak_frac: null`
`manual_exit_manager.py:119` returns the (still-`None`) `peak_frac`, and `:172`/`:200` store
`new_peak or peak_frac` → `null` in JSON. Harmless (`decide_sl` does `peak_frac or 0.0` at `:122`), but the
state schema is nullable and a reader must handle it (my harness tripped on it twice). Store `0.0` instead.

### F-6 — LOW (latent, unreachable today) — spider tier reassignment can break the ≥ +0.20% floor guarantee
`profit_monster.py:497-501` rebinds the module-global `PM_TRAIL_TIERS` to a **mixed-unit** list
`[(0.0,0.1),(0.015,0.3),(0.030,0.5)]` (mins are fractions, distances are percents) when spider is active.
`_trail_distance_for_peak` (`profit_monster.py:366-373`) reads that global **at call time**, and
`manual_exit_manager.py:123` imports the *function*, so the manual trail inherits it. Proved: with those
tiers loaded, `decide_sl` at peak 0.55% returns **floor +0.05%** — the "floor is always ≥ +0.20% after
activation / every exit books profit" guarantee is broken, and the trade would book *below* its activation
profit.
**Not reachable today:** the only importer of `profit_monster` is `manual_exit_manager` (repo-wide AST/grep),
and `profit_monster.run()` executes only in profit-monster's own process, never in position_manager's.
Flagging because it is a module-global side channel that would fail silently and invisibly if anyone ever
calls `profit_monster.run()` in a process that also manages CEO trades. A local copy of the tier table (or
freezing it at import) would remove the coupling.

### F-7 — LOW — a CEO-tightened stop can end up below the CEO's own level
`manual_exit_manager.py:168-178`. Sequence proved in B3e→B3f: CEO loosens the stop → we improve it
(`last_sl` becomes ours) → the next tier boundary relaxes freely, potentially **below the level the CEO had
hand-set**. Defensible ("once we've overwritten it, it's our stop") and consistent with PM semantics, but it
is a behaviour the CEO should know about, since the guard's headline promise is "never relax a CEO stop".

### F-8 — LOW (pre-existing, already documented) — IEEE-754 boundary artifact, direction-dependent
At exactly +0.100% the threshold comparison is a coin flip on the entry price: proved F1 — LONG at exactly
+0.100% returns `None` while SHORT at exactly +0.100% returns `BE-LOCK`. Same at +0.400%. Financially
negligible (one tick), already logged as F-1 in `brain/verdicts/bug-hunter-breakeven-lock-2026-10-23.md`.
Not a regression of this rewrite.

### F-9 — LOW (doc) — misleading comment on the tier table
`hermes_constants.py:1780` says *"first match wins, never tightens"*. `_trail_distance_for_peak` takes the
**last** matching tier (highest applicable) and the tier system **does** loosen at boundaries — which is the
intended behaviour and exactly what the new module relies on. The code is right; the comment would send the
next reader to "fix" it into a bug.

### F-10 — LOW (pre-existing) — gap-through-TP is labelled a trail exit
`position_manager.py:536-545` checks `cur <= sl` **before** `cur >= tp` for LONG. A giant candle that gaps
through both closes at market (money correct) but is labelled `manual_trail_hit`/`atr_trail_hit` instead of
`manual_tp_hit`. Affects all trades, not just CEO trades; noted because the "TP as giant-candle backstop"
story in the new docstring is the one place this bites.

---

## What was NOT found (explicit negatives)

* No ×100/÷100 slip anywhere in `manual_exit_manager.py` — the module contains exactly one unit conversion
  (`:123`) and it is correct; constants arrive in fraction space and the tier function runs in percent space.
* No circular import, no import-time I/O, no import-time DB/network in `profit_monster`.
* No second caller of `update_trail` anywhere in the repo; no second SL writer that touches a CEO trade —
  every other writer is gated: ATR collection `position_manager.py:2086`, sl-zone `:2916`, pump-exit `:2955`,
  ride-it `:3133`, RR engine `:3163`, `trade_watchdog.py:1751` (`move_stop`), `ride_it_exit.py:234` (only
  reachable through the gated `:3135`), `adjust_stop_loss` (`position_manager.py:1629`) is `paper = TRUE` only.
* The TP is structurally untouchable — the only UPDATE in the module touches `stop_loss`.
* No unbounded state growth, no `.tmp` litter, no int/str key mismatch, no NaN/Inf write path (guards at
  `:97-105` all hold).
* No stale trail SL on any open trade (there are no open trades), and no orphan state file.

---

## Overall verdict

**PASS — ship stands. No CRITICAL, no HIGH.** The rewritten trail is unit-correct, direction-correct,
phase-correct, floor-bounded (≥ +0.20%, never negative), CAS-correct, ratchet-correct on CEO stops, and
label-correct through position_manager. It reproduces the one real `manual_trail_hit` trade (#16381) with a
*marginally tighter* stop than the code it replaced, and the committed suite plus 123 independent assertions
all pass.

Two MED items to schedule (neither is a money bug): **F-1** — the guardian will keep stealing
`hard_sl`/`hard_tp`/`trail_sl` labels on CEO exits (already happened twice); **F-2** — a single malformed
state entry permanently kills peak persistence and thereby opens the door to a silent stop relaxation (**F-3**).
The rest are hardening/doc notes.
