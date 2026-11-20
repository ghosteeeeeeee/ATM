# bug_hunter verdict — mfe_exit governed-enable (ba4c5a2d) + two-style entries (e34783dc) + straight-line escape (5c814dc5) (2026-11-20)

Verifier: agent-2 (bug_hunter), adversarial, no fixes applied.
Harnesses (all /tmp, SELECTs + mocks, zero production writes except ONE sanctioned live `run_cycle`):
`/tmp/bh_mfe_verify.py` (H1 — real mfe block + structure_governed source slices exec'd, mocked close/log),
`/tmp/bh_twostyle_verify.py` (H2 — real `_monitor_pending_orders_impl`, /tmp config+state, psycopg2 stub),
`/tmp/bh_mfe_race_c.py` (H3 — race table + real UGB block slice),
`/tmp/bh_escape_verify.py` (H4 — straight-line escape, real monitor + stub DB).
All PASS. Evidence lines below are reproduced by those scripts.

---

## 1. Scope (3 commits)

| commit | subject | files |
|---|---|---|
| `ba4c5a2d` | mfe_exit enabled for structure-governed trades | `scripts/position_manager.py` (12+/2−) **only** |
| `e34783dc` (addendum 1) | two-style entries | `scripts/auto_trader.py`, `scripts/trade_watchdog.py`, `skills/shared/full-analysis/SKILL.md` |
| `5c814dc5` (addendum 2) | straight-line escape + 80k rung | `scripts/hermes_constants.py` (10+ ADDED VALUE), `scripts/trade_watchdog.py` (+24/−1); `data/pending_orders.json` gitignored (`.gitignore:2 data/`) |

`git diff ba4c5a2d -- scripts/position_manager.py` = **0 lines** (worktree == shipped);
`hermes_constants` diff vs ba4c5a2d = only the 5c814dc5 addition (0 MFE lines added/removed).

## 2. Verdict table

| # | Item | Verdict |
|---|---|---|
| A(i) | real-data counterfactual from PG highest/lowest | **PASS + F1 (LOW)** — live peak = **0.5917%** (low 58800), thr **0.4142%**, threshold price **58,905.00 = +4.14% margin @10x**; 121-sample replay fires 18:17:20 @ **58,962.49 = +3.17%**; commit's 0.54/58,925/+3.80% is candle-min arithmetic (F1) |
| A(ii) | units at `live_pnl <= _mfe_thr` (F8 trap) | **PASS** — both unleveraged price-%; roundtrip proven through real `compute_live_pnl` |
| A(iii) | highest/lowest writers live for ai-trader-pending | **PASS** — `refresh_current_prices` every cycle pre-close, no managed-signal skip; corroborated by PG 58800 + HML-SHADOW max +0.592% + ARM-GAP non-zero MFE |
| A(iv) | `structure_governed` call sites = 4, locals in scope | **PASS** — pm:646/4036/4065/**4697** + def pm:192; `_pos_signal` hoisted pm:3259 |
| A(v) | non-managed + jup byte-identical | **PASS** — 24 reachable truth-table rows, exactly 2 diffs, both `(enabled & ceo & gov & !linreg)`; jup/non-managed identical unconditionally; CEO-no-stop stays OFF |
| A(vi) | WIN-CAPTURE shadow unaffected | **PASS + INFO** — code/dedup/log-only identical (H1 T5); *reach* now extends to governed trades (F4) |
| B | race: mfe wins the #17005 bounce; effective distances | **PASS + F7/F8 (INFO)** — mfe 58,905 < UGB 59,066(bypass-dead) < mxm 59,096(frozen) < BE-lock 59,150(frozen) < BE-cap/HML 59,209.15; giveback floor **12bp**, fires at ≥**28bp** fav; peak-0.41 "29-pt" does not reproduce → **72.8 pts / 12.3bp** on entry 59150 |
| C | UGB-PT sibling: exact blocker + >1.5% hole | **PASS + F2/F3 (LOW)** — blocker = `_is_bypassed` pm:**4650-4653** (NOT the trail-state check pm:4655); rung never in trail state (PM query excludes `ai-trader`, profit_monster:86-89; `_save_trail_state` only from run_trail:577; BE-cap writer never touches state); >1.5% peaks rely solely on mfe's 30% (F3) |
| D | full exit enumeration + mfe can't fire on a loser | **PASS** — list §7; peak<ARM → no fire, thr=0.7×peak ≥ 0.28% > 0 → first touch strictly above water (both directions) |
| E | regression | **PASS** — suite 20/20; py_compile 250 OK/1 pre-existing fail (`tpsl_utils_debug.py`, old F-10, untouched since dbd340e0); fresh imports OK; **ONE live `run_cycle` rc=0** (below); mfe_exit: 50 all-time (jup/continuum only), **0 ai-trader ever, 0 since ba4c5a2d**; pipeline.log **0 Tracebacks**; trade-watchdog.log 200 TBs all `<stdin>` heredoc SQL/stdlib, **0 in shipped code** |
| F | scope + constants | **PASS** — ba4c5a2d = position_manager only; MFE_EXIT_ENABLED=True / GIVEBACK_PCT=0.30 / ARM_PCT=0.004 (hermes_constants:2164-2166) unchanged; **F6 (LOW): they are NOT in CEO_PROTECTED_FLAGS despite the comment** |
| Ad1(i) | continuation cannot leak a retest fill | **PASS** — only exact `entry_style=="continuation"` matches (tw:1537); 61/62 live rungs unflagged incl. `btc-ceo-short-continuation` (id text irrelevant); 6-strategy sweep M2 |
| Ad1(ii) | legacy first_break+flag no double-fill | **PASS** — `_ps=None` → fill path → state `triggered` (tw:1649-1651) → belt `:1438-1457` blocks re-fire; state-write failure drops ALL steers (:1660-1669) |
| Ad1(iii) | keeper note/dict consistency | **PASS** — single writer ternary on `fresh_air` (auto_trader:855, codebase count=1); live scan: 1 flagged (backfilled 58736), 0 bad values, 0 on-cross notes without flag |
| Ad1(iv) | dry-run gating both styles | **PASS** — every state write behind `PENDING_ORDERS_CAN_PERSIST` (:1543/:1552/:1568/:1649); execution gated watchdog main :2375/:2399 + `write_outputs` print-only :2051 + pipeline recommend-gate (pending_order_monitor:38-43) |
| Ad1(v) | scope 3 files | **PASS** (§1) |
| Ad2(i) | escape fall-through → fill path, no first_break re-record, guards kept | **PASS** — `_ps="retested"` → retested-branch falls through → stacking + serial guards run (H4 E2/E8/E9: BTC-open blocks fill; 2 escaped rungs → 1 steer) |
| Ad2(ii) | escape can't fire not-crossed | **PASS** — reclaim branch `:1551` runs first; geometry escape px implies crossed both directions (E4) |
| Ad2(iii) | dry-run escape steer gated | **PASS** — steer shown, state byte-identical, not burned; 3 execution gates asserted in source (E7) |
| Ad2(iv) | keeper readiness with 80k rung | **PASS** — real ATR1h=799pt → reach_hi=60,567 < 80,060 (excluded by 19,493pt; needs ATR1h 7,297pt = 12.5% hourly bars); 60085 long rung ≤ reach_hi → `long_ready` via it, no duplicate (E10) |
| Ad2(v) | scope = watchdog + constants + gitignored config | **PASS** (§1, E11) |

**Overall: SHIP-CONFIRMED WITH FINDINGS — 0 HIGH, 0 MEDIUM, 4 LOW, 6 INFO across the three commits.
The new closing path is safe on real data: fires in profit only, never on losers, never below +28bp fav.
The two live stack changes (two-style, escape) re-verify the multi-touch machine without opening a double-fill path.**

---

## 3. (A i–iii) — real-data counterfactual, units, column-writer proof

### A(i) exact numbers the LIVE code would produce (PG columns, not candle-min)

PG row `trades id=17005`: entry **59150.00**, `lowest_price` **58800.0**, `highest_price` 59599.0,
stop 59209.15, exit 59221.00 (HL backfill), close `current_price` 59272.5, signal `ai-trader-pending`,
lev 10, open 16:26:55 → close 18:22:30, `manual_sl_hit`, `trailing_activated` False.

- peak_fav = (1 − 58800/59150)×100 = **0.591716%** (≥ ARM 0.40 → armed)
- thr = 0.591716 × 0.70 = **0.414201%** → threshold price 59150×(1−0.00414201) = **58,905.00**
  → **+4.14% margin @10x** (vs actual −2.07%)
- 121-sample replay of the real `HML-SHADOW` per-cycle `live_pnl` series through the REAL block
  (running peak = min-tracking lows): **no fire while peak < 0.40**; previous sample 18:15:31/32
  +0.456% > thr → no fire; **first fire 18:17:20 at live +0.317% → exit 58,962.49 = +3.17% margin**
  (actual first-touch between samples lies in **[58,905.00, 58,962.49]**). Save = **5.24–6.21pp**.

**F1 (LOW)** — the commit-message counterfactual (peak 0.54% → thr 0.380% → exit 58,925 = +3.80%)
is the *candle-min* number, not the live number. Direction and magnitude hold (and the real save is
larger), but every figure in the message should be the PG-column figure.

### Reconciling 0.52 vs 0.54 vs 0.59 (three samplers, no defect)

| source | low used | peak | where |
|---|---|---|---|
| **PG `lowest_price` = the live code's input** | 58800.0 | **0.5917%** | refreshed from HL mids each cycle (pm:3003-3035) |
| your candle-min | 58829 | 0.5427% | your feed (misses the 58800 wick) |
| ARM-GAP `MFE=0.52%` | mfe_price **58844.5** (`trades.mfe_pct`=0.51648) | 0.5165% | `hl_sync_guardian._compute_mfe_mae` (:3118-3159) reads `signals_hermes.db price_history` — its own sampling window |

Independent corroboration of 58800: HML-SHADOW `live_pnl=+0.592%` at 18:14:30 → price 58,799.6.
The live block uses PG (0.5917) → fires sooner and higher than both other estimates.

### A(ii) units at the compare line (pm:4745) — the F8 trap is clean

`live_pnl` is assigned only at **pm:3268** (`compute_live_pnl` — unleveraged raw price %,
pnl_utils:46-67) and **pm:3270** (fallback `pnl_pct` — from `refresh_current_prices`, itself
`compute_live_pnl` or `compute_hl_pnl_pct` = unrealized/(entry×size), both unleveraged %).
`_mfe_thr = peak_fav × (1 − 0.30)` — peak_fav is price-% from price columns → price-%.
ARM: `float(0.004)×100 = 0.40` (pm:4711). H1 T3 roundtrips `compute_live_pnl(entry, thr_price, dir)
== thr` for 9 peaks × 2 directions (4dp tolerance = live_pnl rounding). **Same units, no trap.**

### A(iii) column-writer proof — peaks are live for ai-trader-pending rungs

1. **Seeding**: `brain.py:928` at creation (LONG highest; SHORT lowest seeds 0 → first refresh
   initializes to current then min-tracks, pm:3003-3006).
2. **Every cycle, pre-close**: `refresh_current_prices()` (pm:2723) does `new_low = min(existing_low,
   cur_price)` from HL mids (pm:3003/3010) and persists `highest_price/lowest_price`
   (pm:3030-3035) — called at **pm:3179, before the exit loop at pm:3229**. It has **no
   managed-signal skip** (the `is_managed_signal` skip at pm:2299 is only inside
   `_collect_atr_updates`, which the exit loop doesn't need for peaks).
3. Guardian also reconciles peaks (hl-sync-guardian:1263/1338) — reset risk documented (pm:4553).
4. **Live evidence for our class**: PG 58800 ≠ 0; HML series peak +0.592%; ARM-GAP MFE non-zero.
5. Fail-open edges (pre-existing class, not new): no HL data for a cycle → peaks not refreshed that
   cycle (pm:2953 `continue`) → stale-but-non-zero (fires later, conservative); a rung that has
   *never* had HL data → `_mfe_lo=0` → `_mfe_fav=None` → no fire (documented pm:4678).

## 4. (B) the race + effective exit-distance table

#17005 bounce ordering (SHORT, ascending price = fires first) — H3:

```
 58,905.00  fav +0.4142%  mfe_exit (pm:4746)                 ← FIRES FIRST
 59,066.17  fav +0.1417%  UGB-PT (pm:4656) — bypass-dead
 59,095.75  fav +0.0917%  mxm trail floor — frozen (dynamic_sl:False, auto_trader:312)
 59,150.00  fav  0.0000%  mxm BE-LOCK — frozen
 59,209.15  fav -0.1000%  BE-cap stop = entry×1.001 (auto_trader:478-483 == DB stop)
 59,209.15  fav -0.1000%  HML twin (pm:4335-4340 = stop's own distance, never leads)
```

mfe's threshold sits **304 pts below** the BE-cap → wins the race on the bounce ✓ (commit claim
confirmed). Structure-lag steps only move the stop (auto_trader `_apply_stop`), capped at
`_be = entry×1.001` for shorts — can never preempt mfe.

**Caveat F7 (INFO)**: within one cycle, ATR/manual-SL hit (pm:3728) is evaluated *before* mfe
(pm:4746). A bounce that gaps the whole 304-pt band between two ~60s samples closes at the stop
(−1.00% margin, never worse). #17005's real series had a sample inside the band (18:17:20) → mfe
wins in practice; first-touch semantics are sample-granular.

**Effective exit distance for governed trades (mfe live)** — H3 sweep:

| peak | thr (exit fav) | giveback | bp | pts @59150 | first vs siblings |
|---|---|---|---|---|---|
| 0.400 (ARM floor) | 0.280% | 0.120% | 12.0 | 71.0 | beats everything |
| 0.410 | 0.287% | 0.123% | 12.3 | **72.8** | beats everything |
| 0.5917 (#17005) | 0.414% | 0.178% | 17.8 | 105.0 | beats everything |
| 1.000 | 0.700% | 0.300% | 30.0 | 177.5 | beats everything |
| 1.500 | 1.050% | 0.450% | 45.0 | 266.2 | **crossover vs UGB-PT (0.45)** |
| 1.667 | 1.167% | 0.500% | 50.0 | 295.8 | crossover vs mxm floor (0.50) |
| 2.000 | 1.400% | 0.600% | 60.0 | 354.9 | UGB/mxm tighter — both dead for us (F3) |
| 5.000 | 3.500% | 1.500% | 150.0 | 887.2 | same |

- **Effective numbers: giveback = max(0.12% = 12bp, 30% of peak); exit always at ≥0.28% = 28bp fav.**
  The BE-cap only exists 10bp *beyond* entry (loss side) → **mfe now dominates ALL governed
  profit-exits for every armed peak** — that is the design (commit message), now with exact figures.
- Task's "peak 0.41 → fires on a 29-pt bounce": **does not reproduce** — 0.123% of entry 59150 =
  **72.8 pts** (12.3bp). 29 pts would be a ~$23.6k entry. Sensitivity assessment: 12bp giveback at
  the ARM floor is *tighter than the BE-cap's 10bp cushion* — but ARM (0.40%) exists precisely to
  keep micro-peaks out, and every fire is still ≥28bp in profit; micro-churn below ARM never fires
  (H1 T3: peaks 0/0.1/0.39 → zero fires across the sweep).

## 5. (C) the UGB-PT sibling question

**Exact blocker for #17005 = the bypass hoist, pm:4650-4653 — not the trail-state check at pm:4655.**

- `_is_bypassed = (not _pos_signal) or any(_s in _pos_signal for PROFIT_MONSTER_BYPASS_SIGNALS) or
  any(... PM_TRAIL_BYPASS_SIGNALS)`; `PROFIT_MONSTER_BYPASS_SIGNALS` contains **`'ai-trader'`**
  (hermes_constants:2322) → `'ai-trader-pending'` matches → `if not _is_bypassed:` wraps **both**
  the shadow log (:4654) and the enforce (:4655). Runtime proof (H3): same geometry, signal
  `ai-trader-pending` → **no log, no exit**; signal `bb_bounce+` → **`ugb_pt` fires** (trail-state
  check passes because the state is empty).
- **Is the rung in the trail state? No — and it never could be:**
  - profit_monster's own position query **excludes** bypass signals (`signal LIKE '%ai-trader%'`,
    profit_monster.py:86-89) → `run_trail` never sees it → never arms → never in state.
  - `_save_trail_state` has **one** call site (profit_monster:577, inside `run_trail`) — the
    BE-cap writer (auto_trader `_apply_stop` → `adjust_stop_loss`) writes `stop_loss` only.
  - live `data/profit_monster_trail_state.json` = **0 entries**.
  - ARM-GAP's `trail=FALSE` reads `trades.trailing_activated` (pm:1531-1536) — an exit-reason
    trigger column, always False for `manual_sl_hit`; it says nothing about trail state.
- **>1.5% peak hole assessment (F3, LOW):** for peaks >1.5% the fixed-0.45 sibling *would* be
  tighter than mfe's 30% — but UGB-PT is bypass-dead for **all** managed signals by design
  (FIX 2026-10-31), PM trail is bypass-dead (same list), and the mxm tiered trail is frozen for
  structure-fixed rungs (`dynamic_sl: False`, auto_trader:312 — "BE/trail stands down"). So mfe's
  30% is the **sole giveback layer**: peak 2.0 → gives back 0.60% (exits +1.40% = +14.0% margin
  @10x); peak 5.0 → gives back 1.50% (exits +3.50%). **Assessment: acceptable, not a safety hole**
  — first touch is always >0 (never round-trips to loss) and it is strictly better than the
  pre-commit world (giveback was 100% of profit down to the BE-cap). It is, however, strictly
  worse than the fixed-0.45 mental model the counterfactual implied — recorded as a design note for
  the CEO, not a defect of this commit (pre-existing, improved-not-worsened).

## 6. (D) doctrine sweep — every exit that can close a managed structural trade (G-list + mfe)

position_manager.py line refs (current):

| # | exit | location | governed status |
|---|---|---|---|
| 1 | ATR/manual SL hit (`manual_sl_hit`/`atr_sl_hit`) + guardian HL-side stop | pm:3728-3735; guardian `_check_hard_stops` | **retained** (the stop IS the doctrine) |
| 2 | TP hit `atr_tp_hit` | gate pm:646 `structure_governed` | **EXEMPT** (gated) |
| 3 | `wave_turn` z±1.5+accel | pm:3746-3766 (no `is_ceo` gate) | **can fire in profit** — pre-existing G-list item |
| 4 | MACD cascade `should_exit` | pm:3911 (token gate TRB/IMX/SOPH/SCR) | not BTC |
| 5 | cascade flip / `cut_loser` | pm:3925 / pm:3990-4011 (`should_cut_loser` pm:511 = stop price p1) | loss/stop side |
| 6 | `stale_exit` | pm:4026-4042, gate pm:4036 | **EXEMPT** |
| 7 | `UNIVERSAL_MAX_HOLD` | pm:4065-4079, gate pm:4065 | **EXEMPT** |
| 8 | soft trigger (2h) | pm:4104 `not is_ceo_trade` + live≤0 | excluded + loss side |
| 9 | HML / `hard_max_loss` | pm:4335-4348, `hml_threshold` pm:217 | threshold = stop's own distance → never leads the stop |
| 10 | TAT `trail_arm_timeout` (bb-squeeze/pump-chain LONG; bb-bounce/ai-trader+ variant-C) | pm:4357-4381 / pm:4385-4420 | variant-C requires live<0 (loss side) |
| 11 | `prearm_lock` (enforced) | pm:4561-4594 | peak ∈[0.25,0.40) + live≤0 → **disjoint from mfe's arm** |
| 12 | `ugb_pt` | pm:4615-4660 | **bypass-dead** for ai-trader (F2) |
| 13 | **`mfe_exit`** | **pm:4667-4760** | **NEW for governed** — in profit only |
| 14 | `time_exit` / `peak_exit` | pm:4779-4785 / pm:4788-4813 | require live<0 (loss side) |
| 15 | rr_engine / pump_exit / ride_it / sl-zone tighten | pm:3542/3576/3604/3654/3708, gates pm:3417/3595/3625 | `not is_ceo_trade` → excluded |
| 16 | T1 mirror `trader_exit`/`hard_max_loss` | pm:3319/3333 | T1 only (not our trades) |
| 17 | weather-vane shield max-hold | pm:3125 | gated off (`WEATHER_VANE_SHIELD_ENABLED`) |
| 18 | external: guardian CUT_LOSER −3% (non-BTC, hl-sync-guardian:1919-1924), hl_fill_monitor copy-exit, kill-switch/blocklist sweep | | unchanged |

**mfe on a loser — proved impossible:** peak < 0.40% (incl. 0/0.1/0.39) → zero fires across a
live-pnl sweep from +1.0 to −5.0 (H1 T3); armed → thr = 0.7×peak ≥ 0.28% > 0 for every peak in
{0.40 … 10.0}, both directions, and the first-touch price is strictly on the favorable side of
entry (SHORT exit px < entry, LONG exit px > entry). **thr > 0 for all armed cases.**

## 7. (E) regression battery

- **Suite**: `analysis/test_manual_exit_manager.py` → **20 passed, 0 failed** (re-run post-5c814dc5).
- **py_compile**: 250/251 `scripts/*.py` OK; the 1 failure is the **pre-existing** broken debug
  file `scripts/tpsl_utils_debug.py` (old F-10, last touched dbd340e0 2026-10-03, in no diff here).
- **Fresh imports**: `position_manager`, `auto_trader`, `trade_watchdog`, `hermes_constants`,
  `manual_exit_manager`, `profit_monster` — all OK.
- **ONE sanctioned live `run_cycle`** (`python3 scripts/auto_trader.py`, 19:13:17Z): **rc=0, stderr
  empty**. Summary: `decision=MANAGE_ONLY, scores {long:-55, short:15, regime:CHOP},
  price=58169.69, tweaks=[], shadow_armed=[], live_armed=[], armed_detail=[], hypo_events=[],
  stats n=58 wr=44.8 pnl=+$0.775 (short wr 51.5 / long 36.0), size_mult 0.66`.
  *Honest note (INFO)*: this ran 54s **before** 5c814dc5 committed (19:14:11Z) — 5c814dc5 touches
  trade_watchdog+constants only (auto_trader unchanged since e34783dc, which the run exercised);
  5c814dc5 is covered by H4 + suite + fresh imports + the pipeline's per-minute fresh-subprocess
  steps. No second run_cycle taken (one-run budget spent).
- **Book**: **BTC OPEN = #17007 only** (SHORT ai-trader-pending, entry 58,674, SL 58,732.674 =
  entry×1.001 BE-cap (lag landed), TP 56,546, 10x, open 18:56:53; at 19:22 low 57,862 →
  **peak 1.3839%, mfe ARMED, thr 0.9687% → first-touch exit 58,105.60 = +9.69% margin @10x** vs
  BE-stop −1.00%; live +10.23% margin at check). **#17005 closed** (`manual_sl_hit` 18:22:30).
  Rungs: 64 orders, states = 57 fired / 14 error / 1 rejected (no pending first_break/retested/
  triggered).
- **mfe_exit history**: 50 all-time (jup_yolo_mirrored / continuum only), **0 on ai-trader signals
  ever, 0 since ba4c5a2d** (new path has not yet fired live; #17007 is its first live test case).
- **Tracebacks**: `logs/pipeline.log` **0** (total); `logs/trade-watchdog.log` 200 — every one is
  `File "<stdin>"` agent heredoc SQL + psycopg2/json stdlib frames (0 in position_manager/
  auto_trader/trade_watchdog); the 19:09–19:17 cycle contains 1, `<stdin>`.

## 8. (F) scope

- `git show --stat ba4c5a2d` → **`scripts/position_manager.py` only** (12+/2−). Constants,
  watchdog, auto_trader, skill untouched by it; worktree position_manager == shipped (0-line diff).
- `MFE_EXIT_ENABLED=True`, `MFE_EXIT_GIVEBACK_PCT=0.30`, `MFE_EXIT_ARM_PCT=0.004`
  (hermes_constants:2164-2166) — unchanged by all three commits.
- e34783dc → exactly 3 files; 5c814dc5 → exactly 2 files + gitignored config; no MFE line
  added/removed by 5c814dc5.

---

## Findings

| id | sev | finding | refs |
|---|---|---|---|
| **F1** | LOW | Commit-message counterfactual uses candle-min peak (0.54 → thr 0.380 → 58,925 = +3.80%); live PG columns give peak **0.5917 → thr 0.4142 → 58,905.00 = +4.14%** (sampled fire 58,962.49 = +3.17%). ARM-GAP's 0.52 is a third sampler (guardian `_compute_mfe_mae`, mfe_price 58844.5). Save claim holds (5.24–6.21pp); message numbers should be the live numbers. | commit msg; pm:4702-4714; hl_sync_guardian:3118-3159 |
| **F2** | LOW | UGB-PT never applied to our trades: blocked by `_is_bypassed` (signal `ai-trader` ∈ `PROFIT_MONSTER_BYPASS_SIGNALS`), **not** the trail-state check the counterfactual hypothesized. Rung can never be in trail state (PM query excludes bypass signals; single `_save_trail_state` call in `run_trail`; BE-cap writer doesn't touch it). `peakTrail@0.45%=+0.07` is informational only. Pre-existing design (FIX 2026-10-31). | pm:4650-4655; constants:2322; profit_monster:86-89, 577 |
| **F3** | LOW | >1.5% giveback hole (design): for governed ai-trader trades mfe's 30% is the ONLY giveback layer (UGB-PT/PM-trail bypass-dead, mxm trail frozen by `dynamic_sl:False`): peak 2.0 gives back 0.60% (vs fixed 0.45), peak 5.0 gives back 1.50%. Always exits ≥28bp in profit — acceptable floor, strictly better than pre-commit; flagged because the "fixed-0.45 sibling" mental model does not hold for our trades. | pm:4615-4665; constants:2274-2328; auto_trader:312 |
| **F6** | LOW | `MFE_EXIT_GIVEBACK_PCT/ARM_PCT/ENABLED` are **not** in `CEO_PROTECTED_FLAGS` (constants:3393-3411) despite the comment "CEO_PROTECTED" (constants:2178) — values unchanged today, but the protection is comment-level only. | hermes_constants:2178, 3393-3411, 2164-2166 |
| **F4** | INFO | WIN-CAPTURE shadow *code* untouched, but its reach now extends to governed trades (was unreachable when the whole block was gated off for CEO trades) — new `[WIN-CAPTURE-SHADOW]` lines for ai-trader rungs. Log-only, per-trade dedup, never closes (proved). | pm:4715-4744; H1 T5 |
| **F5** | INFO | Peak-freshness fail-open: no HL data for a cycle → peaks not refreshed (stale, non-zero → fires later); a rung that never had HL data → no fire at all. Pre-existing class, same basis as UGB-PT/ARM-BE. | pm:2946-2954, 4678 |
| **F7** | INFO | Race caveat: ATR/manual-SL hit (pm:3728) evaluates before mfe (pm:4746) in the same cycle — a bounce that jumps the 304-pt band between samples closes at the stop (bounded −1.00% margin). #17005's real series had an in-band sample → mfe wins live. | pm:3728, 4746 |
| **F8** | INFO | Effective sensitivity stated for the CEO: governed profit exits now dominated by mfe — giveback floor **12bp** (peak 0.40), fires at ≥**28bp** fav; #17005-class peaks give back ~18bp. ARM keeps micro-peaks out (0/0.1/0.39 never fire). Design per commit; numbers now exact. | pm:4697-4757; H1 T3; H3 sweep |
| **F9** | INFO | 58736 rung's note text still carries the pre-F7 mislabel ("1h MAJOR-floor break: trigger 58736 (sl1h 61320−60)" — 61320−60 ≠ 58736); backfill appended the clarification. Note-only; provenance verified: 58736 = round(price×0.997) at arm. | data/pending_orders.json (gitignored) |
| **F10** | INFO | The continuation fresh-air flag is written on ONE path (short ladder-keeper, auto_trader:855); the long keeper has no fresh-air arm today, so no asymmetry — but a future long fresh-air arm must set `entry_style` or it silently keeps the retest-wait. | auto_trader:855, 889-915 |

## 9. Overall verdict

**SHIP-CONFIRMED WITH FINDINGS (all three commits).** The new closing path (mfe_exit for
structure-governed trades) was verified on the incident's real PostgreSQL data and the real
per-cycle sample series: it arms only at peak ≥0.40%, fires only while giving back ≥30% of that
peak, first-touch strictly in profit (≥28bp), cannot fire on losers, and wins the #17005 bounce
race against BE-cap, HML, UGB-PT and every frozen trail. Units are consistent at the compare line;
the peak columns are written every cycle pre-close for ai-trader rungs; the condition change is
byte-identical for every non-(CEO & governed) path. The two entry-machine addenda preserve the
retest-wait for unflagged rungs, cannot double-fill (triggered-belt + state-write-failure drop),
keep stacking/serial/dry-run gates on the new fill paths, and leave the 80k rung out of keeper
reach. 0 HIGH / 0 MEDIUM: nothing blocks shipping; F1 (counterfactual numbers), F2/F3 (UGB sibling
reality + >1.5% giveback) and F6 (protection claim) are accuracy/design records for the CEO.
