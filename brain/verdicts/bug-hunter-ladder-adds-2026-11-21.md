# bug_hunter verdict — ladder ADDS (same-direction fills while a trade is open)

- **Commit verified:** `6b9fb870` "ladder ADDS: same-direction fills while a trade is open (CEO 2026-11-21), opposite still waits" (2026-11-21 04:50:17 UTC), `scripts/trade_watchdog.py` only (45+/25−).
- **Verifier:** bug_hunter (agent-3), 2026-11-21 ~05:00–05:15 UTC.
- **Harnesses (all /tmp, mocks + SELECTs, zero production writes):**
  `/tmp/bh_ladder_adds.py` (51/51), `/tmp/bh_brain_force.py` (20/20), `/tmp/brain_dbdown.py` (rc=1 as designed), plus PG SELECTs (read-only), `analysis/test_manual_exit_manager.py` (20/20), ONE sanctioned live `run_cycle` (`python3 scripts/auto_trader.py`).
  Production `data/pending_orders.json` / `pending_orders_state.json` md5-verified unchanged across the harnesses; `data/guardian_recently_opened.json` unchanged across the mocked brain runs.

---

## Verdict table

| # | Area | Result | Evidence |
|---|------|--------|----------|
| A(i) | 7-case suite (independent rerun/extension) | **PASS 51/51** | flat→fire; same-dir→"firing as ADD" + steer; opposite→no steer + **no state burn** + "no netting" log; **serial claim fires on the ADD path** (rung b deferred, first rung consumed 'triggered'); ladder cmd has `--force` AND `--prearmed`, NO `--manual`; non-ladder `btc-auto-*` NO `--force`; retest first_break→reclaim→cross#2→ADD; plus: DB-fail-open, direction case-matrix, one-shot/orphan, executor status taxonomy |
| A(ii) | brain FORCE end-to-end → Hyperliquid | **PASS (works as intended; stop-stack caveat = F-2)** | `/tmp/bh_brain_force.py`: dup row + `--force` → `⚠️ FORCE: second tranche on BTC alongside open trade id=17014` → `mirror_open` called ONCE with `size_usdt_override=22.2` (rung notional, **independent of existing position** — `mirror_open` has no position parameter and never reads position before sizing, BF8/BF16), `is_manual=False`, order = plain market BUY/SELL (`place_order` default `reduce_only=False`, hyperliquid_exchange.py:609; `mirror_open` never passes it) → HL **aggregates: same-dir fill INCREASES size** (live precedent: `#16306/#16307` 2026-10-20 = 2 rows / 1 HL position; current HL BTC = 0.0004 SH ≈ $22.65 vs row `#17014` $22.30) → INSERT with `direction='SHORT', status='open'` → returns id → CLI `✓ Added trade` → executor 'fired'. Per-row SL trace below (F-2). |
| A(iii) | Opposite + `--force` / flip window | **PASS with finding (F-1/F-4)** | Monitor gate is provably the ONLY direction filter: brain dup SELECT = `SELECT id FROM trades WHERE token=%s AND server=%s AND status='open'` — **no direction column** (brain.py:680-681), `if dup_row and force:` proceeds (687-688), guard-refusal-under-force unreachable (BF19). BF20: force + LONG-only open → brain places the SHORT (netting fill) untouched. Flip/DB-window damage number: **≤ one rung notional = $22.30 (incl. $0.10 buffer) at today's sizes** for the fill itself; worst follow-on (phantom opposite row's stop → `mirror_close` full close) bounded by the whole position ≈ **$22.65**; long rungs $11.20. |
| A(iv) | Direction case-insensitivity | **PASS** | matrix: DB `'SHORT'/'Short'/'short'` → ADD (both sides lowercased, watch 1631-1632); DB `None`/`''` → `str(x or '')` = `''` ≠ `'short'` → **opposite branch → waits (fail-safe, no fire)**; config side is validated to exact `'long'/'short'` before the gate (1486-1488) — uppercase config direction is skipped with a WARN, never compared (T9c). No equal-empty path exists (direction can't be empty after validation). |
| B | 2026-11-10 lesson not reintroduced; exposure bound | **PASS on cadence; FINDING F-3 (no aggregate cap)** | `serial_claimed` initialized per cycle (1423) and set at **1654 BEFORE the steer (1656)** — applies on the ADD path (guard fall-through reaches 1643); T4 proves 1 steer + "serial rung deferred". Numbers below. |
| C | State machine / add-failure statuses | **PASS** | status table below; branch order: multi-touch machine (1540-1598) runs **BEFORE** the stacking gate (1599) — T7 proves cross#1 with an open same-dir position stops at `first_break` with **no ADD and no gate query**; retested+opposite → gate `continue`, state stays `retested`, no burn (T7b). |
| D | Regression | **PASS** | suite **20/20 rc=0**; `py_compile`: core 5/5, scripts 250 OK + 1 pre-existing broken debug file (`tpsl_utils_debug.py`, untouched since 2026-10-03 = known F-10); fresh imports OK (`trade_watchdog`, `pending_order_monitor`, `auto_trader`); **ONE live run_cycle rc=0, stderr empty** (exact summary below); `pipeline.log` **0 Traceback lines** (whole file), `trade-watchdog.log` 224 historical Tracebacks with **0 frames from `/root/.hermes/scripts/`** (all `<stdin>`/heredoc agent noise, F-6 class) and last written 04:46 = pre-commit; gates: `--manual` NOT appended (T5), brain `is_live_trading_enabled(is_manual=False)` → `LIVE_TRADING_ENABLED=True` (constants:33) + `vacation_pause.json` marker (absent now) — `--force` touches neither (BF9 `is_manual=False`); `mirror_open` re-gates (hyperliquid_exchange:1134). Note: `hype_live_trading.json` exists but the runtime gate per code is the constant + `vacation_pause.json` (hyperliquid_exchange:279-282 — AGENTS.md wording is stale; not this commit's issue). |
| E | Scope | **PASS** | commit touches exactly `scripts/trade_watchdog.py` (git stat); `git diff 6b9fb87..HEAD` = docs/automation/skills only, zero scripts; `git diff HEAD` on `trade_watchdog.py brain.py position_manager.py auto_trader.py` empty; brain dup-guard untouched (its FORCE logic predates this commit — only the pending path's flags changed). |

---

## (A ii) Second-tranche + per-row SL trace

**Opening (proven, mocked walk `/tmp/bh_brain_force.py` 20/20):**
1. Executor builds `brain.py trade add BTC short 22.20 <trigger> --real --signal ai-trader-pending … --sl … --target … --force --prearmed` (watchdog 1778-1799) — `--force` for `("btc-ceo-", "btc-auto-ladder-")` (1791-1793).
2. brain gates in order: `validate_levels` (CLI, pre-side-effect) → SHORT knife/floor skipped by `--prearmed` (467-469) → live gate (646-650) → delisted (652) → blacklist (661-665) → HL_MIN $11 (672-675) → **dup guard (677-688): any open row + force → `⚠️ FORCE: second tranche`, no direction check** → stale-orphan (696-715) → marker (733) → `mirror_open(size_usdt_override=22.2)` (825).
3. `mirror_open`: `size_usdt = 22.2 + MIN_ORDER_BUFFER(0.10)` → `raw_sz = size_usdt/price`, market order, `reduce_only` never set → **HL position grows by ~$22.30 notional** (one aggregated position per coin; no reduce/close semantics on the add path). `hl_realized_pnl` from the fill poll is 0 for a normal add.
4. HL verify (839-855): position present (it must be — we just grew it) → INSERT row → `✓ Added trade #N` → executor state **'fired'** → rung consumed.

**Per-row SL afterwards (traced; live precedent #16306/#16307):**
- Stops are **software-enforced per row**, not per-row HL orders: pm `check_atr_tp_sl_hits` iterates rows with each row's own `stop_loss/target` (position_manager.py:589-636); guardian `_check_hard_stops` does the same (hl_sync_guardian.py:2012-2033). `ATR_HL_ORDERS_ENABLED = False` (position_manager.py:~270) — no exchange-side SL pushed at open.
- **But every close is per-COIN and full-size:** row A's stop → `close_paper_position(A)` (1229) → `mirror_close(token, dir)` (1607) → `close_position(coin)` → `exchange.market_close(coin, sz=None)` (**sz=None = entire HL position**, hyperliquid_exchange.py:751). There is **no partial close anywhere** (grep: no multi-row handling in pm/guardian).
- So **row A stopping closes row B's exposure too**, at A's stop price — the add's own stop never gets to act while A is alive. Row B then sits `status='open'` with HL flat until (a) its own level is reached (books paper-computed P&L, `mirror_close` fails "no open position", logged, DB still commits), or (b) guardian step-8 reaps it as `HL_CLOSED` after **2+ consecutive missing cycles (~2 min)** (hl_sync_guardian.py:421-422, 4768-4778).
- **Live precedent:** `#16306` (14:04) + `#16307` (14:16, both `--force`) — ONE HL close at 15:13 (`cut_loser`, exit 82293) while `#16306` lingered to 15:22 (`atr_sl_hit`, exit 82403): 9-minute DB/HL divergence, two different booked exits for one real close.
- Consequences today (sizes $11-23): bounded (cents–dollars of mis-accounting), but the "independent SL per add" expectation is false → **F-2**.

## (A iii) Flip-window damage number

Window = steer emitted (monitor, same step) → `subprocess.run(brain)` (up to 120s; pending_order_monitor emits then executes immediately in one step, lines 43-53). A flip inside it (manual/copy-trader/guardian close + opposite open) reaches brain with `--force`:
- brain's dup guard is direction-blind → proceeds → market order in the STEER's direction = **a REDUCE/net of the live position**, amount = rung size.
- **Fill damage: ≤ $22.30 notional** (short rung $22.20 + $0.10 buffer) — i.e. reduce a larger position by ≤$22.30, or flip a smaller one (position now ≤$22.65 ⇒ flip ≤$22.65 − rung).
- If the net lands **exactly flat**, brain's HL verify (844-851) sees no position → "rolling back" → `close_position` no-op → **rc=1, no REJECTED marker → rung 'error'; HL money moved with NO DB row** (unbooked realized pnl, ≤ ~$0.02 fees+move).
- If the net is **partial**, brain writes an OPPOSITE row while HL remains netted toward the OLD direction → DB now carries both directions; **that phantom row's stop later calls `mirror_close` → closes the ENTIRE remaining HL position** (same full-close mechanism as above) = follow-on ≤ whole position ($22.65 now, scales with book).
- Total bounded worst case today ≈ **$23 notional + ~$0.05 fees**; documented by the ponytail comment (1773-1777) for the fill, but the **phantom-row full-close follow-on is NOT covered** → F-4 (LOW while sizes stay at rung scale).

## (B) Worst-case add exposure + bounding layers (numbers)

Book at verify time: **1 open BTC SHORT `#17014`** ($22.30, 10x, entry 56637, SL 56693.64 = +0.10%, TP 53958); BTC ≈ 56,284. Armed rungs (config ∌ state) = **20**:
- **Down side (the live add direction):** 1 armed short below price — `btc-auto-ladder-1795234161` @55796, $22.20, SL 59416 (**6.49% away → $1.44 worst own-stop loss**), continuation = fills ON CROSS.
- **Up side:** 19 armed longs 59379→80060, **$210.80 total notional**, tight reclaim stops (0.3-0.6% → **$0.96 total at own stops**) — but all are **opposite-gated while `#17014` SHORT is open** (they can't add; they'd only fill as first fills when flat).
- **ARMED+CROSSED right now = 0** → nothing fires this cycle.

**One straight move:**
- Static (config frozen): down-slice = **+$22.20 notional** (1 rung); up-slice from flat = +$210.80 (19 rungs, 1/cycle).
- Dynamic: the **Rule-13 ladder keeper self-replenishes** (auto_trader.py:829/888 — arms a fresh rung when no unfired rung is within ≤3·ATR1h; `_side_mult` doubles to $22.20 when the side's last-5 net is positive, :749-762) → **count is not statically bounded**: a sustained H-hour slice ≈ 60·H adds ≈ **$1,332·H notional added** (~$133·H margin @10x), each with its own structure stop (measured keeper short stops currently 2-6.5% ⇒ **≤$1.44 loss per $22.2 rung**).

**Layers that actually bound it:**
1. **serial one-rung-per-cycle** — real, proven (T4): ≤1 add/~1 min (pipeline `STEPS_EVERY_MIN` includes `pending_order_monitor`, run_pipeline.py:38, 56).
2. **Per-row stops** (pm ATR/trail + guardian hard stops + `hml_threshold` = `min(-4% base, −stop distance)` per row, position_manager.py:217-256) — bound each tranche's loss; the **stack** is stopped as a unit by the earliest row's stop (full HL close).
3. **HL cross-margin** — hard physical bound = account equity (adds are fixed $11-23 notional ⇒ $1.1-2.3 margin each).
4. **Kill switch / vacation** — `LIVE_TRADING_ENABLED` + `vacation_pause.json` gate opens (not the adds' size).
5. **NOT in force on this path:** `MAX_OPEN_POSITIONS=6` (hermes_constants:544) is read only by `decider_run` (signal path) and guardian orphan creation (hl_sync_guardian:1524) — **brain.add_trade and the pending executor never check it**; `MAX_PORTFOLIO_HEAT=0.15` (constants:669) has **zero readers anywhere** (dead constant); `HML_STRUCT_FLOOR_ACCT=-8.0` **RETIRED 2026-11-14** (constants:823); brain's only size line is the **HL_MIN $11 floor, not a cap** (brain.py:672-675, 812-823).

⇒ **F-3:** nothing caps aggregate add exposure — the only true bounds are cadence + keeper reach guards + margin + per-row stops. At today's $11-23 rungs the exposure is trivial; a runaway sequence would show up as open-row count ≫ 6 with no layer stopping it.

## (C) Status table for add failures (executor mapping, watchdog 1804/1831-1835)

| brain outcome (second-tranche path) | rc + marker | state | rung afterwards |
|---|---|---|---|
| FORCE → opened | 0 + `✓ Added trade` | **fired** | consumed (adds once) ✓ |
| FORCE → later pre-open gate REJECT (HL_MIN/blacklist/live-off/vacation/orphan/RSI non-prearmed) | 1 + `[brain.py] ❌ REJECTED` | **rejected** | **retryable**: waits for price reclaim → `retested` → cross#2 → ADD again (1540-1549); never loops while still crossed |
| FORCE → `mirror_open FAILED` / HL-verify rollback / INSERT failure | 1, **no REJECTED marker** | **error** | consumed (terminal) |
| exception / traceback (e.g. brain DB down) | 1 + traceback, no marker | **error** | consumed — proven live-ish: `/tmp/brain_dbdown.py` → **rc=1, traceback at brain.py:678, 0 `✓ Added trade`, 0 REJECTED** |
| `validate_levels` ValueError | 2 (parser.error) | **error** | consumed, pre-side-effect |
| dup-guard refusal **under `--force`** | — | **unreachable** (683 requires `not force`; BF19) | — |
| FORCE line alone (`⚠️ FORCE…`) | non-0 | **error**, NOT rejected (exact-marker, 1831; T10x) | consumed |
| subprocess timeout/lock failure | n/a | **error** (1747-1757 fail-closed) | consumed |

Fail-open trace for a **monitor-side** DB error (1628-1629): steer emitted blind with `--force` (T8) → brain re-queries under its own connection:
- **brain DB also down** → raises at 678 → uncaught → rc=1 traceback → **'error', NO trade (fail-closed)** — rung consumed.
- **brain DB up** (transient monitor-only blip, plausible under `connect_timeout=5`) → dup row found → FORCE → **proceeds with NO direction check → blind ADD, or NETTING fill if the open row is opposite (BF20)** — **F-1**.

---

## Findings

| ID | Sev | Location | Finding |
|----|-----|----------|---------|
| **F-1** | **MEDIUM** | `scripts/trade_watchdog.py:1628-1629` (+ belt 1791-1793) | **DB-exception fail-open changed consequence from safe to netting-capable.** `except Exception: _open = None` treats any psycopg2 failure as flat → emits the add steer → executor sends `--force`. OLD code: same fail-open, but no `--force` ⇒ brain dup-guard REJECTED duplicate ⇒ no trade. NEW: brain's direction-blind dup + force ⇒ if brain's own connect succeeds, an **opposite-direction open gets netted by one rung with zero monitor visibility** (BF20); if brain's DB is also down ⇒ rc=1 ⇒ rung burned terminal 'error'. Fix direction: don't fail open — on exception `continue` (keep armed, no burn), or re-check direction in the executor before `--force`. |
| **F-2** | **MEDIUM** | `position_manager.py:1607` → `hyperliquid_exchange.py:751` (`sz=None`); `hl_sync_guardian.py:2012-2033`, 4768-4778; pre-existing, **now routine** | **N rows ↔ 1 HL position: the first row to stop closes the WHOLE stack.** The add's SL does not protect the add; the surviving row lingers DB-open/HL-flat (live precedent `#16306/#16307`: 9-min divergence, one real close booked at two exits) until its own level or guardian step-8 (~2 min). Ladder adds make this the common case 1/cycle. Needs a close path that either sizes the HL close to the closing row (partial) or closes all same-coin rows atomically. |
| **F-3** | **MEDIUM** | `brain.py:677-691` (no count check); `hermes_constants.py:544,669,823` | **No aggregate cap on the add path.** `MAX_OPEN_POSITIONS=6` never checked by brain/watchdog pending exec (decider/guardian-orphan only); `MAX_PORTFOLIO_HEAT=0.15` has zero readers (dead); `HML_STRUCT_FLOOR_ACCT` retired. Bound = serial 1/cycle + keeper reach guard + HL margin + per-row stops. Keeper self-replenishes ⇒ an H-hour slice ≈ 60·H adds ≈ **$1,332·H notional** at current sizes, unbounded by any portfolio layer. |
| **F-4** | **LOW** | `scripts/trade_watchdog.py:1773-1777` (flagged in-code) | Flip/DB-window netting is bounded (≤$22.30 fill, ≤$22.65 position) **but the phantom-opposite-row follow-on is unflagged**: a partial net writes an opposite row whose stop later full-closes the real position; an exact net moves HL money with no DB row (rc=1 'error'). Acceptable at rung-scale sizes; add the exec-side direction assert the comment names if flips ever appear. |
| **F-5** | **LOW** | `scripts/trade_watchdog.py:1622-1624, 1631-1642` | Gate SQL has **no `server` filter** (brain's dup has `server='Hermes'`) ⇒ monitor and brain can disagree about "open" across servers; and a row with NULL/empty `direction` renders `''`, never matches, and is **mislabeled "opposite"** → rung waits forever (fail-safe, no fire — T9). Cosmetic + theoretical; schema keeps direction populated. |

Nothing blocks release at today's sizes: the add path behaves exactly as ruled (flat→fire, same-dir→add, opposite→wait, serial 1/cycle, belts correct, machine before gate), the 2026-11-10 two-shots-in-one-spike cadence is preserved by `serial_claimed`, and the only consequence that changed-vs-old on a DB blip is captured in F-1.

---

## D evidence (exact)

**ONE sanctioned live `run_cycle`** — `python3 scripts/auto_trader.py` → **rc=0, stderr empty**:
`enabled=true, mode=live, decision=MANAGE_ONLY, scores {long:-20, short:10, regime:CHOP}, price=56281.53, hypo_events=[], shadow_armed=[], live_armed=[], tweaks=[], armed_detail=[], hypotheticals=0, stats {n:58, wins:26, wr:44.8, pnl_usdt:+0.775}`.
**Book before AND after:** exactly **1 open = BTC SHORT `#17014`** (entry 56637, SL 56693.64, TP 53958, $22.30, 10x, signal ai-trader-pending) — no new trades, no closes; last close `#17013` 03:35 `mfe_exit`. Rung book unchanged: config **68 orders / state 75 entries (fired 60, error 14, rejected 1) / armed 20**, `pending_orders.json` + `pending_orders_state.json` md5 identical before/after (only `auto_trader.db` changed = run_cycle's own sanctioned journal). **No new arms** (keeper: short rung 55796 within reach; long ITM/reach-blocked). `pipeline.log` 0 Tracebacks; `trade-watchdog.log` last write 04:46 pre-commit, 0 shipped-code frames in its 224 historical Tracebacks.

**Suite:** `analysis/test_manual_exit_manager.py` → **20 passed, 0 failed, rc=0** (rerun against HEAD `5522515b` — post-6b9fb87 commits are docs-only, `git diff 6b9fb87..HEAD` touches zero scripts).

---

# ACCEPTANCE ROUND — commit `6a6099b4` (F-1 + F-3) — **FINAL PASS**

Verified 2026-11-21 ~05:15-05:20 UTC against `6a6099b4` "F-1 + F-3 from agent-3: no blind adds on DB errors, MAX_OPEN_POSITIONS enforced on the add path".

| Check | Result | Evidence |
|---|---|---|
| Scope | **PASS** | `git show 6a6099b4 --stat`: exactly `scripts/trade_watchdog.py`, 27+/1−; brain/pm/auto_trader untouched |
| **F-1 closed — matches prescription** | **PASS** | watch:1637-1643: `except Exception as _qerr:` → log `open-position query failed ({type(_qerr).__name__}) — deferring one cycle (fail-safe, no blind add)` + `continue` → **no steer, no state, no serial burn**; `except: _open = None` fail-open is GONE (the `-1` line). Import failures (`psycopg2`/`_secrets`) live inside the same try → also defer. Rung re-qualifies next ~1-min cycle. Re-verified on my independent harness: **dbdown → ZERO steers, state file untouched, exact log present, next cycle with DB back fires normally** (T8, 4 checks). The BF20 blind-add/netting consequence is unreachable: no steer ⇒ no `--force` cmd ⇒ brain never sees it. |
| **F-3 closed — matches prescription** | **PASS** | watch:1626-1631 + 1644-1654: second query `SELECT COUNT(*) FROM trades WHERE token=%s AND status='open'` in the SAME try (a count failure → F-1 defer, fail-safe); `_max_open = int(__import__("hermes_constants").MAX_OPEN_POSITIONS)` with `except → 6` (constant verified live = **6**); `if _open_count >= _max_open > 0:` → log `N BTC rows open >= MAX_OPEN_POSITIONS(6) — add deferred (F-3 aggregate cap)` + `continue` (no state burn). Harness on the mock-PG path: **count=6 defers with exact cap log; count=2 same-dir still ADDs; count=0 flat fires; opposite-at-cap waits with no state burn** (T12, 7 checks). Per-coin count (`token=%s`) — the keeper-replenished stack now has the hard ceiling F-3 demanded; dead `MAX_PORTFOLIO_HEAT` stays backlog (documented). |
| Gate ordering preserved | **PASS** | cap/deferral both sit AFTER the multi-touch machine and BEFORE the steer — a defer never burns `first_break`/`retested`/`triggered` state (T12c/T8 asserts). |
| Regression | **PASS** | full independent suite now **59/59 rc=0** (was 51/51 — T8 expectation inverted to defer, 7 new F-3 checks; production `pending_orders*.json` md5 unchanged across run); author's tests + mine agree; **suite 20/20** rerun; `py_compile` OK; fresh imports OK; brain FORCE harness **20/20** re-run (brain untouched); `/tmp/brain_dbdown.py` still rc=1/0-Added-trade; `pipeline.log` (mtime 05:18, post-fix tick) **0 Tracebacks**. No second live `run_cycle` run — the ONE sanctioned cycle in this verification was already spent pre-fix; post-fix code paths are covered by 59/59 + suite + clean logs. |
| Residual deltas vs my prescriptions | **none blocking** | Two notes, both acceptable: (a) F-3 also defers the **flat** fill while count≥6 for that coin — correct (flat-for-coin implies count 0, so unreachable; when count≥6 the coin is by definition not flat); (b) the cap, like the direction gate, still has **no `server` filter** and `btc-ceo-*` non-serial tranches bypass the whole block (pre-existing scope, F-5 accepted as documented). |

**FINAL VERDICT: PASS.** F-1 and F-3 closed exactly as prescribed (defer-on-error fail-safe; per-coin count cap at `MAX_OPEN_POSITIONS=6`); F-2/F-4/F-5 accepted as documented; `MAX_PORTFOLIO_HEAT` wiring on backlog. The ladder ADDS feature (commit `6b9fb870`) plus its acceptance fix (`6a6099b4`) are verified safe to ship.
