# Bug-Hunter Verdict: CEO-Trade Breakeven Lock (commit c4edf08b)

**Date:** 2026-10-23 ~13:45 UTC
**Verifier:** bug_hunter (independent, adversarial)
**Target:** `c4edf08b` — "exit-system: breakeven lock for CEO trades — SL→entry at +0.10% (CEO-approved)", live ~13:29 UTC
**Harness:** `/tmp/verify_breakeven.py` (rerunnable; all numbers below are actual output)

---

## Verdict Table

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| A | Full diff read; constants addition-only | **PASS** | `git diff HEAD~1`: hermes_constants.py +7 lines, 0 deletions — only `PM_BREAKEVEN_LOCK_PCT = 0.001` added at line 1693. `PM_TRAIL_ACTIVATE_PCT = 0.004` (line 1685) and `PM_TRAIL_DISTANCE_PCT = 0.002` (line 1686) byte-identical. `CEO_PROTECTED_FLAGS` DO-NOT-CHANGE dict entries (lines 2881–2882) untouched. manual_exit_manager.py: `decide_sl` added (additive), `update_trail` signature/CAS byte-identical to `HEAD~1`. |
| B | Phase boundaries, ratchet, direction, guards | **PASS** (1 LOW, see F-1) | Boundaries (entry=100): 0.099%→None ✓; 0.399%→BE-LOCK(100) ✓; 0.40%→TRAIL(100.1992) ✓; exactly-0.10%→None ✗ (FP, LOW). Ratchet: 400,000-case random walk (200k/dir, prices 1e-4…1e5, SL 0.9–1.1×entry) → **0 wrong-direction moves, 0 SL-above-price writes**. Direction validation: 'long','Long','SHORT ', '', None, 'BUY', 'UNKNOWN' → all None (no SHORT fall-through). Guards: price=0/−5, entry=0, sl=0/−1 → all None. TP: `decide_sl` has no TP parameter; the CAS UPDATE (line 120) sets only `stop_loss` — TP structurally untouchable. |
| C | CAS vs CEO edits; CEO profit-lock preserved | **PASS** | CAS `WHERE … AND stop_loss = %s` (line 120) compares against `pos['stop_loss']` read at cycle start; any CEO edit between read and write → rowcount 0 → skip + WARN (lines 124–127). CEO SL ABOVE entry for LONG: `old_sl=102, price=100.2 (+0.2%)` → **None** (BE would lower 102→100, ratchet blocks); `old_sl=100.5, price=100.5 (+0.5%)` → **None** (trail would lower); `old_sl=102, price=103 (+3%)` → 102.794 (correct upward ratchet). SHORT mirror: `old_sl=98, price=99.8` → None; `old_sl=100.5, price=99.8` → 100 (BE, correct tightening). `old_sl == entry` exactly → None, no write, no log spam. |
| D | Call-site compatibility, hoist, no removed internals | **PASS** | `position_manager.py:3171` `_mxm.update_trail(pos, direction, _mx_cur, _mx_entry)` matches `(pos, direction, current_price, entry_price)` — unchanged signature. `is_ceo_trade` hoisted to loop top (2875–2876), consumed at 2915 (sl-zone guard), 3162/3167 (RR exclusion + trail call). `trade_watchdog.py:1719–1727` uses only `is_managed_signal`. Repo-wide grep: no caller references anything removed — nothing was removed (old module's 3 public names all retained; `decide_sl` is additive). |
| E | Trail ≥0.40% behavior-identical to old code | **PASS** | Old logic reimplemented inline (`old_decide`) and swept 400,000 random cases (200k/dir): **0 mismatches** in the ≥0.40% band — same formula `price ∓ 0.20%`, same `round(...,8)`, same ratchet compare, same CAS. The ONLY behavioral delta is the new [0.10%, 0.40%) BE band. |
| F | BE→trail supersede; dips never move SL backward | **PASS** | Min trail SL at activation = entry×1.004×0.998 = entry×**1.001992 > entry always** (verified for p=0.40%, 0.4001%, 0.5%, 1.0%) — no gap where trail is active but can't beat BE. LONG sequence (entry=100, old_sl=98): 100.15→**BE 100**; 100.2 hold; 100.05 hold; 99.95 hold (below entry, untouched); 100.39 hold (BE-band new_sl=100 ≤ 100 — **no backward move**); 100.45→**TRAIL 100.2491**; 100.35 hold (trail-band, 100.1991 ≤ 100.2491 blocked); 100.6→TRAIL 100.3988. SHORT mirror: 99.85→BE 100; 99.7/100.02/99.61 hold; 99.55→TRAIL 99.7491; 99.75 hold; 99.4→TRAIL 99.5988. |
| G | Import/syntax clean post-13:29 in pipeline.log | **PASS** | After 13:29 UTC: position_manager ran **rc=0 at 13:32:21 and 13:33:20** (loop body executed with 1 open position → `import manual_exit_manager` at line 2875 executed in a fresh process); pipeline finished `=== Pipeline done (LIVE) ===` 13:39:24. Zero Traceback/ImportError/SyntaxError/NameError; only pre-existing "DRY RUN — orphaned positions" WARNs (13:31/13:41). **Caveat:** no `[MANUAL-TRAIL]` log lines exist yet — sole open trade #16365 is `bb-bounce-v2-long+` (not a CEO trade), so decide_sl's DB-write path has not yet been exercised by live data; runtime validation rests on the fresh-process import succeeding + pure-function tests. |
| H | Label semantics (BE-exit → manual_sl_hit) | **PASS** | BE-lock writes SL == entry; relabel at `position_manager.py:561–564` uses `_profit_side = sl > entry` (LONG) / `sl < entry` (SHORT) → equality → **manual_sl_hit** ✓ (matches module docstring line 25). Columns are `numeric(15,8)` and BE writes `round(entry_price, 8)` — exact scale match, no float-equality drift. All three `manual_*` labels are in the HL stale-order cleanup tuple (position_manager.py:1405–1406). Non-CEO trades unaffected (rr_engine_trail_hit/atr_trail_hit paths intact). A BE exit at price==entry fires `cur <= sl` → scratch at ~0% minus fees — by design. |
| I | Own harness (boundaries, ratchet, sequences) | **PASS** | `/tmp/verify_breakeven.py` — all A–F/I cases pass except the FP boundary case (F-1 below). `is_managed_signal` scoping verified: 'ai-trader-manual/pending/auto' → True; 'ai-trader+' and plain 'ai-trader' → **False** (intentional: auto-signal trades keep their engines, per SKILL.md). |

---

## Findings

### F-1 — LOW — FP boundary: exactly +0.100% profit does not trigger BE-lock
`manual_exit_manager.py:60` (`profit_pct < PM_BREAKEVEN_LOCK_PCT`). `(100.1 − 100)/100 = 0.0009999999999999432 < 0.001` → None. Measured at 5 representative entries (100, 0.034508, 82000, 1.23456789, 1.234e-05): all landed microscopically **below** the threshold at exactly 0.10%, so the effective boundary is 0.10% + ~1e-16 relative. The same fuzz exists at the 0.40% boundary (old code too — there it happened to round UP for entry=100: 0.0040000000000000565). **Impact:** at the exact boundary the BE-lock fires one price tick later. Price ticks are orders of magnitude larger than the epsilon — financially negligible. Not a regression; inherent IEEE-754 threshold comparison.

### F-2 — MED (PRE-EXISTING — not introduced or worsened by this commit) — NaN/Inf price can be written to stop_loss and silently disables the stop
`manual_exit_manager.py:55` guard `current_price <= 0` does **not** reject NaN (all NaN comparisons are False), and the ratchet compare `new_sl <= old_sl` is likewise NaN-poisoned. Measured: `decide_sl('LONG', nan, 100, 98)` → `(nan, nan, 'TRAIL 0.20%')` — a decision, which `update_trail` would CAS-write to the DB. Verified on this DB (PG 16.15): `'NaN'::float8::numeric` succeeds and `'NaN'::numeric = 'NaN'::numeric` is **true** — so the NaN lands in `trades.stop_loss` AND every subsequent CAS still matches → repeated rewrite + log spam each cycle, while `check_atr_tp_sl_hits` (position_manager.py:536 `cur <= sl`) is False forever → **the stop never fires again** for that trade. `+inf` behaves analogously. **Crucially: identical in `HEAD~1`** (old code had the exact same poisoned-compare path — confirmed by the old-vs-new sweep). Suggested fix (out of scope here): `math.isfinite()` guard in `decide_sl` or `update_trail`. Probability of NaN reaching `current_price` is low (price feed writes 0 on failure, which is guarded), but the failure mode is a permanently dead stop, hence MED.

### F-3 — LOW (process) — claimed "19/19 regression" artifact not preserved
Commit message claims a 19-case regression suite; no test file is committed, and the only scratch harnesses (`/tmp/mxm_verify_1.py`, `_1b.py`, `_2.py`) are dated **Oct 22** — they belong to the prior day's manual_exit_manager introduction, not this BE-lock change. The claim is unverifiable as shipped. (My independent harness covers the same ground and passes, so this is a process gap, not a code risk.)

### F-4 — LOW (hygiene) — commit bundles unrelated runtime data
`automation/ceo/vacation_alerts.json` (alert rotation) and `data/watchdog_recommendations.json` (13:18 watchdog write) ride along in an exit-system commit. Benign content (both are normal runtime writes), but they obscure the diff for the one change that moves live money. Common in this repo's workflow; flagged for hygiene only.

### F-5 — INFO — trades with SL = 0/NULL never receive the BE-lock
Guard `old_sl <= 0 → None` (manual_exit_manager.py:55) means a CEO trade opened without an SL is never BE-locked. Pre-existing (old trail had the same guard) and consistent with the standing policy that SL/TP are mandatory at open; no action needed, recorded for completeness.

---

## Adversarial arguments requested (summary)

- **C (CAS vs CEO edit):** the CAS expected-value is the SL as read at cycle start. CEO edit mid-cycle → `stop_loss <> old_sl` → `rowcount = 0` → skip + WARN; our write never lands. Our write first, CEO edit after → CEO's tool writes unconditionally → CEO wins. A CEO SL **above** entry for a LONG is never lowered: BE branch blocked at line 64 (`new_sl <= old_sl`), trail branch blocked at line 68 whenever `price×0.998 ≤ old_sl` — concrete: entry=100, sl=102, price=100.2 → None; price=103 → 102.794 (upward-only).
- **F (BE then dip):** after BE writes SL=entry, a dip into [below-entry, 0.10%) → untouched (profit < threshold); a dip within [0.10%, 0.40%) → BE candidate = entry ≤ old_sl=entry → blocked. A rip past 0.40% → trail SL ≥ entry×1.001992 strictly beats entry. No sequence moves SL backward — confirmed by both the scripted sequences and the 400k-case random walk.
- **E (equivalence):** trail formula, rounding, ratchet comparison, and CAS are unchanged lines; the 400k-case old-vs-new sweep in the ≥0.40% band produced 0 mismatches.

---

## Overall Verdict

**PASS — no CRITICAL, no HIGH.** The change is scoped exactly as specified: constants addition-only (DO-NOT-CHANGE trail pair untouched), trail band behavior-identical to the old code (0/400k mismatches), ratchet-only in every branch (0/400k violations), CAS/CEO-edit precedence intact, TP structurally untouchable, labels correct (BE exit → manual_sl_hit), imports clean in the live pipeline post-13:29. Ship stands. Follow-ups recommended (not blockers): LOW FP boundary artifact at exactly +0.100% (F-1, cosmetic); MED **pre-existing** NaN/Inf write path with a permanently-dead-stop failure mode — worth a separate `math.isfinite` fix (F-2); process nits F-3/F-4.
