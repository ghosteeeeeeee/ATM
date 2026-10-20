# Own Conclusions: Shadow-Mode Paper Trading Spec v1.2 — Independent Validation

**Auditor:** Independent (own-conclusions, fresh eyes)
**Date:** 2026-10-20
**File audited:** `/root/.hermes/plans/shadow-mode-paper-trading-spec-v1.md` (1061 lines, labeled v1.2)
**Method:** Read spec from scratch; verified every constant, function, and table claim against live code by reading the actual files and running Python against the live DBs. All numbers below come from commands executed during this audit.

## Summary

The spec is directionally sound and most of its v1.2 corrections (HML formula, PM trail tiers, trail-arm timeout, stale thresholds, A/B engine facts) verify as accurate against live code. However it contains several factual errors (ATR_SL_MAX value, ATR source interval, PM T1/T2 constants, cut-loser partial-close model, velocity threshold, leverage sourcing), one broken SQL index, and two significant design gaps: `pump_exit`/`ride_it` — the two routed engine families promised in §4.0 — have **no simulation logic defined anywhere**, and the gate-name backfill design cannot attribute the actual blocking gates (they never reach `signals.decision_reason`).

## Verdict: APPROVE WITH CHANGES

---

## Spec Completeness

### Process EVERY signal fire as a simulated live trade — COVERED
- **Evidence:** §2/§5 Phase 1 record ALL signals, not just EXPIRED/SKIPPED. Current `expiry_shadow.py:77` filters `decision IN ('EXPIRED','SKIPPED')` — the extension direction is correct. Measured: 997 signals in last 24h, 5,643 in 7d (~806/day) in `signals_hermes_runtime.db` — the "~1000/day" claim is accurate. Signals table has all columns Phase 2 claims (`z_score`, `z_score_tier`, `momentum_state`, `rsi_14`, `macd_value/signal/hist`, `leverage`, `price`, `signal_metadata` — all verified present).

### Set TP/SL according to the exit engine that would manage it — PARTIALLY COVERED
- **Evidence:** §4 defines 7 engines (ATR, PM Trail, HML, Cut Loser, Speed Stale, Universal Max Hold, Trail Arm Timeout) and defers RR engine to v2 (reasonable — `risk_reward_engine.py` structural S/R confirmed at the cited lines 608-638). **BUT §4.0 explicitly promises "v1 scope: Simulate `atr`, `pump_exit`, `ride_it` engines" and neither `pump_exit` nor `ride_it` has any simulation logic anywhere in Section 4.** These are real, live, distinct exit engines: pump-exit at `position_manager.py:2864` (ATR trailing + momentum + time, constants `PUMP_EXIT_TRAIL_MULT/MOMENTUM_VEL/MOMENTUM_CANDLES/TIME_THRESHOLD/TIME_HOURS`) and ride-it at `position_manager.py:3042` (`ride_it_exit.manage_ride_it_exit`, 2-phase + volume-spike override, 24h max hold). They govern the biggest signal classes (pump-chain+ LONG, mover-, volume-breakout, trend-ride). The schema also has no `exit_pump_exit_json` / `exit_ride_it_json` columns, and Phase 1's 7-engine list omits them. This contradicts the spec's own §4.0 scope statement.

### Collect all context data (regime, volatility, trend, RSI, etc.) — COVERED
- **Evidence:** §3.2 context JSON schema is comprehensive and every claimed source field was verified to exist in the signals table. Phase 2 correctly distinguishes free (already-stored) vs computed-at-record context and stores `context_computed_at` for drift measurement.

### Run A/B tests on exit engines — COVERED
- **Evidence:** §5 Phase 3 + §10.5. All existing A/B engine facts verified: epsilon-greedy with `EPSILON = 0.15` (`ab_optimizer.py:46`), Thompson sampling via `random.betavariate(wins+1, losses+1)` (`hermes_ab_utils.py:105`), evolution kill at `PNL_KILL = -15.0` (`ab_optimizer.py:45`) + spawn logic (line 256+), W&B offline (`mode='offline'`, `hermes_ab_utils.py:23`), `ab_results` = exactly 5 rows all-zero/stale (queried live PostgreSQL), `ab_tests.json` = `{"tests": []}` (empty), unique index `idx_ab_results_test_variant (test_name, variant_id)` exists so the spec's `ON CONFLICT` works. Usage by `decider_run.py` and `hl-sync-guardian.py` confirmed. One risk (see New Findings): writing shadow aggregates into the live `ab_results` table.

### Answer gate justification questions — PARTIALLY COVERED
- **Evidence:** The Appendix C gate names are real — all found in `pipeline.log` (e.g. CONFLUENCE-GATE-BLOCK 6,535 hits; SHORT-RSI-HARD-FLOOR 4,792; CONTINUUM-BLOCK 5,046; RR-ENGINE 17,011 over the log's 10-day window). **However, the spec's attribution mechanism is broken:** gate blocks are logged to pipeline.log (that's what `gate_shadow.py` parses), NOT written to `signals.decision_reason`. Measured on the live signals DB: of 999 signals in 24h, 985 have `decision_reason='compaction_stale_10min'`, and all-time there are only **7 SKIPPED + 1 FAILED rows** in the entire table. The spec's backfill-from-decision_reason (Appendix C) will therefore label ~99% of rows `CONFLUENCE-EXPIRY` and `UNKNOWN` for every execution-time gate — the "Gate X blocked 100, 45 would have won" report will only work for the confluence gate. The fix is to reuse `gate_shadow.py`'s existing pipeline.log parsing (which already attributes per-gate blocks), not to reinvent a weaker decision_reason parser.

### Cost nothing (no money at stake) — COVERED
- **Evidence:** §2 architecture is read-only over signals + candles DBs, writes to its own `brain/shadow_trades.db`. Freeze-safe by construction, consistent with existing shadow systems' design pattern.

### Get enough data to fine-tune everything — PARTIALLY COVERED
- **Evidence:** ~1000 outcomes/day verified feasible (997 signals/24h; 20.4M 1m-candles in `candles.db`, 185 tokens, PK `(token, ts)` confirmed — windowed reads are cheap as §6.4 claims). **But** the one-shot close at ">4.5h old" (§2, inherited from `expiry_shadow.CLOSE_AFTER_HOURS = 4.5`) cannot produce final outcomes for engines that fire at 8h (Universal Max Hold) or 24h (ride_it) on recent signals, and no re-close/update pass is defined — see New Findings.

---

## Technical Accuracy

### Appendix B: Exit Engine Constants — PARTIALLY CORRECT
- **Evidence (correct):** Every cited line number checked and matches: `CUT_LOSER_PNL = -4.00` (hermes_constants:717) ✓, `HML_VOL_ATR_MULT = 0.5` (718) ✓, `TRAILING_ACTIVATION_PCT = 0.0040` (727) ✓, `TRAILING_DISTANCE_PCT = 0.0120` (728) ✓, `PM_TRAIL_ACTIVATE_PCT = 0.004` (1659) ✓, `PM_TRAIL_TIERS` [(0,0.2%),(1.5%,0.5%),(3%,0.8%),(5%,1.2%)] (1732-1737) ✓, `PM_TRAIL_MIN_HOLD = 2` (1738) ✓, `UNIVERSAL_MAX_HOLD_MINUTES = 480` (1132) ✓, `STALE_WINNER_TIMEOUT_MINUTES = 120` / `STALE_LOSER_TIMEOUT_MINUTES = 8` / `STALE_WINNER_MIN_PROFIT = 0.6` / `STALE_LOSER_MAX_LOSS = -1.0` (hermes_constants:564-567, used at position_manager:612-637) ✓, `BB_SQUEEZE_TRAIL_ARM_TIMEOUT_MIN = 60` / `PUMP_CHAIN_TRAIL_ARM_TIMEOUT_MIN = 45` (1671/1682) ✓, `MAX_LEVERAGE = 5` (position_manager:157) ✓.
- **Evidence (errors):**
  - `ATR_SL_MAX = 5.0% (cap)` — **WRONG. Actual `ATR_SL_MAX = 0.025` = 2.5%** (hermes_constants:696); `ATR_SL_MAX_INIT = 2.5%` (712).
  - `ATR_PERIOD = 14 (on 1h candles) @ volatility_gate_v2.py:520` — that is the **volatility gate's** ATR (verified: `candles_1h` query at volatility_gate_v2:488-520). The ATR SL/TP **engine** uses `get_fresh_atr` = **15m primary, 1h fallback** (`tpsl_utils.py:51,172-175`, via `atr_cache`). Simulating the engine with 1h ATR will produce different SL/TP distances than live.
  - `RIDE_IT_MAX_HOLD_MINUTES = 1440 @ position_manager.py:3448` — **wrong name and location.** Actual: `RIDE_IT_MAX_HOLD_HOURS = 24` (hermes_constants:4307), enforced in `ride_it_exit.py:342`. position_manager:3448 is only the ride_it *exemption* check for universal max hold (substring match on 'ride_it'/'trend-ride'/'volume-breakout'/'mover-' etc.).
  - `ATR_SL_MIN_INIT`/`ATR_SL_MIN_ACCEL` attributed to `tpsl_utils.py` — they're defined in hermes_constants.py:711/705 (imported by tpsl_utils). Minor.
  - `TRAILING_DISTANCE_PCT` is 0.0120 (fraction) in code but the spec's pseudocode divides it by 100 as if it were 1.20 — a literal implementer importing the constant would be off by 100×.

### Section 4.0: SIGNAL_EXIT_CONFIG routing — INCORRECT
- **Evidence:** The dict exists at hermes_constants:1832 ✓ and `'pump-chain+': 'pump_exit'`, `'mover-': 'ride_it'`, `'volume-breakout+': 'ride_it'`, `'trend-ride+': 'ride_it'` all verified ✓. But:
  1. **The default is wrong.** `_match_exit_config` (`position_manager.py:55`) returns **`None`** on no match — it never defaults to `'atr'`. The spec's simplified matcher (`rstrip('+-')` then default `'atr'`) also diverges from the real version/stem matcher: e.g. `'pump-chain-v5'` → real code: `pump_exit` (via version-stripped stem match), spec pseudocode: `'atr'`.
  2. **The "routes each signal to exactly one engine" framing is architecturally false.** `_collect_atr_updates` (position_manager:1969) applies `compute_atr_sl_tp` to **ALL** open positions regardless of exit config; pump_exit/ride_it/rr_engine are *additional* exit layers on top, and the protective cascade (HML, cut_loser, speed stale, universal hold) applies to everything. The routing selects an extra family — it does not replace the ATR engine. The spec's independent-engine-race simulation model happens to match this reality, but the written routing model would mislead an implementer into simulating only one engine per signal.

### Section 4.1: ATR SL/TP engine — PARTIALLY CORRECT
- **Evidence (correct):** The headline correction is right — the live engine continuously trails SL from peak at `TRAILING_DISTANCE_PCT` (1.20%), tighten-only, with one-way gate (`tpsl_utils.py:567-620`), INIT floor 1.5% / in-loss floor 1.5% / ACCEL floor 0.30% ✓, EXTREME widens ×1.2 ✓, profitable trail exits labeled `atr_trail_hit` (position_manager:565) ✓.
- **Evidence (errors):** ATR_SL_MAX is 2.5% not 5.0% (above). ATR source is 15m-primary not 1h (above). The formula `sl = atr × get_sl_multiplier_v2(atr_pct, signal_type)` is **not the engine's formula** — `get_sl_multiplier_v2` exists (volatility_gate_v2:832) but is used by signal_compactor/decider, not by `compute_atr_sl_tp`. The real engine computes `sl_pct = k × atr_pct` where k comes from `_atr_sl_k_scaled` (phase/momentum/speed-percentile scaled) or `_atr_tier` for new trades, then a **confidence-grade R:R override** (RR_K_GRADE_A..D, tpsl_utils:449-460), plus lifecycle-role adjustments (×1.5/×2.0 early, ×0.8 lagging). Also the spec models TP as static from entry — live TP also trails from peak (tighten-only, tpsl_utils docstring + code). A faithful sim is materially more complex than §4.1 pseudocode.

### Section 4.2: PM Trail — MOSTLY CORRECT
- **Evidence:** Tiered distances ✓ (0.20/0.50/0.80/1.20% by peak profit bands 1.5/3/5%), activation 0.40% (documented intent) ✓, spider override values ✓ (`SPIDER_TRAIL_ACTIVATE_PCT=0.003`, spider tiers 0.10/0.30/0.50%, hermes_constants:1817-1818, profit_monster:497), bypass list = `PROFIT_MONSTER_BYPASS_SIGNALS` with **exactly 40 families** ✓ (verified programmatically; includes pump-chain, atr-spike, ai-trader, hh-hl, continuum-osc as claimed) — applied via SQL NOT-LIKE in `get_all_open_positions` so bypassed signals never reach the trail ✓. Min-hold 2 ✓ (profit_monster:429 `now - activated_at < PM_TRAIL_MIN_HOLD*60`).
- **Evidence (gaps/errors):** Spider regime source is the **5m aggregate regime** (`/var/www/hermes/data/regime_5m.json`, profit_monster:60-67), not `regime_4h` as the spec pseudocode says. `PM_TRAIL_MIN_HOLD` also gates *activation* (position held ≥2min since open, profit_monster:462) — spec captures only the post-activation half. A second bypass list `PM_TRAIL_BYPASS_SIGNALS = ('slow-grind','slow-grind+')` (trail-only bypass, still gets T1/T2) is not mentioned. **New finding below: likely live unit bug in activation** — spec must decide which behavior to shadow.

### Section 4.3: Hard Max Loss — CORRECT
- **Evidence:** Verified numerically by simulating the live code path (`position_manager.py:3551-3590`): with `HML_VOL_ATR_MULT=0.5`, the Oct-10 cap (`if _hml_vol_floor < _hml_account_cap: _hml_vol_floor = _hml_account_cap`) means the ATR branch can only equal, never exceed, `CUT_LOSER_PNL/lev` — **HML == -4.00/lev for every (ATR, lev) combination tested (9 ATRs × 4 leverages, all equal)**. The spec's "ATR branch is dead code" claim is CONFIRMED. Unit test `-4.00/5 == -0.80` ✓.
- **Evidence (error):** Leverage sourcing is wrong. Live code: `_hml_lev = max(float(pos.get('leverage') or 1), 1.0)` — position leverage, no cap in HML. Spec: `min(signals.leverage or 5, MAX_LEVERAGE=5)`. Measured on live trades (14d): leverage 5 (191 trades), **3 (125)**, 10 (9), 40 (1) — execution leverage is per-token (`token_intel.max_leverage` registry), not a global 5. A fixed-lev-5 sim gives HML=-0.80% where live at lev 3 is -1.33% and at lev 10 is -0.40% — the sim would systematically mis-time HML exits for a large share of trades. (Also: `signals.leverage` is NULL in 7,665/7,669 rows — it doesn't "default to 10".)

### Section 4.4: PM T1/T2 Tier Exits — INCORRECT
- **Evidence:** No constants `PM_T1_EXIT_PCT`/`PM_T2_EXIT_PCT` exist anywhere. Real system (`profit_monster.py:535-557` is the run() orchestrator, not the logic): `run_tier("tier1", PM_TIER1_MIN_PCT=0.65, PM_TIER1_MAX_PCT=2.0, PM_TIER1_MAX_CLOSE=2, PM_TIER1_SKIP_TOP_PCT=20, ...)` and `run_tier("tier2", 2.0, 5.0, 1, 0, ...)` (hermes_constants:1641-1652). So T1 = close when pnl in **0.65–2.0%** (skip top-20% runners, max 2/wake), T2 = **2.0–5.0%** (max 1/wake) — not "take 50% at +1.5% / 25% at +3.0%". Closes are full position closes, not the spec's partial-exit model. T1/T2 is also absent from Phase 1's engine list and has no `exit_*_json` schema column — §4.4 is documented but not implementable from this spec.

### Section 4.5: Cut Loser — PARTIALLY CORRECT
- **Evidence (correct):** Band edges -1.0 / -2.5 / -3.0 ✓ (CL_TIER1_MAX_PCT=-1.00, CL_TIER1_MIN_PCT=-2.5, CL_TIER2_MAX=-2.5, CL_TIER2_MIN=-3.0, hermes_constants:1965-1973 — note MIN/MAX naming is inverted vs the spec's intuition, but the spec's bands land in the right places).
- **Evidence (errors):** Live `close_position` (`cut_loser.py:166`) closes the **entire position** via `hl_close(token)` — there is no "cut 50% then remainder" partial-close anywhere. The spec invented the 50%/50% model. Also the `CL_TRAIL` trailing-loss tier (`cut_loser.py:478+`, activates at -0.30%, tracks worst, cuts on recovery bounce) is mentioned in prose but absent from the pseudocode and Phase 1 engine list.

### Section 4.6: Speed Stale Exit — PARTIALLY CORRECT
- **Evidence (correct):** Thresholds match: loser = pnl ≤ -1.0% + stalled ≥8min, winner = pnl ≥ +0.6% + stalled ≥120min (`position_manager.py:612-640` using STALE_* constants) ✓. `SPEED_PERCENTILE_STALL = 33` ✓ (SPEED_STALL_THRESHOLD=33).
- **Evidence (errors):** `VELOCITY_STALL_THRESHOLD = 0.001` is wrong — live is `VEL_STALE_THRESHOLD_PCT = 0.05` (% per candle, hermes_constants:559). More importantly, live stall = **`speed_percentile < 33` AND `|vel_5m| < threshold`** computed by SpeedTracker across pipeline runs; the spec's pseudocode drops the percentile conjunct entirely and replaces it with ad-hoc per-candle price-move tracking. Without the percentile check the sim will over-fire stale exits.

### Section 4.7: Universal Max Hold — CORRECT (citation aside)
- **Evidence:** `UNIVERSAL_MAX_HOLD_MINUTES = 480` ✓ with ride_it exemption ✓ (`position_manager.py:3453-3475`, substring match incl. 'mover-' fix). The 24h ride_it hold exists but lives in `ride_it_exit.py:342` (see Appendix B errors). Note the live check uses trade `open_time`; the sim's entry convention (signal ts) is a fine approximation given §6.6's honest disclaimer.

### Section 4.8: Trail Arm Timeout — CORRECT
- **Evidence:** LONG-only ✓, bb-squeeze 60min ✓, pump-chain 45min ✓, fires when age ≥ timeout AND `live_pnl < PM_TRAIL_ACTIVATE_PCT*100` (0.40%) i.e. trail never armed (`position_manager.py:3599-3633`). Enable flags `BB_SQUEEZE_TRAIL_ARM_TIMEOUT_ENABLED` / `PUMP_CHAIN_TRAIL_ARM_TIMEOUT_ENABLED` exist and are True (omitted from spec, harmless).

### Section 10.5: A/B engine integration — CORRECT
- **Evidence:** All claims verified (see Completeness §A/B above). `ab_results` schema matches the spec's INSERT columns exactly; unique `(test_name, variant_id)` confirmed so `ON CONFLICT` is valid.

---

## New Findings

1. **BROKEN SQL in schema (§3.1):** `CREATE INDEX idx_shadow_best_exit ON shadow_trades(best_exit_engine)` (line 163) references `best_exit_engine`, but the column was renamed to `first_exit_engine` (line 123: "renamed from best_exit_engine per validation"). This CREATE INDEX will fail with "no such column" — the validation renamed the column but not the index. Definite bug.

2. **Probable live unit bug the spec must not paper over:** `profit_monster.run_trail` activates with `if pnl >= PM_TRAIL_ACTIVATE_PCT` where `pnl` is in **percent** (compute_live_pnl returns e.g. 1.5 = 1.5%) and `PM_TRAIL_ACTIVATE_PCT = 0.004` — i.e. live activation appears to trigger at **+0.004%**, not the documented +0.40%. The spider path explicitly converts (`PM_TRAIL_ACTIVATE_PCT = SPIDER_TRAIL_ACTIVATE_PCT * 100` → 0.3), and position_manager's trail-arm timeout converts with `*100  # 0.004 → 0.40%` — confirming percent is the intended unit. The spec simulates activation at +0.40%. If live really arms at +0.004%, shadow and live will diverge on every PM trail trade. **Verify before building; the shadow should log both interpretations until resolved.**

3. **Slow-engine truncation gap:** Shadow closes signals at >4.5h (inherited `CLOSE_AFTER_HOURS`), but Universal Max Hold exits at 8h and ride_it at 24h. Forward replay can only use candles that exist — recent signals can never reach those exits, no re-close/update pass is defined, and the §9 "data completeness >95% (`first_exit_engine IS NOT NULL`)" metric will systematically fail while biasing the A/B toward fast engines. Define: close only engines whose horizon has elapsed, plus a daily re-close pass that updates still-open sims.

4. **Gate attribution design fails for every gate except confluence:** measured 24h in signals DB — 985/999 rows have `decision_reason='compaction_stale_10min'`; all-time SKIPPED=7, FAILED=1. Execution gates (RSI floor, continuum, pump-chain-high, etc.) appear only in pipeline.log (thousands of `[GATE-NAME] ... blocked` lines verified). Reuse `gate_shadow.py`'s BLOCK_RE/CONF_RE log parsing to attribute gate names instead of the Appendix C decision_reason regex.

5. **Leverage model wrong for HML and `leverage_used`:** execution leverage is per-token (`token_intel.max_leverage`); live 14d trades: lev 5 ×191, **lev 3 ×125**, lev 10 ×9, lev 40 ×1. Spec's hard cap-at-5 rule misprices HML for ~40% of trades. Sim should look up the token's registry leverage (and still apply the MAX_LEVERAGE=5 cap where the execution path applies it).

6. **`ab_results` pollution risk:** shadow sims will write ~1000s of aggregate rows/day into the same PostgreSQL table the live epsilon-greedy/evolution engine reads. If live A/B is ever re-enabled, it would select variants on simulated data. Use a `shadow-` test_name namespace **and** exclude shadow rows from live selection, or use a separate table.

7. **Multi-signal positions unaddressed:** live positions carry comma-joined signal strings (`signal_parts = signal.split(',')`, position_manager:2856). One live trade can correspond to several shadow rows — the `trade_id` validation join (§3.1, §6.2) will be many-to-one; state this explicitly.

8. **Reconciliation table incomplete:** `brain/temporal_confluence_shadow.db` (live, timer `hermes-tc-shadow.timer` verified running) is a 7th shadow system missing from §10's table; `exit_optimizer_shadow` writes proposals to JSON (not its own DB) — fine, but worth stating.

9. **Minor factual slips:** "signals.leverage defaults to 10" (it's NULL in 99.95% of rows); "backfill within 2h purge window" (PENDING archived at 24h, EXPIRED kept 14d — `archive-signals.py:28-32`; the mechanism works but the premise is wrong); expiry_shadow's existing fwd-returns use **5m** candles with entry = open of first 5m candle ≥ signal ts while the spec switches sims to 1m — state the dual-granularity decision; §6.4 should say filter `is_closed=1` (existing code does); missing 1m candles *inside* a sim window are not handled (binary search assumes continuity).

---

## Recommendations

1. **Fix the broken index** (`idx_shadow_best_exit` → `first_exit_engine`) — trivial but blocks table creation.
2. **Either define pump_exit + ride_it simulation logic (with their constants: PUMP_EXIT_*, ride_it 2-phase/volume-spike, RIDE_IT_MAX_HOLD_HOURS) or explicitly move them to v2 with an "exit_pump_exit_json/exit_ride_it_json = NULL, not simulated" label** — as written, §4.0 promises them and §4/§3/§5 silently omit them, while pump-chain+ LONG is the top signal class.
3. **Correct the factual errors:** ATR_SL_MAX 2.5% (not 5%); engine ATR = 15m-primary via atr_cache (1h only as fallback); speed-stale velocity threshold 0.05 with the speed_percentile<33 conjunct restored; cut_loser = full close (drop the invented 50%/25% model) or explicitly define it as a *hypothetical* partial variant; PM T1/T2 constants = (0.65–2.0%, skip-top-20%) / (2.0–5.0%) full closes, or drop §4.4 from v1.
4. **Replace the routing model:** document that ATR SL/TP applies to ALL positions and exit configs add layers; use the real `_match_exit_config` (import it, don't re-implement — position_manager already hoisted it module-level for exactly this reason) with `None` default → treat as ATR-baseline.
5. **Fix gate attribution:** reuse gate_shadow.py's pipeline.log parser for `gate_name`; the decision_reason backfill can remain a secondary source.
6. **Fix leverage sourcing:** read per-token registry leverage for HML and `leverage_used`.
7. **Add a re-close pass** (daily) for slow-engine horizons, and relax the §9 completeness metric per-engine-horizon.
8. **Add `sim_version` column** to shadow_trades — engine logic will change; rows from different logic versions must not be pooled in A/B.
9. **Disambiguate `first_exit_pnl_pct` vs `net_pnl_pct`** (both documented as "after fees") — pick one canonical column for reports.
10. **Verify the PM trail activation unit question live** (finding 2) before implementing the 0.40% activation in the sim.
11. **Time estimate:** 6-8h is plausible only if pump_exit/ride_it are cut to v2 and the ATR sim accepts the simplified k-formula. If §4.0's full v1 scope stands with a faithful ATR engine (phase k-scaling, confidence grades, lifecycle, TP trailing), budget 10-16h.

## Approval

- [ ] Approved as-is
- [x] Approved with changes (list changes — see Recommendations 1-10)
- [ ] Rejected (explain why)

The architecture (extend expiry_shadow, own SQLite DB, windowed 1m replay, engine-race simulation, qualitative validation bar) is sound and the v1.2 corrections are largely verified. With the changes above — especially pump_exit/ride_it scope resolution, gate attribution via log parsing, leverage sourcing, and the schema index fix — this is buildable and will deliver what T asked for.
