# bug_hunter verdict — structure-lag adverse-swing fix (#16882)

- **Target commit:** `8532ce50` "fix: structure-lag never CHASES an adverse swing"
  (verified against working tree = HEAD `4e492a40`, which adds a 2-line
  top-level state-type guard at `scripts/auto_trader.py:408-409` — does NOT
  touch the adverse logic; harness re-run against HEAD = identical result)
- **Date:** 2026-11-12 18:3x UTC
- **Method:** real-code replay harness (`/tmp/bh_lag_harness.py`, fake psycopg2,
  temp `HERMES_DATA_DIR=/tmp/bh_hermes_data`, zero live/production writes),
  code trace, PG SELECTs, log greps, suite run.
- **Harness result: 44/45 checks PASS** (output: `/tmp/bh_harness_out.txt`)

## Verdict table

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| A1 | SHORT seed sh=72459.4, stop 71950 → no write, state recorded | **PASS** | `writes=[]`; state `{'sh':72459.4}` |
| A2 | favorable sh=72295 → 71950→72490.4 (=72459.4+31) | **PASS** | `writes=[(71950, 72490.4)]` — matches event trail 15:19 |
| A3 | favorable sh=71740 → 72490.4→72326 | **PASS** | `writes=[(72490.4, 72326.0)]` — matches 15:49 |
| A4 | **ADVERSE sh=72191.5 → ZERO stop writes, state updated** | **PASS** | `writes=[]`, state `sh=72191.5`. THE #16882 regression test: stop stays 72326 (old code chased to 71771 → hit at 16:53) |
| A5 | spec expectation "favorable 71900 → no-op (72222.5 == current stop)" | **FAIL (spec arithmetic, not code)** | actual `writes=[(72326, 72222.5)]`. After A3 stop=72326 and A4 writes nothing, "current stop" cannot be 72222.5 — no sequence of A1–A4 leaves stop at 72222.5 (A4's no-raise path keeps 72326; any A4 raise would leave ≥72327). Spec premise is wrong; the actual write is the design-correct one-behind favorable trail (72326→72222.5 = prev structure 72191.5+31, still > price 71900, still under CEO 72500). See finding F-1 |
| A5b | no-op IS reachable, but only via price-floor within 1 of stop | **PASS** | at price=72253.5: floor 72325.75, \|72326−72325.75\|=0.25≤1 → no write (different reason than spec claims) |
| A6 | adverse + tight stop (71950) → raise to 72222.5 | **PASS** | `writes=[(71950, 72222.5)]`; state recorded |
| A7 | LONG seed (sl 69000, stop 68500) → no write | **PASS** | `writes=[]`, state `sl=69000` |
| A8 | LONG favorable sl 69300 → 68500→68969 (=69000−31) | **PASS** | `writes=[(68500, 68969)]` |
| A9 | LONG adverse sl 69100, stop 69269 → ZERO writes + state | **PASS** | `writes=[]`, state `sl=69100` (t2 69069 < 69270 → keep) |
| A10 | LONG adverse + stop beyond (68500) → raise 68500→69069 (=69100−31) | **PASS** | `writes=[(68500, 69069)]` |
| B1 | Adverse clamps can never invert direction (cap/floor off-by-direction) | **PASS** | Code trace: clamps run FIRST (`auto_trader.py:475-479`), gate runs AFTER (`:480` `target = t2 if t2 > stop + 1 else None`). Applied ⇒ t2 strictly > stop+1 ⇒ cannot lower, for either side. 9 hand-built clamp-edge cases (1.05p cap binds, 1.001p floor binds, 0.95p floor binds, 0.999p cap binds, t2==stop+1 boundary, t2 within 1pt) all correct |
| B2 | Adverse brute sweep | **PASS** | 72 cases (3 prices × 3 stop offsets × 4 ATRs × 2 sides) → 36 writes: **0** lowerings, **0** at/beyond price, **0** outside ±5% price band |
| B3 | Favorable bump w/ stale/huge prev_sh — cap vs PRICE not entry | **PASS** | prev_sh=1,000,000, entry=60,000, price=71,000 → write exactly 74,550 = price×1.05 (`:435` `min(want, price*1.05)`; floor `:434` price×1.001). LONG mirror: stale prev_sl=10,000, entry=80,000, price=69,500 → 66,025 = price×0.95 (`:443`) |
| B4 | Breached stop → zero writes (F-3) both sides | **PASS** | stop==price and stop-through-price cases: `writes=[]` (`:424`) |
| C1 | Adverse raise CAS-miss (rowcount 0) → state NOT recorded | **PASS** | forced rowcount 0 → 1 UPDATE attempt, state stayed `sh=71740` — branch falls to `elif` (`:486`) → `_apply_stop` False → no record |
| C2 | CAS-miss retried next cycle | **PASS** | next call: `writes=[(71950, 72222.5)]` + state `72191.5` |
| C3 | Favorable CAS-miss → F-6 preserved | **PASS** | not recorded → retried → write+record |
| C4 | Adverse no-raise records immediately (no CAS) | **PASS** | 0 UPDATE attempts even under forced-miss, state `72191.5` (`:481-485`) |
| D1 | Breached + no state → NO seed (F-3 precedes seed) | **PASS** | state file `{}` (F-3 `:424` < seed `:444`) |
| D2 | Breached + adverse → state stuck (no update) | **PASS** | state unchanged at `71740`, 0 writes — see finding F-2 |
| D3 | Breach recovery with stale prev → safe raise only | **PASS** | `writes=[(71900, 72222.5)]`, state unstuck — stale state cannot cause a chase or a breach |
| E1 | `analysis/test_manual_exit_manager.py` | **PASS** | `20 passed, 0 failed` (rc=0) |
| E2 | py_compile + fresh import | **PASS** | both OK (re-run against HEAD `4e492a40`) |
| E3 | Live `auto_trader.py` cycle rc=0, zero Tracebacks | **PASS** | run with `HERMES_DATA_DIR=/tmp/bh_livecycle` (config + candles.db copy — zero live writes): **RC=0**, stderr empty, 0 Tracebacks, `enabled=True mode=live decision=BRACKET price=71958.9`, tweaks=[] (0 open positions), no arms fired (R:R/ITM gates). Additionally the production watchdog ran `run_cycle()` in-process post-fix at 17:49:54 and 18:19:55 — both completed, and `auto_trader cycle failed` appears **0 times** in the entire trade-watchdog.log |
| E4 | pipeline.log tail | **PASS** | 0 Tracebacks in the whole file; tail (18:30:32) normal rc=0 steps |
| E5 | No unexpected other `stop_loss` writer for ai-trader-* | **PASS (with note)** | grep of all 10 `UPDATE trades SET stop_loss` sites: position_manager writers all guarded `not is_ceo_trade`/`is_managed_signal` (ATR `:2151`, pump `:3197`, RR `:3405`, soft `:3867`, MFE `:4393`, ride-it `:3375`); XMIRROR clear `:3105` is hl_copy-namespace only (`trust_tiers.py:77-96`); decider_run SL-FIX `:6656/:6676` is exec-time wrong-side correction inside its own open path (ai-trader trades open via brain.py, not there). **One real co-writer:** `manual_exit_manager.py:262` MANUAL-TRAIL runs on ai-trader trades **by design** (coexist gate `auto_trader.py:493-495`) and fully stands down for `dynamic_sl:false` legs (`manual_exit_manager.py:197`) |
| E6 | Armed config orders carry `dynamic_sl:false` | **PASS** | all 13 entries in `data/pending_orders.json` have `dynamic_sl:false`; UNFIRED ones (`btc-ceo-long-75630`, `btc-auto-1794264564-659cac-long`, `btc-ceo-long-breakout`, `btc-ceo-long-72560`, `btc-ceo-short-71440`; plus `hype-short-7060` in one-shot `error` state) — all False |
| F1 | No open BTC trade | **PASS** | PG SELECT: `status='open'` → **0 rows** (all tokens). #16882: closed, entry 71637, exit **71789**, `manual_sl_hit`, **−1.0609%**, close_time 2026-11-12 16:53:27 (stop_loss column still holds the pre-fix chased 71771.1995 — historical record only) |
| F2 | State file still holds `16882` — harmless? | **PASS** | `data/tweak_struct_state.json` `16882 → {sh:72191.5, ts:1794502194}` (≈16:49, written pre-fix). Key is only read when trade id 16882 appears in `open_positions` — impossible (PG serial ids never reuse; open count 0). Prune at `:528` drops it at the first dirty save after ts+72h (~2026-11-15). First live exercise of the fix = the next fired rung (fresh key → seed path) |

## Findings

**F-1 (LOW) — verification spec's A5 expectation is arithmetically unreachable.**
Spec claims "favorable sh=71900 → target 72222.5 == current stop → no-op".
In the specified sequence the stop after A3 is 72326 and A4 writes nothing,
so "current stop" is 72326, never 72222.5 (any A4 raise would leave ≥72327).
Actual behavior — favorable trail write `72326 → 72222.5`
(`auto_trader.py:461-464` → `:486`) — is **design-correct**: one-behind target
(72191.5+31), above price, under the CEO 72500 line, and only reachable after
a real lower-high print. No code change; correct the verification spec.
Severity: LOW (spec/documentation).

**F-2 (LOW) — F-3 breach guard freezes structure state while breached.**
`auto_trader.py:424-426` returns before seed (`:444`) and before any record
(`:481-488`), so a breached trade's state never updates (D2). Assessed:
benign — the hit-check owns the exit during a breach; on recovery the stale
prev resolves to a raise-only write (D3), never a chase and never a breach
(all writes price-clamped). Self-heals (F-1 re-seeds malformed/absent prev).
Worst realistic case: a hit-check miss leaves state stale for the rest of
the trade. No change required.

**F-3 (LOW) — 72h prune crashes on a corrupt ENTRY (top-level guard only).**
`auto_trader.py:528-529` `float((v or {}).get('ts') or _now)` raises
`AttributeError: 'list' object has no attribute 'get'` when any *value* in
tweak_struct_state.json is a non-dict (probe: entry `["corrupt","entry"]` →
exception reproduced). The exception escapes `tweak_structure_fixed` (caught
at `:599` → WARN, cycle continues), but then **no state save ever succeeds
again** while the corrupt entry persists → structure state freezes for all
trades (stop writes themselves stay CAS-safe and converge; log-spam WARN
every dirty cycle). Commit `4e492a40` (landed mid-verification, 18:22) closed
the top-level variant only. Code-produced entries are always dicts and the
save is atomic (`tmp + os.replace`), so reachability = external/manual file
corruption. Suggested one-liner: `(v if isinstance(v, dict) else {})` in the
prune comprehension. Severity: LOW.

**F-4 (INFO) — adverse-raise risk asymmetry between sides (by design, spec-sanctioned).**
Short adverse raise moves the stop *away* from price (to structure+buf:
71950→72222.5 = looser, later exit on a real break); long adverse raise moves
it *toward* price (to structure−buf: 68500→69069 = tighter, earlier exit on a
real break). Both land the stop exactly one-beyond the new structure and both
are raise-only (`:480`), so neither can recreate a chase. Spec explicitly
requires "LONG mirrors all four" — no defect, documented for the record.

**F-5 (INFO) — mxm is a sanctioned second stop writer.**
`manual_exit_manager.py:262` can move ai-trader stops (close-trail, improve-only
when live SL ≠ its last write). It stands down entirely for `dynamic_sl:false`
legs (`:197`) — i.e., all 13 armed configs — so for armed rungs R1 is the sole
authority. For hand-opened ai-trader-manual legs the two coexist per the CEO
synthesis gate (`auto_trader.py:493-495`). No unexpected writer found.

**F-6 (INFO) — mid-verification HEAD move.**
`4e492a40` (18:22:08, parallel bug_hunter) added the top-level state-type
guard at `:408-409`. All harness/E checks were (re-)run against this HEAD;
results unchanged (44/45).

## Overall verdict: **PASS**

The fix does exactly what it claims: the #16882 adverse sequence produces
**zero stop writes** (state still advances), favorable bumps are unchanged
one-behind trails, the adverse path is provably raise-only through every
clamp (9 edge cases + 72-case sweep, 0 violations), CAS-miss/F-6 semantics
hold on both paths, LONG mirrors all four behaviors, and regression is clean
(20/20 suite, py_compile, fresh import, live cycle rc=0 / 0 Tracebacks,
post-fix watchdog cycles clean, no competing writer, armed orders all
`dynamic_sl:false`, no open trades). The single harness FAIL is the
verification spec's own arithmetic (F-1), not the code. Three LOW findings
(F-1 spec, F-2 frozen-state-while-breached, F-3 prune entry guard) — none
block shipping; F-3's one-line hardening is recommended.

Artifacts: `/tmp/bh_lag_harness.py`, `/tmp/bh_harness_out.txt`,
`/tmp/bh_livecycle/` (temp mirror — live `data/` untouched: auto_trader.db
mtime 18:19, pending_orders.json 17:41, tweak_struct_state.json 16:49 all
pre-date the mirror run).
