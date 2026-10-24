# bug_hunter verdict — CEO token guard (profit_monster + cut_loser) + pending-engine `--force`

**Date:** 2026-10-24 (verification run 20:45–21:00 UTC)
**Verifier:** bug_hunter subagent (adversarial pass — no fixes applied, nothing in the repo modified)
**Commits verified:**
- `a2af2e0f` 2026-10-24 20:38:22 +0000 — *exit-system: token-level CEO guard in profit_monster + cut_loser (#16384 merge lesson)*
- `2e944bef` 2026-10-24 18:55:26 +0000 — *watchdog: pending engine passes --force* (the pending-engine change; ancestor of HEAD, working tree clean)

**Harnesses (rerunnable, in /tmp):**
- `/tmp/bugh/harness_guard.py` — real-DB SELECT-only calls + scratch-schema proxy (`bugh_scratch.trades`, `SET search_path` redirect) proving guard fires/doesn't fire per scenario. 24/24 PASS, idempotent (ran twice clean).
- `/tmp/bugh/harness_pending.py` — pending-engine one-shot state machine, `--force`/`--manual` cmd build (`subprocess.run` stubbed — brain.py never executed), `is_live_trading_enabled` gates. 21/21 PASS.
- `python3 /root/.hermes/analysis/test_manual_exit_manager.py` — **20 passed, 0 failed**.

**Overall verdict: PASS WITH FINDINGS** — the guard as shipped does what the commit claims for the two functions it touches, scoping/server-filter/ORDER-BY/bypass are all correct, imports are circular-free, the `--force` change is confined to the dup guard, and both services are cycling clean post-commit. One **HIGH** gap inside cut_loser itself (MAE-guard path bypasses the new guard), one **MED** false-exclusion path (paper managed rows), one **MED** residual (inverse-close authority, documented), plus LOWs.

---

## Verdict table

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| A1 | Full diff read (both commits) | **PASS** | `git log -1 -p` = +20 lines profit_monster.py, +13 cut_loser.py (insert-only, no deletions); `git show 2e944bef` = +7 lines trade_watchdog.py (comment + `"--force"` list element). SKILL.md change is prose only. |
| A2 | Exclusion keyed on TOKEN across ALL rows of that token | **PASS** | `profit_monster.py:111-118`, `cut_loser.py:88-90` — `ceo_tokens` set, `rows` filtered by `r[1] not in ceo_tokens`. Multi-row tokens (e.g. incident's #16382+#16384 both BTC) are excluded together. Correct scoping: HL merges same-coin → one asset; `TOKEN_MAP` (hyperliquid_exchange.py:1353) has only 4 identity entries (HYPE/BTC/ETH/SOL), no alias collisions → raw `token` == HL coin. Harness G2b/G2c. |
| A3 | Main query still bypasses per-row signals (no regression) | **PASS** | Diff is insert-only; `PROFIT_MONSTER_BYPASS_SIGNALS` NOT-LIKE block untouched (`profit_monster.py:84-97`, `cut_loser.py:62-76`). Live: open row #16383 `hl_copy_trader` (a bypass signal) absent from PM before guard could matter — pre-guard behavior preserved. Guard applied after fetch; ORDER preserved (harness A4). |
| A4 | `server='Hermes'` filter consistency main vs guard | **PASS** | PM main `profit_monster.py:93` `server = 'Hermes'`; PM guard `:107` `server='Hermes'`. CL main `cut_loser.py:72`; CL guard `:84`. Identical. Note: guard omits the main query's `entry_price>0 AND current_price>0` (harness C4) — conservative direction (more exclusion), acceptable. Harness C3: a `server='Tokyo'` managed row does NOT exclude — consistent with main query which wouldn't see it either. |
| A4b | Per-row fetch semantics (DISTINCT tokens, param safety) | **PASS** | `SELECT DISTINCT token`, psycopg2 `%s` with `%tag%` params — literal `%` only inside params, no `%%` double-substitution issue. |
| B1 | No circular import (manual_exit_manager must not import profit_monster) | **PASS** | AST scan of `manual_exit_manager.py`: import set = {hermes_constants, hermes_log, math, json, os, time, psycopg2(lazy), _secrets(lazy)} — no profit_monster/cut_loser anywhere (docstring mention only, line 14). No module imports profit_monster at all. Fresh-process `import profit_monster, cut_loser, manual_exit_manager` → IMPORT-OK (harness B1/B2). |
| B2 | No import-time side effects from the new lazy import | **PASS** | `manual_exit_manager` module body = tuple defs + `_MANUAL_TIERS_PCT` list comp + `_STATE_FILE` path join (no I/O; state file read lazily in `_load_state`). `hermes_log` at import only defines. Lazy `from ... import MANAGED_TAGS` runs on first call, cached after. Existing importers (position_manager:2876, hl-sync-guardian:2078, trade_watchdog:1750) prove the import path is safe. |
| B3 | MANAGED_TAGS LIKE patterns match COMPOSITE signals | **PASS** | Harness B3a/B3b: `'continuum+,ai-trader-manual'` → excluded (matches `%ai-trader-manual%`); `'ai-trader-pending,foo'` → excluded. Also matches positional variants (`'ai-trader-,hmacd_mtf--'` exists in DB but matches no tag → correctly NOT managed). `is_managed_signal()` (manual_exit_manager.py:70-73) uses identical substring semantics → guard and exit-authority agree. |
| C1 | CLOSED managed row must NOT exclude | **PASS** | Harness C1: managed sibling `status='closed'` → pipeline token stays in both lists (guard query has `status='open'`). |
| C2 | Paper managed row | **FAIL → finding F-2 (MED)** | Harness C2: `paper=true`, `server='Hermes'`, `status='open'`, signal `ai-trader-manual` → pipeline coin IS excluded from both lists. Neither guard filters `paper`. Real-DB context: 0 paper ai-trader rows exist (all 63 ai-trader rows are `paper=False`), 39 Hermes-paper rows are all cascade/NULL signals — path is real but never yet taken. |
| C3 | Managed row with `server != 'Hermes'` must NOT exclude | **PASS** | Harness C3 (server='Tokyo') → token kept. (Legacy note: 6 closed `Tokyo` ai-trader-manual rows exist — brain.py:1393-1394 documents `Tokyo` as the pre-2026-10-16 default that "no exit manager sees"; all closed, new defaults are Hermes.) |
| C4 | Blast-radius quantification (what the guard costs) | **PASS (documented below)** | See "Blast radius" section. |
| C5 | Lone managed row (no pipeline sibling) | **PASS** | Harness C5: managed row self-excluded from both lists — correct, `manual_exit_manager` owns its exits (pre-fix PM could close CEO rows directly; now it can't). |
| D | Stale guard: managed row closes → token returns next cycle | **PASS** | Harness D1: after flipping the managed row to `closed` (scratch), same code, next call → token back in BOTH lists. Guard is per-query state (`ceo_tokens` is a local), no file/cache. |
| E(i) | Fresh fire, no position | **PASS** | Dup guard: `dup_row is None` → force irrelevant (brain.py:543). Live evidence: 15 prior pending fires, all `status=fired`, no dup (pending_orders_state.json). |
| E(ii) | Fire while same-coin position open (merge now expected) | **PASS** | brain.py:547-548 `dup_row and force` → warns and proceeds. Live: `btc-ceo-add-long-80500` executed `--force` at 2026-10-24 20:14:44, opened **#16384** at 20:14:52 while pipeline #16382 open (trade-watchdog.log:1435630-1435631, state `fired`). |
| E(iii) | Orphaned `triggered` state → steer-only, no auto re-fire | **PASS** | trade_watchdog.py:1273-1292: `triggered` past 15 min → urgent steer `auto_executable: False`, no `action` payload, then `continue` (no execute). Harness Eiii-a/b/c. |
| E(iv) | Re-run after `error` state → one-shot holds | **PASS** | trade_watchdog.py:1273 — `("triggered","fired","error")` all `continue`. Harness Eiv-a (no steer), Eiv-b/c (state `fired`/`error` transitions with stubbed subprocess), Eiv-d (re-run yields no execute action). |
| E(v) | Vacation pause / kill switch still gate with `--force`, no `--manual` | **PASS** | brain.py:507-511 gate = `is_live_trading_enabled(is_manual=args.manual)` (wiring :1494); `--force` never reaches it. hyperliquid_exchange.py:288-297: constant `LIVE_TRADING_ENABLED` gates even manual; pause marker gates only `is_manual=False` — which is the pending engine's shape. Harness Ev-a..d (pause simulated in a TEMP `HERMES_DATA`, production untouched). |
| E(vi) | `--force` bypasses ONLY the dup guard | **PASS** | Static: every `force` occurrence in brain.py = lines 359/366 (signature+doc), 543/547/548 (dup guard), 1411/1494 (arg+wiring). Orphan check (:553-574), RSI floor, blacklist, notional, delist, gates all unconditional. Harness Eforce-a/b/c. |
| F | Test suite + post-commit logs | **PASS** | `test_manual_exit_manager.py`: **20/20**. profit_monster.log: last Traceback line 105443 (old, 2026-10-17 era) vs first post-commit cycle line 134706 → **0 anomalies after 20:38:22**; cycles every 60s (`Firing — group A / Found 0 open positions`) through 20:56:57, service exit 0. cut_loser.log: last Traceback 122033 vs post-commit window at 161600 → **0 anomalies**; `MAE guard: 1 positions to check / Found 0 open positions` normal. pipeline.log and trade-watchdog.log: 0 ERROR/Traceback lines after 20:38. |
| G1 | Functions run clean against real DB (SELECT-only) | **PASS** | `get_all_open_positions()` → `[]`, `get_losing_positions()` → `[]`, no error log (only open row = #16383 HYPE, bypassed signal; 0 open managed rows at run time). |
| G2 | Guard fires: open `ai-trader-pending` row on a token with a pipeline row → token disappears from BOTH lists | **PASS** | Scratch-schema proxy (see method note): token `PMXPIPE` (pipeline + open managed sibling) absent from both lists; PM logged `[PM] CEO-tranche token guard: standing down on ['PMXCOMP1', 'PMXCOMP2', 'PMXPAPER', 'PMXPIPE', 'PMXZERO']`; control tokens present. Production verified untouched: 0 rows id≥990001, open rows unchanged, scratch schema dropped (harness X1/X2). |

**Method note (G):** instead of inserting a fake row into the live `trades` table (which would race the 60s profit-monster/cut-loser timers AND could be picked up by position_manager's `is_managed_signal` path — potentially issuing a real HL stop-replace/close against the live account), the harness creates a scratch schema `bugh_scratch.trades (LIKE public.trades)` and redirects the functions' own connection via `SET search_path TO bugh_scratch, public`. The exact shipped SQL executes against an identical schema — zero production-row writes.

---

## Blast radius while the guard is active on a coin (item C, argued from code)

**LOST for the guarded pipeline row** (all fed by the now-filtered lists):
- profit_monster: tier-1 quick scalp, tier-2 runner, PM trail (0.20% giveback tiers), spider-profit variant — everything in `profit_monster.run()` (lines 525-584) hangs off `get_all_open_positions()`.
- cut_loser: trailing-loss tier, **HARD-STOP at -3%** (`cut_loser.py:621-651`, iterates the guarded `positions`), tier-1 quick cut, tier-2 deep cut — all off `get_losing_positions()`.
- Net effect: a guarded pipeline coin keeps no *profit-taking* and no *proactive small-loss cutting*. A winner can round-trip to the ATR SL instead of being trailed/scalped; a loser rides past the -0.3%..-1% tier band to ATR SL / hard caps.

**STILL COVERING the pipeline row** (argue-from-code):
- **ATR SL/TP**: `position_manager.check_atr_tp_sl_hits` (position_manager.py:484) + TPSL engine run every pipeline cycle (`run_pipeline.py` STEPS_EVERY_MIN includes `position_manager`). The ATR skip is per-row `is_managed_signal(signal)` (position_manager.py:2080-2089) — a *pipeline* row is not managed, so its full ATR stack runs regardless of siblings. (Merge caveat: this ATR SL closing the pipeline row closes the whole merged HL position — explicitly accepted in SKILL.md.)
- **hard_max_loss / trail_arm_timeout / stale_exit**: position_manager canonical closes (position_manager.py:3712-3715, :610, `check_stale_position`) — per-row, unaffected by the guard.
- **Guardian**: hl-sync-guardian orphan/missing reconciliation runs every cycle (seen live: `Sync cycle / Orphans: none / Missing: none`, pipeline.log 20:44:26) — so a *stale/orphaned* managed row (DB-open, HL-gone) self-heals, which also un-shields the coin.
- **manual_exit_manager itself**: runs inside `position_manager.check_and_manage_positions()` (:2876+) for the managed row — the coin's exits are not unmanaged; they're just executed at the CEO stack's levels.
- **cut_loser MAE guard**: **NOT excluded — see F-1.**

---

## Findings

### F-1 — HIGH — cut_loser's MAE-guard path bypasses the new CEO token guard (guard incomplete inside its own module)
- **Where:** `scripts/cut_loser.py:314-343` (`get_positions_for_mae_guard` — its own query, no `MANAGED_TAGS` filter), called at `cut_loser.py:604-605` **before** the guarded `get_losing_positions()` at `:608`; `run_mae_guard` at `:346-434` → `close_position` at `:392/:429`.
- **What:** while a CEO managed row is open on token X, the tiers/trail/HARD-STOP stand down (good), but the MAE guard still evaluates the pipeline LONG on X every wake ("MAE guard: 1 positions to check" in the live log) and will HL-close it under `tier="MAE-GUARD"` if the drop-from-peak threshold is met — closing the **merged** position under cut_loser authority, i.e. the exact #16384 incident class (wrong authority ends the CEO tranche; §11-7 blended re-sync).
- **Also:** the ATR-aware variant (`btc_crash_filter.check_position_protection`, :364-397) and legacy fallback (:401-434) both consume the unfiltered list; `close_position` (:179) has **no** managed-row check of its own.
- **Doc overstatement:** SKILL.md now claims "profit_monster + cut_loser now skip any token holding an `ai-trader-manual/pending/auto` row" — true for `get_losing_positions`, false for the module as a whole.
- **Mitigations:** crash-only (protective intent, low frequency), and pipeline ATR SL/TP is an accepted residual anyway. **Suggested fix (not applied):** mirror the guard into `get_positions_for_mae_guard`, or explicitly document MAE as the deliberate exception in the guard comment + SKILL.md.

### F-2 — MED — guard does not filter `paper`: a paper managed row falsely shields a live pipeline coin
- **Where:** `scripts/profit_monster.py:106-110` and `scripts/cut_loser.py:83-87` — `WHERE server='Hermes' AND status='open' AND (LIKE…)`; no `AND paper IS FALSE`.
- **What:** a `paper=true` `ai-trader-manual` row on server Hermes excludes that token from PM/cut_loser for the whole time it's open — but a paper row exists only in the DB and **cannot merge** into a live HL position, so the exclusion has no merge-safety justification while stripping profit-taking/loss-cutting from a live position. Harness C2 proves the behavior.
- **Reality check:** 0 paper ai-trader rows exist (all 63 are `paper=False`); the scenario needs a CEO paper-mode managed trade opened on a live pipeline coin. That's why MED, not HIGH.
- **Suggested fix:** add `AND paper IS FALSE` to the guard query (keep it out of the main query, which legitimately includes paper? no — the main query is server='Hermes' only too; put the `paper` condition on the guard side only).

### F-3 — MED (residual, documented) — close authority for a merged position still has multiple non-CEO actors
- The guard transfers PM/cut_loser out, but a merged position can still be closed whole by: pipeline row's ATR SL/TP (position_manager), `hard_max_loss`/stale/trail-timeout exits, F-1's MAE guard, **and** the CEO row's own exit stack (manual_exit_manager closing the managed row closes the entire HL position including the pipeline leg — the mirror image of #16384).
- Documented: SKILL.md flat-check procedure + "the pipeline row's ATR SL/TP still participates on a merged position … attribution corrupts either way". The controls are (a) flat-check before arming an add, (b) alignment of TPs. Flagged so the CEO knows the guard narrows — but does not close — the multi-actor close surface.

### F-4 — LOW — cut_loser silently excludes (no log line)
- PM logs (`profit_monster.py:114-117`), cut_loser does not (`cut_loser.py:89-90` has no log call) — verified in harness (L1/L2: CL stdout empty while CL excluded the same tokens). Incident forensics ("why didn't cut_loser act?") will show nothing. Suggest mirroring PM's log line.

### F-5 — LOW — guard failure takes the whole module down and mislabels the error
- Guard sits inside the same `try` as the main query: an ImportError/SQL error → `except` → `return []` with prefix **"DB query error:"** (`profit_monster.py:125-127`, `cut_loser.py:98-100`). Effect: PM/cut_loser stop operating on **all** coins (fail-safe for wrongful closes — nothing gets closed — but fail-open for profit-taking/loss-cutting), with a misleading log label. The actual exception text follows the prefix, so it's diagnosable.

### F-6 — LOW — `--force` help text now false
- `brain.py:1411-1412` help says *"never used by automation"*; `trade_watchdog.py:1411` (automation) now passes it. Comment at trade_watchdog.py:1393-1398 documents the change; brain.py's help/comment (:366-367 "NEVER passed by the automated pipeline") was not updated.

### F-7 — LOW — token join is case-sensitive raw string
- `profit_monster.py:113`, `cut_loser.py:90` compare raw `token` values. A CEO row stored `'btc'` vs pipeline `'BTC'` would slip past the guard. Historical data: 0 rows with `token <> UPPER(token)`; brain.py stores the token as passed and the dup guard (:541) makes the same assumption — consistent with system convention, but `UPPER(token)` in the guard (or storing normalized) would make it robust.

### Notes / observations (no severity)
- **Orphaned managed row** (DB `open`, HL gone) would shield the coin indefinitely — but hl-sync-guardian's Missing/orphan reconciliation closes such rows each cycle (live log), self-healing the guard.
- **`ai-trader-auto` tag** has zero rows in the DB — reserved, correctly wired.
- `vacation_pause.json` absent now; if a pause is active when a pending order crosses, brain rejects → state `error` → **order burns permanently** (pre-existing one-shot design: "CEO re-arms explicitly").
- Harness side-effect disclosure: the scratch runs caused 6 diagnostic lines (`[PM] CEO-tranche token guard: standing down on ['PMX…'…]`, timestamps 2026-10-24 20:51–20:52) to append to `logs/pipeline.log` (hermes_log writes to both stdout and that file). They contain only `PMX*` harness tokens, are correctly timestamped, and were left in place — rewriting the multi-GB open log to remove them risked breaking appends from long-running processes. No other production artifact was written; production DB rows verified untouched (harness X1/X2). (`git status` shows `automation/ceo/vacation_alerts.json` + `data/watchdog_recommendations.json` modified during the verification window — those are the vacation-guardrail timer (20:58) and trade-watchdog service (20:44) running normally, not the harnesses; the harnesses write only to /tmp.)

---

## Overall verdict

**PASS WITH FINDINGS.** Ship is functionally correct for its stated scope: token-level exclusion with the right key, right status/server filters, no bypass/order regression, no circular import, no import side effects, composite LIKE semantics correct, per-query guard auto-returns, and the pending-engine `--force` is provably scoped to the dup guard with vacation/kill-switch gates and one-shot semantics intact (20/20 unit tests, both services cycling clean post-commit, live #16384-fire evidence). Before the next CEO add to an open pipeline position, the one thing worth fixing or explicitly accepting is **F-1 (MAE-guard bypass)** — the guard's invariant does not hold inside cut_loser itself.

**Artifacts:** harnesses `/tmp/bugh/harness_guard.py`, `/tmp/bugh/harness_pending.py` (rerun: `python3 /tmp/bugh/harness_guard.py`, `python3 /tmp/bugh/harness_pending.py`); outputs `/tmp/bugh/run1.txt`, `/tmp/bugh/run2.txt`, `/tmp/bugh/pending_run.txt`.
