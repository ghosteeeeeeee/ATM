# bug_hunter verdict — CEO deep-run rulings 20261121T163236Z (UNCOMMITTED changeset)

Verifier: bug_hunter (agent-5) · 2026-11-21 · authority = `automation/ceo/checkpoints/20261121T163236Z-decision.md`
Scope verified: `scripts/auto_trader.py`, `scripts/brain.py`, `scripts/trade_watchdog.py`, `analysis/test_pending_machine.py` (exactly these 4 modified).
Harnesses (SELECTs + mocks only, /tmp): `harness_a.py`, `harness_a2.py` (D2.2 behavioural, extracted `_lag_stop` with mocked `_apply_stop`/`DB`), `harness_c.py` (D2.3 end-to-end on `brain.add_trade`, `psycopg2.connect` stubbed), plus the shipped suites. ONE sanctioned live run: `python3 scripts/auto_trader.py` → `run_cycle` rc=0.

## Verdict table

| Ruling | Verdict | Evidence |
|---|---|---|
| **D1(c)** ROUND → shadow-only | **PASS** (code) / **MEDIUM finding** (counterfactual fidelity) | zero `_apply_stop`/`rule='ROUND'` left (grep = 0 hits; shadow block 611–625 does no writes, proven by harness: 0 apply calls); dedup `(pid,_rt)` per process (auto_trader.py:64, 619–620); structure trail untouched (diff hunks only 597/615/618 + call-site args) |
| **D2.1** entry distance/leak | **PASS — no entry-trigger code changed** | `git diff -U0 scripts/` hunks: get_open_btc, `_be_armed`, `_lag_stop`, hi/lo call args, brain band/CLI, watchdog heat/flag/payload/cmd — no trigger/fill-leak hunk anywhere |
| **D2.2** peak-gated BE | **PASS** (implementation) / **HIGH finding** (ruling's #17026 counterfactual is wrong) | `_be_armed` 67–90; `_be` computed once at 518–520; birth BE-lock 544–548 goes through it; clamps 544/567/590/615/618/644/653/667/674 all read that one `_be` (AST: exactly 2 stores, no re-derivation); fail-safe matrix 34/34; plumbing per-row |
| **D2.3** RSI band on ADDs | **PASS** + 2 LOW findings | band gate brain.py:475–494 before every other gate; resolution chain caller→metadata→`_fill_time_rsi` (476–486) identical to money gate (521/535); payload key 1755 == executor read 1879; single writer 1711; classifier 1912/1916 maps band→`rejected` (no-burn) |
| **D3** heat gate | **FAIL — blocker** | `get_account_value_curl()` returns `account_value=None` **always** (HL puts it under `marginSummary`) → `_eqv=0` → `heat=None` → **every `btc-auto-*` fill deferred, forever (dark ladder)**; live-proven below; the shipped test mocks the wrong shape so it passes anyway |
| **E** regression | **PASS** | pending-machine 9/9 groups, manual_exit_manager 20/20, py_compile 3/3, fresh imports, live `run_cycle` rc=0, pipeline.log 0 Tracebacks, trade-watchdog.log 0 Tracebacks from shipped files, hermes_constants untouched, no protected-flag edits |
| **F** timeout residue | **PASS (benign)** | `20261121T163236Z-result-{1,2}.md` never written and **nothing references them** (grep repo-wide = 0 outside decision.md); all other modified files are runtime/report writes (list below); no dangling edit in any other file |

---

## (A v) PeakReanchor / peak consistency — CALL: **CONSISTENT (load-bearing, holds)**

Code:
- brain seeds `entry_price = hl_entry` (brain.py:943 col 4) **and** `lowest_price = hl_entry` for SHORT (brain.py:968 col 29) → at creation `seed == entry` exactly, so `_reanchor_seed_peak`'s `abs(seed-entry) <= entry*1e-9` gate (position_manager.py:2732) passes.
- Every entry rewrite moves the peak in the **same SQL statement**: pm PeakReanchor builds one `UPDATE trades SET current_price…, entry_price…, <seed>` (position_manager.py:2915–2935, comment "Single statement so entry and seed can never diverge"); guardian mirror-fill does the same (hl-sync-guardian.py:2966–2971); guardian reconcile resets both peaks with the entry (hl-sync-guardian.py:1338–1344).
- `_be_armed` reads **only the direction-appropriate column** (`lo` for SHORT, `hi` for LONG) — exactly the column the reanchor moves.

Real events (verified, not claimed):
- `pipeline.log:672425` — `[PeakReanchor] BTC SHORT trade=17015 entry 55762.0 -> 56199.5, lowest_price 55762.0 -> 56199.5` (this is the **55762→56199.5 event — it belongs to #17015, the duplicate, not #17014**; lead's pm:2908 citation is the right code, wrong trade id).
- `pipeline.log:643758` — `🔁 BTC peak re-anchor: lowest_price 56331.925 → 56637.0 (moves with entry)` for #17014 (opened 03:54:07).
- Both moved `lowest_price` with `entry_price`.

**Counterfactual if `lowest_price` were NOT moved:** (56199.5 − 55762)/56199.5 = **0.7786% ≥ PM_TRAIL_ACTIVATE_PCT (0.40%) → `_be_armed` ARMS AT BIRTH** for a SHORT that had never been 0.40% favourable → `_be = entry*1.001 = 56255.70` from cycle 1 → BE-cap active immediately = the exact phantom class (ETH #16421 / UGB-PT 1.45s after open, hermes_constants.py:791). So the reanchor is load-bearing for D2.2 and it holds on every path examined.

Residual (INFO): if the peak has already moved when entry is corrected, `_reanchor_seed_peak` correctly refuses (real MFE is preserved) — peak-vs-new-entry can then include prints from the seconds between brain's INSERT and the HL fill; bounded by fill latency, and the failure direction is fail-safe (peak behind entry → `(entry−lo)/entry < 0` → unarmed).

---

## (A vi) The three counterfactual re-walks (real data: PG rows + `auto_trader.db` events + `candles_1m`)

### #17026 (LONG, entry 60182, open 13:28:12 → exit 15:17:18 manual_sl_hit −3.7885%)
Event trail (auto_trader.db events):
1. `13:39:28` stop 59152.0 → **59580.36** (rule R1) — a structure/birth write; old `_be` was **0** at that cycle (proof: 59580.36 < `_be` 60121.818, an armed clamp would have written 60121.818) → new code also `_be=0` (DB `current_price` was still ≤ entry after the 13:29 dump to 59540) → **identical**.
2. `14:09:28` stop 59580.36 → **60121.818 = 60182×0.999 = `_be` exactly** — a BE clamp (favourable/adverse/birth clamp all require `_be` set) → old code armed (in profit).
   **New code at 14:09:** `highest_price` = 60951.5 (peak first printed 14:03; candle high 60996 at 14:03; position_manager updates ~60s, and old code's fresh `current_price > 60182` at 14:09 proves an update landed) → (60951.5−60182)/60182 = **+1.2786% ≥ 0.40% → ARMED** → same `_be` → **same write**.
3. Kill: first 1m low ≤ 60121.818 = **15:16**, exit 15:17:18 ✓. Post-15:18 price never exceeded 60360 (low 59690) — no recovery either way.

**Verdict: D2.2 does NOT save #17026.** The decision's premise ("#17026-class: wick-peak ~0.1% never arms") is **contradicted by the data**: DB `highest_price = 60951.5` (+1.28%), candle high 60996 (+1.35%). It arms at 13:36 (first 1m high ≥ 60426.7), the 14:09 clamp reproduces, identical −3.7885% exit. (Had it *not* armed, the stop would have stayed 59580.36 — the 15:16 low 59723.46 and every later print stayed above 59580.36, i.e. the trade would have survived. Arming is the only thing that kills it.) Metric "BE-at-birth retest kills → 0 new after arm-on-peak" will **not** be met for this class; the incident was a *mid-trade clamp at a genuine +1.28% peak*, not a birth BE-lock.

### #16915-class (SHORT, entry 62911, lowest 62061.5 = +1.3503% peak → arms)
Event trail: `01:20:28` 64265 → **65058.98** (adverse raise), `01:50:27` → **64489.57** (favourable tighten), `02:20:29` → **64408.8445**, exit 02:30:32 manual_sl_hit −24.5108%.
Each written value is **outside** what an armed `_be = 62911×1.001 = 62974.0` would permit (an armed adverse raise would have been capped to 62974, not 65058.98; an armed favourable target would have been capped to 62974, not 64489.57) → **old `_be` was 0 at every write cycle → price was above entry (underwater) at every write** → new `_be` is a strict subset of old → also 0 → **byte-identical stop path, identical −24.51% exit.** It arms at some point (peak 1.35%) but arming only ever binds while in profit, and it was never in profit at a write. D2.2 changes nothing here — exactly "arms → clamp as before".

### #17014 (SHORT, entry 56199.5, open 03:54:07 → exit 06:20:31 manual_trail_hit +2.0374%)
Event trail: `04:09:21` 57019.0 → **56693.637** (structure R1 — ROUND not yet committed; 89a0bb24 landed 05:47), `06:09:22` 56693.637 → **56000.0** (rule shows `R1` because the `rule='ROUND'` tag only landed in b3207603 at 06:51, **after** this write; `56000` is exactly `ceil(price/500)*500` for price ∈ (55500, 56000] — the structure trail cannot produce an exact 56000.0, it would be `price*1.001` = 56000.00456 or a swing-derived float). **The 06:09 write was the ROUND anchor** (value-exact + ROUND live 05:47–06:51 + price in band + only one event).

Re-walk under NEW code:
1. 04:09 structure write **unchanged** (price 56637 > entry → `_be=0` in both codes).
2. 06:09 ROUND write → **suppressed → `📊 [ROUND-ANCHOR-SHADOW] WOULD-RATCHET 17014 SHORT stop=56693.637 -> 56000`**, stop stays **56693.637**.
3. No further structure write: the only remaining motion is a rally 55800 → 56700, which prints **higher** 15m swing highs = *adverse* for SHORT → `t2 = s1h[0]+0.1·atr` is then BE-capped to `_be = 56255.70` (armed: lowest ≤ 55944 → 0.4545% ≥ 0.40%) → `t2 > stop+1`? 56255.70 > 56694.64 → **False → None → no raise**. Favourable steps need a *lower* swing high, which a rally does not print. (Actual events show zero writes between 04:09 and the 06:20 close, corroborating.)
4. 06:20:31 price 56085 < 56693.637 → **no exit** (the actual exit was caused by the ROUND write).
5. First 1m high ≥ 56693.637 after 06:20:31 = **06:38** → stop hit → `manual_sl_hit` at ≈56693.637 → (56199.5−56693.637)/56199.5 = **−0.879% → ≈ −8.79% at 10x ≈ −$0.39** (actual was **+2.0374% / +$0.09**).

**Verdict: D1(c) converts #17014 from a banked winner (+$0.09) into a loser (≈ −$0.39).** That is the *intended* trade of "break of structure only", but the decision's metric ("premature round-reclaim exits → structure-only saves") must be counted with this sign: the 7d review will see #17014-class exits become −8.79% instead of +2.04%. (Secondary path: the standing `profit_lock` steer "move SL 56693.6 → breakeven 56637" was age=3/unexecuted in the real run; if it ever executes, the exit is 56637 ≈ −0.78% instead — still a loser.)

---

## (B ii–iv) Shadow faithfulness + `_be`-state bias — CALL: **faithful for the n=1 live instance; structurally BIASED (over-count) — recommend an independent legacy-BE in the shadow guard**

- **(B i)** zero stop writes: grep `rule='ROUND'` across `scripts/` = **0 hits**; the shadow block (611–625) contains no `_apply_stop` (shipped selfcheck + harness: 0 apply calls from the shadow path).
- **(B ii) condition is textually identical to the old active code.** `git show HEAD:scripts/auto_trader.py` old block:
  `if _rt > price and _rt < stop and (not _be or _rt <= _be): if _apply_stop(_rt, stop, pid, rule='ROUND')`
  vs new 615: `_round_hit = _rt > price and _rt < stop and (not _be or _rt <= _be)` — **byte-identical guards** (SHORT); 618 is the LONG mirror. Walked #17014 @06:09:22 through both: old `_be = 56199.5×1.001 = 56255.70` (in profit), `_rt = 56000 ≤ _be` → TRUE → write; new `_be_armed` → lowest ≤ 55944 → 0.4545% ≥ 0.40% → armed → same `_be` → same TRUE → log. **Faithful.** (And if `lowest_price` had lagged → unarmed → `_be=0` → `not _be` → still TRUE → same log: the outcome is identical either way for this instance.)
- **(B iii) dedup:** module-level `_round_shadow_logged` (auto_trader.py:64), keyed `(pid, _rt)` (619–620), **per process** as ruled. Harness: same level logs once across cycles; a *new* round level logs again (re-ratchet). Old code could never re-write the same level anyway (`rt < stop` fails once `stop == rt`), so dedup only suppresses log spam, not counterfactual lines.
- **(B iv) `_be`-state bias — the shadow's BE-cap guard uses the NEW peak-gated `_be`, the old code used in-profit-at-birth `_be`.** New `_be` ⊆ old `_be` (same formula once armed; 0 whenever old was 0), so the guard `not _be or rt…` is **strictly more permissive** in the window *in-profit ∧ peak < 0.40%*. Concrete case (harness, PASS): SHORT entry 60182, price 60100 (in profit, peak 0.14% → unarmed), stop 60800, `_rt = 60500 > old _be 60242.18` → **old code BLOCKED the write, new shadow LOGS `WOULD-RATCHET 60800 -> 60500`**. Bias size: for BTC ≈ 60k the window is price ∈ (entry×0.996, entry) where the next 500-round exceeds entry×1.001 → a **~0.30%-wide band directly under entry** (entry 60182 → price ∈ (60000, 60182)); once price is ≥0.40% in profit the two agree exactly. Second-order: because the shadow never writes, `stop` stays looser than the old system's, so `rt < stop` is also evaluated against a looser stop → additional over-count during reclaims above an already-taken round (e.g. old stop 56000 vs shadow stop 56693.637: a reclaim to 56400 makes `rt=56500 < stop` true for the shadow and false for old).
- **Direction of bias: ONE-WAY — the shadow can only OVER-COUNT `WOULD-RATCHET` lines, never under-count.** Consequence: the 7d review (2026-11-28, "saved ≥$1 → reconsider hybrid") would over-estimate ROUND's value → risk of restoring a rule that didn't earn it. **My call: yes, give the shadow an independent legacy-BE** — one line at 615/618: compute `_lb = entry*1.001/0.999` whenever `price` is in profit (ignore peak) and use `_lb` in `_round_hit` only. Severity MEDIUM (review-integrity only; zero live effect).

---

## (C v) Band-rejected classification — CONFIRMED retryable / no-burn

- Band prints exactly `[brain.py] ❌ REJECTED: {token} {direction} — prearmed ADD …` (brain.py:491/493) and `return None` **before any DB access** (gate at 475 is the first statement after `direction=`; harness: no connect attempted on the reject path).
- Watchdog classifier trade_watchdog.py:1912 `_rejected = any(ln.startswith("[brain.py] ❌ REJECTED") …)` → 1916 status `"rejected"` (success requires rc==0 + "✓ Added trade", which a band block never satisfies) → `rejected` is a **waiting state** (1409 prune list, 1540 re-cross re-arm, "no-burn … rejection != failure" comment 1894–1906). Harness simulated the classifier on the real band line → `status='rejected'`. **A band-blocked ADD waits for its reclaim, does not burn the rung.** ✓
- (C i) source consistency: band chain `signal_rsi_14 → _signal_metadata['rsi_14'|'rsi'] → _fill_time_rsi(token)` (476–486) is **the same chain** the money gate uses (`_rsi_chk = signal_rsi_14` 521 → metadata 524–530 → `_fill_time_rsi` 535); `None` fails open (401–402) as ruled.
- (C ii) plumbing verified end-to-end: monitor ADD branch sets the key (1711) → rebuilt payload carries `"prearmed_add": order.get("prearmed_add")` (1755) → `execute_safe_actions` passes `action["order"]` (2411) → executor `if order.get("prearmed_add"): cmd.append("--prearmed-add")` (1879) → argparse `--prearmed-add` (brain.py:1695) → `prearmed_add=args.prearmed_add` (1789) → gate `if prearmed and prearmed_add` (475). Key strings match exactly; test group 8 asserts payload-True / flat-None / cmd-with / cmd-without.
- (C iii) first-entry byte-identical: the flat path never sets the key, payload value is `None`, executor test is falsy → command line identical (`--prearmed-add` absent — asserted). Gate can't fire without both flags (harness: `prearmed=False` → no band; `prearmed_add=False` → no band; `RSI=None` → no band).
- (C iv) who else could set it: **only** trade_watchdog.py:1711 (repo grep); `data/pending_orders.json` has 71 orders, **zero** `prearmed_add` keys; the key is never persisted (config file is read-only for this mutation, one-shot `state` doesn't carry it) → no stale-flag path. Residual race (LOW): flag is set from the monitor's DB read; if the open position closes before brain inserts, the band applies to what becomes a first entry — fail-safe direction (a missed catch, never a loss).

---

## (D ii) Equity-shape proof — DARK LADDER CONFIRMED (blocker)

Live read (2026-11-21, read-only `/info`):
```
get_account_value_curl() -> {'account_value': None, 'withdrawable': '8.022137', 'positions_raw': [...]}
raw clearinghouseState top keys = ['marginSummary','crossMarginSummary','crossMaintenanceMarginUsed',
                                   'withdrawable','assetPositions','time']   # NO top-level accountValue
marginSummary.accountValue = '16.176435'   (re-read: 16.112161)
```
`hyperliquid_exchange.py:521` does `result.get("accountValue")` → **always `None`** (HL nests it under `marginSummary`; cf. hl_leaderboard.py:212 and hl_wallet_discovery.py:111, which both read `state['marginSummary']['accountValue']`). `pump_hunter.py:539` only works because it uses `withdrawable` (present top-level).

Watchdog path (trade_watchdog.py:1676–1689): `_eq` is a dict → `_eqv = float(None or 0) = 0.0` → `_heat = None` → calibration line `heat=None equity=0.00` → WARN `equity read failed — heat defer` → `continue`. **Every `btc-auto-*` evaluation defers, permanently → dark ladder.** Live simulation with the real function and the real numerator: `notional=11.10 equity_parsed=0.0 heat=None → DEFER`. Even with the correct parse the current book defers (`11.10 / 16.11 = 0.6889 > 0.15`) — but that is the cap legitimately binding, not a parser failure; the parser failure makes the ruling's calibration metric ("heat logged every add-gate") unmeasurable and the WARN indistinguishable from a real HL outage.

**The shipped test encodes the bug:** `analysis/test_pending_machine.py:239` `HLE.get_account_value_curl = lambda: {'account_value': EQUITY[0]}` — the mock returns the shape production never returns, so groups 8 passes while production can never pass. (Also `get_account_value_curl` never raises — it returns `{}` on exception (hyperliquid_exchange.py:525–526) — so the `except` branch at 1695 is unreachable for network errors; the `None` branch at 1686 is what actually fires, and it is mislabelled "equity read failed" when the read succeeded.)

Other D checks:
- (D i) numerator = `SELECT COALESCE(SUM(amount_usdt),0) FROM trades WHERE status='open'` — **all coins, no token filter** ✓, same cursor before `_cur.close()` (1638–1643) ✓, literal ruling compliance. NOTE (INFO): it also counts paper/copy rows while the denominator is live HL equity.
- (D iii) three distinct defers ✓: breach → INFO `HEAT-DEFER heat=… cap=0.15` (1691); `heat is None` → WARN `equity read failed` (1687); exception → WARN `heat gate error (Type)` (1696). Calibration line fires on **every evaluation that reaches the gate** (1682) — but NOT when F-1 (1650) or F-3 (1660) defer first, so "every evaluation" is narrower than the ruling's wording.
- (D iv) scope: gate is inside the stacking block (entered only when `crossed and (btc-auto-* or serial)`, 1599) and further guarded by `oid.startswith("btc-auto-")` (1672). `btc-ceo-*` (19 orders) and the hand-arm `hype-short-7060` never reach it (or are excluded by prefix) → **hand-arm bypass ✓**; all 51 `btc-auto-*` ids reach it on every crossed fill — **no btc-auto fill can bypass** (block condition is exactly `startswith("btc-auto-")`). Fills that never reach the block (status-machine `continue`s: not-crossed, first-break wait, rejected-reclaim, opposite-dir wait, serial throttle) skip the heat check — **all of those are non-fills, so skipping is correct**; the only early `continue`s *inside* the block (F-1 DB error, F-3 MAX_OPEN) are themselves defers, so no fill escapes the gate. Scope note (INFO): the gate also covers **flat first fills** of `btc-auto-*` (test group 8 enshrines this) — broader than the ruling's "add-path/adds" wording.
- (D v) F-1 interaction: F-1 `continue`s at 1653 *before* the heat gate → single defer, F-1's log only, no double-defer ✓ ordering fine.
- (D LOW) ordering noise: the heat gate (1672) runs **before** the opposite-direction wait (1713), so when heat > cap a `HEAT-DEFER (D3)` is logged for an order that would have waited anyway → inflates the ruling's "defers counted" calibration metric.

---

## E — Regression

- `analysis/test_pending_machine.py` → **ALL PENDING-MACHINE TESTS PASS (9 groups)** rc=0 (groups 1–7 pre-existing, 8 = D3 heat + flag plumbing, 9 = band predicate). Test writes go to `tempfile` via `paths.HERMES_DATA = _tmp` (line 20) → **zero production writes**.
- `analysis/test_manual_exit_manager.py` → **20 passed, 0 failed** rc=0.
- `python3 -m py_compile scripts/{auto_trader,brain,trade_watchdog}.py` → OK; fresh `import auto_trader, brain, trade_watchdog` → OK.
- **ONE sanctioned live run:** `python3 scripts/auto_trader.py` → **rc=0**, empty stderr. Summary: `enabled=true, mode=live, decision=BRACKET, scores{long:0, short:10, regime:CHOP}, price=60072.47, tweaks=[], shadow_armed=[], live_armed=[], hypo_events=[], hypotheticals=0`, stats n=58 WR 44.8% +$0.775, by_direction long 25T 36.0% +$0.064 / short 33T 51.5% +$0.711. **Book at run:** 3 open rows (APT/CRV/CHIP LONG, $11.10 each, Σ notional $33.30, all `paper=False`, signal `pump-chain+`) — no BTC position → `get_open_btc()` empty → structure/ROUND paths not exercised live (covered by harness instead).
- Logs: `logs/pipeline.log` **0 Tracebacks**; `logs/trade-watchdog.log` 273 Tracebacks but **0 from shipped files** (all inside embedded agent shell transcripts, `File "<stdin>"`); last watchdog cycle 17:39 (after trade_watchdog.py mtime 17:12) ran clean. No `D3 calibration` / `ROUND-ANCHOR-SHADOW` / `prearmed ADD` lines in production logs yet — **no live evaluation of either new gate has occurred** (no `btc-auto-*` cross and no open BTC structure position since the edit), so the dark ladder is proven by direct invocation, not yet observed in production.
- Scope: `git status` = the 4 code files + runtime/report writes (below); **`hermes_constants.py` untouched (not in status) — the "zero edits" promise holds**; no protected-flag change (`LIVE_TRADING_ENABLED`, `CEO_PROTECTED_FLAGS`, `CONFLUENCE_REQUIRED`, DailyFillCap, entry/fill-leak code all untouched; `MAX_PORTFOLIO_HEAT` still only has its definition at hermes_constants.py:669 + this new reader).

## F — Deep-run timeout residue (all benign)

Missing: `automation/ceo/checkpoints/20261121T163236Z-result-1.md` and `-result-2.md` (the timed-out subagents' own reports). **Repo-wide grep for `20261121T163236Z-result` → 0 hits outside decision.md** → nothing dangles on them. Also not done (parent's steps, not code): the `## CEO Deep Run` section of `ceo_report.md` and the OpenMemory store.
Other modified files are runtime/report writes, not code:
`automation/bug_report.json` (timestamp refresh), `automation/ceo/ceo_report.md` (append of an earlier `CEO Status — 20261121T153826Z` block), `automation/ceo/vacation_alerts.json` (alert-list rotation), `automation/error_alerts.md` (hourly appends), `automation/signal_rotation.md` (timestamp line), `data/watchdog_recommendations.json` (watchdog output), `brain/associative_memory.db` (runtime DB), untracked `automation/ceo/2026-11-21_entries-exits-decisions.md` (lead's decision brief). No other file carries a dangling edit.

---

## Findings (severity · location · what)

1. **BLOCKER (D3, liveness)** `trade_watchdog.py:1676–1689` + `hyperliquid_exchange.py:521` — equity parser reads a key HL never returns at top level → `account_value` always `None` → `_eqv=0` → `heat=None` → **every `btc-auto-*` ladder fill deferred forever (dark ladder)**; calibration log permanently `heat=None equity=0.00`; the WARN is indistinguishable from a real HL outage. Live-proven (shape + sim above). Fails safe (no over-fill) but the ruling's feature and its metric are dead. Fix direction (not applied, per instructions): read `marginSummary.accountValue` (as hl_leaderboard.py:212 / hl_wallet_discovery.py:111 do) or `withdrawable`, and make the test mock use the real shape.
2. **HIGH (D2.2, ruling premise)** `auto_trader.py:67–90, 518–520` + decision.md:11 — **#17026 is not saved**: peak is +1.2786% (DB `highest_price=60951.5`, candle high 60996), not "~0.1%"; it arms at 13:36, the 14:09:28 clamp to `entry×0.999 = 60121.818` reproduces identically under the new rule, and the 15:16 retest still hits it → same −3.7885%. The decision's headline counterfactual and the metric "0 new BE-at-birth retest kills" are wrong for this class (it was a mid-trade clamp at a genuine peak, not a birth lock).
3. **MEDIUM (D1(c), review integrity)** `auto_trader.py:615, 618` — shadow guard uses the new peak-gated `_be`; old code used in-profit-at-birth `_be` → in the in-profit/peak<0.40% band (~0.30% wide under entry) plus the never-tightened `stop`, the shadow **over-counts** `WOULD-RATCHET` lines (one-way bias) → the 7d "saved ≥$1 → restore hybrid" decision can be flipped by a counterfactual the old code would not have written. n=1 live instance (#17014@06:09) verified faithful. Suggested fix (not applied): independent legacy-BE in the shadow guard only.
4. **MEDIUM (D1(c), economics — expectation, not a defect)** `auto_trader.py:611–625` — re-walk: shadowing the 06:09 ROUND write leaves #17014's stop at 56693.637, the rally prints no favourable structure (adverse raise is BE-capped at 56255.70 < stop), price crosses 56693.637 at 06:38 → **−8.79% (≈ −$0.39) instead of +2.0374% (+$0.09)**. The 7d metric must count #17014-class outcomes with this sign.
5. **LOW (D2.3)** `brain.py:404` — `rsi = float(rsi)` uncaught: a non-numeric `_signal_metadata.rsi_14` raises `ValueError` out of `add_trade` → brain CLI traceback → no `REJECTED` marker → watchdog 1916 classifies terminal **`error` (rung burned)** instead of retryable `rejected`. Reachability today = 0 rows (PG: 0 trades with non-numeric `rsi_14`); the money gate shares the same pattern (pre-existing).
6. **LOW (D2.3)** `trade_watchdog.py:1711` — ADD flag set from the monitor's DB read; if the position closes before brain inserts, the band applies to a first entry (could block a #17016-class catch). Fail-safe direction; window = same cycle.
7. **LOW (D3)** `trade_watchdog.py:1672` vs `1713` — heat gate runs before the opposite-direction wait → over-cap cycles log `HEAT-DEFER (D3)` for orders that would have waited anyway → inflates the "defers counted" calibration metric; and the calibration line is skipped entirely when F-1/F-3 defer first.
8. **INFO** `trade_watchdog.py:1672` — heat covers **flat first fills** of `btc-auto-*` too, not only ADDs (broader than the ruling's wording; test group 8 depends on it); non-`btc-auto-` ids (`btc-ceo-*`, `hype-short-7060`) bypass — both hand-arms, intended.
9. **INFO** `trade_watchdog.py:1641` — numerator counts **all** open rows (incl. paper/copy) against live HL equity; literal ruling compliance, but heat can overstate vs real exposure.
10. **INFO** `auto_trader.py:621–625` + `auto_trader_db.py:279` — shadow lines land **only** in `data/auto_trader.db` `events` (SQLite INSERT, no text log); the decision's metric source ("pipeline/auto_trader log") must query that table.
11. **INFO** `auto_trader.py:78–80` — `float(True) == 1.0` would arm (documented in harness); unreachable from PG numeric columns.
12. **INFO** `decision.md` evidence #4/pm:2908 — the `55762 → 56199.5` PeakReanchor event is **#17015**, not #17014 (`pipeline.log:672425`); #17014's own reanchors are `56331.925 → 56637.0` (`pipeline.log:643758`) and a later entry correction to 56199.5. Consistency conclusion is unaffected (see A v).

## Overall verdict

**CHANGES REQUIRED BEFORE COMMIT — 1 blocker, 1 high.**
D1(c), D2.1, D2.2 (implementation) and D2.3 are faithful to the rulings and pass independent re-execution (34/34 fail-safe cases, behavioural birth/clamp/shadow runs, 9+20 regression tests, rc=0 live cycle, exact 4-file scope, `hermes_constants.py` untouched). **D3 as shipped can never pass** (equity shape mismatch → permanent defer → dark ladder, with the test mocking the wrong shape), and **D2.2 does not deliver the ruling's flagship counterfactual** (#17026 arms at +1.28% and loses the same −3.79%). The D1(c) shadow is faithful for the one live instance but structurally over-counts (one-way bias) and flips #17014-class outcomes from +2.04% to ≈−8.79% — both must be reflected in the 2026-11-28 review design before this diff is relied on.
