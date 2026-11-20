# bug_hunter verdict — no-burn re-cross-wait + prearmed + fresh-air + multi-touch (2026-11-20)

Verifier: agent-1 (bug_hunter), adversarial, no fixes applied.
Harnesses: `/tmp/bh_h1_status.py`, `/tmp/bh_h2_monitor.py`, `/tmp/bh_h2m_machine.py`,
`/tmp/bh_h4_keeper.py`, `/tmp/bh_h4b_readiness.py`, `/tmp/bh_h4c_fix2.py`, `/tmp/bh_h5_prearmed.py`
(all state/config redirected to `/tmp`, subprocess mocked, psycopg2 faked, zero production writes
except ONE sanctioned live `run_cycle`). Live reads are SELECTs / file reads only.

---

## 1. Scope (4 commits, per-commit file sets)

| commit | subject | files |
|---|---|---|
| `8021dbd9` | no-burn re-cross-wait | `scripts/auto_trader.py`, `scripts/trade_watchdog.py` |
| `792d7b12` | prearmed carve-out | `scripts/brain.py`, `scripts/trade_watchdog.py` |
| `79737b53` | keeper fresh-air fallback | `scripts/auto_trader.py` |
| `3b93e685` | multi-touch EXECUTION | `scripts/trade_watchdog.py`, `scripts/auto_trader.py`, `skills/shared/full-analysis/SKILL.md` |

Union = exactly the 4 claimed files. `git diff 8021dbd9~1 HEAD -- scripts/pending_order_monitor.py` = **0 lines**
(it only delegates: `tw.monitor_pending_orders()` + `tw._execute_pending_order()`, so every state write
funnels through trade_watchdog under the same flock — no competing writer). `brain.py` changed **only** by
the prearmed commit (16+/1−). Working tree clean for all four files. (The 8021dbd9~1..HEAD range also
contains unrelated commits `52131532` touch-research / `47cb1481` automation — not part of this batch.)

## 2. Verdict table

| # | Item | Verdict |
|---|---|---|
| A(i) | taxonomy: REJECTED→`rejected`, non-zero-no-marker→`error`, success→`fired`, timeout→`error` | **PASS** (5/5, harness H1) |
| A(ii) | false-`rejected` breadth of `"REJECTED" in out` | **FINDING F1 (MEDIUM, latent)** — demonstrably broad; narrower match given below |
| B(i) | first_break/retested/rejected transitions (supersedes T2a-c) | **PASS** (H2m M1–M7, M12–M14) |
| B(ii) | multi-order: rejected/first_break `continue` is per-order, serial slot not consumed | **PASS** (H2m M8; H2 Bii-1..4) |
| B(iii) | `changed=True` → atomic write runs at loop end | **PASS** (disk read after each call) |
| B(iv) | partial reclaim / never-reclaim walk | **PASS** (H2 Biv, Biv-2) |
| B(v) | prune/TTL of `pending_orders_state` | **FINDING F3 (MEDIUM)** — none exists; 27 orphan entries, oldest 2026-10-18 |
| C | double-fire path proof (steer ⇒ state was `retested` ⇒ set `triggered` ⇒ belt) | **PASS** — proof in §5 |
| D | keeper readiness / fresh-air / dedupe / ITM | **PASS** + **FINDING F2 (MEDIUM)** sh1h=0 dead rung |
| E | `_unfired` consumers | **PASS** — readiness only (2 call sites); sibling consumer named |
| F | regression battery + ONE live run_cycle + live book | **PASS** (§7) |
| G | scope | **PASS** (§1) |
| Ad1(i–viii) | two-state machine | **PASS** (§4) |
| Ad2 | fresh-air stop = `sh1h + 0.1·ATR1h`, no lookahead, note updated, structure unchanged | **PASS** + F2 + F7 |
| Ad3 | #17004 pnl math | **row CONSISTENT**; `$1.54` is a mis-multiplication (§8) |
| Ad4 | first_break/retested prune + readiness semantics | **correct-by-design**, leak = F3 (§6) |

**Overall: SHIP-CONFIRMED WITH FINDINGS — no HIGH, no double-fire path, no money-safety hole found.
2 MEDIUM (F1 false-rejected breadth, F2 sh1h=0 dead rung), 1 MEDIUM (F3 unbounded state growth), 5 LOW, 2 INFO.**

---

## 3. (A) Status taxonomy + the false-`rejected` analysis

### A(i) author's cases re-run (H1, mocked `subprocess.run`, state in /tmp) — 5/5 PASS

```
PASS gate REJECTED (knife) rc=1            status='rejected'
PASS gate REJECTED (HARD_FLOOR) rc=1       status='rejected'
PASS non-zero rc, no marker (API fail)     status='error'
PASS success rc=0 + Added trade            status='fired'
PASS timeout -> exception path             status='error'
```
Ordering is correct: `success = rc==0 and "✓ Added trade" in out` is evaluated **first**, so a run that
actually opened always lands `fired` even if a REJECTED string is also present (H1: rc=0 + REJECTED text → `fired`).
Belt re-run on current code: state `rejected` → `skipped: already rejected`, **0 brain calls**.

### A(ii) Is `"REJECTED" in out` too broad? — YES, breadth demonstrated (F1)

`_rejected = "REJECTED" in out` at **trade_watchdog.py:1731**; `out = stdout + stderr` (:1745).

Harness OBS rows (all `rc=1`, all currently classified **`rejected`** = retryable, not terminal):

| input | classified | money opened? |
|---|---|---|
| `[brain.py] ❌ mirror_open FAILED for BTC: HTTP 429: upstream said REJECTED` | `rejected` | no |
| stderr `Traceback ... File "brain.py", line 673 ... print(f"[brain.py] ❌ REJECTED: ...")` | `rejected` | no |
| `[brain.py] ⚠️ note: upstream policy REJECTED seen earlier` + `ERROR: exchange write failed` | `rejected` | no |
| `❌ mirror_open FAILED ...: maker_rejected: post-only would cross` | `error` (lowercase ≠ match) | no |
| `[brain.py] ❌ REJECTED: BTC SHORT — blocked by SHORT_BLACKLIST` | `rejected` | no |
| `❌ REJECTED ... live_trading is DISABLED` / `amount_usdt=5.0 < HL_MIN` | `rejected` | no |
| `✗ REJECTED: ... conf-1s` | `rejected` | no |

**Who emits REJECTED, and under which exit codes** (grep of `brain.py`, all 10 sites are inside `add_trade`):
- `brain.py:495,521` knife / HARD_FLOOR · `602,608,614` conf-1s / noise (`✗ REJECTED`) ·
  `637` live_trading DISABLED · `642` delisted · `653` blocked-by-blacklist · `663` HL_MIN · `673` DUPLICATE.
- Every one is immediately followed by `return None` → CLI `brain.py:1751` `if trade_id is None: sys.exit(1)`
  → **rc=1 and no trade opened** (gates are all before `mirror_open`, brain.py:815). `decider_run.py:3531`
  documents the same fact ("brain prints policy rejects to STDOUT … then exits 1").
- Non-gate sources that can put the word in `out`: raw HL API error text echoed by
  `hyperliquid_exchange.py:1349-1357` (`err_msg` → `{"message": err_msg}` → brain prints
  `mirror_open FAILED for X: {message}`), and any traceback whose failing source line contains REJECTED.
  Lowercase `maker_rejected` does **not** match (case-sensitive) — verified.

**Double-fire consequence:** a false `rejected` re-arms on reclaim and re-fires. That is only a double-fire
if a position was actually opened — which requires `rc!=0` *and* an open trade *and* a REJECTED substring.
`rc=0 ∧ "✓ Added trade"` is the only open path, and brain never prints REJECTED after `mirror_open`
(last REJECTED site = brain.py:673, `mirror_open` at :815). **Not reachable today**; the exposure is
(a) transient/permanent execution failures flipping from terminal-burn to retry-loop, and
(b) a future brain edit that echoes REJECTED-shaped text.

**Exact narrower match (recommended):**
```python
_rejected = any(ln.startswith("[brain.py] ❌ REJECTED")
                for ln in out.splitlines())
```
Covers **all 7** watchdog-reachable gate sites (495, 521, 637, 642, 653, 663, 673 all carry that prefix);
excludes `mirror_open FAILED …`, the `[HYPE Mirror] FAILED open …` echo, incidental warnings, and
**indented** traceback source lines (frame source is indented, print output is column-0).
The two `✗ REJECTED` sites (602/608/614) are unreachable for this command — the watchdog hardcodes
`--signal ai-trader-pending --strategy ai-trader`, which can never satisfy `strategy.startswith('Hermes-conf-')`,
`signal == 'conf-1s'`, or `NOISE_SIGNALS` (brain.py:598-615).

---

## 4. (B/Ad1) Two-state entry machine — full flow re-verified

Code: **trade_watchdog.py:1489-1528** (machine), `:1402` (skip tuple), `:1584` (execute_order steer),
`:1602-1604` (`triggered` write, CAN_PERSIST-gated), `:1614-1622` (atomic write / fail→drop steers).

| case | expected | observed (H2m) |
|---|---|---|
| M1 fresh+cross#1 | `first_break`, **no steer**, persisted | ✅ disk=`first_break`, steers=0 |
| M2 `first_break`+crossed | no write, no steer, ts unchanged | ✅ |
| M3 `first_break`+reclaim | `retested` (entry **retained**, not deleted), no steer | ✅ |
| M4 `retested`+not crossed | continue, no write | ✅ |
| M5 `retested`+cross#2 | 1 steer + `triggered` persisted | ✅ |
| M6 `rejected`+crossed | wait, no steer | ✅ |
| M7 `rejected`+reclaim | → `retested` (old `del` is gone) | ✅ |
| M8 mixed cycle | `first_break` does **not** consume serial; first `retested` fills; 2nd deferred & stays `retested` | ✅ |
| M9 fresh+not crossed | no state written at all | ✅ disk=`{}` |
| M10 `retested`+cross#2 + position OPEN | stacking guard blocks, state stays `retested` | ✅ |
| M11 orphan alert | old `triggered` >15 min → ORPHANED steer, **no action payload** | ✅ |
| M12 LONG symmetry | first_break → retested → fill | ✅ |
| M13 `btc-ceo-*` non-serial | two touches required too | ✅ |
| M14 steer never while `first_break` | 0 steers both prices | ✅ |
| M15 recommend mode | see F4 | `first_break`/`retested` **are** written |

- **(ii) persistence** — every `changed=True` write is flushed by the single `if changed: atomic_write_json(...)`
  at **:1614** after the loop; verified by reading the file *after* each call (all M-cases show disk state).
- **(iii) :1402 skip tuple** is `("triggered","fired","error")` → `first_break`/`retested`/`rejected` fall
  through full validation to the machine (M1–M8 all reached it). `first_break`/`retested` orders are re-validated
  every cycle; a later malformed edit would freeze their state (harmless, they just stop progressing).
- **(iv) can `first_break`/`retested` reach the executor without a steer?** No, by construction:
  `grep '"execute_order"'` → only **:1584** (builder) and **:2224** (consumer). The builder is reachable
  **only** from the `retested ∧ crossed` fall-through; in the same block `state[oid]='triggered'` is written
  (:1603) whenever execution is possible (CAN_PERSIST ⇔ autopilot ⇔ `execute_safe_actions`/`pending_order_monitor`
  will run). In recommend mode the steer is emitted but `triggered` is *not* persisted and **no executor runs**
  (both gated on `mode == 'autopilot'`). Orphan steer at :1411 has no `action`.
- **(v)** orphan-`triggered` alert unchanged (M11).
- **(vi)** serial/stacking/steer only after cross#2 (M8, M10).
- **(vii)** keeper `_unfired` (auto_trader.py:741-749) excludes only `('fired','error','rejected')` →
  `first_break`/`retested`/`triggered` count as **unfired** (H4c table): ready when the trigger is below price,
  i.e. exactly the `retested` condition — correct.
- **(viii) #17004 walk (candle-verified, `data/candles_1m`):** armed 15:56 (no state) → cross#1 at 16:03/16:04
  (low 58773/58769 ≤ 58918) → **`first_break`, no fill** → reclaim 16:05 (high 59216 > 58918) → `retested`
  → **no further print ≤58918 through 16:45** (min low 59136 at 16:27) → **NO FILL = $0**. Commit's
  counterfactual **CONFIRMED** with market data. (Actual fill was 16:05:11 @59044 — i.e. the old code bought
  *into the bounce*, above its own trigger.)

## 5. (C) Double-fire path proof (by code path, not by test)

1. **Steer ⟺ `state[oid] == 'retested' ∧ crossed`** — the machine at :1501-1528 `continue`s on every other
   combination: `rejected`(crossed), `first_break`(both), `retested`(not crossed), fresh+crossed (→`first_break`),
   fresh+not-crossed (nothing). There is no other `steers.append` with an `execute_order` action (:1411 = orphan,
   no action; all other appends are outside this function).
2. **Same cycle, same lock**: the fill branch writes `state='triggered'` (:1603) before returning; the single
   atomic write at :1614 is the *only* way steers escape — if it throws, `return []` (**:1622**) drops **all**
   steers, so an unpersisted trigger can never execute.
3. **Executor belt** `_execute_pending_order_impl` (**:1669**) refuses `('fired','error','rejected')` under the
   flock, reloading state at claim time; verified `0` brain calls for each (H1). State at executor time is
   therefore always `triggered`/absent-never-`first_break`.
4. **Re-entry after a fill** requires the state to be *absent*: `first_break`/`rejected` never steer, and
   `retested` only steers once — after which the state is `triggered`→`fired`/`error`/`rejected`, all refused.
5. Two entry points only (`trade_watchdog.execute_safe_actions:2224`, `pending_order_monitor.py:53`), both
   funnel into `_execute_pending_order`; no steer is persisted/replayed between cycles.

→ **No path produces a steer for a `first_break`/`rejected` state; a second fill requires a fresh state
absent (re-arm) after a non-consuming transition.** Author's claim holds.

## 6. (Bv / Ad4) prune, leak, and "waiting forever"

- **No prune/TTL anywhere** for `pending_orders_state` (grep prune/ttl/expire in trade_watchdog → nothing;
  no prune script touches the file). Live file: **71 entries, oldest ts 2026-10-18, 27 entries whose order is
  no longer in `pending_orders.json`** — those are never visited by the monitor (it iterates `cfg["orders"]`)
  and therefore never deleted (H2 Bv: orphan stayed). Statuses: `fired 56 / error 14 / rejected 1 / first_break 0 / retested 0`.
- Growth classes: `first_break`/`retested`/`rejected` persist **forever** if the level is never reclaimed or the
  order is removed. Correctness impact: none (monitor iterates config; keeper only reads statuses).
  Size impact only → **F3 MEDIUM** together with the keeper's per-cycle arm (below).
- **Is a permanently-waiting `first_break` correct-by-design?** Yes — it is an *armed* rung awaiting its
  reclaim, not a consumed one; the side is still guarded by it. Keeper numbers (H4c, price 60000, rung 59940,
  trig1h 59440 in reach):
  ```
  state=None       -> derived=False (ready)
  state=first_break-> derived=False (ready)      # only possible while price > trigger
  state=retested   -> derived=False (ready)
  state=triggered  -> derived=False (ready)
  state=rejected   -> derived=True   (not ready)
  state=fired/error-> derived=True   (not ready)
  first_break with price BELOW trigger -> derived=True  (NOT ready → keeper derives a newer rung)
  ```
  So the addendum's premise ("first_break that never reclaims ⇒ keeper sees ready ⇒ no newer rungs") is
  **false**: while `first_break` the price is *below* the trigger, `reach_lo <= trig < price` fails
  (auto_trader.py:773) and the keeper **does** keep deriving (H4c last block, D2: 5/5 cycles derived).
  Once reclaimed (`retested`, price above trigger) it correctly counts as ready and stops derivation —
  that rung *is* the live guard for the side.

## 7. (F) Regression + live book

- `python3 -m py_compile scripts/{trade_watchdog,auto_trader,brain,pending_order_monitor}.py` → **OK**
- `python3 analysis/test_manual_exit_manager.py` → **20 passed, 0 failed, rc=0**
- `python3 scripts/trade_watchdog.py --selfcheck` → **PASS (5 interval-merge cases), rc=0**
- Tracebacks: `logs/pipeline.log` last 4000 lines = **0**; `logs/trade-watchdog.log` = 7, **all** from
  `<stdin>`/`<string>` ad-hoc agent commands (SyntaxError/NameError/FileNotFoundError…) — **none** in
  trade_watchdog.py / auto_trader.py / brain.py / pending_order_monitor.py.
- **ONE sanctioned live run_cycle** (`python3 scripts/auto_trader.py`, rc=**0**, stderr empty):
  ```
  enabled=True mode=live decision=MANAGE_ONLY price=59485.4
  scores long=-40 short=30 regime=CHOP | shadow_armed=[] live_armed=[] tweaks=[] hypo_events=[]
  ladder_keeper=None ladder_keeper_long=None skipped=None
  ```
  No crash, keeper read state+config end-to-end, derived nothing (short side ready via the unfired 58736 rung;
  long side out of reach), no `rejected`→`retested` re-arm (price never reclaimed 59940).

**Live book @16:59 (SELECTs + file reads):**
- Open positions: **1 — BTC SHORT #17005**, entry 59150, `stop_loss 59755`, target 57030, amount 22.30,
  10x, `hl_notional_usdt 22.477`, stamped pnl −0.14 / −0.6323 (unleveraged live convention), price 59400.5.
- State: `fired 56 / error 14 / rejected 1 / first_break 0 / retested 0`.
- **All 14 historical `error` burns still `error`** (incl. the 13 knife/floor shorts and `hype-short-7060`
  blacklist) — forward-only confirmed; **nothing I ran re-armed them** (my harnesses only ever wrote `/tmp`;
  the sanctioned run_cycle writes decisions/hypotheticals, not one-shot state).
- `btc-ceo-short-60000` (59940) still `rejected` @15:43:03 — the no-burn fix's first live act; re-arms only
  when price reclaims **>59940** (currently 59400 → crossed → waits). Keeper readiness excludes it (H4b:
  rejected ⇒ derives fresh).
- Armed unfired: **1 short** `btc-auto-ladder-1795192756 @58736` (SL 59090, TP 56546, serial, dynamic_sl false)
  + **16 longs** (75630 … 62402).

## 8. (Ad3) #17004 numbers — row is CONSISTENT; `$1.54` is wrong

`SELECT … FROM trades WHERE id IN (17004,17005)`:
```
17004 closed entry 59044 exit 59450 amount 22.30 lev 10 hl_notional 22.4367
      pnl_usdt -0.15  pnl_pct -6.8932  hype_pnl_usdt 0.0  hype_pnl_pct 0.0  manual_sl_hit
17005 open   entry 59150 stop 59755    amount 22.30 lev 10 hl_notional 22.477
      pnl_usdt -0.14  pnl_pct -0.6323  hype_* 0.0
```
- raw move = (59451−59044)/59044 = **0.68931 %**; ×10 = **6.8931 %** = `pnl_pct -6.8932` ✅ (leveraged return on margin).
- dollar loss = 0.68931 % × `hl_notional_usdt 22.4367` = **$0.1547** → `pnl_usdt -0.15` ✅.
- margin = notional/leverage = 2.24 → −6.8932 % × 2.24 = **−$0.154** ✅.
- The addendum's "−6.89 % of margin = −$1.54" applies the **margin-% to the notional** (22.30): arithmetically
  wrong. The CEO's pasted **$−0.15 is `pnl_usdt`** and is correct.
- **No inconsistency in the row itself.** Sideways findings (pre-existing, not from this batch): (a) `pnl_pct`
  is unleveraged on OPEN rows and leveraged on CLOSED rows — documented at `position_manager.py:542-558` and
  `brain.py:1202`; (b) in the same closed row `hype_pnl_pct` is return-on-notional while `pnl_pct` is
  return-on-margin (evidence: #17000 3x → `pnl_pct 0.6967` vs `hype_pnl_pct 0.2323`; 8/8 sampled rows match
  `pnl_pct = raw×lev`, `hype_pnl_pct = raw`); (c) `brain.py` close-path comment "amount_usdt is MARGIN…
  calc_notional = amount_usdt * lev" contradicts actual sizing (`hl_notional_usdt ≈ amount_usdt` on every
  sampled row) — if HL ground truth were present, `hype_pnl_pct` would be computed off a 10×-inflated notional.

---

## 9. Findings (severity + line refs)

### F1 — MEDIUM (latent, safety-adjacent): `"REJECTED" in out` is too broad
`scripts/trade_watchdog.py:1731`. Any non-zero brain run whose stdout/stderr contains the uppercase word is
classified retryable-`rejected` (H1 OBS rows: mirror_open failure message, traceback quoting a REJECTED line,
incidental warning). Double-fire is **not** reachable today (all brain REJECTED prints are pre-open
`return None` → rc=1; success requires rc==0 ∧ "✓ Added trade"), but the classifier sits on the money path and
converts execution failures into re-arming state. Fix shape: `any(ln.startswith("[brain.py] ❌ REJECTED") for ln in out.splitlines())`.

### F2 — MEDIUM: fresh-air stop uses an unvalidated `sh1h` → dead rung + dark short side
`scripts/auto_trader.py:818` `round(sh1h + 0.10 * atr1)` — the short path never checks `sh1h`, while the long
side does (`:861 if not long_ready and sh1h`). `structure_summary`→`classify` returns `(None, None)` for
**both** sh and sl when a TF has <2 swing highs or <2 swing lows (`structure_analysis.py:classify`), so
`sh1h = 0` is reachable whenever the 1h structure is UNDEFINED but `atr1`/`sl15` are populated. Then
`sl = round(0.1*atr1) ≈ 40` → shape `target < trigger < sl` fails → monitor skips the rung **every cycle**
(`trade_watchdog.py:1477-1483`) while keeper readiness (`:773`) still counts it → **short side dark**.
Reproduced: `bh_h4c_fix2.py` FIX2d/FIX2d2 (`trig=59341 sl=40 tp=58141 → "SHORT shape wrong … skipped"`,
`summary` still derived it). Fix shape: gate the fresh-air arm on `sh1h` exactly like `:861`.

### F3 — MEDIUM: unbounded `pending_orders_state` growth + ≤1 new rung per keeper cycle in a slide
No prune/TTL (§6): 71 entries, oldest 2026-10-18, **27 orphans** for orders no longer in config.
Keeper arms **one new rung per 30-min cycle** while price stays below every trigger — `bh_h4_keeper.py` D6:
6/6 cycles derived (1→6 rungs); ceiling ≈48 rungs/day during a sustained slide, each carrying a real SL/TP and
each going `first_break` (never filling). Money is bounded by serial-per-cycle + stacking + brain dup guard,
but config/state growth and `first_break` accumulation are unbounded until a reclaim. Suggest a state TTL/prune
for entries whose order left the config, and a "already have a `first_break` rung below price" readiness clause.

### F4 — LOW: recommend/dry-run now mutates one-shot state
`trade_watchdog.py:1504,1512,1524` set `first_break`/`retested` with unconditional `changed=True`, while the
`triggered` write (`:1602`) is `PENDING_ORDERS_CAN_PERSIST`-gated and the comment at `:1616-1618` still claims
"recommend/--dry-run: … NOT persisted, order stays armed" (H2m M15). A recommend/dry-run cycle advances the
entry machine without execution authority. (Behaviour is arguably intended — the machine is market-state, not
mode-state — but the documented invariant is now false.)

### F5 — LOW: executor refusal tuple misses the new waiting states
`trade_watchdog.py:1669` `("fired","error","rejected")` — `first_break`/`retested` would pass the belt.
Unreachable today (§5.3), but this is the belt to the monitor's suspenders: add them.

### F6 — LOW: gate taxonomy ≠ the stated intent ("other gates must stay `error`")
`brain.py:637,642,653,663,673` all print `[brain.py] ❌ REJECTED` → live_trading-off/vacation, delisted,
blacklist, HL_MIN notional and DUPLICATE become retryable `rejected` (H1 OBS), not terminal `error`.
All are pre-open (`return None`) so nothing opens; retry is throttled by the reclaim, so no money risk —
but it *is* a behaviour change beyond "RSI gate rejections", and a sub-min `rejected` rung still *covers* a new
arm in `_arm_real_leg` (`auto_trader.py:281` tuple lacks `'rejected'`). Conversely `STALE ORPHAN`
(`brain.py:700`, "rejecting to prevent double-entry") prints **no** marker → still terminal `error` — a
dup-safety rejection that burns the rung, inconsistent with the no-burn doctrine.

### F7 — LOW: keeper note misattributes the trigger/SL source
Base template always prints `trigger {trig} (sl1h {sl1h}−60)` and `SL {sl} (sl1h+0.6·ATR15 reclaim)` even when
the value came from the sl15 fallback or fresh-air. Live proof: `btc-auto-ladder-1795192756` note says
`trigger 58736 (sl1h 61320−60)` but 61320−60 = 61260 (it is `sl15−60`); `btc-auto-ladder-1795190956` carried
two contradictory SL claims (`sl1h+0.6·ATR15` **and** `price×1.006`). Audit text only — but it cost real
verification time and will mislead the next reader.

### F8 — LOW (pre-existing, sideways): `pnl_pct` / `hype_pnl_pct` conventions differ by row status and by column
See §8. Not introduced by this batch; flagging per "see something, say something".

### F9 — INFO: #17005 is an open first-break fill, and would fill anyway
`btc-auto-ladder-1795190956` first crossed ~16:25 (1m low 59218 ≤ 59220) and filled **16:26:55 @59150**,
**5 minutes before** the multi-touch commit (16:31), with the condemned arbitrary stop `SL 59755 = price×1.006`
of the arm price. Under the new machine: first_break 16:25 → retested ~16:30 (close 59242 > 59220) →
cross#2 ~16:32 (close 59194) → **FILL anyway**. So the machine's counterfactual is level-dependent:
$0 for #17004 (verified), not for #17005. FIX2 is forward-only — no re-stop path; the sanctioned run_cycle
returned `tweaks=[]`, so #17005 keeps SL 59755 (0.6 % above price at 16:59).

### F10 — INFO: `--prearmed` scope is exactly as claimed
Skipped region = `brain.py:470-525` only (knife/floor RSI + its fail-open enrichment print), bracketed by
`if direction == 'SHORT' and prearmed:` (:467, prints `⏭ PREARMED`) and `… and not prearmed:` (:470).
Everything else is outside: volatility-regime/metadata/tape backfills, conf-1s/noise, HL-first,
kill-switch+vacation (:637), delisted (:642), directional block (:653), HL_MIN (:663), dup (:673),
stale-orphan (:700), CLI `validate_levels` (:1712). `prearmed=` appears only at `brain.py:408,1654,1747` and
`trade_watchdog.py:1683` (appended to **every** pending execution) — no other caller. Live in-process proof
(`bh_h5_prearmed.py`, `mirror_open` stubbed to raise, audit_logger stubbed, `amount_usdt=5.0` guarantees a
pre-open return): RSI 10 → knife `REJECTED` with `prearmed=False`; with `prearmed=True` → `⏭ PREARMED` +
HL_MIN `REJECTED`, **no knife/HARD_FLOOR line**, `mirror_open` never reached. `btc-ceo-*` gets `--force` +
`--prearmed`: `force` is read only at `brain.py:683/687` (dup guard), `prearmed` only at :470 — independent,
no interaction, no widening beyond those two gates. (Trivial: the `PREARMED` log is SHORT-only, so a LONG
pending order logs nothing — cosmetic.)

---

## 10. Bottom line

The four commits do what they claim: gate-rejections no longer consume rungs, the executor belt holds,
`continue` is per-order, every state transition persists through the single atomic write, **no steer can be
produced for a non-`retested` state (double-fire proof by path)**, the keeper keeps deriving behind rejected
rungs, the prearmed carve-out skips exactly the knife/floor RSI block, the fresh-air stop now sits on major
structure, and the two-state machine blocks #17004's first break ($0 vs −$0.15, candle-verified).
Suite 20/20, py_compile OK, selfcheck PASS, pipeline 0 tracebacks, one live `run_cycle` rc=0, historical
`error` burns untouched (forward-only confirmed).

Ship it — but F1 (narrow the REJECTED match), F2 (guard `sh1h` before the fresh-air arm) and F3 (prune/TTL +
rung-spam ceiling) should land before the next slide, because all three fail *quietly* (retry loop, dark side,
file growth) rather than loudly.

---

# APPENDIX — acceptance round for F1–F7 (commit `f44708c6`)

Verifier: agent-1 (bug_hunter), re-run independently against my own prescriptions.
New harnesses: `/tmp/bh_acc_f1_f5_f6.py`, `/tmp/bh_acc_f2_f3_f4_f7.py` (all /tmp, subprocess +
psycopg2 mocked; one in-process `add_trade` for F6b that is guaranteed pre-open).
Scope of this commit: **exactly 3 files** — `scripts/trade_watchdog.py`, `scripts/brain.py`,
`scripts/auto_trader.py` (`git diff --name-only f44708c6~1 f44708c6`). `pending_order_monitor.py`,
`skills/…` untouched.

> **Line-ref correction to §9 above:** the `brain.py` refs in the first verdict were taken before
> `792d7b12` (+11 lines) landed. Current REJECTED sites: **506, 532** (knife/floor) ·
> **613, 619, 625** (`✗ REJECTED` conf-1s/noise — unreachable for this command) ·
> **648** live_trading · **653** delisted · **664** blacklist · **674** HL_MIN · **684** DUPLICATE ·
> **711** STALE ORPHAN (F6b). All other refs re-checked against the current file.

## PASS/FAIL per finding

| Finding | Verdict | Evidence |
|---|---|---|
| **F1** exact REJECTED match | **PASS** | 5/5 taxonomy + 4 extras; 11/11 coverage sites |
| **F2** fresh-air guarded on `sh1h` | **PASS** | dead-rung repro gone; structure arms byte-identical |
| **F3** 7d waiting-state prune | **PASS** (+1 new LOW, see below) | 8d/9d waiting pruned, 6d/fresh kept, fired/error/triggered never; re-qualify can't fill |
| **F4** machine writes gated | **PASS** (+ prune-in-dry-run call below) | dry: state `{}` untouched ×5; live: first_break→retested→FILL ✓ |
| **F5** refusal tuple += first_break, retested | **PASS** | both refused, 0 brain calls; absent-state control still executes |
| **F6** taxonomy in-code + **F6b** orphan marker | **PASS** | comment matches behaviour; real orphan path prints the exact marker, emoji decoded, → `rejected` |
| **F7** single source per arm | **PASS** | 3/3 sources exact, zero contradictions, multi-touch rule in base note, events aligned |
| F8 / F9 / F10 | **OUT OF SCOPE** (pre-existing / forward-only / INFO) — unchanged | — |

### F1 — PASS
Matcher `trade_watchdog.py:1759` `any(ln.startswith("[brain.py] ❌ REJECTED") for ln in out.splitlines())`.
- **Coverage 11/11:** every watchdog-reachable site carries that exact prefix (506, 532, 648, 653, 664,
  674, 684, 711); the three `✗ REJECTED` sites (613/619/625) do **not** match — correct, they are
  unreachable (`--signal ai-trader-pending --strategy ai-trader` cannot hit conf-1s/noise).
- **5/5 taxonomy:** brain marker→`rejected` · traceback-quoting-frame→`error` ·
  `mirror_open FAILED … REJECTED`→`error` · plain failure→`error` · success→`fired`.
- **Three false-positive classes all excluded:** incidental warning→`error`, lowercase
  `maker_rejected`→`error`, traceback frame (indented)→`error`; blacklist + HL_MIN gates still
  classify `rejected` (coverage preserved).

### F2 — PASS
`auto_trader.py:808` `if not (trig and trig < price) and sh1h:` (mirrors `:874` on the long side).
- `sh1h=0` → **no arm at all** (0 shorts, no summary event) — the `sl≈40` dead rung from
  `bh_h4c` FIX2d is gone, and the monitor sees an empty config → **no `SHORT shape wrong` loop**
  (`steers=0, disk={}`).
- `sh1h=62400` → fresh-air armed `sl=62440` = `sh1h+0.1·ATR1h`, shape `tp<trig<sl` valid.
- Structure arms unchanged: 1h-floor `61260 / 61410`, 15m-fallback `58736 / 59090` (identical to
  the pre-fix formulas).

### F3 — PASS
Prune at `trade_watchdog.py:1391-1399`, before the loop, statuses `("first_break","retested","rejected")` only.
- **8d `rejected` → pruned · 9d `first_break` → pruned · 7d+1h `retested` → pruned**
- **6d `rejected` → kept · fresh `rejected` → kept · 8d `fired` → kept · 9d `error` → kept ·
  9d `triggered` → kept** (one-shot guards intact).
- **Config order persists:** the order stays in `pending_orders.json`; only the wait-state is dropped.
- **Cannot double-fire:** pruned + crossed in the *same* call → state absent → `elif crossed:` →
  `first_break`, **0 steers**; a pruned `retested` (one touch from filling) also re-qualifies to
  `first_break` — i.e. two more touches, a *delay*, never a direct fill.
- **Orphans:** waiting-state orphans (order removed from config) are now cleared; `fired` orphans kept.
- **Live inventory vs what the prune clears:** file = 71 entries (`fired 56 / error 14 / rejected 1`),
  oldest 2026-10-18; **prune would clear 0 today** (the only waiting state is `btc-ceo-short-60000`,
  1.9 h old); **27 orphans, all `fired`, 0 waiting** → the consumed-orphan half of my F3 is
  *deliberately* not addressed (deleting a `fired` guard for an id that could be re-armed later
  re-opens double-fire — correct trade-off). Residual: file grows ~1 entry per consumed order
  (~70 in 33 d); acceptable, optional 90-day TTL for config-absent entries only if it ever matters.

### F4 — PASS; prune-in-dry-run call below
Machine writes now inside `if PENDING_ORDERS_CAN_PERSIST:` (rejected→retested, first_break→retested,
fresh→first_break).
- **dry-run, persist-off:** fresh+crossed → `{}`; reclaim → `{}`; cross#2 → `{}`; an *existing*
  `first_break` not advanced on reclaim; an *existing* `rejected` not advanced → **my F4 observation
  resolved** (state file untouched by a non-authoritative cycle).
- **live path regression:** cross#1 → `first_break` → reclaim → `retested` → cross#2 → **1 FILL steer +
  `triggered`** ✓.

### F5 — PASS
`trade_watchdog.py:1687` `("fired","error","rejected","first_break","retested")` — `first_break` and
`retested` both refused with **0 brain calls** and state unchanged; control (absent state) still
executes (1 call).

### F6 / F6b — PASS
- **F6a:** in-code taxonomy at `trade_watchdog.py:1745-1753` states the *intended* scope (all pre-open
  brain rejections = retryable `rejected`, throttled by reclaim; only non-marker failures stay terminal
  `error`) and matches observed behaviour exactly — no doc/behaviour drift.
- **F6b:** `brain.py:711` now prints
  `[brain.py] ❌ REJECTED: BTC — STALE ORPHAN: BTC id=999 hl_ep=0.0 age=72.0h — rejecting to prevent double-entry`
  — verified on the **real orphan path** (fake dup/orphan cursors, `prearmed=True` to pass the RSI gate,
  `mirror_open` stubbed to raise): `add_trade` returned `None`, exactly one STALE ORPHAN line,
  **`\u274c` decoded to the emoji (no literal `\u274c` text)**, line starts with the exact marker →
  the F1 matcher classifies it **`rejected`** (retryable) instead of the old terminal `error` burn.

### F7 — PASS
`auto_trader.py:835-848` — one `_src` per arm, mutually exclusive, event `_ev` aligned
(`ladder_keeper` summary = `(…, SL x, TP y)` with the source tag):
- **1h-floor** note contains `1h MAJOR-floor break: trigger 61260 (sl1h 61320−60), SL 61410 = sl1h+0.6·ATR15 reclaim (break failed)`;
  no `15m fresher-low`, no `FRESH-AIR`, no `sh1h+0.1`.
- **15m-fresh-low** note contains `15m fresher-low break: trigger 58736 (sl15 58796−60), SL 59090 = sl15+0.6·ATR15 reclaim (break failed)`;
  **no `sl1h` anywhere** (the old false `sl1h 61320−60` claim is gone).
- **FRESH-AIR** note contains `FRESH-AIR continuation: trigger 59341 (price 59520×0.997), SL 62440 = sh1h+0.1·ATR1h MAJOR structure`;
  no `sl1h+0.6`, no `price×1.006 reclaim` — **the two contradictory SL claims from my live proofs are gone**.
- All three carry the base rule `Fills only on the reclaim+re-cross (multi-touch — first break never fills)`.

## The two answers requested

### 1. `auto_trader.py:281` (`_arm_real_leg` coverage tuple) — **leave it unchanged; do NOT add `'rejected'`**
The two predicates ask opposite questions and must stay asymmetric:
- `_unfired` (keeper readiness, `:741`): *"is there a live guard on this side **right now**?"* — a
  rejected rung deep below price / blocked by a gate is not a guard → **exclude** → derive fresh. (F-fix correct.)
- `_arm_real_leg` coverage (`:281`): *"will this existing order **eventually fire at this level**, so a
  twin would duplicate it?"* — a rejected rung is alive and re-fires after reclaim → it **does** cover →
  keep it **out** of the tuple. Adding `'rejected'` would make the bracket path arm a twin within
  0.5×ATR1h of a rung that is still going to fire → two live rungs at ~the same trigger; for a
  non-serial `btc-ceo-*` twin the stacking guard does not apply, so that is a genuine double-position
  path. `first_break`/`retested` are likewise absent from `:281` → they cover → correct.
- My original F6 residual (a *permanently* blocked rejected rung — HL_MIN / blacklist — "covers" and
  suppresses a proper twin) stands as **LOW**, but the fix is **not** the coverage tuple: the right
  levers are rung lifecycle (config removal; now also the 7d waiting-state prune) or sizing/level
  correctness. Un-covering would trade a narrow suppression window for a duplicate-fire window.

### 2. Prune in dry-run (ungated) — **my call: gate it too** (`if PENDING_ORDERS_CAN_PERSIST:` around the prune loop)
Observed: `trade_watchdog.py:1391-1399` mutates the one-shot file under `CAN_PERSIST=False` (harness
`F4b` reproduced the deletion).
- It is *mostly* hygiene, but **not entirely trade-affecting**: deleting a waiting state resets that
  rung's progress — a `retested` rung (one touch from filling) needs two more touches afterwards.
  That is a delayed/missed entry decided by a mode documented as non-authoritative.
- It **cannot** double-fire (verified: state absent → `first_break`, never a direct fill).
- Side effect: the prune forces `changed=True` → an `atomic_write_json`; if that write fails the
  function `return []`s and **drops that cycle's steers** — in dry-run that silently hides the very
  steers the mode exists to display.
- Cost of gating: one line, deferred to the next authoritative cycle (pipeline runs every 1 min).
- **Verdict: gate it** for symmetry with F4 (one-shot state written only by authoritative cycles).
  If it is deliberately left ungated, impact is **LOW** (no double-fire, ≤7d-old waits only) — but then
  it must at least get the `try/except` below.

## New finding from this round

**N1 — LOW (new, introduced by F3): non-`numeric` `ts` crashes the whole monitor**
`trade_watchdog.py:1395` `(_now - float(v.get("ts") or 0)) > 7 * 86400` — `float('yesterday')` raises
`ValueError`, and the prune sits **outside every `try`**: `monitor_pending_orders` (`:1322`) has
`try/finally` only, so the exception reaches `pending_order_monitor.main` (pipeline step → traceback,
rc≠0) and `analyze_all` (`:1878`) → **the entire pending-order monitor / watchdog cycle dies** until the
file is repaired — armed rungs stop firing, i.e. the original incident's failure class. Every other
`float(ts)` read in this function is inside the per-order `try` (orphan alert, `:1423`); the orphan alert
also *instructs the CEO to hand-edit this file*, so hand-edits are an expected input. Harness:
`ts: "yesterday"` → `RAISED ValueError: could not convert string to float: 'yesterday'`.
Fix shape: wrap the prune loop in `try/except Exception: pass` (or a safe-float). Note also that a
**missing/`0` `ts`** → `or 0` → age = now → pruned on the very next cycle (benign: re-qualifies fresh,
but it is an instant-prune, not a 7d one). The lock is released correctly (`finally`) — no lock leak.

## Regression re-run (acceptance round)
`py_compile` trade_watchdog/auto_trader/brain → **OK** · `analysis/test_manual_exit_manager.py` →
**20 passed, 0 failed** · `trade_watchdog.py --selfcheck` → **PASS (5 cases)**.

## Acceptance verdict
**F1–F7: all PASS against my prescriptions** (7/7), scope exactly 3 files, no HIGH/medium regressions.
One new **LOW (N1)** and one recommended-but-optional hardening (gate the prune in dry-run) — both are
one-liners in the same block. F8/F9/F10 remain out of scope as agreed.

---

# FINAL CLOSE-OUT — N1 + prune gating (commits `fea03eaa`, `d7846f70`)

Verifier: agent-1 (bug_hunter). Harness `/tmp/bh_fin_n1.py` (23/23 ok, 0 FAIL), all /tmp,
psycopg2 faked. Scope of both commits: **exactly `scripts/trade_watchdog.py`** (`git diff --name-only
fea03eaa~1 d7846f70`); `auto_trader.py` diff across them = **0 lines**.

| Item | Verdict | Evidence |
|---|---|---|
| **N1 refined** (per-entry ts guard) | **PASS** | corrupt `ts='yesterday'` → entry **kept + WARN** `waiting-state btc-auto-ladder-bad: non-numeric ts — kept (not prunable)`, **cycle completes** (original ValueError repro now logs and continues); **8d `good` PRUNED in the same call** (the red test), 9d `first_break` pruned, fresh kept, fired/error/triggered never; **3 valid aged entries pruned in one cycle, no RuntimeError** (candidates materialised as a list before `del` — no dict-view mutation) |
| **Prune gated on `PENDING_ORDERS_CAN_PERSIST`** (my call) | **PASS** | dry-run: 8d entry **kept**, status unchanged, **no prune log**; live: pruned + logged |
| **`auto_trader:281` left unchanged** (my call) | **PASS** | `git diff … -- scripts/auto_trader.py` = 0 lines; tuple still `('fired','error')` — `rejected` keeps covering, no twin path |
| **Machine regression after both changes** | **PASS** | `first_break`+crossed → wait/0 steers → reclaim → `retested` → cross#2 → **FILL steer + `triggered`** |
| **F3 boundary intact** | **PASS** | rejected 7d→pruned/re-qualify `first_break` · rejected 6d kept · fired/error/triggered 7d kept |
| **Regression battery** | **PASS** | `py_compile` OK · `analysis/test_manual_exit_manager.py` **20/20** · `--selfcheck` PASS |

### Notes on the refinement (no action required)
- **`ts: null`/missing → instant-prune** (`or 0` → age = now): accepted, documented benign — the entry
  re-qualifies fresh and can never fill directly (proven). Not a 7d wait, but a safe default.
- **Self-healing:** a kept corrupt-`ts` entry repairs itself on its next transition — the machine writes a
  fresh numeric `ts` (observed: `bad` went `rejected → retested` with a valid ts in the same run), after
  which the prune works normally. So the WARN is a short-lived "repair me" signal, not a permanent hole.
- **WARN cadence:** one line per cycle (≈1440/day) while a corrupt entry persists — loud by design,
  matches the repo's "never fail silently" convention.
- The guard is `(TypeError, ValueError)` rather than bare `Exception`: covers str/list/dict/None corrupt
  values; a JSON int beyond float range would raise `OverflowError` (absurd hand-edit, not covered) —
  noted only for completeness, not a finding.

## FINAL VERDICT
**F1–F7 7/7 PASS · both prescriptions implemented as specified · N1 (which I introduced the report for)
closed and then correctly refined after the first all-or-nothing guard was caught red by the author's own
test.** Scope stayed at the claimed files each round; F8 (pnl conventions), F9 (#17005 legacy stop,
forward-only) and F10 (INFO) remain out of scope as agreed.

**No open findings. Verdict: ACCEPTED — ship.**
