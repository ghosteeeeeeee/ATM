# Bug Hunter Verification: Shadow-Mode Paper Trading Spec v1.2

**Verified:** 2026-10-20 by bug_hunter
**Spec:** `/root/.hermes/plans/shadow-mode-paper-trading-spec-v1.md` (1061 lines)
**Method:** Full spec read; every Appendix B constant located in live code; all 8 exit-engine sections traced against `position_manager.py`, `tpsl_utils.py`, `profit_monster.py`, `cut_loser.py`, `volatility_gate_v2.py`, `ride_it_exit.py`; A/B engine verified against live code + PostgreSQL; schema DDL executed verbatim in SQLite; HML formula executed as a unit test.

## Summary

The architecture is sound and the core engines (ATR peak-trailing, HML `CUT_LOSER_PNL/lev`, PM Trail tiers, routing table, existing-infra inventory) are verified correct — including the non-obvious claim that HML's ATR vol-floor is dead code after the Oct-10 cap (I traced and executed it: threshold is always −0.80% at lev 5). However, several constants in sections labeled "CORRECTED/NEW — verified against live code" are **fabricated or wrong** (PM T1/T2 thresholds and partial-exit logic, velocity stall threshold, trail-arm-timeout semantics), the schema DDL **fails when executed verbatim** (index references renamed column), the v1 scope claims `pump_exit`/`ride_it` simulation but provides no logic for them, and §10.5 proposes writing shadow-simulated data into the **live** `ab_results` table.

## Verdict: FAIL

Fail — not because the design is wrong, but because the spec asserts "all formulas below are verified against live code" while multiple formulas are not, and one DDL block breaks at build time. All findings are bounded and fixable in a ~2–3h v1.3 revision. Do not build until Findings 1–7 are corrected.

## Spec Completeness

- [x] All major sections present (1–13, Appendices A–C)
- [ ] No contradictions — **FAIL**: §2 diagram lists "RR Engine" among engines to simulate, contradicting §4.9/§4.0 (v2, not simulated); §4.4 PM T1/T2 is documented but absent from the Phase-1 "7 engines" list and has **no `exit_*_json` storage column** in the schema; §4.0 claims v1 simulates `atr`, `pump_exit`, `ride_it` families but §§4.1–4.8 contain **zero simulation logic for `pump_exit` and `ride_it`**, and there are no schema columns for them
- [ ] Clear requirements — **PARTIAL**: engine lists differ across §2/§4/§5; intra-candle and cross-engine tie-break for `first_exit_engine` undefined; `exit_*_json.pnl_pct` gross-vs-net ambiguous (§3.3 vs schema comment on `first_exit_pnl_pct`)

## Code Verification

### Constants — PARTIAL FAIL (Appendix B + §4 bodies)

| Claim | Location claimed | Verified | Result |
|---|---|---|---|
| `CUT_LOSER_PNL = -4.00` | hermes_constants.py:717 | line 717 exactly | ✅ PASS |
| `HML_VOL_ATR_MULT = 0.5` | hermes_constants.py:718 | line 718 exactly | ✅ PASS |
| `PM_TRAIL_ACTIVATE_PCT = 0.004` | hermes_constants.py:1659 | line 1659 exactly | ✅ PASS |
| `PM_TRAIL_TIERS` 0.20/0.50/0.80/1.20% | :1732–1737 | [(0.0,0.002),(0.015,0.005),(0.030,0.008),(0.050,0.012)] | ✅ PASS |
| `PM_TRAIL_MIN_HOLD = 2` | :1738 | line 1738 | ✅ PASS |
| `TRAILING_ACTIVATION_PCT = 0.0040` | :727 | line 727 | ✅ PASS |
| `TRAILING_DISTANCE_PCT = 1.20%` | :728 | `0.0120` at line 728 | ✅ PASS |
| `UNIVERSAL_MAX_HOLD_MINUTES = 480` | :1132 | line 1132 | ✅ PASS |
| `MAX_LEVERAGE = 5` | position_manager.py:157 | line 157 | ✅ PASS |
| `STALE_LOSER_TIMEOUT_MINUTES = 8` | position_manager.py:612 | defined hermes_constants.py:565, used PM:621 | ✅ value PASS (citation off ~9 lines) |
| `STALE_WINNER_TIMEOUT_MINUTES = 120` | position_manager.py:626 | defined :564, used PM:635 | ✅ value PASS (citation off) |
| `STALE_LOSER_MAX_LOSS=-1.0` / `STALE_WINNER_MIN_PROFIT=+0.6` (§4.6) | — | hermes_constants.py:566–567 | ✅ PASS |
| `BB_SQUEEZE_TRAIL_ARM_TIMEOUT_MIN = 60` / `PUMP_CHAIN…= 45` (§4.8) | — | hermes_constants.py:1671/1682 | ✅ PASS |
| `SPIDER_TRAIL_ACTIVATE_PCT = 0.003`, spider tiers 0.10/0.30/0.50 (§4.2) | — | :1817 + profit_monster.py:497 | ✅ PASS |
| `EPSILON = 0.15` (§10.5 "15% exploration") | — | ab_optimizer.py:46 | ✅ PASS |
| ATR(14) on 1h candles; EXTREME widens ×1.2 | — | volatility_gate_v2.get_atr_pct (candles_1h); tpsl_utils.py:528 | ✅ PASS |
| `ATR_SL_MIN_INIT = 1.5%` @ tpsl_utils.py | Appendix B | actually hermes_constants.py:711 | ⚠️ citation error, value PASS |
| `ATR_SL_MIN_ACCEL = 0.30%` @ tpsl_utils.py | Appendix B | actually hermes_constants.py:705 | ⚠️ citation error, value PASS |
| `ATR_PERIOD = 14` @ volatility_gate_v2.py:520 | Appendix B | no such constant; `14` hardcoded inline in `get_atr_pct` | ⚠️ citation error, value PASS |
| `RIDE_IT_MAX_HOLD_MINUTES = 1440` @ position_manager.py:3448 | Appendix B | **does not exist**. Actual: `RIDE_IT_MAX_HOLD_HOURS = 24` hermes_constants.py:4307, enforced ride_it_exit.py:342 | ❌ FAIL (value equivalent, name+location wrong) |
| `VELOCITY_STALL_THRESHOLD = 0.001` (§4.6) | — | **does not exist**. Actual: `VEL_STALE_THRESHOLD_PCT = 0.05` hermes_constants.py:559 (% per candle) | ❌ FAIL (fabricated, 2× effect error) |
| `PM_T1_EXIT_PCT = 1.5%`, `PM_T2_EXIT_PCT = 3.0%` (§4.4) | — | **do not exist**. Actual: `PM_TIER1_MIN/MAX = 0.65/2.0`, `PM_TIER2_MIN/MAX = 2.0/5.0` (hermes_constants.py:1641–1649) | ❌ FAIL (fabricated thresholds) |
| Cut Loser `CL_TIER1_MIN=-1.0/MAX=-2.5` "cut 50%", `T2` "cut remaining" (§4.5) | — | Actual `CL_TIER1_MIN_PCT=-2.5`/`MAX_PCT=-1.0`, `CL_TIER2_MIN=-3.0`/`MAX=-2.5` (:1965–1973); **full-position closes, no 50%/25% partials anywhere in cut_loser.py** | ❌ FAIL (ranges roughly right; partial logic fabricated) |

### Exit Engine Logic — PARTIAL FAIL

- **4.0 Routing — PASS with note.** `SIGNAL_EXIT_CONFIG` at hermes_constants.py:1832 ✅; `_match_exit_config()` at position_manager.py:55 ✅. Spec's simplified pseudocode (exact → rstrip('+-') → default 'atr') omits the live matcher's `-vN` version-suffix stripping, `-`/`_` prefix branches, and stem matching, and live returns **`None`** on no-match (constants comment says default is 'pm_trail'; the fall-through path is the ATR+PM cascade). Versioned signals ('pump-chain-v5') would be **misrouted** if a builder follows the pseudocode instead of importing `_match_exit_config`. Spec should mandate importing the real function.
- **4.1 ATR SL/TP — PASS.** Core claim verified: continuous peak-trailing at `TRAILING_DISTANCE_PCT=1.20%`, tighten-only, profitable exits relabeled (`atr_trail_hit`), EXTREME ×1.2 (tpsl_utils.py:528). `get_sl_multiplier_v2`/`get_tp_multiplier_v2` exist (volatility_gate_v2.py:832/871, used by signal_compactor). Note: live engine is ~700 lines with entry floor (`ATR_SL_MIN` from entry), k-tiering/phase scaling, brand-new-trade guard, snap logic — the pseudocode's "INIT 1.5% → ACCEL 0.30% after first PM cycle" floor model does not match live structure. Acceptable as approximation if labeled as such.
- **4.2 PM Trail — PASS with note.** Activation 0.40%, tiered distances, spider override, min-hold all verified (profit_monster.py:376–500). Note: the *direct* trail bypass list is `PM_TRAIL_BYPASS_SIGNALS` (only 2 entries: slow-grind); the ~40-family `PROFIT_MONSTER_BYPASS_SIGNALS` list bypasses the whole Profit Monster via SQL-level filter in `get_all_open_positions()` — functionally the spec's claim holds, but the mechanism/list name is imprecise. Live also requires min hold since trade open, not only since activation.
- **4.3 Hard Max Loss — PASS.** I traced position_manager.py:3551–3587 and executed the spec's unit test: the vol-floor branch (`-0.5×ATR`, capped at account limit Oct-10) can never bind — threshold is **always** `CUT_LOSER_PNL/leverage` (−0.80% at lev5 for ATR 0.3/1.0/2.0/3.0). Spec's "unconditional, ATR branch is dead code" is correct. Leverage handling (`min(leverage, 5)`) matches `get_trade_params` (PM:2315).
- **4.4 PM T1/T2 — FAIL.** Thresholds fabricated (see table): real windows are [0.65–2.0%] and [2.0–5.0%], not single triggers at 1.5%/3.0%; exits are **full closes** via `brain.py trade close` (profit_monster.run_tier → close_position), not 50%/25% partials; `max_close` caps, fire windows, and trail-state skipping unmodeled; no schema column stores T1/T2 results; Phase-1 engine list omits them.
- **4.5 Cut Loser — FAIL.** Tier windows approximately right, but "cut 50% / cut remaining" partial logic is fabricated (full closes). Spec also omits three live sub-engines: `CL_HARD_STOP_PCT = -3.0` (cut any trade at −3.0% immediately), MAE guard (enabled, 3.0% ATR-scaled, tightened ×0.6 on BTC crash), and CL trailing loss (disabled — worth a one-line note). `cut_loser.py` also excludes the 40 `PROFIT_MONSTER_BYPASS_SIGNALS` families.
- **4.6 Speed Stale — FAIL.** Timeouts (8/120min) and PnL gates (−1.0/+0.6) ✅, but: (1) `VELOCITY_STALL_THRESHOLD = 0.001` is fabricated — live is `VEL_STALE_THRESHOLD_PCT = 0.05` per candle; (2) the live stall predicate is `speed_percentile < 33 AND |vel_5m| < 0.05` — the spec lists `SPEED_PERCENTILE_STALL = 33` but its pseudocode **never applies it**, so shadow will declare stalls the live system would not; (3) live uses SpeedTracker `last_move_at` external state — shadow can't reconstruct in-hold speed history (token_speeds keeps only a 241-row current snapshot), which is presumably why the percentile gate was dropped — this limitation must be stated, not silently encoded with a fake constant.
- **4.7 Universal Max Hold — PASS with note.** 480min ✅, ride_it exemption ✅, but live exempts by **substring match** on the signal string (`'ride_it','trend-ride','trend_ride','volume-breakout','volume_breakout','mover-'`, PM:3456–3462), not via `_match_exit_config`, and ride_it's own 24h cap lives in ride_it_exit.py:342. Spec's `max_hold = 1440` unification is an acceptable approximation but the citation (`RIDE_IT_MAX_HOLD_MINUTES` @ PM:3448) is wrong (that line is the stale-exit close).
- **4.8 Trail Arm Timeout — FAIL (semantics).** Constants ✅ (60/45, LONG-only ✅). But live closes when **current** `live_pnl < 0.40%` **at** the 45/60-min mark (PM:3620–3627); the spec simulates "armed once at any point → never times out." A trade that touched +0.5% then fell back to +0.1% before minute 45 **is** closed live but would survive in the shadow sim. Also `BB_SQUEEZE_/PUMP_CHAIN_TRAIL_ARM_TIMEOUT_ENABLED` flags exist and gate the behavior — sim should respect them.
- **4.9 RR engine v2 — PASS.** `risk_reward_engine.py` exists (1200+ lines claim plausible); scoping to v2 is the right call and well-argued.

### Integration Points — PARTIAL FAIL

- **Shadow systems (§10) — PASS.** `expiry_shadow.py` (brain/expiry_shadow.db, 15,480 events — spec said 15,402, snapshot drift), `gate_shadow.py` (24,641 vs 24,470 ✅), `t5_shadow.py`, `mom_filter_shadow.py`, `exit_optimizer_shadow.py` all exist; systemd timers exist for expiry/gate/t5/mom-filter (**no timer found for exit_optimizer_shadow — spec's "Running" status questionable**). `signal_outcomes` table exists in the signals DB. Current `expiry_shadow.record()` indeed records only EXPIRED/SKIPPED with a MAX(id) watermark — extension approach is feasible.
- **A/B engine (§10.5) — PASS on facts, FAIL on strategy.** `ab_optimizer.py`: `epsilon_greedy_pick` (EPSILON=0.15 ✅) + `evolve_test` (kill losers, spawn, redistribute 60% weight ✅). `hermes_ab_utils.py`: Thompson sampling via `betavariate(wins+1, losses+1)`, ≥5 trials/30d gate ✅. `ab_results` table exists in PG brain: 5 rows, all 0 wins/0% WR/0 PnL ✅; UNIQUE index on (test_name, variant_id) exists so the spec's `ON CONFLICT` works ✅. `config/ab_tests.json` empty ✅. **But** (see Finding 3) writing ~1000/day shadow-simulated aggregates into the live `ab_results` table and running the evolution engine on them risks contaminating any future live A/B restart.
- **Signals DB columns (Phase 2) — PASS.** `z_score`, `z_score_tier`, `rsi_14`, `macd_value/signal/hist`, `momentum_state`, `leverage`, `price`, `signal_metadata` all exist in the `signals` table; `signal_metadata` contains speed_percentile/bb_position etc. as claimed.
- **Candles (§6.4) — PASS.** `candles_1m` is PK'd on `(token, ts)` ✅; 20.4M rows / 185 tokens / 3.2GB DB — the OOM warning about full-history caching is correct in direction (Python-side full cache would be multiple GB). Windowed reads via the PK range are the right call.

## Findings

### 1. HIGH — Schema DDL fails verbatim: index references renamed column
- **Location**: §3.1, line 163 (`idx_shadow_best_exit ON shadow_trades(best_exit_engine)`) vs lines 122–123 (column renamed to `first_exit_engine` "per validation")
- **Issue**: The CREATE TABLE has no `best_exit_engine` column. Executed verbatim in SQLite: `sqlite3.OperationalError: no such column: best_exit_engine` (reproduced).
- **Impact**: Schema init script dies mid-creation; if errors are swallowed, the shadow DB silently lacks that index.
- **Fix**: Rename index to `idx_shadow_first_exit ON shadow_trades(first_exit_engine)`; run the full DDL block in a scratch DB as part of Phase 1 unit tests.

### 2. HIGH — §4.4 PM T1/T2 thresholds and partial-exit logic are fabricated
- **Location**: §4.4 (lines 473–505)
- **Issue**: `PM_T1_EXIT_PCT=1.5%` / `PM_T2_EXIT_PCT=3.0%` do not exist; real windows are PM_TIER1 [0.65–2.0%], PM_TIER2 [2.0–5.0%] (hermes_constants.py:1641–1649). There are no 50%/25% partial closes — `run_tier` fully closes positions via `brain.py trade close`. Max-close caps, fire windows, and trail-state skipping are unmodeled. Spec claims this section is "verified."
- **Impact**: Simulated T1/T2 outcomes would be systematically wrong (wrong trigger points, wrong PnL per exit), poisoning the A/B comparison the whole system exists to produce.
- **Fix**: Rewrite §4.4 from profit_monster.py `run_tier` (windows-in-range semantics, full closes, MAX_CLOSE caps, trail-state skip) — or drop T1/T2 from v1 scope explicitly (recommended) since it has no schema column anyway.

### 3. HIGH — Writing shadow-simulated results into the live `ab_results` table
- **Location**: §10.5 "Implementation" (lines 919–923) + INSERT/evolution reuse (lines 890–908)
- **Issue**: Spec proposes writing ~1000/day simulated rows into PG `brain.ab_results` (the live A/B engine's table) and running the live evolution engine on them. Nothing prevents those rows from being read by `get_ab_variant()`/Thompson sampling or evolution if live A/B is ever re-enabled; `ON CONFLICT (test_name, variant_id)` overwrites shared keys.
- **Impact**: Simulated outcomes silently steering live variant selection (real-money impact); loss of provenance between measured and simulated data.
- **Fix**: Use a separate table (`shadow_ab_results`) or at minimum a hard namespace prefix (`shadow:`) + a `source` column, and never feed shadow rows to `get_ab_variant`/live evolution. State this invariant in the spec.

### 4. MEDIUM-HIGH — v1 scope claims `pump_exit` and `ride_it` simulation but specifies neither
- **Location**: §4.0 (line 265: "v1 scope: Simulate `atr`, `pump_exit`, `ride_it`") vs §§4.1–4.9 and the §3.1 schema
- **Issue**: No section defines pump_exit (ATR trailing mult + momentum velocity/candles + time exit, position_manager.py:2864–3030) or ride_it (2-phase + volume-spike override + 24h cap, ride_it_exit.py) simulation logic; no `exit_pump_exit_json`/`exit_ride_it_json` columns exist. `pump-chain-`/`ai-trader`/`ema300-dip`/`grind-breakout` families route to `rr_engine` (not simulated) — fine — but every `pump_exit`/`ride_it` signal has no defined v1 treatment.
- **Impact**: Builder ambiguity → either silent scope expansion mid-build or those signals simulated with the wrong (ATR-only) engine, biasing per-family exit rankings — exactly the report the system is built to produce.
- **Fix**: Either (a) add §4.10/4.11 with pump_exit + ride_it logic + schema columns, or (b) reword v1 scope to "simulate the 7 universal engines; route `pump_exit`/`ride_it` signals through the universal stack and label `exit_config` for stratified analysis."

### 5. MEDIUM — §4.6 Speed Stale: fabricated velocity constant + missing stall gate
- **Location**: §4.6 (lines 545–581)
- **Issue**: `VELOCITY_STALL_THRESHOLD = 0.001` doesn't exist (live: `VEL_STALE_THRESHOLD_PCT = 0.05` %/candle, hermes_constants.py:559). `SPEED_PERCENTILE_STALL = 33` is listed but never used in the pseudocode; live requires `speed_percentile < 33 AND |vel| < thresh`, and stall time comes from SpeedTracker `last_move_at` (external state that shadow cannot reconstruct — token_speeds holds only a current snapshot).
- **Impact**: Shadow will over-trigger stale exits vs live (single-condition instead of AND-condition; different velocity threshold), mis-ranking the speed-stale engine and any A/B that includes it.
- **Fix**: Use the real 0.05 threshold; explicitly document the fidelity gap ("shadow omits the speed_percentile gate because in-hold speed history is unavailable — expect more stale fires than live") and consider adding a `stall_gate_note` in `exit_speed_stale_json`. Consider downgrading speed-stale from "ranked engine" to "informational" in v1.

### 6. MEDIUM — §4.8 Trail Arm Timeout: "armed once" vs "current pnl at timeout" semantics
- **Location**: §4.8 pseudocode (lines 630–643)
- **Issue**: Spec breaks out of the loop the moment PnL ever ≥ +0.40% ("trail armed, no timeout"). Live closes if `hold ≥ 45/60min AND current live_pnl < 0.40%` (position_manager.py:3620–3627) — a trade that armed then gave back gains IS closed live. Also the `_ENABLED` kill switches (constants 1670/1681) aren't mentioned.
- **Impact**: Trail-arm-timeout engine systematically under-fires in shadow; its savings estimate (the 30d counterfactual was +$1.48) would be understated or misattributed.
- **Fix**: Simulate the timeout as an event check at minute 45/60 on current simulated PnL, not an "ever-armed" latch; respect both ENABLED flags.

### 7. MEDIUM — Internal contradictions in the engine roster
- **Location**: §2 diagram (line 56: "RR Engine (R:R-based)" among engines simulated) vs §4.9 (not simulated in v1); §5 Phase 1 (line 683: "7 engines") omits §4.4's T1/T2; §3.1 schema has no T1/T2 column.
- **Impact**: Divergent understandings between spec reader, builder, and reviewer; RR results could be silently simulated by mistake.
- **Fix**: One authoritative engine roster table (engine × v1-simulated? × schema column × source file) placed in §4.0; make §2 and §5 reference it.

### 8. MEDIUM — `first_exit_engine` tie-breaking undefined
- **Location**: §3.1/§4.3 (multi-engine first-fire), §4.1 (SL-before-TP check order within a candle)
- **Issue**: No precedence rule when two engines fire in the same 1m candle (e.g., HML and ATR SL both hit on the same low; TP and trail both hit on the same high). Live PM wakes every 15–60s with mid prices, so intra-candle order exists in live but not in a 1m OHLC sim.
- **Impact**: Non-deterministic `first_exit_engine` for the many candles where low ≤ both thresholds; A/B rankings become run-to-run unstable.
- **Fix**: Define a deterministic cross-engine precedence (e.g., loss-side: HML → ATR SL → cut-loser → stale → hold-limit; profit-side: ATR TP → PM trail → T1/T2) and record multi-fire engines in the engine JSONs (`fired: true` even when not first).

### 9. LOW-MED — No retention/purge mechanism for 90-day policy; concurrency unspecified
- **Location**: §12.3 ("90 days, then archive"), §6.4
- **Issue**: No purge job, no table-size projection (~1000 rows/day × 90d ≈ 90k rows + fat JSON columns — fine, but unbounded growth if purge never ships). `record()` (30min timer) and `close()` (1h timer) can overlap on the same SQLite file; no WAL/busy_timeout/lock specified (Hermes convention is lock files).
- **Fix**: Add purge to `expiry_shadow.py` main or a systemd timer; specify `PRAGMA journal_mode=WAL` + `busy_timeout` or reuse `hermes_file_lock`.

### 10. LOW — Misc precision items
- **Timestamp format in success metrics** (§9): `created_at > datetime('now','-1 day')` compares ISO-`T` strings against SQLite space-separated format — off-by-boundary errors; normalize or use `strftime('%Y-%m-%d', created_at)`.
- **Excess-return proxy undefined** (§3.1 `excess_*`): which market series? Reuse `expiry_shadow._market_rows_all()` and say so.
- **Data-completeness metric** (§9) counts `unclosed_no_candles` as incomplete — those are expected outcomes; exclude them from the denominator.
- **Gate-backfill regex** (Appendix C): live reasons often have leading whitespace (`'  🚫 [CTX-GATE] ...'` — verified in runtime DB samples) — `re.match(r'\[([A-Z-]+)\]')` fails on leading spaces/emoji; add `.strip()` + emoji tolerance. `compaction_stale` → CONFLUENCE-EXPIRY mapping verified against live data (7,655 rows) ✅.
- **§10 status check**: `exit_optimizer_shadow.py` exists but I found no systemd timer for it — "Running" status unverified.
- **Exit-engine JSON `pnl_pct` gross/net ambiguity** — document it.
- **Citations**: ATR_SL_MIN_INIT/ACCEL are in hermes_constants.py (705/711) not tpsl_utils.py; ATR_PERIOD constant doesn't exist (inline 14 in volatility_gate_v2.get_atr_pct); STALE_* usages are at PM:621/635 not 612/626; `RIDE_IT_MAX_HOLD_MINUTES` doesn't exist (RIDE_IT_MAX_HOLD_HOURS=24, hermes_constants.py:4307).

### 11. LOW — Per-signal candle re-reads (performance)
- **Location**: §6.4
- **Issue**: Windowed reads are correct, but many signals share a token/window; naïve per-signal reads re-fetch the same 1m rows ~N times per batch. `expiry_shadow.py` already has a `_candles_cache` pattern to reuse.
- **Fix**: Cache per (token, floor_ts) within a batch; cap cache size.

## Buildability Assessment

- [x] **Dependencies identified** — mostly: all named deps exist (`expiry_shadow.py`, `volatility_gate_v2.py`, `rsi_utils.py`, `chop_detector.py`, both DBs). Missing from the list: `position_manager._match_exit_config` (must import, not reimplement — Finding 4.0 note), `speed_tracker` (state not reconstructable — Finding 5), `ride_it_exit.py`/`pump_exit` logic if scope (b)-chosen.
- [ ] **Time estimates realistic** — core v1 (record + 7 engines + report): 6–8h is defensible for the simplified sim. But Phase 3 "A/B Testing Framework (1 hour)" is optimistic once Finding 3 forces a separate results store + aggregation, and pump_exit/ride_it scope (Finding 4) is unestimated either way. Budget 8–11h total after spec fixes.
- [x] **Scope controlled** — RR engine properly deferred to v2 with strong justification; dashboard deferred; no dashboard/API creep. The one creep vector is §10.5's "reuse the evolution engine" — trim to a read-only report in v1.
- **Hidden complexities not addressed**: intra-candle path ambiguity (Finding 8); speed-history unavailability (Finding 5); partial-close engines (T1/T2, cut_loser tiers) cannot be represented in a single `first_exit_*` outcome — partial-exit PnL accounting needs a decision (simulate full closes, or a `partial_closes` JSON array); signal re-fire/dedup semantics beyond `signal_id UNIQUE`.

## Security / Safety

- [x] **No protected flags touched** — spec modifies no values in `hermes_constants.py`; reads only. `LIVE_TRADING_ENABLED`, kill switches, blacklists untouched.
- [x] **No live-trading impact path** — shadow DB is a separate file (`brain/shadow_trades.db`), runtime DB and candles DB read-only; freeze-safe by design; systemd timers isolated.
- [ ] **DB connection discipline** — SQLite concurrency/purge unspecified (Finding 9); PG writes proposed into live `ab_results` (Finding 3 — the one real safety issue, and it's data-integrity, not money-path, since live A/B is currently phased out and `ab_tests.json` is empty).
- [x] **No data-corruption vectors** — INSERT OR IGNORE + UNIQUE signal_id watermark pattern matches the proven `expiry_shadow.py` design.

## Recommendations

1. **Fix Findings 1–7 before build** (schema index, §4.4 rewrite, ab_results isolation, pump_exit/ride_it scope decision, §4.6 constants, §4.8 semantics, engine roster table). Est. ~2–3h revision → v1.3.
2. **Import `_match_exit_config` from position_manager** — never reimplement routing; the v1 spec pseudocode will misroute versioned signals.
3. **Run the full §3.1 DDL verbatim in a scratch DB** as a Phase-1 unit test (this is how Finding 1 was caught in 30 seconds).
4. **Add a constant-verification appendix discipline**: every Appendix B row must be `grep -n`-verified at write time; four rows failed that bar here while the doc claimed verification.
5. **Label fidelity gaps explicitly** (speed-stale gate, entry-price optimism, ATR engine simplification, partial-close engines) in a "Known Divergences from Live" section so Day-8 analysis doesn't over-read shadow rankings.
6. **Keep v1 report read-only** — defer the evolution-engine integration to v2; the 7-engine + gate-justification reports already deliver the CEO's questions.
7. Consider simulating only the engines that are actually *decision-relevant* in v1 (ATR, PM trail, HML, universal hold) and marking stale/cut-loser/trail-arm as informational until Findings 5–6 fixes land.

**Verified-correct highlights worth keeping:** the HML dead-code analysis (§4.3) is genuinely correct and non-obvious — I executed it; the ATR peak-trailing characterization (§4.1) is right and correctly supersedes the "static initial stop" myth; the existing-systems inventory (§10) and A/B engine facts (§10.5) all check out against live code and PostgreSQL.
