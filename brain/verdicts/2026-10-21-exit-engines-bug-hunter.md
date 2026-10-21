# Bug Hunter Verification: New Exit Engines (RR, Pump Exit, Ride It)

**Commit:** `bff34851` — "scripts: shadow_trader — add 3 missing exit engines (RR, Pump Exit, Ride It)"
**Verified:** 2026-10-21 by bug_hunter
**Method:** code read of commit diff + full function source, live-source comparison (`position_manager.py`, `ride_it_exit.py`, `risk_reward_engine.py`, `hermes_constants.py`), real DB run (`--close` + `--report`), 32-case synthetic test suite, micro-benchmark.

## Summary

The 3 engines integrate cleanly (schema, UPDATE params, tie-break, report all verified working) and constants match the live values — but the Pump Exit trail is **inverted** (behaves as a 0.30% hard stop instead of a 3×ATR trail, proven on 19/19 real closes at exactly −0.300%), the Pump time-exit semantics are **backwards vs live**, `reclose_events()` was never updated, and the Ride-It/RR sims diverge materially from live exit logic.

## Verdict: FAIL

3 CRITICAL/HIGH defects make the new engines' shadow data unreliable for A/B decisions. Integration plumbing itself is correct. Fix findings 1–3, re-close affected rows, then re-verify.

## Constants Verification

| Constant group | Match? | Evidence |
|---|---|---|
| Pump Exit (5 consts) | ✅ Exact | shadow_trader.py:58-62 vs hermes_constants.py:4403-4407 — `3.0 / -0.5 / 2 / 2.0 / 2.0` all identical |
| Ride It (core 8) | ✅ Exact | shadow:65-72 vs hermes_constants.py:4419-4433 — `2.0 / 0.013 / 0.025 / 3.0 / 0.02 / 0.012 / -0.5 / 2` identical |
| `RIDE_IT_MAX_HOLD` | ✅ Equivalent | shadow `RIDE_IT_MAX_HOLD_MIN=1440` min (pre-existing, line 52) = live `RIDE_IT_MAX_HOLD_HOURS=24` (4438) |
| `RIDE_IT_PHASE1_TO_PHASE2_TIME` | ⚠️ Unit drift | shadow:76 = `120` **minutes**; live:4439 = `7200` **seconds**. Behaviorally both = 2h (shadow compares `hold_minutes < 120`), but the comment claims "from hermes_constants.py:4416-4439" — a mechanical constant sync would break it. |
| `ATR_SL_MIN_ACCEL` (pump accel) | ✅ Magnitude / ❌ direction | shadow:41 = `0.30` (percent, used `/100` → 0.003) vs live hermes_constants:727 = `0.003` — same 0.3%, but the clamp direction is inverted (Finding 1) |
| RR Engine approximation | ❌ Not faithful | 0.8×ATR SL / 1.6×ATR TP / 0.6×ATR trail vs live: 1.0×ATR SL **+1.5% floor/2.5% cap + structural S/R extension**, structural-break exits (PRIMARY live rule), structural/0.5×ATR trail, **no TP at all** (Rule 2 removed, risk_reward_engine.py:1323). See Finding 5. |
| Spike constants | ⚠️ Defined, unused | `RIDE_IT_SPIKE_*` (shadow:73-75) never referenced — live volume-spike override (ride_it_exit.py:320-339) not simulated |

## Simulation Logic Verification

- **Direction handling** ✅ — LONG/SHORT verified in synthetic tests (T2 pump SHORT ceiling exit at `entry×1.003`, pnl `(entry/exit−1)`; T13 rr SHORT SL above entry, correct pnl formula; ride_it phase-1 SL/TP mirror correctly).
- **Trail SL calculation** ❌ — Pump trail has the accel clamp **inverted** (Finding 1). RR trail has **no accel cap** and no floors/caps (Finding 5). Ride-It trail base slightly differs (live uses `current_price × 1.2%` distance at update time, shadow uses `peak × (1−1.2%)` — minor).
- **Momentum exit** ⚠️ — Window/indexing correct (T4: fires on exactly 2 consecutive, resets on 1 big drop, no off-by-one, guard `i ≥ 2` prevents negative indices, `prev_c > 0` guard prevents div-by-0). BUT computed on **1m candles with a 5m-calibrated −0.5% threshold** — live reads `candles_5m` (position_manager.py:2993, ride_it_exit.py:158) → systematically under-fires (Finding 6). Ride-It momentum also misses live's `profit > 1%` gate and phase-2-only restriction (Finding 4).
- **Time exit** ❌ — Shadow fires when `hold ≥ 2h AND pnl ≥ +2%` (exits winners); live fires `pump_exit_dead_money` when `profit < 2% AND hold > 2h AND velocity fading` (exits losers). Inverted + missing velocity gate (Finding 2).
- **Edge cases** ⚠️ — empty candles → `None` ✅, `atr_pct=None` → `None` ✅, single candle → no crash ✅, zero close guarded ✅, `entry_price=0` → `ZeroDivisionError` (T5g, Finding 9; 0 zero-price candles currently in candles_1m so not reachable today).

## Integration Verification

- ✅ **Engines called in `close_events()`** — shadow_trader.py:1107-1109, all 3 present after the 7 legacy engines.
- ✅ **Tie-break precedence** — `_PRECEDENCE` (1118-1129) includes `rr_engine:4, pump_exit:5, ride_it:6` inserted between `atr:3` and `speed_stale:7`; sort key = (exit_ts, precedence) unchanged. Placement is a judgment call (spec §4.0 predates these engines) and is reasonable (signal-specific engines before generic timeouts). Inline comment at 1112-1113 still lists only the old 7 — stale (Finding 10).
- ✅ **Schema columns** — `exit_pump_exit_json`, `exit_ride_it_json` added to CREATE TABLE (119-121) **and** ALTER TABLE fallback (166-180). Verified both paths: fresh DB gets columns; simulated legacy DB (columns dropped) re-adds them via ALTER. `exit_rr_engine_json` already existed (now actually written — it was schema-only before this commit).
- ✅ **UPDATE statement** — 1154-1173: 21 placeholders / 21 params, counted and matched; empirically executed on 19 real rows with all engine JSONs stored.
- ✅ **Report** — `--report` EXIT ENGINE A/B groups by `first_exit_engine`; new engines appear (`rr_engine n=6`, `pump_exit n=10` after this run).
- ❌ **`reclose_events()` NOT updated** — still simulates 7 engines, 7-engine precedence, UPDATE omits the 3 new columns (Finding 3).
- ❌ **`analyze_exit_engines` (`--analyze-exits`) NOT updated** — hardcodes 7 column names (Finding 8).

## Findings

### CRITICAL — Pump Exit accel constraint inverted: 3×ATR trail behaves as a 0.30% hard stop
- **Location**: scripts/shadow_trader.py:826 (`trailing_sl = max(trailing_sl, accel_floor)`), :835 (`min(..., accel_ceiling)`) vs live position_manager.py:2952-2954 / 2967-2969
- **Issue**: Live does `if new_sl > floor: new_sl = floor` → SL capped so it can never be **tighter** than 0.3% from entry (trail stays wide). Shadow does `max(trail, floor)` → SL forced to be **at least** as tight as 0.3% from entry on candle 0. Exact opposite clamp.
- **Impact**: With any `atr_pct > 0.1` (3×ATR trail wider than 0.3%), the effective SL is `entry×0.997` immediately. **Evidence (real data, this run): 19/19 `pump_exit_trail` exits landed at exactly −0.299/−0.300%, at 1–21 minutes**, regardless of atr_pct (0.66–1.9). Synthetic T1/T2 reproduce it. Because tie-break sorts by `exit_ts` first, pump_exit now claims first-exit on the majority of fresh closes (10 of 19 rows) with a tiny loss, masking momentum/time exits and masking `ride_it` (which fired +3.18% at 169m but lost every tie to pump's 21m). The EXIT ENGINE A/B report will wrongly show pump_exit as a 0%-WR engine and distort every downstream gate/attribution analysis.
- **Fix**: Mirror live clamp: LONG → `trailing_sl = min(trailing_sl, entry_price * (1 - ATR_SL_MIN_ACCEL/100))`; SHORT → `trailing_sl = max(trailing_sl, entry_price * (1 + ATR_SL_MIN_ACCEL/100))`. Note live also starts from the position's initial `current_sl` (`new_sl = max(current_sl, trailing_sl)`) — the shadow sim has no initial-SL concept for pump, so the fixed trail will start at `peak − 3×ATR` (wider than live's initial SL); acceptable approximation, but document it. After fix, re-close rows where `exit_pump_exit_json` shows a −0.300% trail.

### HIGH — Pump time-exit semantics inverted vs live `pump_exit_dead_money`
- **Location**: scripts/shadow_trader.py:866 vs position_manager.py:3053-3063
- **Issue**: Shadow: `hold ≥ 2h AND pnl ≥ +2%` → exits **winners** (verified T3: fires `pump_exit_time` at +3.6%). Live: `profit < 2% AND hold > 2h AND vel_fading` → exits **losers** as `pump_exit_dead_money`. The polarity of the profit test is opposite, the velocity-fade gate is missing, and the exit label differs (`pump_exit_time` vs `pump_exit_dead_money`).
- **Impact**: Shadow records profit-taking exits the live system never takes, and never records the dead-money exits the live system does take. Engine-name mapping also breaks: report shows `pump_exit_time` which doesn't exist live.
- **Fix**: Invert the condition to `current_pnl < PUMP_EXIT_TIME_THRESHOLD and hold_hours > PUMP_EXIT_TIME_HOURS`, add the velocity-fade check (compare last two closes, direction-aware), and emit `pump_exit_dead_money` as exit_type to match the live canonical label.

### HIGH — `reclose_events()` not updated for the new engines (inconsistent attribution)
- **Location**: scripts/shadow_trader.py:1442-1481 (7 engines at 1444-1450, 7-engine `_PRECEDENCE` at 1453-1457, UPDATE at 1466-1481 missing `exit_rr_engine_json`/`exit_pump_exit_json`/`exit_ride_it_json`)
- **Issue**: `--reclose` re-simulates only the legacy 7 engines and overwrites `first_exit_engine`/pnl.
- **Impact**: A row first closed by `close_events()` with e.g. `first_exit_engine='ride_it'` (and populated new-engine JSONs) gets re-closed with a 7-engine-only result: `first_exit_engine` then contradicts the stored `exit_ride_it_json.fired=true` with an earlier `exit_ts`. Silent data corruption of the A/B key column for any row matching the reclose criteria (`universal_hold` with hold <480m, or `unclosed_no_candles`, last 7 days).
- **Fix**: Add the 3 engine calls, the 3 precedence entries (4/5/6 with the rest shifted), and the 3 new columns to the UPDATE — keep the two code paths identical (or factor one `simulate_engines()` helper used by both).

### HIGH — Ride It: phase-1 fall-through, missing profit gate, missing volume-spike override
- **Location**: scripts/shadow_trader.py:913-931 (phase-1 block has no `else`/`return` — trail at 934, momentum at 953-973 run inside phase 1), no profit gate before 968, RIDE_IT_SPIKE_* (73-75) unused
- **Issue**: Live phase 1 (ride_it_exit.py:347-369) does **only** SL management and returns; momentum is phase-2-only (`hold ≥ 2h`, ride_it_exit.py:348/371) **and gated on `profit > 1%`** (:383); the volume-spike override (tight 0.5% trail on vol>5× + move>3%) runs in any phase (:320-339).
- **Impact**: Verified synthetically: T6 → `ride_it_momentum` fires at hold=6m **at a loss** (live: HOLD); T7 → fires at −1.20% in phase 2 (live: profit gate → HOLD); T10 → `ride_it_trail` fires at hold=61m inside phase 1 (live: no trailing until 2h). The sim systematically over-fires ride_it exits and can never reproduce spike-mode exits.
- **Fix**: Wrap trail/momentum in `if hold_minutes >= RIDE_IT_PHASE1_TO_PHASE2_TIME:` (phase 2 only), add `current_pnl > 1.0` gate on momentum, and either implement spike mode (needs volume — `_load_candles_window` doesn't select volume) or add an explicit `spike_override: 'not_simulated'` note in the JSON.

### HIGH — RR engine is a different engine, not a simplified version of `risk_reward_engine.py`
- **Location**: scripts/shadow_trader.py:1008-1009 (0.8×ATR SL, 1.6×ATR TP), 1015-1017 (0.6×ATR trail), vs risk_reward_engine.py:594-606 (1.0×ATR + floor `min(1.5%, 2×ATR)` + cap 2.5% + structural extension), 1265-1321 (structural support/resistance break = live PRIMARY exit), 1323 (Rule 2 TP **REMOVED** from live), 1331-1357 (structural trail w/ 0.5×ATR fallback + accel cap at entry±0.3%)
- **Issue**: Shadow adds a fixed 1.6×ATR TP (`rr_tp_hit`, verified T12) that live explicitly removed; omits structural-break exits entirely (live's main rule — `rr_engine_support_break`/`resistance_break`); omits the ATR_SL_MIN/MAX floor+cap (T14: shadow stops at −0.24% on a 0.4% ATR token where live's floor = 0.8% would hold); omits the entry±0.3% accel cap (T11: shadow exits at −0.202% where live caps the trail at −0.3% → no exit); no liquidation-zone exit (Rule 4).
- **Impact**: `rr_engine` results (2621 signals are routed to `rr_engine` in live!) do not represent live RR behavior in either direction — early noise stops on low-ATR tokens, fictitious TP wins, no structural-break cuts. Spec §4.9 itself flagged this as "a multi-hour sub-project — scope separately"; the commit's approximation is much shallower than that warning.
- **Fix**: Minimum for credible shadow data: apply live's floors/caps (`sl_pct = min(max(atr_pct×1.0, floor), 2.5)` with `floor = min(1.5, 2×atr_pct)`), accel cap `min/max` at entry×0.997/1.003 on the trail, drop or clearly label `rr_tp_hit` as `rr_tp_simulated_not_live`, and add a `structural_break` approximation (swing highs/lows from the same 1m candles) or document its absence in the JSON (`structural_break: 'not_simulated'`).

### MEDIUM — Momentum thresholds calibrated for 5m, applied to 1m candles
- **Location**: scripts/shadow_trader.py:843-857, 953-973 (both momentum blocks) + `_load_candles_window` :183-194 (candles_1m)
- **Issue**: Live reads `candles_5m` for both pump momentum (position_manager.py:2993-3001) and ride-it candle counts (ride_it_exit.py:158-166). The −0.5% velocity threshold is a per-**5m**-candle number.
- **Impact**: A −0.5% 1-minute drop is far rarer than a −0.5% 5-minute drop → shadow momentum exits systematically under-fire (and earliest possible fire is 2m vs live's ≥10m). Partially masked right now by Finding 1 (trail kills trades first).
- **Fix**: Either re-aggregate closes to 5m buckets inside the momentum checks (5 closes → 4 velocities) or rescale the threshold for 1m. Prefer 5m aggregation — keeps constants byte-identical to live.

### MEDIUM — New signal-specific engines run on ALL signals, ignoring `SIGNAL_EXIT_CONFIG` routing
- **Location**: scripts/shadow_trader.py:1107-1109 (no routing gate) vs spec §5 ("simulate ALL applicable exit engines (based on SIGNAL_EXIT_CONFIG routing)"); `exit_config` is stored at record time (:444) but unused at close time
- **Issue**: Live only runs pump_exit for `pump_chain+`-routed signals, ride_it for its routed set, rr_engine for its set. Shadow applies all 3 universally.
- **Impact**: `first_exit_engine` attributes engines to trades that would never have used them: in this run 10/19 first-exits = `pump_exit`, including `ichimoku+` and `volume-buildup-` trades (live default path / rr / ride_it respectively), and rows with `exit_config='atr'`. Cross-signal A/B pollution.
- **Fix**: Gate the 3 new engines (or at least their tie-break candidacy) on `exit_config` matching the engine — the column already exists. Keep them in the JSONs (`fired` recorded, `applied: false`) so counterfactual analysis remains possible.

### MEDIUM — Multi-part signals mis-routed by `_match_exit_config_safe`
- **Location**: scripts/shadow_trader.py:270-274 (passes the whole comma-joined source) vs position_manager.py:2891-2895 (splits `signal_parts` first)
- **Issue**: `_match_exit_config` expects ONE part. For `source='pump-chain+,pump-chain-v6+'` the whole string matches no key → returns None → labeled `'atr'`.
- **Impact**: **599/599 multi-part rows in the DB are labeled `exit_config='atr'`** (verified by SQL), even when a part routes to pump_exit/ride_it/rr_engine. Pre-existing, but now load-bearing — it must be fixed before using `exit_config` to gate the new engines (Finding 7's fix depends on it).
- **Fix**: `for part in str(source).split(','): cfg = _match_exit_config(part.strip())\n if cfg: return cfg` — same loop live uses; fall back to `'atr'` only if no part matches.

### MEDIUM — `--analyze-exits` still queries only the 7 legacy columns
- **Location**: scripts/shadow_trader.py:1611-1614, 1619-1623, 1634 (`engine_names` list of 7)
- **Issue**: The dedicated exit-engine comparison mode does not read `exit_rr_engine_json`, `exit_pump_exit_json`, `exit_ride_it_json`.
- **Impact**: `--analyze-exits` silently omits the 3 new engines — reports will disagree with `--report`'s A/B section.
- **Fix**: Add the 3 columns + names to both SELECTs and `engine_names`.

### LOW — `entry_price=0` crashes the whole `--close` run
- **Location**: scripts/shadow_trader.py:866 (pump time-exit divides by `entry_price` on **every** candle), :905-906 (ride_it), :1016+ (rr when `tp_price=0`); no per-trade try/except around the simulation block (:1079-1187)
- **Issue**: Verified T5g: `_simulate_pump_exit(0, ...)` → `ZeroDivisionError`. The trade loop only guards the `created_at` parse; an exception in any engine propagates, `conn.commit()` (:1189) never runs → the entire close batch rolls back and `--close` dies.
- **Impact**: Not currently reachable — SQL check on `candles_1m`: **0 rows with open≤0 or close≤0** out of 7,056,218. One dirty candle row later = full close outage.
- **Fix**: Guard `if not entry_price or entry_price <= 0: skip` at the top of the per-trade block, and/or wrap each trade body in try/except with `continue` + log (per AGENTS.md "add debug/audit output, don't ignore errors").

### LOW — Stale "7 engines" references after the 10-engine change
- **Location**: scripts/shadow_trader.py:13 (module docstring), :1061 (`close_events` docstring), :1924 (`--close` help), :1112-1113 (tie-break comment lists only the old order)
- **Issue**: All say 7 / list only legacy engines.
- **Impact**: Cosmetic/maintenance confusion; next reader may "fix" the missing engines again.
- **Fix**: Update all four to 10 and list the new precedence.

### LOW — `rr_engine` exit_type mislabels trail-caused exits as `rr_sl_hit`
- **Location**: scripts/shadow_trader.py:~1018 (`exit_type = 'rr_trail_hit' if sl_price > entry_price else 'rr_sl_hit'`)
- **Issue**: The label only distinguishes trail vs initial when the SL is above entry (in profit). Any trail-locked exit below entry is reported `rr_sl_hit` (real example: ETH rows, −0.047% at 24m, trail-raised SL).
- **Impact**: `first_exit_reason` GROUP BYs conflate "initial stop hit" with "trail tightened then hit" — loses the distinction the A/B wants.
- **Fix**: Track whether the trail ratchet raised the SL (`sl_price > initial_sl`) and label `rr_trail_hit`/`rr_sl_hit` from that.

### INFO (sideways find) — live pump-exit accel clamp may itself be wrong — DO NOT change without T
- **Location**: position_manager.py:2952-2954 (and risk_reward_engine.py:1354-1357): `_accel_floor = entry × (1 − 0.003)` then clamp DOWN every cycle
- **Issue**: As written, live's pump trail can never raise the SL above `entry×0.997` — i.e., the live pump trail **never locks profit beyond −0.30%**, while `hermes_constants.py:727` says "0.30% floor — allow trailing to lock in profits". The shadow's *other* engines model this floor relative to **peak** (e.g., `_simulate_atr_sl_tp` :522), which does lock profit.
- **Impact**: If the constants comment reflects intent, live is losing profit-lock on pump trades. If the clamp reflects intent, the comment is wrong. Either way the shadow must mirror whatever live actually does (Finding 1 fix mirrors the code).
- **Action**: Flagged for T per AGENTS.md — hermes_constants/position_manager changes require explicit instruction.

## Verified Working

- `git show bff34851` diff read in full (310 insertions, 1 file); code matches commit claims on what was added (10 engines — count confirmed)
- Constants: all 5 Pump Exit + 8 core Ride It values byte-match hermes_constants.py:4403-4439
- `python3 scripts/shadow_trader.py --close` → `close: 19 pending, 19 closed`, no errors, second run `0 pending`; **0.075s** wall for 19 trades
- `python3 scripts/shadow_trader.py --report` → EXIT ENGINE A/B renders; new engines present (`rr_engine n=6`, `pump_exit n=10`); ride_it will appear when it wins a tie
- Schema: fresh-DB CREATE path has all 3 columns; simulated legacy DB (columns dropped) re-adds both via ALTER path — verified by execution
- UPDATE statement: 21 placeholders = 21 params (counted); empirically wrote all 10 engine JSONs on 19 rows
- Tie-break: all 10 engines in `_PRECEDENCE`; multi-fire JSONs recorded for non-winning engines (`fired:true` visible for all 3 new engines on closed rows); observed ordering consistent with (exit_ts, precedence)
- Synthetic suite: `brain/verdicts/exit_engines_synthetic_test_2026-10-21.py` → **31/32 as designed** (the 1 failure is Finding 9's real ZeroDivisionError) — covers direction (LONG+SHORT), trail, momentum window/reset, time exit, phase 1/2, SL floor/cap (1.3%/2.5%), TP, max hold 1440m, empty/None/single-candle edges
- Performance: pump 0.93 ms, ride_it 0.80 ms, rr 0.39 ms per call on 1440 candles → +2.1 ms/trade (~2.1s per 1000 trades) — negligible; memory unchanged (candles loaded once, linear single-pass loops)
- No division-by-zero in production data: 0 zero-price rows in 7,056,218 candles_1m rows

## Recommendations

1. **Fix Finding 1 (inverted accel clamp) first** — it invalidates every `pump_exit` row closed since `bff34851` and poisons `first_exit_engine` attribution via earliest-ts-wins. After the fix, re-close: `UPDATE shadow_trades SET closed=0 WHERE exit_pump_exit_json LIKE '%-0.3%'` (or simply reopen rows whose `first_exit_reason='pump_exit_trail'` with `first_exit_pnl_pct≈-0.3`), then `--close` + `--reclose`.
2. Fix Finding 2 (time-exit polarity + velocity gate + canonical `pump_exit_dead_money` label) in the same pass — both are one-line-level changes in `_simulate_pump_exit`.
3. Fix Finding 3 (`reclose_events`) **before the next `--reclose` run** — every re-close silently reverts a row to the 7-engine world. Factor a shared `simulate_engines(entry_price, d, candles, atr_pct, ...) → results, precedence` used by both paths so they can never diverge again.
4. Decide scope for Ride It/RR fidelity (Findings 4-5): minimum viable = phase gating + momentum profit gate for ride_it; floors/caps/accel cap + drop-or-label TP for rr. Structural-break simulation can stay explicitly out-of-scope **if** the JSON says `structural_break: 'not_simulated'` so downstream analysis doesn't treat RR results as live-faithful.
5. Gate the 3 engines on `exit_config` (Finding 7) — but fix the multi-part routing bug (Finding 8) first, or 599 existing multi-part rows gate on the wrong label.
6. Update stale 7-engine references (Finding 10) and the spec: `plans/shadow-mode-paper-trading-spec-v1.md` §4.0 Engine Roster + Tie-Break Rule still say "7 engines / RR+pump+ride ❌ v2" — the roster, precedence table, and §4.9 should record what was actually shipped and its known fidelity gaps.
7. Guard `entry_price <= 0` per trade (Finding 9) — cheap insurance for the whole close path, not just the new engines.
8. Store this session's results in OpenMemory (`shadow_trader exit engines bug_hunter FAIL — pump trail inverted, time exit inverted, reclose stale`) so the next session doesn't re-derive them.
