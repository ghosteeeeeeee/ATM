# Own Conclusions: Shadow-Mode Paper Trading Spec v1 — Independent Validation

**Auditor:** own-conclusions (independent, fresh eyes)
**Date:** 2026-10-20
**Spec:** `/root/.hermes/plans/shadow-mode-paper-trading-spec-v1.md` (v1, 567 lines)
**Method:** Read the spec from scratch; verified every constant, formula, and claim against live code (`position_manager.py`, `profit_monster.py`, `cut_loser.py`, `tpsl_utils.py`, `hermes_constants.py`, `volatility_gate_v2.py`, `expiry_shadow.py`, `signal_compactor.py`); ran numeric comparisons of spec formulas vs live logic; queried `signals_hermes_runtime.db`, `candles.db`, and the shadow DBs directly.

## Summary

The architecture, data schema, and forward-return methodology are sound and build on genuinely existing infrastructure (`expiry_shadow.py` runs every 30 min via systemd timer, 15,402 events collected). However, **three of the six exit-engine simulations contain factual errors relative to the live code** — the HML formula is inverted (fires 2-4× too early at typical ATR), the ATR SL/TP engine omits the live engine's defining feature (peak-trailing), and the "stale exit" matches no live exit rule. As spec'd, the A/B results would be poisoned: HML would race to "first to fire" on nearly every trade. The 5-6 hour estimate is achievable only for a simplified approximation; the spec does not acknowledge this tradeoff or the RR engine (a placeholder in §4.6, realistically a sub-project on its own).

## Verdict: APPROVE WITH CHANGES

Approve the concept, schema, and rollout. Reject §4 (exit engine simulation logic) as written — it must be corrected against the actual code before Phase 1 begins. See Recommendations for the specific fix list.

---

## Spec Completeness

### Process EVERY signal fire — COVERED
- **Evidence:** §2 records ALL signals (not just EXPIRED/SKIPPED). Verified feasible: ~986 signals/24h in `signals_hermes_runtime.db` (measured: `SELECT COUNT(*) ... created_at > datetime('now','-1 day')` = 986; 975 EXPIRED, 8 SKIPPED, 2 EXECUTED, 1 PENDING). The "~850/day" claim in the spec is slightly low but in the right range. Runtime DB retains rows for 14 days (`archive-signals.py` CUTOFF_HOURS_OTHERS=336), EXPIRED/SKIPPED purge is 2h (`signal_compactor.py:5993 _purge_stale_unexecuted(hours=2)`) — the 30-min record cadence catches everything, same as current `expiry_shadow.py`.

### Set TP/SL according to the exit engine that would manage it — PARTIALLY COVERED
- **Evidence:** The live system routes each signal to exactly one exit config via `_match_exit_config()` (`position_manager.py:55`) against `SIGNAL_EXIT_CONFIG` (`hermes_constants.py:1832`): `'atr'`, `'rr_engine'`, `'pump_exit'`, `'ride_it'`, or default. **The spec never mentions `SIGNAL_EXIT_CONFIG` or this routing.** Without it, the spec cannot fulfill its own stated goal ("the exit engine that would manage it"). Worse, two of the five actual live exit configs — `pump_exit` (pump-chain+ LONG, v5/v6 LONG) and `ride_it` (mover-, volume-breakout, trend-ride) — have **no corresponding simulation engine** in §4. Signals that route to them live get no faithful shadow.

### Collect all context data — PARTIALLY COVERED
- **Evidence:** §3.2's field list is mostly computable and several fields are ALREADY captured at fire time in the `signals` table: `z_score`, `z_score_tier`, `rsi_14`, `macd_value/signal/hist`, `momentum_state`, `leverage`, `price`, and a `signal_metadata` JSON containing `bb_position`, `speed_percentile`, `wave_phase`, `momentum_score`, `price_at_signal`, `btc_score`, `btc_regime`, `btc_linreg_bias` (verified from a live row). The spec ignores this free data and plans to recompute. Gaps:
  - **Context drift:** Phase 2 says "at record time, compute" vol regime/ATR/chop/tide — but recording happens in a 30-min batch AFTER fire, so "context at signal fire" is actually "context up to 30 min after fire". In EXTREME regimes this drift matters. The spec does not address it.
  - **`market_phase: "trend_building"`** (§3.2 example value) does not exist. Actual values: NEUTRAL, STORMY, CALM, RECOVERY, DECLINING (`signal_compactor.py:2763` comment). Cosmetic, but shows the field was guessed, not verified.
  - **Leverage trap:** `signals.leverage` defaults to **10** (schema `DEFAULT 10`), but live execution caps at `MAX_LEVERAGE = 5` (`position_manager.py:157,2315`). HML threshold = CUT_LOSER_PNL/leverage. If the shadow reads `signals.leverage`, HML fires at −0.40% instead of −0.80% — a 2× error baked into every simulation. Spec must specify the leverage source.

### Run A/B tests on exit engines — PARTIALLY COVERED
- **Evidence:** §3.1's per-engine `exit_*_json` columns and §5 Phase 3 are a valid A/B design (each signal simulated through all engines, candle-walked on 1m data — this is better than `exit_optimizer_shadow.py`'s MFE/MAE replay, which cannot know path order). But the engines themselves are wrong (see Technical Accuracy), and the "best_exit_engine = first to fire" label is a misnomer: first ≠ best. It is a "which engine exits earliest" metric.

### Answer gate justification questions — PARTIALLY COVERED
- **Evidence:** §5 Phase 4 promises "Gate X blocked 100, 45 would have won". Two problems:
  1. **No mechanism to populate `gate_name`.** Measured decision_reason distribution (24h): 974/975 EXPIRED = `'compaction_stale_10min'`, the rest are `[CTX-GATE]` strings. There is no structured per-gate attribution column in the signals table; gate names must be parsed from free-text `decision_reason` or re-derived. The spec stores the column but never specifies how it gets filled.
  2. **Appendix C omits the dominant gate:** confluence-by-expiry is the single largest filter in the system (974 of 986 blocks in the last 24h = 98.9%). It is not in the gate table. Also note `gate_shadow.py` (running since Oct 1, 24,470 events) ALREADY produces per-gate shadow WR reports — the spec's Phase 4 duplicates it without saying so.

---

## Technical Accuracy

### Constants (Appendix B) — CORRECT
- **Evidence:** All line numbers and values verified:
  - `CUT_LOSER_PNL = -4.00` — `hermes_constants.py:717` ✓ (note: `position_manager.py:119` imports it as `CUT_LOSER_PNL_HERMES`; same value)
  - `HML_VOL_ATR_MULT = 0.5` — line 718 ✓
  - `PM_TRAIL_ACTIVATE_PCT = 0.004` — line 1659 ✓
  - `PM_TRAIL_DISTANCE_PCT = 0.002` — line 1660 ✓
  - `TRAILING_ACTIVATION_PCT = 0.0040` — line 727 ✓
  - `RR_ENGINE_CONF_HARD_BLOCK_RR = 0.55` / `_CONFIRMED = 0.35` — lines 4054-4055 ✓
  - `ATR_PERIOD = 14` ✓ — though in `volatility_gate_v2.py` it is hardcoded (line 520), not a named constant, and **the ATR is computed on 1h candles** (line 496 `FROM candles_1h`), not 5m/1m. The spec should state this since the simulation walks 1m candles.

### §4.1 ATR SL/TP — INCORRECT (incomplete to the point of misrepresenting the live engine)
- **Evidence:** The spec simulates a **static** initial stop: `sl_price = entry * (1 − atr_pct*SL_MULTIPLIER/100)`, never moved. The live engine (`tpsl_utils.compute_atr_sl_tp`, called every PM cycle at `position_manager.py:2129`) is a **continuously trailing** engine — this is its defining behavior:
  - SL anchored to `highest_price`/`lowest_price` peak, tightens as price moves favorably (`tpsl_utils.py:33-36`: "LONG → SL anchored to highest_price (peak). Tightens as price rises.")
  - Trail distance = `TRAILING_DISTANCE_PCT = 1.20%` (`hermes_constants.py:728`), and profitable trail breaches are labeled `atr_trail_hit`, not `atr_sl_hit` (`position_manager.py:538-565`)
  - INIT floor `ATR_SL_MIN_INIT = 1.5%` vs established floor `ATR_SL_MIN_ACCEL = 0.30%`, cap `ATR_SL_MAX`, EXTREME-vol widening ×1.2 (`tpsl_utils.py:528`), phase-based k scaling, TP also trails (peak-anchored)
  - The constants file itself says the ATR SL "trails at ~0.15% from peak" in some regimes (`hermes_constants.py:1660` comment)
  A static-stop simulation will systematically understate ATR-engine exits and bias every comparison against it. If a simplified engine is intended, it must be labeled a lower bound, not "the ATR SL/TP engine."

### §4.2 PM Trail — PARTIALLY CORRECT
- **Evidence:** Constants and first-tier semantics correct: activation at +0.40% unleveraged price PnL ✓ (`profit_monster.py:454`), exit when pnl falls trail-distance below peak ✓ (`profit_monster.py:439`). But four live behaviors are missing:
  1. **Trail distance is TIERED**, not flat 0.20% (`hermes_constants.py:1732-1737` `PM_TRAIL_TIERS`: 0.20% for peak <1.5%, 0.50% for 1.5-3%, 0.80% for 3-5%, 1.20% for 5%+). Flat 0.20% exits winners far too early above 1.5% profit.
  2. **`PM_TRAIL_MIN_HOLD = 2`** min post-activation before exit fires (line 1738; `profit_monster.py:429`).
  3. **Spider regime override** (`profit_monster.py:487-501`): in NEUTRAL/spider regime, activation drops to 0.30% (`SPIDER_TRAIL_ACTIVATE_PCT`) and tiers tighten to 0.10/0.30/0.50%.
  4. **Bypass lists:** `PROFIT_MONSTER_BYPASS_SIGNALS` (hermes_constants.py:1748-1796, ~40 signal families — pump-chain, atr-spike, ai-trader, hh-hl, continuum-osc…) never route through PM Trail live. The spec's §4.4 acknowledges bypass exists but the simulation plan doesn't say it will consult the list.

### §4.3 Hard Max Loss (HML) — INCORRECT (formula inverted; verified numerically)
- **Evidence:** The spec computes `hml_threshold_pct = max(account_threshold_pct, atr_threshold_pct)  # less negative`. The live code (`position_manager.py:3551-3587`) does the opposite: the vol floor may only **widen** HML toward the account limit and is **capped** at `CUT_LOSER_PNL/leverage`, after which the account threshold always governs. I executed both implementations:

  | ATR% | Spec formula | Live code | Match |
  |------|-------------|-----------|-------|
  | 0.3  | −0.15%      | −0.80%    | NO |
  | 0.5  | −0.25%      | −0.80%    | NO |
  | 1.0  | −0.50%      | −0.80%    | NO |
  | 1.5  | −0.75%      | −0.80%    | NO |
  | ≥1.6 | −0.80%      | −0.80%    | YES |

  At typical NORMAL-vol ATR (0.3-1.0%), the spec's HML fires 2-4× too early. Consequence: simulated HML would be the "first to fire" engine on nearly every trade, destroying the A/B. **Correct live simulation: `threshold = CUT_LOSER_PNL / leverage`, unconditionally** (the ATR branch is currently neutered dead code — `position_manager.py:3584-3586` after the Oct-10 cap fix; confirmed by the Oct-12 comment "Account limit now governs everywhere", line 3568).

### §4.4 Profit Monster Trail (Full) — INCORRECT/VAGUE
- **Evidence:** "Same as PM Trail but with additional logic" is circular: PM Trail (§4.2) IS `profit_monster.py run_trail()`. There is no second, fuller PM trail engine in the code. The spec appears to double-count one engine while the real system additionally has **profit_monster T1/T2 tier exits** (quick-scalp/runner partial profit-taking, `profit_monster.py:535-557`) and **cut_loser.py two-tier loss cutting + trailing loss** (`CL_TIER1 -1.0%..-2.5%`, `CL_TIER2 -2.5%..-3.0%`, hermes_constants.py:1965-1976) — neither has a simulation engine in §4.

### §4.5 Stale Exit — INCORRECT
- **Evidence:** Spec: fixed `MAX_HOLD_MINUTES = 240`, exit at close. No live exit works like this. Actual stale/max-hold exits:
  - Speed stale loser: pnl ≤ −1.0% AND stalled (speed_percentile <33 AND |velocity|<threshold) ≥ **8 min** (`position_manager.py:612-623`, `STALE_LOSER_TIMEOUT_MINUTES=8`)
  - Speed stale winner: pnl ≥ +0.6% AND stalled ≥ **120 min** (line 626-637)
  - `UNIVERSAL_MAX_HOLD_MINUTES = 480` (8h, not 4h) with **ride_it exemption** (24h) (`position_manager.py:3448-3472`, constants line 1132)
  - trail_arm_timeout: bb-squeeze 60m / pump-chain 45m LONGs that never reach +0.40% (`position_manager.py:3599-3630`)
  - Soft peak-exit: 2h flat → 0.3% tight trail (`position_manager.py:3477-3535`)
  A flat 240-min exit matches none of these and will misrepresent "hold to stale" outcomes (live would cut stalled losers at 8-60 min, and let ride_it run 24h).

### §4.6 RR Engine — STUB (not a specification)
- **Evidence:** The constants are right, but the "logic" section is a placeholder: "(RR engine adjusts SL/TP based on S/R levels, ATR, etc.)". The actual implementation (`risk_reward_engine.py`, ~1200+ lines) does structural S/R level detection, stop-hunt buffering (`risk_reward_engine.py:608-638`), regime-exempted thresholds, and continuous re-evaluation at every PM cycle with immediate-close on trail breach (`position_manager.py:3068-3149`). Simulating this faithfully per-signal is the single hardest piece of the whole project and is not sized anywhere in the plan.

### Data schema (§3.1) — MOSTLY CORRECT, a few gaps
- **Evidence:**
  - `signal_id UNIQUE` + `INSERT OR IGNORE` ✓ consistent with edge-case handling (§6.3)
  - Forward-return columns correctly mirror the proven `expiry_shadow.py` engine (same method as gate_counterfactual_audit) ✓
  - Indexes appropriate for the report queries; `created_at` as ISO TEXT sorts correctly for the `datetime('now','-1 day')` queries ✓
  - **Missing fields:** (a) `trade_id`/actual-execution join key — §6.2 promises "compare shadow PnL vs actual PnL for EXECUTED signals" but provides no column to join to PostgreSQL `trades`; (b) fee/slippage: §12 Open Questions decided to include fees (~0.04%) and 0.1% slippage, but **no field, no constant, and no step in any §4 formula applies them** — the decisions were never incorporated; (c) `context JSON` duplicates columns already in the signals table rather than referencing them (acceptable, but wasteful); (d) no `context_computed_at` timestamp to measure the record-vs-fire drift flagged above.
  - `mfe_pct`/`mae_pct` are defined as "from best exit sim" while `mfe_4h`/`mae_4h` come from the forward-return walk — naming is confusing but not wrong.

### Existing infrastructure claims (Appendix A) — CORRECT but incomplete
- **Evidence:** `expiry_shadow.py`, `t5_shadow.py`, `gate_shadow.py`, `cell_stats.db`, `volatility_gate_v2.py`, `rsi_utils.py`, `chop_detector.py` all exist ✓. But Appendix A omits **`exit_optimizer_shadow.py`** (shadow exit-config optimizer with documented honest-counterfactual limits — directly relevant), `mom_filter_shadow.py`, `signal_outcomes` table, and the tc-shadow. The systemd timer for expiry_shadow is live (verified: `hermes-expiry-shadow.timer` fires hourly at :00/:30).

---

## New Findings (not in the spec)

1. **7 shadow systems already exist and accumulate data** — expiry (15,402 events), gate (24,470 events), t5, tc, mom_filter, exit_optimizer, signal_outcomes. The spec positions itself as a new system without stating whether it supersedes, extends, or duplicates them. `gate_shadow.py` already answers "per-gate shadow WR" (Phase 4 goal #1). Risk: three overlapping shadow DBs, three per-gate answers that disagree.
2. **Leverage source trap** — `signals.leverage` DEFAULT 10 vs live cap 5 (details above). Silent 2× HML error.
3. **Context captured at record time ≠ context at fire time** — 30-min batch drift; `signal_metadata` (captured at fire) is the only true fire-time context and the spec ignores it.
4. **Memory blowup risk in §6.4** — "cache candles in memory (per token)" ported from `expiry_shadow.py` would load ALL 1m candles per token (~218k rows/token measured). With ~150 tokens/day that is ~33M tuples resident → OOM. The close pass should binary-search and load only the `[entry_ts, exit_ts]` window per signal (the 1m table is PK'd on `(token, ts)` so range reads are cheap).
5. **Validation sample too thin for the stated bar** — §7.3 requires "shadow PnL matches actual within 5%", but only ~2 EXECUTED signals/day exist → n≈14/week, and live trades go through the full cascade (cut_loser tiers, soft trigger, speed stale, cascade flip) which the shadow doesn't simulate, so >5% mismatches are guaranteed for structural reasons, not bugs. This success metric will fail noisily and waste investigation time.
6. **"Best exit" terminology** — first-to-fire across independent simulations is not "best"; recommend renaming `best_exit_engine` → `first_exit_engine` before analytics hardwire the wrong meaning.
7. **Entry-price convention optimism** — entry = candle open at signal ts assumes zero detection-to-execution latency. Live trades enter minutes later (the AGENTS.md staleness gotcha). All shadow PnL will be optimistic vs live, systematically. Fine for relative A/B (same convention across engines), but the spec should state it so nobody reads absolute shadow PnL as achievable.
8. **`ATR_PERIOD=14` in volatility_gate_v2 is hardcoded on 1h candles** — spec should record the timeframe, since HML/attribution analysis will otherwise assume 5m/1m.

---

## Recommendations

**Must fix before Phase 1 (blockers):**
1. **Rewrite §4.3 HML** as `threshold = CUT_LOSER_PNL / leverage` (verified formula; include the numeric test above as a unit test). Delete the `max(...)` formula.
2. **Rewrite §4.1 ATR SL/TP** to include peak-trailing (TRAILING_DISTANCE_PCT=1.20% from peak, tighten-only), INIT/ACCEL floors (1.5%/0.30%), ATR_SL_MAX cap, EXTREME ×1.2 widening, and the `atr_trail_hit` relabel. Or explicitly scope v1 as "initial-stop-only lower bound" and rename the engine so results aren't mistaken for live ATR behavior.
3. **Rewrite §4.2 PM Trail** to include PM_TRAIL_TIERS (0.20/0.50/0.80/1.20%), PM_TRAIL_MIN_HOLD=2, spider override (0.30%/0.10%), and consult PROFIT_MONSTER_BYPASS_SIGNALS + PM_TRAIL_BYPASS_SIGNALS for routing.
4. **Rewrite §4.5 Stale exit** as the actual exit set: speed-stale loser (−1.0%/8min-stalled), speed-stale winner (+0.6%/120min-stalled), UNIVERSAL_MAX_HOLD=480min with ride_it exemption, trail_arm_timeout.
5. **Add `SIGNAL_EXIT_CONFIG` routing** via `_match_exit_config()` so each shadow signal is evaluated under the engine family that would actually manage it; add `pump_exit` and `ride_it` engines (or explicitly declare them out of v1 scope with the affected signal families named).
6. **Specify the gate_name backfill pass**: record at fire (PENDING), UPDATE decision/decision_reason/gate_name from the runtime DB within the 2h purge window, and parse `[CTX-GATE]`-style reasons into structured gate names. Add CONFLUENCE-EXPIRY to Appendix C (it is ~99% of blocks).
7. **Specify leverage source** = execution leverage (capped at MAX_LEVERAGE=5), not `signals.leverage`.

**Should fix (high value):**
8. Pull free fire-time context from the `signals` table + `signal_metadata` instead of recomputing; add `context_computed_at` to measure drift.
9. Reconcile with the shadow ecosystem: state explicitly that this supersedes/extends `gate_shadow.py` and `exit_optimizer_shadow.py` for gate justification, or reuse their DBs.
10. Add fee (0.04%) and slippage (0.1%) application points per the §12 decisions — or move them back to open questions.
11. Add `trade_id` join column for the EXECUTED validation; replace the 5%-match bar with a qualitative reconciliation on the handful of EXECUTED trades (or wait 30d for n≈60).
12. Replace per-token full-history candle caching with windowed reads.

**Re-estimate:** the 5-6h plan is realistic for a *simplified* v1 (record + 1m candle walk + corrected HML/stale/PM-trail + ATR-with-trailing + forward returns + reports ≈ 6-8h with tests). Faithful RR-engine and pump_exit/ride_it simulation add substantial work (RR engine alone is a multi-hour sub-project requiring structural S/R re-implementation); recommend scoping them to v2 with explicit "not simulated in v1" labels rather than shipping the current placeholder.

---

## Approval

- [ ] Approved as-is
- [x] **Approved with changes** — blockers 1-7 above (esp. HML formula, ATR trailing, stale exit, exit-config routing, gate backfill); should-fixes 8-12 strongly recommended
- [ ] Rejected

*Verification artifacts: numeric HML comparison executed during this audit (see §4.3 table); signal counts, decision distributions, and candle coverage queried directly from `data/signals_hermes_runtime.db`, `data/candles.db` (20.4M 1m rows, 185 tokens, fresh to 17:49 UTC), and `brain/expiry_shadow.db`/`brain/gate_shadow.db` on 2026-10-20.*
