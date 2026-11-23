# bug_hunter verdict — add-to-winners gate (1d440698) + skill recovery + equal-sizing config

- **Verifier:** agent-9 (bug_hunter, fresh-eyes), 2026-11-23 ~06:15–06:35 UTC
- **Scope:** commit `1d440698` (trade_watchdog.py + analysis/test_pending_machine.py + skills/shared/full-analysis/SKILL.md), the SKILL.md truncation recovery, `data/pending_orders.json` equal-sizing rewrite, regression (compile/suites/imports/ONE live run_cycle/logs).
- **Out of scope:** §17 bracket-band math/clamp internals (agent-8 owns that).
- **Harness:** `/tmp/bhv/test_winner_gate.py` (mocks only, zero production writes) — **22/22 pass**; `/tmp/bhv/cfg_check.py`, `/tmp/bhv/skill_matrix.py`.
- **Overall verdict: PASS WITH FINDINGS — 0 HIGH, 1 MEDIUM, 1 MEDIUM(test-gap), 2 LOW, 2 INFO.**

## Verdict table

| # | Item | Verdict | Evidence |
|---|------|---------|----------|
| 1 | add-to-winners gate (1d440698) | **PASS** (findings F-1, F-2, F-3) | 3-col SELECT exact (trade_watchdog.py:1897-1898); every exit path exercised 22/22; defer writes no state; flag rides only winning adds; flat + opposite untouched (diff shows both as context) |
| 2 | SKILL.md truncation recovery | **PASS — complete** | 1,310 lines; exact line-count chain 1097→1132→1216→1257→1291→1299→**1310**; commit-walk matrix: **0 missing added lines** across e027e737/5f793ccd/a291e0ef/484d7a2b/1fa0acbf/1d440698; `git diff 1fa0acbf 1d440698 -- SKILL.md` = **+11/-0 only** (the WINNER-CONDITION block) — no deletions left behind |
| 3 | equal-sizing config rewrite | **PASS** (finding F-4) | 84/84 rungs `amount_usdt = 11.10`; no rung >11.10 or <11.0; all required keys/side-rules/ids consistent; band_exempt count = 1; 61,750 dictation present with band_exempt:true, no 62,250/62,402 remnant; `_side_mult` = hard 1.0, only 2 callers, both `round(11.1 * 1.0, 2)` |
| 4 | regression | **PASS** | py_compile 4/4 OK; pending-machine ALL PASS; manual-exit 20/20; fresh imports OK; ONE live `run_cycle` rc=0; **0 Tracebacks** in pipeline.log / trade-watchdog.log / pipeline.err.log since 05:30 |

## Item 1 — the gate (trade_watchdog.py:1985-2020)

Production query (captured from the harness, exact string):
`SELECT id, direction, pnl_pct FROM trades WHERE token=%s AND status='open' LIMIT 1`

Exit paths (all verified by harness, state file inspected after each):

| Case | Row | Result | State written |
|------|-----|--------|---------------|
| winning +1.35% | `('1','SHORT',1.5)` | ADD fires, `prearmed_add=True`, logs "WINNING" | `{'status':'triggered'}` (intended) |
| losing −0.80% | `('1','SHORT',-0.8)` | defer, logs "NOT in profit" | **none** — next cycle green (+0.42%) fires with flag |
| NULL pnl | `('1','SHORT',None)` | defer (`or 0` → 0.0) | none |
| 2-col row | `('1','SHORT')` | defer (IndexError caught) | none |
| garbage `'n/a'` | — | defer (ValueError caught) | none |
| breakeven 0.0 | — | defer (strictly `> 0`) | none |
| flat (no open row) | `None` | fill, **no** flag, no ADD wording | triggered |
| opposite dir (3-col, +5%) | `('1','LONG',5.0)` | defer (netting branch), logs "opposite" | none |
| DB down | — | defer (query except → continue) | none |

- **pnl_pct semantics:** no live open row exists (`status='open'` = 0), so proven from the writer: `hl-sync-guardian.py` `sync_pnl_from_hype` SELECTs `WHERE status='open'` (L1820-1825) and UPDATEs `pnl_pct` (L1886) using `pnl_utils.compute_live_pnl` (L47-67: direction-aware, **unleveraged**, entry-based %, rounded 4). Matches the "open-row unleveraged price-%" claim. Column type `numeric` → psycopg2 `Decimal` → `float(...)` coercion in the gate is correct. All other `pnl_pct` writers (hl_fill_monitor:569, hl_reconciliation:171, hl-sync-guardian:635/859/917) are close-path.
- **Flag persistence:** `prearmed_add` is set only on the in-memory `order` dict, which is re-read from `pending_orders.json` every cycle; state stores only `{status, price, ts}` (harness-checked) → no cross-cycle stale flag, disk config never carries the flag.
- **Flat/opposite unchanged:** `git show 1d440698` shows both branches as context lines only; harness confirms behavior.

## Item 2 — skill-completeness grep matrix

Line-count chain (each = parent + commit's net, exact):

| Ref | lines | Δ |
|---|---|---|
| e027e737^ (25371000) | 1097 | — |
| e027e737 (MTF volume + integrity rule) | 1132 | +37 −2 |
| 5f793ccd (MTF RSI Structure) | 1216 | +84 |
| a291e0ef (§16 conviction) | 1257 | +41 |
| 484d7a2b (§17 bracket band) | 1291 | +34 |
| 1fa0acbf (61,750 band_exempt) | 1299 | +8 |
| 1d440698 (§7 WINNER-CONDITION) | **1310 = current** | +11 −0 |

Commit-walk (every added non-blank line of every skill commit, whitespace-normalized, checked against current file): **missing = 0** for all six commits.

| Required section | Present | grep count (file / Output-Template block) |
|---|---|---|
| §16 Entry conviction | ✅ line 1005 | `§16` ×3, `Entry conviction` ×1 |
| §17 bracket band + `band_exempt` | ✅ line 1043 | `§17` ×1, `band_exempt` ×2 |
| MTF RSI Structure | ✅ line 407 | `MTF RSI Structure` ×1, `RSI-STRUCT` ×6, `HH/HL/LH/LL` ×2 |
| MTF-volume integrity rule | ✅ line 176 header, line 200 `DATA-INTEGRITY RULE` | `MTF VOLUME` ×1 (template), `DATA-INTEGRITY` ×1 |
| Output-Template: CHOP | ✅ | line 1208 (block offset 12) |
| Output-Template: MTF VOLUME | ✅ | line 1212 (offset 16) |
| Output-Template: RSI-STRUCT | ✅ | lines 1216, 1246 (offsets 20, 50) |
| Output-Template: ENTRY QUALITY | ✅ | line 1258 (offset 62) |
| Output-Template: BRACKET DISTANCE | ✅ | line 1261 (offset 65) |
| §7 WINNER-CONDITION (CEO words + enforcement) | ✅ line ~684 | `WINNER-CONDITION` ×1, `pnl > 0` ×1 |

**Truncation incident fully healed:** final `1d440698` skill diff-stat is `11 ++++++++(0 −)`, and `git diff 1fa0acbf 1d440698 -- SKILL.md` is exactly the 11-line WINNER-CONDITION block — the 1,313-line deletion never survived the amend.

## Item 3 — config internal consistency (`data/pending_orders.json`, gitignored)

84 orders (83 BTC + 1 hype), checked wholesale (not spot-check only):

- `amount_usdt`: **all 84 = 11.1** (min=max=11.10). No rung >11.10 ✓; no rung < HL floor 11.0 ✓ (`HL_MIN_NOTIONAL_USDT = 11.0`, hermes_constants.py:632).
- Required keys: `id, coin, direction, trigger, trigger_price, amount_usdt, leverage, sl, target, confidence, dynamic_sl, note` present on **84/84**; `serial` present on **80/84** → **F-4**.
- Side rules: short `sl > trigger` 0 violations; long `sl < trigger` 0 violations; targets all on the profitable side 0 violations; trigger/direction directionality (`below`↔short, `above`↔long) 0 mismatches.
- Duplicate ids: **0**. `band_exempt` present on exactly **1** rung: `btc-auto-ladder-long-1795176554` (trigger 61750, sl 61561, tp 63591, band_exempt true) — the §17 dictation; note text records 62402→62250→61750. **No rung left at 62250 or 62402.**
- Uniformity: confidence 60 ×84; dynamic_sl False ×84; leverage 10×63 / 5×21; notes 84/84; entry_style key on 16 (continuation 5 / retest 11 / null 16−16…, remainder absent = hand-arm heritage).
- 12-rung spot check across old/new printed (btc-ceo-long-75630, btc-ceo-short-grind, 4 auto shorts, 4 auto longs, the 61,750 dictation, btc-ceo-long-80000): notes, entry_style, sl/target, serial, dynamic_sl, confidence, leverage all coherent.
- `_side_mult` (auto_trader.py:883) returns literal `1.0`; repo-wide callers = exactly 2 (auto_trader.py:1047, 1087), both `round(11.1 * _side_mult(...), 2)` → **cannot derive below base**. Separate `size = cfg.size_usdt × self_tuning size_mult` path is floored at `HL_MIN_NOTIONAL_USDT` (auto_trader.py:1167-1171) — live-confirmed: this run logged `size 6.77 < HL min 11.0 — floored`.
- Note: file mtime 06:09 — the keeper armed `btc-auto-ladder-long-1795414188` @62500 (amount 11.1 ✓) and re-levelled `btc-auto-ladder-1795401586` short 60250→60750 (§17) AFTER the rewrite; revalidated post-hoc, still fully consistent. Scope's "82 rungs" is now 84 (keeper adds since).

## Item 4 — regression

- `py_compile`: trade_watchdog, auto_trader, hermes_constants, position_manager → **OK**.
- `analysis/test_pending_machine.py` → **ALL PENDING-MACHINE TESTS PASS** (rc=0), incl. the two updated 3-col mocks (lines 188, 270) — log shows `BTC #1 short open and WINNING (pnl +1.50%) — firing as ADD`.
- `analysis/test_manual_exit_manager.py` → **20 passed, 0 failed**.
- Fresh imports of the four modules in a clean interpreter → OK.
- **ONE sanctioned live run:** `python3 scripts/auto_trader.py` → **rc=0**, stderr empty. Summary: `enabled=true, mode=live, decision=BRACKET, price=61566.01, scores long 40 / short −30 / regime CHOP, hypo_events=[], armed_detail=[], live_armed=[], shadow_armed=[]` (book: **0 open positions**, `armed_detail` empty — consistent with 0 open DB rows). Run's own events: `size 6.77 < HL min 11.0 — floored`, `long/short real R:R 0.74 < 1.0 — leg not armed`. No add-gate line possible live (nothing open to add to); the §17 keeper lines from the surrounding pipeline cycle: `ladder_keeper: §17 re-level short btc-auto-ladder-1795401586 trigger 60250 → 60750 (band 1.0-2.0% …)` and `ladder_keeper_long: armed btc-auto-ladder-long-1795414188 long @ 62500`.
- Logs since 05:30: pipeline.log 15,300 lines, trade-watchdog.log 50 lines, pipeline.err.log (0 bytes) → **0 Tracebacks**. Only non-fatal noise: `[hl_info] Error: HTTP Error 500` (HL API, caught) and `signals_runner … 0 errors`.

## Findings

**F-1 — MEDIUM (test gap): the new gate has no committed regression coverage.**
`analysis/test_pending_machine.py` only gained third-column shapes (lines 188, 270). There is **no suite assertion that losing/NULL/odd rows DEFER**. An implementation with the `if _pnl > 0` gate deleted entirely still passes the whole suite (the surviving assertions — "same-dir ADD" and "ADD must carry the band flag" — are satisfied by gate-less code), i.e. the CEO's doctrine could silently unship green. The 5/5 standalone harness cited in the commit message was not committed (nothing in the diff-stat but the 3 files). Fix: add 3 assertions to group 5 (−0.80 → no steer + state untouched; `None` → defer; `0.0` → defer).

**F-2 — MEDIUM: gate reads ONE nondeterministic open row when a token is stacked.**
`scripts/trade_watchdog.py:1897-1898` — `SELECT id, direction, pnl_pct … WHERE token=%s AND status='open' LIMIT 1` with **no ORDER BY**. Stacked same-direction rows are exactly the add scenario (the F-3 COUNT at L1903-1905 and the heat SUM exist because multiple rows per token are possible). Base short @63000 + add @62000 with price 62100 = one leg green, one leg red; which row the gate samples is plan-dependent, so the gate can approve an add to a net-underwater position (the exact case the CEO forbade) or deny a legitimate one. Fix: `ORDER BY id ASC` (deterministic base trade) or gate on the stack's aggregate net.

**F-3 — LOW: suite mock shape still mismatches production at one site.**
`analysis/test_pending_machine.py:194` — `OPEN[0] = ('1','LONG')` is a **2-tuple**; production now returns 3 columns. The assertion ("opposite waits") still passes for the right reason *today* (the opposite branch returns before indexing `[2]`), but it would also pass if a future refactor misrouted the opposite row into the pnl parse (IndexError → swallowed by the per-order except → continue → no steer), hiding the regression. Fix: `('1','LONG',1.5)`.

**F-4 — LOW: 4 of 84 rungs lack the `serial` key** (scope required it on every rung).
`btc-ceo-long-75630`, `btc-auto-1794264564-659cac-long`, `hype-short-7060`, `btc-ceo-short-flagfloor` → `order.get("serial")` = None. Consequence: (a) no one-per-cycle sequencing for them; (b) for the 3 that are not `btc-auto-*`, the entire open-position/add-gate block (`trade_watchdog.py:1873`) is skipped, so a same-direction crossing fills **without the winner gate and without the band flag** — CEO doctrine uncovered on hand-arms. Config is gitignored → no baseline, so pre-existence can't be proven; the amount rewrite (json load/dump preserves keys) makes pre-existence likely. Fix: seed `serial: True` (or explicitly document hand-arms as non-serial) and/or move the gate out from under the `btc-auto-||serial` guard.

**F-5 — INFO: gate freshness depends on the sync loop.** `pnl_pct` on an open row is only as fresh as `sync_pnl_from_hype`'s last cycle; a stalled guardian means the gate decides on a stale number (sign-flip risk near breakeven). No live row existed to measure lag; note only.

**F-6 — INFO (see-something):** `[hl_info] Error: HTTP Error 500: Internal Server Error` recurs in pipeline.log since 05:30 (HL API, caught, no traceback) — cosmetic, but worth watching if it persists into trading hours.
