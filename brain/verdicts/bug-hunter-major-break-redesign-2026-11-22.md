# bug_hunter verdict — major-break redesign (uncommitted changeset), 2026-11-22

**Scope verified:** `scripts/trade_watchdog.py` (E1 gate + fold-in B heat + result-3 hunks),
`scripts/auto_trader.py` (BE_ARM_PEAK_PCT), `scripts/hermes_constants.py` (4 constants +
PREARM_LOCK_ENFORCE retire), `analysis/test_pending_machine.py` (E1-compat attempt).
Authority: `automation/ceo/checkpoints/20261122T220223Z-decision.md` (+ its ADDENDUM) and the
lead's SCOPE ADDENDUM message (result-3 hunks now in tree).

**Verified-against stamp (the file moved under me — see §0):**
| file | sha256 (first 20) | mtime |
|---|---|---|
| scripts/trade_watchdog.py | `89768cc0e162b474b607` | 2026-11-22 22:56:22 |
| scripts/auto_trader.py | `42c9f971c1c1099f68ef` | 22:17:53 |
| scripts/hermes_constants.py | `cfb643478824a698274a6` | 22:16:58 |
| analysis/test_pending_machine.py | `67b1ac0c9680c325a5e6` | 22:34:06 |

**Method:** code reads + 5 harnesses in `/tmp/bh/` only (byte-identity differential vs `git show
HEAD:`, four-hook fill-walk, 74-cycle no-unconfirmed-fill sweep, real-rung walk with real
candles/equity, suite-fix copy) + live read-only probes + ONE sanctioned `run_cycle`.
**No production file edited; no fix applied anywhere (prescriptions only).**

---

## 0. Changeset was still being written during verification (disclosure)

`scripts/trade_watchdog.py` changed **three times while I was verifying**: 22:54:08 (+72 lines,
result-3's `_local_atr15`), then 22:56:22 (the `res`-guard fix), then stable (sha unchanged across
checks at 23:00, 23:12, 23:18). I verified the **final** state stamped above. The 22:54 intermediate
had a real bug (see F-4, caught and fixed by the lead before my final pass) — recorded because it
shows the guard was load-bearing.

**Disclosures (production writes):**
1. **ONE sanctioned live run:** `auto_trader.run_cycle()` → rc=0 (§F).
2. **Unintended-but-code-path write:** my helper probe hit E1's own cache-repair path and called
   `atr_cache.save_atr('BTC', 149.04, '15m')` → `data/atr_cache.json` BTC entry refreshed at
   22:55:36. That is the exact repair the ruling asked for; value is now stale again (age >300s) and
   falls back to `_local_atr15`. No other write outside `/tmp`.
3. Read-only: PG `trades`, HL account, `candles.db` (mode=ro), logs.

---

## 1. Verdict table

| # | Item | Verdict | Evidence |
|---|---|---|---|
| **A** | **E1 gate — safety (no unconfirmed fill)** | **PASS (proven)** | 74-cycle sweep (4 states × 2 styles × 6 closes × 2 directions) + 15-case hook walk: **0 fills** while flag ON and close short of level by < K×ATR15. Hook walk §3. |
| A(ii) | flag-OFF = byte-identical legacy | **PASS** | Head-to-head differential §4: with `BOUNCE_SHADOW_ENABLED=False` the output is **byte-identical** to `git HEAD` except 4 wall-clock `ts` values + the intentional `(notional=`→`(margin=` label. With the shadow on, exactly one extra line (the E3 log). |
| A(ii) | DEFER = no fill + no state burn + no double-fill | **PASS** | S6/S7/S16: state preserved (`retested`), 0 fills on DEFER, exactly 1 fill on recovery, 0 on the 3rd cycle (one-shot). |
| A(iii) | confirmation math / tz / closed-guarantee / ATR | **MATH PASS · CLOSED-GUARANTEE FAIL** | long `close >= level+thr`, short `close <= level−thr` ✓ (`trade_watchdog.py:1377-1379`); `ts` INTEGER unix-seconds, ORDER BY ts DESC ✓. **But `is_closed=1` does NOT mean closed** — F-2. ATR: cache→local→defer now works (§5). |
| A(iv) | memo per-oid per-cycle, no leak | **PASS** | `_mom_memo = {}` per impl call (`:1591`), keyed by `oid`; flag-OFF returns before any query. |
| A(v) | escape: not blocked / can't bypass | **FAIL — blocked (F-1)** | S11/S12 + real-rung escape walk: logs `STRAIGHT-LINE escape … qualifying to fill` and **never fills**. Cannot *bypass* the gate (sweep), but it *is* gated by its own memo. |
| A(vi) | continuation rungs show displacement | **PASS** | Hook 4 (`:1828-1852`): unconfirmed → `first_break` + exact log text; confirmed → fill (S8/S9/S10 + real rung `btc-auto-ladder-1795315174`). |
| A(vii) | getattr fallbacks safe | **PASS w/ note (F-5)** | missing flag → `True` (fail-closed, gate stays on); missing K → 0.5; no crash. |
| **B** | fold-in B heat margin | **PASS w/ note (F-6, F-7)** | SQL `SUM(amount_usdt/NULLIF(leverage,0))` `:1895`; cap 0.15 unchanged; btc-auto scope, defer/fail-safe, `heat=`/`D3 calibration` tokens all intact (differential + live log). Live numbers §6. |
| **C** | fold-in A BE_ARM_PEAK_PCT | **PASS** | `_be_armed` reads `BE_ARM_PEAK_PCT` (`auto_trader.py:92-93`), single call site `:524` = birth + ongoing; mirrors + fail-safes verified; `git diff` shows **zero** `+/-PM_TRAIL_ACTIVATE_PCT` value lines; 14/14 selfcheck PASS. No other reader on the BE path (§7). |
| **D** | prearm retire | **PASS** | `PREARM_LOCK_ENFORCE = False` (`hermes_constants.py:2249`); shadow gate is `PREARM_LOCK_SHADOW_ENABLED` (`position_manager.py:4671`) and the would-fire log (`:4691`) sits **before** `if PREARM_LOCK_ENFORCE:` (`:4692`) → still logs, no exit. Not in `CEO_PROTECTED_FLAGS` (`:3415-3438`). |
| **E** | 4 new constants, nothing else | **PASS** | `hermes_constants.py` diff = **2 hunks, both ours** (constants block `:2208-2218`, PREARM `:2244-2249`); every hunk has a revert one-liner. No LOSERS/other-session hunks in this file. `BOUNCE_SHADOW_ENABLED` **is** read now (result-3 landed) — complete log-only path, no half-build. |
| **F** | regression | **PASS w/ suite red (F-3)** | py_compile 4/4 OK; fresh imports OK; both selfchecks exit 0 (re-run by me); `test_manual_exit_manager.py` **20/20**; live `run_cycle` rc=0 (§8); logs: **0 tracebacks in shipped code** since 22:00 (3 are the watchdog agent's own throwaway snippets); machine suite still red (prescription §9). |
| **G** | cross-cutting | **PASS** | 25 armed rungs census §10; real-rung walk (retest + continuation + escape) §10; add-path/heat/band gates byte-identical to HEAD (§4); E1 never loses or double-burns state (§3). |

**Overall: PASS WITH FINDINGS — the safety property (never fill without displacement) is proven;
two spec deviations (F-1 escape, F-2 in-flight candle) and one red test file (F-3) must be fixed
before the 7d metric review.**

---

## 2. Known-issue diagnosis (the broken suite) — ROOT CAUSE IS NOT THE FLAG

### (i) The four hooks as shipped (final line refs — result-1's table is stale by +72/+80 lines)

| Hook | where | behavior shipped |
|---|---|---|
| helper `_momentum_close_confirmed` | `trade_watchdog.py:1373-1379` | long `close >= level+thr`, short `close <= level−thr` |
| `_local_atr15` (result-3) | `:1382-1416` | mean TR of the last 14 **`candles_15m`** `is_closed=1` bars (rows DESC, `rows[i+1]` = prior bar); freshness: `ts+900` older than 1800s → None; any failure → None |
| `_momentum_confirm(oid, coin, direction, trigger_price, memo)` | `:1419-1483` | flag off → `_MOM_OFF` **before any query**; ATR: `get_atr` → `_local_atr15` → `save_atr` repair → defer; then close query; any exception → `_MOM_DEFER` |
| memo | `:1591` | `_mom_memo = {}` per cycle |
| **Hook 1** first_break + crossed (retest style) | `:1763-1786` | confirm **before** escape: `True` → `_ps="retested"` fall-through; else escape check (0.5%, no confirm); not escaped → DEFER warn + `continue` (no state write) |
| legacy `first_break && _cont → None` | `:1787-1788` | untouched |
| **Hook 2** retested cross#2 | `:1789-1803` | `False` → `continue`; `DEFER` → warn + `continue`; `True`/`OFF` → fill |
| **Hook 3** fresh cross (retest style) | `:1804-1827` | `True` → fill; else (incl. `OFF`) → `first_break` + FIRST-break log + `continue`; `DEFER` adds the warn |
| **Hook 4** continuation cross | `:1828-1852` | `True`/`OFF` → fill; else `first_break` + (`DEFER` warn \| unconfirmed text) + `continue` |

Group-1's exact sequence under **flag OFF** (fresh first cross → `first_break` at Hook 3's else
branch; reclaim → `retested`; cross#2 → Hook 2 gets `_MOM_OFF` → falls through → fill) is
**correct** — and I ran it: with the mock fixed, group 1 passes (§9).

### (ii) Why flag-OFF broke the cross#2 fill — mock/SQL mismatch, not the flag

The traceback the suite actually produced:

```
[WARN] pending order a: open-position query failed (TypeError) — deferring one cycle (fail-safe, no blind add)
AssertionError: re-cross must fill
```

Mechanism: `analysis/test_pending_machine.py:60` dispatches the fake psycopg2 cursor with
`elif 'SUM(amount_usdt)' in sql:`. Fold-in B changed the text to
`SUM(amount_usdt/NULLIF(leverage,0))` (`trade_watchdog.py:1895`) → no longer matches → the mock
falls through to its `'row'` sentinel → returns `None` → `float(None[0])` raises `TypeError` in the
heat read → the stacking fail-safe swallows it → **no fill**. The flag patch itself
(`:43-44`, read lazily at `trade_watchdog.py:1439`) **works** — proved by the fixed copy passing
group 1 with the same patch.

### (iii) Why `TW._momentum_confirm = lambda: True` broke the first-cross state write

Reproduced verbatim:

```
[WARN] pending order entry error (skipped, cycle continues): <lambda>() takes 0 positional arguments but 5 were given
KeyError: 'a'   # at stt()['a']['status'] == 'first_break'
```

The stub has **0 parameters**; all four shipped call sites pass **5 positional args**
(`:1763, :1795, :1805` + Hook 4) → `TypeError` → swallowed by the per-order isolation
(`trade_watchdog.py` order loop) → the order is skipped entirely → **no state at all** → KeyError.
(An arity-correct `lambda *a, **k: True` would fail differently: the fresh cross would *fill* —
that is the designed E1 behavior — so `first_break` would never be written.)

**The test's comment is also wrong:** `_momentum_confirm` is **module-level** (`:1419`), not nested;
module patching works (proved twice). Correct the comment when applying the fix.

### (iv) Correct suite fix — prescription (NOT applied)

Two lines, in `analysis/test_pending_machine.py`:
1. `:60` → `elif 'SUM(' in sql:` (matches both the old and new heat SQL).
2. `:333` / `:341` → 5 positional args: `TW._momentum_confirm('x', 'BTC', 'long', 60000.0, {})`
   and `('y', 'BTC', 'long', 60000.0, {})`.
3. Optional hygiene: delete the stray `_AC.getatr = None` (`:338`); rewrite the `:38-41` comment
   ("module patching is dead" → "module-level helper; flag patch works").

No candles fixture, no per-test close, no flag-patch relocation needed: keep
`_HC0.MOMENTUM_CONFIRM_ENABLED = False` at import (test-only — no production module imports this
file; `grep -rn test_pending_machine scripts/ automation/ config/` = empty), group 11 flips it
True→False in its own `finally`.

**Validated:** copy at `/tmp/bh/test_fixed.py` → `ALL PENDING-MACHINE TESTS PASS`, exit 0
(groups 1-11, incl. the bounce-shadow line at group 1's reclaim).

---

## 3. (A) Four-hook fill-walk (flag ON, ATR=200 → thr=100, level 63000 LONG)

| # | scenario | steer | state | log |
|---|---|---|---|---|
| S1 | fresh cross **confirmed** (63150) | **1** | triggered | — |
| S2 | fresh cross unconfirmed (63050) | 0 | first_break | FIRST break seen |
| S3 | fresh cross **DEFER** | 0 | first_break | confirm-data-missing + FIRST break |
| S4 | reclaim first_break → retested | 0 | retested | level reclaimed |
| S5 | retested x#2 **confirmed** | **1** | triggered | — |
| S6 | retested x#2 unconfirmed | 0 | **retested (preserved)** | — |
| S7 | retested x#2 **DEFER** | 0 | **retested (preserved)** | confirm-data-missing |
| S8 | continuation **confirmed** | **1** | triggered | — |
| S9 | continuation unconfirmed | 0 | first_break | `continuation cross unconfirmed (displacement < K×ATR) — falls back to retest-wait` |
| S10 | continuation DEFER | 0 | first_break | confirm-data-missing |
| S11 | **escape, live px 0.6% past, close undisplaced** | **0** | first_break | `STRAIGHT-LINE escape … qualifying to fill` ← **F-1: spec says fill** |
| S12 | **escape + DEFER** | **0** | first_break | escape line + confirm-data-missing ← **F-1** |
| S13 | escape + confirmed | 1 | triggered | — (fills via the *confirm* branch, not the escape) |
| S14 | first_break + crossed, unconfirmed | 0 | first_break | — (silent continue, no burn) |
| S15 | first_break + crossed, confirmed | 1 | triggered | — |
| S16a/b/c | DEFER → recovery → repeat | 0 → **1** → 0 | retested → triggered | no double-fill, one-shot holds |

**No-unconfirmed-fill sweep:** 74 cycles (long/short × {None, first_break, retested} × {retest,
continuation} × closes at −150/−50/+50/+99/+100/+150 around the level, thr=100) →
**0 violations** (fill only when `close` displaced ≥ thr). Escape probes: 0 fills (over-blocking,
not under-blocking).

### 4. (A) byte-identity proof — flag-OFF path vs `git HEAD`

`git show HEAD:scripts/trade_watchdog.py` vs the shipped file, same 6 scenario groups
(retest flow, escape, continuation, no-burn taxonomy, add-path, D3 heat + band plumbing),
timestamps normalized, run as separate processes:

* **`BOUNCE_SHADOW_ENABLED=False` (isolates E1):** output **byte-identical** to HEAD except
  4 wall-clock `ts` values in the taxonomy state dumps. **Zero E1-caused differences.**
* **`BOUNCE_SHADOW_ENABLED=True` (as shipped), raw diff — the complete list:**
  1. `+ [BOUNCE-SHADOW] would-fill LONG @ 63000 (rung short poke unconfirmed + closed back inside = rejection)…` (E3, log-only, own flag);
  2. `notional=50.00` → `margin=50.00` and `notional=200.00` → `margin=200.00` (fold-in B label — the `heat=` / `cap=` / `D3 calibration` tokens are unchanged);
  3. 4 × `ts` wall-clock values.
* Everything else identical: FIRST-break/reclaim/retested/fill, escape fill, continuation fill,
  taxonomy (rejected/error/fired), ladder `--force --prearmed` belt, dbdown defer, F-3 cap defer,
  same-direction ADD, opposite-wait, heat under/over/equity-fail/hand-arm bypass, D2.3 band flag.

**DEFER state-preservation:** Hook 1's DEFER branch writes nothing (`:1781-1786`); Hook 2's
DEFER only warns (`:1799-1802`) so `retested` survives; Hook 3/4 DEFER advance to `first_break`
(lead's documented deviation #1 — the legacy not-confirmed state, still reclaim→retested→fill
reachable, not a burn). Recovery fills **exactly once** (S16).

---

## 5. (A)(iii) ATR source + the circular-dependency fix (result-3 hunks)

* `get_atr('BTC','15m')` was **None live** (entry age 5119s; only SPX fresh) → without the fallback
  E1 would defer **every** BTC fill forever. The addendum's ruling is now implemented:
  `_local_atr15` (`:1382-1416`) + `save_atr` repair (`:1454-1458`) + defer only if both fail.
* **Independent re-run of the lead's harness (my own fixtures):**
  * 15 bars, h−l=10 → `10.0` ✓; cross-bar-gap bars → `1.5` ✓ (**DESC order correct** — rows[i+1] is the prior bar; a wrong order would give a different value);
  * newest bar close **3100s** old → `None` ✓ (freshness arithmetic `now − (ts+900) > 1800` correct, ts = open time);
  * newest bar close **1700s** old → `10.0` ✓ (edge);
  * 14 bars → `None`; empty table → `None` ✓;
  * end-to-end: cache-miss → local ATR → displaced close → **True**; undisplaced → **False**; no candles → **`defer`**; flag OFF with no data → **`'off'`** (returns before any query) ✓;
  * cache repair observed: `atr_cache.json` gained `{'BTC': {'atr': 10.0, 'ts': …}}` → `save_atr(token, atr, interval)` positional signature is used correctly.
* Fail-safe matrix: flag-off→OFF · ATR valid (either source)→True/False · ATR missing→DEFER ·
  any exception→DEFER. Matches the lead's flow exactly.

---

## 6. (B) live heat numbers (fold-in B)

Live PG (`brain.trades`, read-only) + live HL equity at 23:16Z:

| quantity | value |
|---|---|
| open rows | **1** — SPX LONG #17054, `amount_usdt=11.10`, **`leverage=5`**, status open |
| `SUM(amount_usdt)` (old, notional) | 11.10 → heat = 11.10/15.775 = **0.704** → defer (the dark-ladder bug) |
| `SUM(amount_usdt/NULLIF(leverage,0))` (new) | **2.22** → heat = 2.22/15.774754 = **0.1407** < 0.15 → **pass** |
| HL `marginUsed` cross-check | 2.215634 ✓ (formula matches the exchange's own margin) |
| two such rows | 4.44/15.775 = **0.2815** → defer |
| three | 6.66/15.775 = **0.4222** → defer |
| rows with `leverage IS NULL` / `= 0` | **0** (all-time and open) → NULLIF exclusion has no live effect |

**Note (F-7):** the decision's calibration examples (`0.069 / 0.137 / 0.206`) assume **10x**; the
live open row is **5x**, so one position already sits at **94% of the cap** and the ladder binds at
**two** concurrent rungs (still "≥2 rungs", as the ruling wanted, but the headroom is thinner than
the example). `heat=`, `margin=`, `cap=`, `D3 calibration` tokens and the `HEAT-DEFER` line are
byte-identical to HEAD apart from the label (§4).

---

## 7. (C) protected-constant diff attribution

`git diff scripts/hermes_constants.py` = **exactly 2 hunks, both from this run:**

1. `@@ -2207,0 +2208,11 @@` — `MOMENTUM_ATR_K = 0.5`, `MOMENTUM_CONFIRM_ENABLED = True`,
   `BOUNCE_SHADOW_ENABLED = True` (each with a REVERT line) + the BE-ARM comment block +
   `BE_ARM_PEAK_PCT = 0.025` (REVERT = set 0.004).
2. `@@ -2233 +2244,6 @@` — `PREARM_LOCK_ENFORCE = True → False` + dated retirement comment
   (original comment retained). `PREARM_LOCK_SHADOW_ENABLED = True` and `PREARM_LOCK_THR_PCT = 0.25`
   untouched.

**No other session's hunks are present in this file** (no LOSERS change in the working tree —
`LOSERS` was already committed; the other dirty files in `git status` — `automation/error_alerts.md`,
`automation/ceo/vacation_alerts.json`, `brain/verdicts/…`, `data/watchdog_recommendations.json`,
`automation/ceo/*` — belong to other sessions).

**Protected-value proof:** `git diff … | grep -E '^[+-](PM_TRAIL_ACTIVATE_PCT|MAX_PORTFOLIO_HEAT|MULTI_TOUCH_ESCAPE_PCT|MFE_EXIT…)'` → **empty**.
Values re-read live: `PM_TRAIL_ACTIVATE_PCT = 0.004` (`:2056`), `MAX_PORTFOLIO_HEAT = 0.15` (`:672`),
`MULTI_TOUCH_ESCAPE_PCT = 0.5` (`:2151`). The only `PM_TRAIL` lines in the diff are the import
line, docstrings and comments.

**Leftover readers of `PM_TRAIL_ACTIVATE_PCT`:** `auto_trader.py:60` (import kept, code use
removed), `:511` comment. Other hits are *different* mechanisms and are correct:
`position_manager:4676` (prearm shadow's own domain ceiling), `:2075` BB-squeeze arm timeout,
`shadow_trader` (its own local constant), `jup_exit_sim`/`mfe_exit_grid`/`self_learner` (analysis).
**Nothing on the BE path reads it** — `_be_armed` (`auto_trader.py:67-93`) is the only BE gate and
it reads `BE_ARM_PEAK_PCT`; its single call site `:524` computes `_be` for both birth and every
subsequent cycle; SHORT/LONG mirrors (`:92-93`, peak = `lo`/`hi`) and fail-safes
(entry/price falsy → False; not in profit → False; `float(None)`/garbage → False; `peak<=0` → False)
all verified; 14/14 selfcheck PASS.

---

## 8. (F) regression battery + live run

* `py_compile` on the 4 in-scope files → **OK**.
* Fresh imports → OK; `MOMENTUM_CONFIRM_ENABLED=True, K=0.5, BOUNCE=True, BE_ARM=0.025,
  PREARM_ENFORCE=False, PM_TRAIL=0.004`;
  `inspect.signature(_momentum_confirm) = (oid, coin, direction, trigger_price, memo)` — **all four
  shipped call sites match** (5 positional); only the test's group 11 doesn't.
* `selfcheck_…_e1.py` → **exit 0** (25/25), `selfcheck_…_exit.py` → **exit 0** (14/14) — re-run by me
  after the final edit.
* `analysis/test_manual_exit_manager.py` → **20 passed, 0 failed**.
* **ONE sanctioned live `auto_trader.run_cycle()` → rc=0**, 0.2s:
  `decision=BRACKET, price=60922.41, regime=CHOP, score_long=10, score_short=-30,
  mode=live, live_armed=[], shadow_armed=[], armed_detail=[], tweaks=[], hypotheticals=0`.
  Book after the run: **1 open position** — SPX LONG #17054, $11.10 @5x, entry 0.28171, uPnL −0.049,
  margin 2.2156; equity **$15.7748**, withdrawable $13.559.
* **Live gate lines:** none since the changes landed — the 22:46 and 23:09 watchdog cycles had **no
  crossed rung** (25 armed rungs all away from price: nearest long 61327 / short 60704 vs BTC
  ~61000), so no `HEAT-DEFER`, no `momentum confirm data missing`, no `BOUNCE-SHADOW` yet.
* **Tracebacks:** `pipeline.log` since 22:00 → **0**. `trade-watchdog.log` since 22:00 → 3, all inside
  the watchdog *agent's* throwaway snippets (`NameError: DB_HOST`, `psycopg2.connect(**str)`,
  a SQL SyntaxError) — **0 in shipped code**.
* **Scope:** the 4 files + checkpoint/selfcheck files only (§7).

---

## 9. (F/G) 25 armed rungs — census + walk with real configs

Census from production `pending_orders.json` × `pending_orders_state.json` (23:12Z): **25 armed**
(86 state entries: 70 fired, 14 error, 2 retested) — 16 with `entry_style=None` (→ retest style),
6 `retest`, **3 `continuation`**; **all BTC, none crossed** at BTC≈61000.

Walked three real order configs through the shipped hooks with real `candles_15m` rows
(`_local_atr15('BTC') = 196.58` → thr 98.29) and real equity:

| real rung | scenario | result |
|---|---|---|
| `btc-auto-ladder-1795383583` short 60704 **retest** | close 60600 (displaced) | **fill** ✓ |
| " | close 60680 (crossed, <thr) | first_break, no fill ✓ |
| " | reclaim (60800) | `retested` + `[BOUNCE-SHADOW] would-fill LONG @ 60704 … size 22.2 USD 10x` ✓ (E3 live, log-only) |
| " | cross#2 close 60550 / 60680 | **fill** / no fill ✓ |
| `btc-auto-ladder-1795315174` short 59282 **continuation** | close 59150 / 59250 | **fill** / first_break + unconfirmed log ✓ |
| `btc-auto-ladder-1795383583` first_break **escape** | live px 60300 (0.67% past), close 60680 undisplaced | **no fill** ← F-1 |
| " escape | close 60550 (confirmed) | fill ✓ |

D2.3 band predicate, heat gate (under/over/equity-fail/hand-arm bypass), add-path
(ladder belt / dbdown / F-3 cap / same-dir ADD / opposite-wait) and the band-flag plumbing are all
**byte-identical to HEAD** (§4) — the prior rounds' gates still work.

---

## 10. Findings (severity + line refs)

### F-1 — HIGH — the STRAIGHT-LINE escape can never fill while `MOMENTUM_CONFIRM_ENABLED=True`
`scripts/trade_watchdog.py:1763-1802`. Hook 1 calls `_momentum_confirm` **before** the escape and
memoizes it (`:1763`); on `False`/`DEFER` the escape still fires and sets the **local** `_ps =
"retested"` (`:1780`) with no `continue` — so control falls into Hook 2 (`:1789`), where the **same
memoized result** forces `continue` (`:1797-1802`). Net effect, reproduced live (S11/S12 + the real
rung): the log says `STRAIGHT-LINE escape … qualifying to fill` **every cycle** and **nothing ever
fills**; disk state stays `first_break` (no corruption, no burn — but the escape is dead and the log
lies).
*Contradicts:* decision line 10 ("escape keeps its 0.5% condition … inherently confirmed"),
result-1's Hook-1 row + deviation #2 ("defer → escape still checked" — checked, then vetoed), and
the in-code comment `:1757-1762`.
*Why "inherently confirmed" is false:* escape tests `px` (from `data/prices.json`, a separate feed —
BTC present, both files ~20s apart) while confirmation tests the newest `candles_1m` close; the two
diverge whenever the candle feed lags (observed: the current-minute row is sometimes *absent*) or
ATR data is missing. When they agree the fill still happens — via the **confirm** branch (`S13`),
i.e. the escape's unique contribution (qualify at 0.5% px without displacement) is gone.
*Not a money-loss risk* (it can only under-fill, never over-fill), but it silently disables a
designed fill path for exactly the fast-takeoff class it was written for.
*Suggested fix (one of):* skip Hook 2 when the order was qualified by escape this cycle (e.g. set a
local `_escaped = True` and let `if _mom is False and not _escaped: continue`), or evaluate the
escape before/instead of the confirm call when `_ps == "first_break"`.

### F-2 — MEDIUM — `is_closed=1` does **not** mean "closed" for `candles_1m` → E1 can confirm on an in-flight candle
`trade_watchdog.py:1468-1470` (`AND is_closed=1 ORDER BY ts DESC LIMIT 1`) assumes a closed-guarantee
that the writer does not provide: `price_collector._store_candles` inserts the **open** candle with
`is_closed=1` unconditionally (`price_collector.py:192-197`, and its own comment: *"it would freeze
the currently-open candle at its first partial snapshot forever (the seeder sees mid-minute OHLC)"*);
the aggregator's `is_closed=0` developing writer skips rows already marked 1
(`price_collector.py:780-784`).
*Live proof (6-minute sampler, `candles_1m`):* at `now%60 = 19/48/49` the newest BTC row was the
**current minute** (ts = minute open, age 19–49s) with `is_closed=1`; `SELECT DISTINCT is_closed`
→ `(1,)`, `COUNT(*) WHERE is_closed=0` → **0 all-time**.
*Effect:* the "latest CLOSED 1m close" is usually the developing candle ⇒ confirmation ≈ live price
⇒ the wick-capture class E1 exists to filter can still fill if the spike is present at check time
and reverses before the minute closes. The displacement threshold still applies (so this is a
weakened filter, not an open gate).
*Suggested fix (one line):* `AND ts < (strftime('%s','now') / 60) * 60` (or `ts <= now-60`).

### F-3 — MEDIUM — the in-scope test file is red (known issue; root cause diagnosed, fix prescribed)
`analysis/test_pending_machine.py:60` (mock SQL dispatch) and `:333`/`:341` (helper arity).
Not a production defect — production is unaffected — but the committed regression suite fails as
shipped. Fix in §2(iv), **validated** (all groups pass). Also correct the `:38-41` comment
(`_momentum_confirm` is module-level; the flag patch works).

### F-4 — INFO (already fixed) — intermediate helper could never confirm
The 22:54:08 intermediate guarded the candle check with `if res != _MOM_DEFER` while `res` was
initialized to `_MOM_DEFER` → **always DEFER** with the flag on. Fixed at 22:56:22 (guard now tests
ATR validity, `:1459-1479`); my end-to-end probes confirm True/False/defer/off behave. Recorded
because it is exactly the guard the selfcheck would have caught 2 minutes later — the shipped
selfcheck passes only because it ran after the fix.

### F-5 — LOW — missing-flag fallback keeps the gate ON
`trade_watchdog.py:1439` `getattr(hc, "MOMENTUM_CONFIRM_ENABLED", True)`: a partial revert
(`git checkout scripts/hermes_constants.py` alone) does **not** disable E1 — it stays enforced
(fail-closed, no crash). The rollback note ("readers have safe fallbacks") is true for *crashing*,
but "revert = set the flag False" requires the constant to exist. K fallback `0.5` (`:1442`) fine.

### F-6 — LOW — heat SQL excludes `leverage IS NULL`/`0` rows
`trade_watchdog.py:1895`: `amount_usdt/NULLIF(leverage,0)` → NULL → `SUM` **skips** the row, i.e. a
NULL-leverage open position contributes **0** heat (fail-open on the numerator). Live: **0** such
rows all-time, so no impact today; non-numeric leverage would raise → caught → defer (fail-safe).
Selfcheck explicitly asserts the `leverage=0 ignored` semantics, so this is the intended reading —
flagging only so the fail-open direction is a conscious choice at review.

### F-7 — LOW — decision's calibration numbers assume 10x; live is 5x
One open row gives heat **0.1407** (not 0.069) — 94% of the 0.15 cap with a *single* position, so
the second rung defers. Still "binds at ≥2 rungs" as the ruling wanted, but headroom is thinner than
the spec's example; worth writing the live numbers into the 7d review baseline.

### F-8 — INFO — result-1's report is stale / partly wrong post-result-3
Its hook table (lines 1682–1775) no longer matches (hooks now `:1763-1852`, +72 lines from
`_local_atr15` + bounce-shadow); its claim that escape "needs no data, so it still fires when
ATR/candle data is missing" is **false as shipped** (F-1). Its sideways find (ATR cache write-after-
fill) is now fixed by the addendum/result-3.

### F-9 — INFO — `BOUNCE_SHADOW_ENABLED` is no longer dead
It is read at `trade_watchdog.py:1736` (gated, `getattr(..., False)` fail-off, try/except
`:1734-1747`, log-only, zero state/steer mutation — verified: state and steer counts identical to
HEAD with the shadow on). It fires on **every** `first_break → reclaim`, including flag-OFF legacy
first_breaks and DEFERred ones (correct per construction — a rung in `first_break` was by
definition never confirmed). Under flag OFF the "unconfirmed" wording is legacy-semantic (no
confirmation concept exists) — harmless, log-only; note for the 7d reading.

---

## 11. Overall verdict

**PASS WITH FINDINGS.** The core safety property of E1 is *proven*, not assumed: across a
74-cycle exhaustive sweep plus a 15-case hook walk and three real armed-rung configs, **no fill ever
occurred without a closed-candle close displaced by ≥ `MOMENTUM_ATR_K` × ATR(15m)** in the break
direction, and DEFER never fills, never burns state, and never double-fills. The flag-OFF path is
**byte-identical to git HEAD** (differing only in the intentional fold-in B label, the E3
shadow log, and wall-clock timestamps). Fold-ins A/B, the prearm retirement, the four new
constants, and every protected value check out; the 25 armed rungs, the add-path, the D3 heat gate
and the D2.3 band all still behave.

Blocking-before-review (not blocking-the-tree — all failures are fail-safe / log-only):
1. **F-1 (HIGH)** escape is dead under the live flag — one of the two spec deviations;
2. **F-2 (MEDIUM)** `is_closed=1` reads an in-flight candle — the other;
3. **F-3 (MEDIUM)** apply the 2-line suite fix so the committed regression suite is green.

Nothing was fixed in this pass (per brief). Harnesses live in `/tmp/bh/`
(`diff_run.py`, `diff_raw.py`, `e1_walk.py`, `e1_sweep.py`, `e1_live_rungs.py`, `test_fixed.py`);
the real suite, the four source files, and all production data were left untouched except the
disclosed `atr_cache.json` repair and the sanctioned `run_cycle`.

---

# ✅ ACCEPTANCE ROUND — FINAL PASS (2026-11-22 23:45Z)

**F-1, F-2, F-3 are closed in the tree exactly as prescribed. Re-verified independently; full
battery green. The changeset is CLEARED FOR COMMIT.**

Stamped against: `scripts/trade_watchdog.py sha256 e9550419627af5b6f857 (mtime 23:30:07)`,
`analysis/test_pending_machine.py sha256 bd9ea4f30d655d49c7eb (mtime 23:26:28)`,
`auto_trader 42c9f971…`, `hermes_constants cfb64347…` (both unchanged from §stamp).

## F-1 (HIGH) — CLOSED ✅
Code verified, not just claimed:
* `trade_watchdog.py:1718` `_escaped = False` — initialized at the per-order state-machine top,
  **before the `rejected` branch**, so every rung that reaches the state machine defines it. The
  in-branch-init NameError class (prior-cycle `retested` → Hook 2 → caught by per-order isolation →
  silent no-fill) is structurally impossible now; the in-code comment at `:1713-1717` records it.
* `:1798` `_escaped = True` set **only** inside the escape distance test (0.5%), `:1815`
  `if not _escaped:` guards the memoized re-confirm — escape-qualified fills skip it and fall
  through to the fill; every non-escape path still runs the full confirm gate.
* **Independent checks (12/12 PASS, `/tmp/bh/fixcheck.py`):**
  * the exact two-cycle scenario: cycle1 with only an in-flight near-level bar → confirm **DEFER** →
    `first_break` + `momentum confirm data missing`; cycle2 px 0.6% past → **FILL, state=triggered**,
    `STRAIGHT-LINE escape` logged, **no `entry error`**;
  * prior-cycle `retested` + DEFER → no fill, stays `retested`, DEFER logged, **no NameError**;
  * gate still intact on non-escape paths: fresh cross undisplaced → no fill; retested cross#2
    undisplaced → no fill; fresh cross displaced → fill.
* **No gate bypass:** `_escaped` can only become True after the 0.5%-by-distance test, only in the
  `first_break` branch, only for the current order/cycle — it cannot unlock any other fill. Re-ran
  the 74-cycle sweep with a **fixed** mock (see harness honesty below): **24 confirmed fills
  observed, 0 unconfirmed-fill violations**, and both escape probes now fill (steer=1) as the
  ruling intends. Real-rung walk: both escape cases now `steer=1 … state=triggered` ✓.

## F-2 (MEDIUM) — CLOSED ✅
* `trade_watchdog.py:1475-1478`: `SELECT close FROM candles_1m WHERE token=? AND is_closed=1
  AND ts < ? ORDER BY ts DESC LIMIT 1` with `int(time.time() // 60 * 60)` (minute floor).
  `ts` is the bar's **open** time, so `ts < floor(now)` admits exactly the ended bars (the
  in-flight bar's open == floor) — correct even at an exact minute boundary.
* Verified both directions: in-flight **displaced** bar → **`defer`** (cannot confirm); ended
  displaced → **True**; ended undisplaced → **False**.
* **I agree with the split** (and checked it): the monitor's own price read
  (`trade_watchdog.py:1644-1647`) still has **no** `ts <` filter — `px` decides *crossed* and should
  be the freshest close, while the *fill* decision must rest on an ended bar. Cross-on-live-price /
  confirm-on-ended-close is the right asymmetry; no objection.

## F-3 (MEDIUM) — CLOSED ✅
* `diff /tmp/bh/test_fixed.py analysis/test_pending_machine.py` → **IDENTICAL** (my three
  prescriptions verbatim: the `SUM(` matcher, the 5-positional helper calls, the stray line/comment
  cleanup).
* Shipped suite: **`ALL PENDING-MACHINE TESTS PASS`** (groups 1-11, exit 0) — including group 1's
  re-cross fill, group 2's escape, group 11's flag-off→OFF / ATR-miss→DEFER.

## Full battery re-run (after the fixes)
| check | result |
|---|---|
| `py_compile` 4 in-scope files | **OK** |
| `analysis/test_pending_machine.py` | **ALL PASS** (11 groups) |
| `analysis/test_manual_exit_manager.py` | **20 passed, 0 failed** |
| `selfcheck_20261122T220223Z_e1.py` | **exit 0** |
| `selfcheck_20261122T220223Z_exit.py` | **exit 0** |
| `e1_walk.py` (hook walk + local-ATR + flag-off + one-shot) | **ALL E1 WALK CHECKS PASS** |
| `e1_sweep.py` (74 cycles) | **24 confirmed fills, 0 unconfirmed-fill violations** |
| `e1_live_rungs.py` (3 real armed rung configs, real ATR/equity) | **9/9 OK** (expectations made ATR-relative — the live ATR15 moved 196→219 during the session, so a fixed `close` fixture legitimately stopped being "displaced"; the gate was right, my fixture was stale) |
| `diff_raw.py` flag-OFF vs `git HEAD` | **same delta set as §4** — one `[BOUNCE-SHADOW]` line, 4 wall-clock `ts`, 2× `notional=`→`margin=`. The `_escaped` / `ts<` changes introduce **zero** new flag-OFF differences. |

**Harness honesty (same bug class the lead disclosed, mine caught and fixed before these numbers):**
(1) my real-rung fixture omitted a `UNIQUE(token, ts)` index, so `INSERT OR REPLACE` was a no-op and
an old close won `ORDER BY ts DESC`; (2) my sweep's psycopg2 mock returned a bare `0.0` for the SUM
row — `float(0.0[0])` TypeError swallowed by the fail-safe, which would have made the sweep
*vacuous* (0 fills = 0 violations). Both fixed, both re-run; the sweep is only reported above with
the confirmed-fill counter proving it observed fills.

**Disposition of the remaining findings:** F-4 (fixed mid-flight) recorded; F-5 fail-closed revert
behavior accepted by the lead; F-6 NULLIF direction noted (0 live rows); F-7 live-5x sizing note
recorded for the 7d review; F-8/F-9 informational.

## FINAL VERDICT
**PASS — approved for commit.** Safety property holds under the final code (0 unconfirmed fills
across 74 cycles + 15-case hook walk + 3 real rungs), the escape path is restored to its ruling
(0.5% px, no confirm, no state corruption), confirmation now rests only on **ended** 1m bars, the
flag-OFF path remains byte-identical to HEAD, all four suites/selfchecks are green, protected
constants untouched, and the scope is the 4 files + checkpoints.

