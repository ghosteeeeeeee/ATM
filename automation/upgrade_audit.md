# Upgrade Audit Trail

## Plan: short-signal-drought-2026-10-02.md
- **Date scanned:** 2026-10-03 18:10
- **Core request:** Root-cause SHORT drought (49 LONG vs 1 SHORT on SHORT_BIAS day). Proposed 6 fixes.
- **Difficulty:** Level 1 (table/exemption fixes) — Fixes 4-6 need CEO
- **Value:** HIGH — conf=99 shorts were dying at decider vol gate
- **Status:** ✅ Fixes 1-3 IMPLEMENTED (2026-10-02); Fixes 4-6 PENDING CEO
- **Reason:** Verified in code: (1) v1 REGIME_SIGNALS has continuum-trend± all regimes + mtf-regime-trend± asymmetry fix (volatility_gate.py comments dated 2026-10-02); (2) PUMP-CHAIN-SHORT-RSI-MIN bearish override shipped (commit 151bf30a); (3) VEL-FILTER bear-gated downtrend exemption shipped (signal_compactor.py:3819-3840). Fixes 4 (PRESERVE-SPIKE vs RSI-FLOOR), 5 (RSI ceiling bear exemption), 6 (full SHORT-gate audit) are CEO decisions — not implementer calls.

## Plan: chop-v2-spec.md (score multipliers — remaining piece)
- **Date scanned:** 2026-10-03 18:10
- **Core request:** Per-coin trend score routing + chop exit module. Audit said should_trade_signal_v2 + chop_exit.py missing.
- **Difficulty:** Level 2 (multiplier wiring); chop_exit.py still Level 2-3
- **Value:** HIGH for multipliers — CHOP 14d MEAN-REV LONG only profitable family; weak-trend momentum was allowed with phantom "penalty"
- **Status:** ✅ SCORE MULTIPLIERS IMPLEMENTED this session; chop_exit.py still PENDING
- **Reason:** should_trade_signal already routes block/allow by trend score (score>=61 momentum OK, 31-61 allowed, <30 blocked). Gap: 31-59 momentum allowed at FULL confidence despite reason text saying penalty; mean-rev boost never applied. Wired CHOP_MOMENTUM_PENALTY_MULT=0.3 and CHOP_MEANREV_BOOST_MULT=1.2 into signal_compactor final_score. chop_exit.py (CHOP_TRAIL/CHOP_KILL) deferred — <2h killer already gone (14d <2h: 8T +$2.62); current NEUTRAL bleed is atr_sl/hard_sl, not young-trade bleed. Revisit chop_exit only with fresh exit data.

## Plan: 2026-09-07_partial-close-trailing-runner.md Option 1
- **Date scanned:** 2026-10-03 18:10
- **Core request:** 50% partial close at PM_TRAIL activation + runner trail (ICP case study).
- **Difficulty:** Level 2-3 (tpsl_utils partial size + profit_monster)
- **Value:** MEDIUM (was HIGH) — plan requires backtest before deploy
- **Status:** ⏭️ SKIPPED (data does not justify yet)
- **Reason:** Ran plan's validation SQL on PostgreSQL trades (30d): winners_with_mfe=43, would_benefit(mfe/pnl>2)=16 → 37.2% (passes plan's >30% gate) BUT mfe coverage only 11.1% (109/985 closed). Median left-on-table on winners = 0.47pp (not ICP-scale 4pp); only 20/43 winners had mfe>pnl+0.5pp. Sample too thin + coverage gap → do not build partial-close plumbing on this. Option 3 (PM_TRAIL_TIERS) already live. Option 2 (regime-adaptive trail) conflicts with CEO "DO NOT CHANGE PM_TRAIL_DISTANCE" guard. Re-run backtest when mfe_pct coverage >50%.

## Plan: regime-direction-filter-spec.md
- **Date scanned:** 2026-10-03 18:10 (reconfirm)
- **Core request:** Block wrong-direction signals via 5m regime in add_signal().
- **Difficulty:** Level 1
- **Value:** LOW-MEDIUM
- **Status:** ⏭️ SKIPPED (reconfirmed)
- **Reason:** Prior audit (2026-10-02) correct — redundant with TREND_FILTER + 5m/15m regime_confirmation; spec internally contradictory; wrong JSON path. No action.

## Plan: tier2-item2-chop-regime-merge-spec.md
- **Date scanned:** 2026-10-03 18:10 (reconfirm)
- **Core request:** Merge 4 chop/regime systems into regime_engine.py.
- **Difficulty:** Level 4
- **Value:** HIGH (duplication) but high risk
- **Status:** ⏭️ SKIPPED (reconfirm) — pending CEO (3 open questions in spec)
- **Reason:** Circular dependency + fail-open risk while LIVE_TRADING_ENABLED=True. Not implementer decision.

## Plan: oscillator-matrix-lifecycle.md
- **Date scanned:** 2026-10-03 18:10 (reconfirm)
- **Core request:** Oscillator confidence multipliers shadow→live.
- **Difficulty:** Level 1
- **Value:** MEDIUM-HIGH
- **Status:** ✅ ALREADY LIVE (reconfirm)
- **Reason:** OSCILLATOR_MULT_ENABLED=True since 2026-10-01 (validated 1035 joins). Retuned 2026-10-02 (MID falling 0.7, LOW accelerating 0.9). No action.

## Plan: system-overhaul-plan.md
- **Date scanned:** 2026-10-03 18:10 (reconfirm)
- **Core request:** Multi-tier overhaul (confluence invert, family focus, etc).
- **Difficulty:** Level 2-4
- **Value:** HIGH but PENDING CEO
- **Status:** ⏭️ SKIPPED (reconfirm) — items 1-3 need CEO; item 4 time-blocks intentionally NOT done (T disabled 2026-09-30, philosophy: no time-of-day blocks); item 9 doji flag done
- **Reason:** Not implementer decisions. Time-block repopulation contradicts trading philosophy.

## Plan: mtf-regime-trend + multi-timeframe-regime-trend
- **Date scanned:** 2026-10-03 18:10 (reconfirm)
- **Status:** ✅ IMPLEMENTED then 🛑 PLUS auto-killed (48h 7T 3W -$0.41). MINUS still enabled. No action.

## Plan: thesis-validation-system.md
- **Date scanned:** 2026-10-03 18:10 (reconfirm)
- **Status:** ✅ FULLY IMPLEMENTED (TVS_ENABLED=True). No action.

## Plan: regime-aware-signal-params-spec.md (accel_300_v3)
- **Date scanned:** 2026-10-03 18:10
- **Core request:** Per-volatility-regime parameter tuning for accel_300_v3; noted v1/v2 REGIME_SIGNALS mismatch.
- **Difficulty:** Level 2 (needs vol-regime-at-entry data collection first)
- **Value:** LOW-MEDIUM — accel-300-v3-low sample; v1/v2 mismatch largely addressed by Oct 2 vol-gate symmetry fixes
- **Status:** ⏭️ SKIPPED
- **Reason:** Spec itself says vol regime not stored on trades — prerequisite data collection not in place. v1 now has accel-300-v3-long+ in all regimes; v2 handles via SIGNAL_TYPE_OVERRIDES EXTREME block. Not a clean L1.

## Plan: Empty/stub plans + already-shipped signal plans (batch)
- **Date scanned:** 2026-10-03 18:10
- **Plans:** oversold-bounce, contrarian-zone, breakout-long, btc-crash-filter, conf-filter, spider-profit, losers-list, ema300-rejection, accel300-long-fix, exit-mechanics-v2, short-bias-fix (2026-08-19)
- **Difficulty:** N/A
- **Value:** LOW (already shipped or investigation-only)
- **Status:** ✅ VERIFIED SHIPPED / ⏭️ SKIPPED
- **Reason:** oversold_bounce.py registered (OVERSOLD_BOUNCE_ENABLED); breakout_long.py registered; btc-crash-filter constants live (BTC_CRASH_BLOCK_ENABLED=True); conf-filter live; spider constants live; contrarian zone is coin_tracker_score analysis not a signal module; losers-list constants live; short-bias-fix was investigation-complete (no filter changes needed). No implementation debt.

---

## Plan: regime-direction-filter-spec.md
- **Date scanned:** 2026-10-02 18:15
- **Core request:** Block wrong-direction signals in add_signal() using 5m regime from regime_5m.json (LONG_BIAS blocks SHORT, SHORT_BIAS blocks LONG).
- **Difficulty:** Level 1-2 (small filter + constants)
- **Value:** LOW-MEDIUM (redundant — see reason)
- **Status:** ⏭️ SKIPPED
- **Reason:** Two direction filters already exist in add_signal(): (1) TREND_FILTER_ENABLED=True — EMA20/50 on 1H blocks counter-trend with full exemption set (choch, reversion, pump-chain, mtf_zscore, coin_tracker_hot); (2) 5m+15m regime confirmation blocks SHORT when both EMAs BULLISH. Spec is also internally contradictory — logic says NEUTRAL→allow, but the RESOLV motivating example claims a NEUTRAL-regime SHORT "would have blocked." Spec code has wrong JSON path (`regime_data.get(token)` vs actual `regime_data['regimes'][token]`). Marginal value does not justify a third overlapping direction gate.

## Plan: tier2-item2-chop-regime-merge-spec.md
- **Date scanned:** 2026-10-02 18:15
- **Core request:** Merge 4 chop/regime systems (chop_detector, market_phase_gate, volatility_gate_v2, BTC_CHOP_GATE inline) into regime_engine.py facade + shims.
- **Difficulty:** Level 4 (EPIC) — ~1,964 lines, 8 consumer files, golden-master test, cutover
- **Value:** HIGH (reduces duplication) but high risk
- **Status:** ⏭️ SKIPPED (pending CEO)
- **Reason:** Spec itself lists 3 open questions for CEO: (1) BTC threshold unify 0.20 vs 0.15, (2) fail-closed confirm, (3) implement now vs defer. Circular dependency + fail-open risk while LIVE_TRADING_ENABLED=True. Not an implementer decision.

## Plan: mtf-regime-trend-signal-spec.md + multi-timeframe-regime-trend-spec.md (duplicate pair)
- **Date scanned:** 2026-10-02 18:15
- **Core request:** New mtf_regime_trend signal — 4h regime alignment + 1m pullback entry. Two files, same signal.
- **Difficulty:** Level 3 (new signal module)
- **Value:** MEDIUM (was HIGH pre-deployment)
- **Status:** ✅ IMPLEMENTED 2026-10-02 → 🛑 PLUS SIDE AUTO-KILLED
- **Reason:** signals/mtf_regime_trend.py exists (12,887 bytes), constants present, registered. MTF_REGIME_TREND_PLUS_ENABLED=False (auto_1hr 2026-10-02 15:11) — 48h 7T 3W -$0.41, last hour flipped 3W→4L -$0.70 hard_sl/hard_max_loss. MTF_REGIME_TREND_MINUS_ENABLED still True (no SHORT sample yet). No re-implementation needed. Duplicate plan file is redundant — no action.

## Plan: thesis-validation-system.md
- **Date scanned:** 2026-10-02 18:15 (CORRECTS prior "NOT IMPLEMENTED" entry)
- **Core request:** MFE thesis validation + re-entry scoring + cooldown override.
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** ✅ FULLY IMPLEMENTED (prior audit entry was stale)
- **Reason:** TVS_ENABLED=True (hermes_constants.py:4181). Full constant set present (MFE thresholds, boosts 1.15x/1.25x, penalty 0.85x, lookback=5). DB columns thesis_validated + thesis_mfe on signal_outcomes (added in position_manager.py:607-613). MFE write path in signal_schema.py:4087-4107. Score integration in signal_compactor.py:1929+ (thesis_validation_mult in final_score product). Implemented between 2026-10-01 18:10 audit and 2026-10-02.

## Plan: oscillator-matrix-lifecycle.md (FOLLOW-UP retune)
- **Date scanned:** 2026-10-02 18:15
- **Core request:** Follow-up from Oct 1 sideways finding — MID falling zone at mult=1.0 was losing.
- **Difficulty:** Level 1 (constant value update)
- **Value:** HIGH — stops boosting two losing zones
- **Status:** ✅ RETUNED
- **Reason:** Re-ran 45d join on PostgreSQL trades × _signal_metadata (btc_score+wave_phase), 539/1793 trades with oscillator context. MID falling: 62T 40.3% WR -$1.25 at mult 1.0 → set 0.7. LOW accelerating: 81T 42.0% WR -$0.94 at mult 1.1 (actively boosted a loser — old 36T sample said profitable, zone flipped) → set 0.9. Constants in hermes_constants.py:1251,1254. Pipeline restarted.

## Plan: pump_chain_v5_short generator RSI filter (from signal_report ISSUES)
- **Date scanned:** 2026-10-02 18:15
- **Core request:** Add RSI filter at signal GENERATION time for pump-chain SHORT (execution already gates).
- **Difficulty:** Level 2
- **Value:** LOW (noise reduction only)
- **Status:** ⏭️ SKIPPED
- **Reason:** PUMP_CHAIN_SHORT_RSI_MIN=40 already enforced at execution in signal_compactor.py:2797-2800. Same for LONG RSI_MIN/MAX. Generator-side filter would reduce signal spam but not change money outcomes (0 executed blocked by RSI today). YAGNI — execution gate is the money path.

---

## Summary (2026-10-02)

### Scanned this session: 4 unaudited Oct-1-evening plans + 1 follow-up + 1 sideways finding
### Evaluated: 6
### Implemented this session: 1 (Level 1)
1. oscillator-matrix retune — MID falling 1.0→0.7, LOW accelerating 1.1→0.9 (data: 45d PostgreSQL × _signal_metadata join)

### Status corrections
- thesis-validation-system: NOT IMPLEMENTED → ✅ FULLY IMPLEMENTED (audit was stale)
- mtf-regime-trend: implemented same-day, PLUS side auto-killed on poor WR

### Skipped this session: 4
1. regime-direction-filter — redundant with TREND_FILTER + regime_confirmation, spec buggy/contradictory
2. tier2 chop-regime merge — Level 4, 3 open CEO questions
3. mtf-regime-trend re-implementation — already built, PLUS auto-killed
4. pump_chain_v5_short generator RSI — execution gate already holds

### Remaining High-Value Candidates
1. **chop-v2-spec.md** — Level 2-3 — HIGH — should_trade_signal_v2 + chop_exit.py still missing
2. **partial-close-trailing-runner.md Option 1** — Level 2-3 — HIGH — 50% partial close at trail activation
3. **continuum-integration-spec.md remaining items** — Level 2 — MEDIUM-HIGH — phase/market_phase/volume_regime boosts
4. **MID bottoming mult** — Level 1 — LOW — 13T 61.5% WR but -$0.69 (big losers); sample small, already at 0.8
5. **neutral wave_phase** — wave_phase='neutral' falls through to 1.0x (6T all losing); tiny sample, skip until more data

### Sideways findings
- 1254/1793 closed trades (70%) lack oscillator context in _signal_metadata — coverage gap, mult only affects ~30% of trades
- LOW accelerating zone flipped from profitable (old 36T sample) to losing (81T current) — zones are non-stationary; consider periodic re-validation cron
- HIGH accelerating still boosted 1.2x at 53.8% WR +$0.61 — acceptable, monitor
- pipeline.service is long-running; signal-compactor is timer-based (fresh process/min). Constants reload on next timer fire either way; restarted pipeline.service anyway

### Success Rate this session: 1/1 implemented (100%)
### Cumulative: ~22/34 fully or mostly implemented or correctly skipped (65%)

---

## Plan: oscillator-matrix-lifecycle.md
- **Date scanned:** 2026-10-01 18:10
- **Core request:** Enable continuum oscillator confidence multipliers after shadow validation (Phase 1→3).
- **Difficulty:** Level 1 (EASY) — flag flip after validation
- **Value:** MEDIUM-HIGH — penalizes losing zones (LOW falling, HIGH falling, MID bottoming), boosts winners
- **Status:** ✅ FULLY IMPLEMENTED (2026-10-01)
- **Reason:** Shadow log had 24,596 entries (Sep 21–Oct 1). Joined 1,035 shadow entries to closed PostgreSQL trades. Penalized zones (mult<1): n=300, total -$8.61, 33.3% WR. Boosted zones (mult>1): n=627, total +$9.87, 50.9% WR. Matrix directionally correct. `OSCILLATOR_MULT_ENABLED = True` set in hermes_constants.py. Pipeline restarted.


## Plan: system-overhaul-plan.md (Tier 1 items only — plan itself PENDING CEO APPROVAL)
- **Date scanned:** 2026-10-01 18:10
- **Core request:** Multi-tier system overhaul. This session only implemented discrete Level 1 data-hygiene items, NOT the full plan.
- **Difficulty:** Level 1 for items done; Level 2-4 for remaining tiers
- **Value:** HIGH for executed items
- **Status:** PARTIAL — Tier 1 item 9 (doji_bottom flag) DONE; item 4 (time blocks) intentionally NOT done (T disabled 2026-09-30); items 1-3 still pending CEO
- **Reason:** Fixed doji_bottom gated by DOJI_TOP_ENABLED (data inconsistency). Time-block repopulation skipped — CEO explicitly disabled TIME_BLOCK 2026-09-30 ("pumps and dumps happen at all times"). Confluence inversion / PnL reconciliation / profitable-family focus still need CEO approval.

## Plan: continuum-filter-analysis.md
- **Date scanned:** 2026-10-01 18:10
- **Core request:** Block SHORT when BTC continuum score>10 AND zscore_tier!=STRONG_NEG. Do NOT block low-score LONGs.
- **Difficulty:** Level 1-2 — filter + constants (~40 LOC)
- **Value:** HIGH — data-backed (338T/14d). Neutral-zone SHORTs 22T 40.9% -$0.61; other states 88T 38.6% -$3.91. Filter would block both.
- **Status:** ✅ FULLY IMPLEMENTED (2026-10-01) — SHORT side only
- **Reason:** SHORT_CONTINUUM_FILTER_ENABLED=True, SCORE_MAX=10, ALLOW_Z=('STRONG_NEG',) in hermes_constants.py. Filter in signal_compactor.py after accel-300 RECOVERY block. LONG side intentionally untouched (plan: low-score LONGs are profitable mean-reversion).

## Plan: pump-chain-exit-analysis.md
- **Date scanned:** 2026-10-01 18:10
- **Core request:** Fix pump-chain+ early stops; clean stale REGIME_SIGNALS EXTREME allowlist for pump-chain-.
- **Difficulty:** Level 1 (allowlist cleanup); Level 2+ for entry-quality generator filters
- **Value:** MEDIUM — allowlist was dead-path hygiene; entry quality already enforced at execution (RSI_MIN=40, HIGH block)
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Removed pump-chain- SHORT from REGIME_SIGNALS['EXTREME'] in volatility_gate.py and volatility_gate_v2.py (stale, contradicts VOL_PHASE_MULTS Pump_Flow=0.0). Keep pump-chain+ LONG in EXTREME (57% WR edge). Generator-side RSI filter for pump_chain_v5_short NOT done — execution gates hold (0 executed today); noise not money-losing. Deferred as Level 2.

## Plan: ride-it-exit-spec.md
- **Date scanned:** 2026-10-01 18:10
- **Core request:** 2-phase ATR trail + volume spike override for volume-breakout/mover exits.
- **Difficulty:** Level 2-3
- **Value:** HIGH (per BABY case study)
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** ride_it_exit.py exists, RIDE_IT_ENABLED=True, all v3 constants present, SIGNAL_EXIT_CONFIG maps volume-breakout+/mover+ to ride_it. Verified 2026-10-01.

## Plan: squeeze-breakout-signal-spec.md
- **Date scanned:** 2026-10-01 18:10
- **Core request:** New squeeze_breakout signal (BB compression → breakout).
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** signals/squeeze_breakout.py registered, SQUEEZE_BREAKOUT_ENABLED=True with full constant set.

## Plan: continuum-ma-signal-spec.md
- **Date scanned:** 2026-10-01 18:10
- **Core request:** MA-smoothed continuum score crossover signal.
- **Difficulty:** Level 3
- **Value:** MEDIUM
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** signals/continuum_ma.py registered, CONTINUUM_MA_ENABLED=True.

## Plan: 2026-09-08_short-filter-overhaul.md
- **Date scanned:** 2026-10-01 18:10
- **Core request:** Fix VEL-FILTER dead code (range(3)); relax SHORT filters after simulation.
- **Difficulty:** Level 1 for dead-code fix
- **Value:** HIGH for dead-code fix; threshold changes UNSOUND per prior audit
- **Status:** ✅ Dead-code FIXED; threshold changes SKIPPED
- **Reason:** signal_compactor.py:3758-3760 now uses `range(SHORT_VEL_FILTER_GREEN_THRESHOLD)`. Simulation script still not built — do NOT raise VEL threshold without it. Prior independent audit called original plan UNSOUND.

## Plan: thesis-validation-system.md
- **Date scanned:** 2026-10-01 18:10
- **Core request:** MFE thesis validation + re-entry scoring + cooldown override.
- **Difficulty:** Level 3
- **Value:** HIGH
- **Status:** NOT IMPLEMENTED
- **Reason:** Still no TVS_ENABLED / thesis_validated column. Multi-file DB migration — not a Level 1 win. Next session candidate after L1 backlog clear.

## Plan: chop-v2-spec.md
- **Date scanned:** 2026-10-01 18:10
- **Core request:** Per-coin trend score routing + chop_exit module.
- **Difficulty:** Level 2-3
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** get_coin_trend_score() exists. should_trade_signal_v2(), chop_exit.py, score-based routing still missing. Large change — not attempted this session.

---

## Summary (2026-10-01)

### Scanned this session: 20 recent plans + prior audit (25 plans)
### Evaluated: 20 new/re-checked
### Implemented this session: 4 Level 1 wins
1. oscillator-matrix-lifecycle — OSCILLATOR_MULT_ENABLED=True (validated 1035 trade joins)
2. system-overhaul Tier1#9 — doji_bottom own flag DOJI_BOTTOM_ENABLED
3. continuum-filter-analysis — SHORT continuum filter (score>10, z!=STRONG_NEG)
4. pump-chain-exit-analysis — stale REGIME_SIGNALS EXTREME pump-chain- removed

### Already implemented (verified, no action): ride-it-exit, squeeze-breakout, continuum-ma, VEL-FILTER dead code, pump-chain-v5-spec, regime-fixes, winrate-fix, btc-timing-guard, chop-gating, volatility-gate-tuning, volatility-regime-adaptive, regime-transition-smoothing, profitability-fix, 30s-migration

### Remaining High-Value Candidates
1. **chop-v2-spec.md** — Level 2-3 — HIGH — trend-score routing + chop_exit
2. **thesis-validation-system.md** — Level 3 — HIGH — MFE re-entry scoring
3. **pump_chain_v5_short generator RSI filter** — Level 2 — MEDIUM — stop spam generation (execution already gates)
4. **partial-close-trailing-runner.md Option 1** — Level 2-3 — HIGH — 50% partial close at trail activation
5. **system-overhaul Tier 1 items 1-3** — need CEO — confluence invert, profitable-family focus, PnL reconcile

### Success Rate this session: 4/4 Level 1 implemented (100%)
### Cumulative from prior audit + this session: ~21/29 fully or mostly implemented (72%)

### Sideways findings
- signal_report ISSUES #1 still open: pump_chain_v5_short generates without RSI/vol filters (execution gates hold)
- MID falling oscillator zone has mult=1.0 but 23.1% WR / -$6.99 in join — candidate for future multiplier tuning (0.5-0.7x)
- hermes-signal-compactor.service inactive (timer-based, fires later) — not an error


## Plan: thesis-validation-system.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Track MFE after each trade to validate thesis. Boost re-entry scores when thesis was validated. Override cooldowns when setup improves.
- **Difficulty:** Level 3 (HARD) — new DB columns, score formula changes, cooldown override logic, MFE integration
- **Value:** HIGH — turns 98.6% signal expiry into executed trades on validated setups
- **Status:** NOT IMPLEMENTED
- **Reason:** No TVS_ENABLED, no thesis_validated column in signal_outcomes. Complex multi-file change requiring DB migration, signal_compactor.py score formula, cooldown override logic, and MFE integration from position_manager.py.

## Plan: chop-v2-spec.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Per-coin trend classification (0-100 score), score-based signal routing, chop-specific exit module (CHOP_TRAIL, CHOP_KILL).
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — get_coin_trend_score exists, but should_trade_signal_v2 and chop_exit.py not built
- **Value:** HIGH — fixes <2h trades -$281.92% PnL in NEUTRAL, fixes cut-loser-CL-T1 -$505.32%
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** get_coin_trend_score() exists in chop_detector.py. But: should_trade_signal_v2() not implemented, chop_exit.py not created, chop exit config not in hermes_constants.py, score-based routing multipliers not in signal_compactor.py.

## Plan: 2026-09-23_regime-based-signal-fixes.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Block LONG when linreg=LEAN_BEAR, block accel-300 SHORT in RECOVERY, disable pullback-entry- SHORT.
- **Difficulty:** Level 1 (EASY) — config changes and simple condition blocks
- **Value:** HIGH — prevents 0% WR trades in bad conditions
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** All 3 fixes confirmed in code: LEAN_BEAR LONG block in signal_compactor.py, accel-300 RECOVERY block, pullback-entry- MINUS_ENABLED=False.

## Plan: 2026-09-23_emergency-winrate-fix.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Lower SHORT_RSI_FLOOR 50→40, disable loser signals, add oversold SHORT guard, add continuum bullish SHORT penalty.
- **Difficulty:** Level 1 (EASY) — config changes
- **Value:** HIGH — unblocks SHORT in RSI 40-50 sweet spot
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** SHORT_RSI_FLOOR=40, trend_purity disabled, pullback-entry disabled, oversold guard active, bullish SHORT penalty in signal_compactor.py.

## Plan: continuum-integration-spec.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Wire continuum oscillator phases, market phases, volume regime, z-score, wyckoff into signal scoring.
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — multiple integration points in signal_compactor.py
- **Value:** MEDIUM-HIGH — faster regime detection, better direction alignment
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** LEAN_BEAR LONG block exists. But: phase boost (phase>=3 → 1.3x), market_phase boost, volume_regime boost, zscore_tier boost, wyckoff_phase filter, phase 6 auto-approve all NOT implemented.

## Plan: pump-chain-v5-spec.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Add velocity filter (30m > -0.3%) and continuum oscillator filter (block bottoming/flat) to pump-chain.
- **Difficulty:** Level 2 (MEDIUM) — signal file changes
- **Value:** HIGH — pump-chain+ 51.9% WR → estimated 90%+ with filters
- **Status:** ✅ FULLY IMPLEMENTED (2026-09-30)
- **Reason:** pump_flow_signal.py has 30m velocity filter (PUMP_FLOW_TOKEN_30M_THRESHOLD=0). 5m threshold tightened from -0.2% to -0.5% (PUMP_FLOW_TOKEN_VEL_THRESHOLD=-0.5). SHORT velocity filter active (PUMP_FLOW_SHORT_VEL_THRESHOLD=0). pump_chain_long.py and pump_chain_v5.py also have 30m velocity filters.

## Plan: trade-watchdog-spec.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Autonomous trade monitor with profit lock, regime alignment, stale trade detection, auto-execution.
- **Difficulty:** Level 3 (HARD) — new system with dashboard, API, systemd
- **Value:** MEDIUM — proactive trade management
- **Status:** EXISTS (trade_watchdog.py) — needs verification of completeness
- **Reason:** trade_watchdog.py exists and runs via systemd.

## Plan: structural-awareness-overhaul.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Wire existing systems (coin_tracker_analysis, sl_zones, continuum_oscillator) into a structural bias engine, entry optimizer, proactive positioner.
- **Difficulty:** Level 4 (EPIC) — 3 new files, multiple integration points
- **Value:** MEDIUM — structural awareness, but high complexity risk
- **Status:** NOT IMPLEMENTED
- **Reason:** structural_bias.py, entry_optimizer.py, proactive_positioner.py not created. High risk of over-engineering.

## Plan: pump-catching-and-exit-optimization.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Block chop, catch pumps, ride winners. BTC Timing Guard, pump-chain velocity, PM trail widening, cut-loser tightening.
- **Difficulty:** Level 1-2 (EASY-MEDIUM)
- **Value:** MEDIUM-HIGH
- **Status:** ✅ MOSTLY IMPLEMENTED
- **Reason:** BTC Timing Guard active ✅, cut-loser tightened ✅, time block extended ✅, pump-chain velocity filter ✅ (30m + 5m tightened). Remaining: pump_flow_engine velocity raise, PM trail widening (tiered trail already implemented via PM_TRAIL_TIERS).

## Plan: oscillator-matrix-lifecycle.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Implement continuum oscillator as confidence multiplier system with shadow mode → validation → live.
- **Difficulty:** Level 1 (EASY) — flip OSCILLATOR_MULT_ENABLED to True
- **Value:** MEDIUM — multipliers already defined, just needs activation
- **Status:** IN SHADOW MODE
- **Reason:** OSCILLATOR_MULTS defined in hermes_constants.py. OSCILLATOR_MULT_ENABLED = False (shadow mode).

## Plan: profitability-fix-plan.md
- **Date scanned:** 2026-09-29 17:00, 2026-09-30 12:00
- **Core request:** Exit system fixes, signal kills, regime gating, token management, speed filter, time-of-day.
- **Difficulty:** Level 1 (EASY) — config changes
- **Value:** HIGH — estimated +$4.21/7d
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** All key fixes done: pullback-entry- exit changed to ATR, ema300-dip-long killed, ENA blacklisted, cut-loser tightened, speed threshold added, time block extended.

## Plan: 2026-09-12_btc-momentum-sync-plan.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** 5-layer defense: BTC momentum gate, transition detection, stale signal filter, RSI/z-score guard, continuum context boost.
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — multiple integration points
- **Value:** HIGH — eliminates -$1.42 LONG bleed, prevents 7-10% blowups
- **Status:** ✅ MOSTLY IMPLEMENTED
- **Reason:** Layer 1 (BTC Momentum Gate) ✅ — directional bias in signal_compactor.py reads momentum_state. Layer 3 (Stale Signal Filter) ✅ — staleness decay exists. Layer 4 (RSI/Z-Score Guard) ✅ — RSI floors/ceilings active. Layer 5 (Continuum Context Boost) ✅ — directional bias multiplier active. Layer 2 (Transition Detection) — not explicitly implemented as separate function, but covered by directional bias + chop detector.

## Plan: 2026-09-11_btc-timing-guard.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Per-signal-type BTC momentum thresholds to prevent chasing.
- **Difficulty:** Level 1 (EASY) — config + ~25 lines
- **Value:** HIGH — prevents chasing entries after BTC already moved
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** BTC_TIMING_GUARD_ENABLED=True, all per-signal thresholds defined, implementation in signal_compactor.py lines 1251-1295.

## Plan: 2026-09-11_chop-regime-signal-gating.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Hard BTC momentum gate + gate STANDALONE_BYPASS in flat markets.
- **Difficulty:** Level 1 (EASY) — ~20 lines + 3 constants
- **Value:** MEDIUM-HIGH — prevents trend signals firing into chop
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** BTC_CHOP_GATE_ENABLED=True, BTC_CHOP_GATE_THRESHOLD=0.20, implementation in signal_compactor.py. STANDALONE_BYPASS gated when BTC flat.

## Plan: 2026-09-11_volatility-gate-tuning.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** ATR ratio + BTC trend boost for direction-aligned expansion trades.
- **Difficulty:** Level 2 (MEDIUM) — extend existing volatility_gate_v2.py
- **Value:** MEDIUM — boost SHORT in falling expansion (83% WR setup)
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** get_atr_ratio() in volatility_gate_v2.py, get_btc_trend() exists, ATR ratio + BTC trend boost in get_combined_multiplier() (lines 568-588). Constants: VOL_GATE_ATR_RATIO_EXPANSION=1.5, VOL_GATE_EXPANSION_SHORT_FALLING_BOOST=1.2, VOL_GATE_EXPANSION_LONG_RISING_BOOST=1.1.

## Plan: 2026-09-11_volatility-regime-adaptive-signals.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Per-signal-family weighting by volatility regime (momentum boost in expansion, mean-rev boost in compression).
- **Difficulty:** Level 2 (MEDIUM) — ~25 lines + 8 constants
- **Value:** MEDIUM — adapt signals to market conditions
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** signal_compactor.py lines 1841-1893: computes ATR ratio, classifies expansion/compression, applies per-family multipliers (1.2x momentum in expansion, 0.8x mean-rev, 0.7x momentum in compression, 1.2x mean-rev). Constants in hermes_constants.py.

## Plan: 2026-09-09_regime-transition-smoothing.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Directional bias from momentum_state, alt-BTC divergence, stronger directional outcome penalty.
- **Difficulty:** Level 1-2 (EASY-MEDIUM) — ~30 lines + 4 constants
- **Value:** HIGH — reduces regime transition bleed
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** DIRECTIONAL_BIAS_ENABLED=True with momentum_state reading (signal_compactor.py:1776-1801). ALT_BTC_DIVERGENCE_ENABLED=True (signal_compactor.py:1815-1830). DIRECTIONAL_OUTCOME_PENALTY=0.5 (tightened from 0.7).

## Plan: 2026-09-09_pump-chain-v2-spec.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Token 30m velocity filter, 5m threshold tightening, SHORT velocity filter for pump-chain.
- **Difficulty:** Level 2 (MEDIUM) — signal file changes
- **Value:** HIGH — pump-chain WR from 57.5% to 93.5%+ (backtested)
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** 30m velocity filter in pump_flow_signal.py (PUMP_FLOW_TOKEN_30M_THRESHOLD=0). 5m threshold tightened to -0.5% (PUMP_FLOW_TOKEN_VEL_THRESHOLD=-0.5). SHORT velocity filter (PUMP_FLOW_SHORT_VEL_THRESHOLD=0). Also in pump_chain_long.py and pump_chain_v5.py.

## Plan: 2026-09-09_grass-breakout-analysis.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** New squeeze_reversal signal — BB squeeze → mean-reversion breakout.
- **Difficulty:** Level 3 (HARD) — new signal module
- **Value:** MEDIUM — catches BB squeeze breakouts
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** signals/squeeze_reversal.py exists with squeeze detection, BB proximity, RSI filters. Registered in signals/__init__.py. Constants in hermes_constants.py.

## Plan: 2026-09-08_trend-ignition-signal-spec.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** New trend_ignition signal — early-stage breakout at trend START.
- **Difficulty:** Level 3 (HARD) — new signal module
- **Value:** MEDIUM — catches趋势启动点 (100% WR in 7d backtest)
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** signals/trend_ignition.py exists with volume spike, compression, breakout detection. Registered in signals/__init__.py. Constants in hermes_constants.py.

## Plan: 2026-09-11_btc-pump-rider-gradual-rally.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Gradual rally detection mode for btc_pump_rider.py — catch slow BTC rallies + lagging alts.
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — ~58 lines + 8 constants
- **Value:** MEDIUM — catches gradual rallies missed by explosive breakout detection
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** detect_btc_gradual_rally() and find_lagging_alts() in btc_pump_rider.py. Constants: BTC_PUMP_RIDER_GRADUAL_ENABLED=True, all thresholds defined.

## Plan: 2026-09-07_partial-close-trailing-runner.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Partial close at PM_TRAIL activation (50% scalp, 50% runner), regime-adaptive trail width.
- **Difficulty:** Level 2-3 (MEDIUM-HARD) — changes to profit_monster.py + tpsl_utils.py
- **Value:** HIGH — estimated ~3x improvement on winning trades (0.84% → 2.64% on ICP case)
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** Option 3 (Tiered Trail) is IMPLEMENTED via PM_TRAIL_TIERS. Option 1 (Partial Close) is NOT implemented — no PARTIAL_CLOSE constant, no partial position close logic. Option 2 (Regime-Adaptive Trail) NOT implemented. Option 4 (Time-Based Trail) NOT implemented. The tiered trail is the most impactful part and it's done.

## Plan: 2026-09-08_short-filter-overhaul.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Relax SHORT filters, fix dead code, build simulation script.
- **Difficulty:** Level 1-2 (EASY-MEDIUM)
- **Value:** MEDIUM — unblock profitable SHORTs
- **Status:** MOSTLY IMPLEMENTED (audit-corrected version)
- **Reason:** Original plan was UNSOUND per audit. Revised fixes: VEL-FILTER dead code (range(3) bug) — need to verify. SHORT_RSI_FLOOR lowered to 40 ✅. SHORT-NEUTRAL block has bypasses ✅. Simulation script not built.

## Plan: 2026-09-04_continuum-engine-spec.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** State-based continuum engine replacing event-based signals.
- **Difficulty:** Level 4 (EPIC) — architecture overhaul
- **Value:** MEDIUM — state-based trading
- **Status:** EXISTS (continuum_engine.py) — core engine built, not full spec
- **Reason:** continuum_engine.py exists with state tracking, but full spec (6 dimensions, compound scorer, entry/exit signals) not fully implemented.

## Plan: 2026-08-29_wave-period-analysis-plan.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Wave period analysis — periodicity detection, pattern classification, trading integration.
- **Difficulty:** Level 2 (MEDIUM) — analysis scripts + integration
- **Value:** MEDIUM — token-specific wave patterns
- **Status:** PARTIALLY IMPLEMENTED
- **Reason:** wave_period_detector.py, wave_trade_context.py, wave_classifier.py exist. Phase 1 (discovery) complete. Phase 2 (validation + integration) pending.

## Plan: 2026-08-29_amplitude-enhancement-brainstorm.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Amplitude-based token classification and wave period trading system.
- **Difficulty:** Level 3 (HARD) — new system
- **Value:** MEDIUM — amplitude-based signal weighting
- **Status:** NOT IMPLEMENTED
- **Reason:** Analysis complete but no integration into trading system.

## Plan: 2026-09-21_btc-4year-cycle-macro-thesis.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Macro thesis — BTC 4-year cycle, LONG bias for 2-3 years.
- **Difficulty:** Level 4 (EPIC) — macro integration
- **Value:** LOW-MEDIUM — thesis, not actionable code
- **Status:** THESIS ONLY
- **Reason:** Analysis document, no code implementation needed. Could inform LONG bias in signal scoring.

## Plan: 2026-08-26_30s-price-interval-migration.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Split architecture for 30s price collection — latest_prices for exits, price_history for signals.
- **Difficulty:** Level 1 (EASY) — single line change
- **Value:** MEDIUM — faster exit management without breaking signals
- **Status:** ✅ FULLY IMPLEMENTED
- **Reason:** Status says IMPLEMENTED. Dual-track writes in signal_schema.py.

## Plan: 2026-08-22_copy-trader-dashboard-enhancements.md
- **Date scanned:** 2026-09-30 12:00
- **Core request:** Copy trader dashboard with stats, per-token table, exit reasons, equity curve.
- **Difficulty:** Level 2 (MEDIUM) — dashboard + API
- **Value:** MEDIUM — visibility into copy trading
- **Status:** Phase 1 IMPLEMENTED
- **Reason:** copy_trader_api.py and copy_trader.html exist with all Phase 1 features.

---

## Summary (2026-09-30)

### Scanned: 25 plans
### Evaluated: 25 plans

| Status | Count | Plans |
|--------|-------|-------|
| ✅ FULLY IMPLEMENTED | 14 | regime-fixes, winrate-fix, btc-timing-guard, chop-gating, volatility-gate-tuning, volatility-regime-adaptive, regime-transition-smoothing, pump-chain-v2, squeeze-reversal, trend-ignition, gradual-rally, profitability-fix, 30s-migration, pump-catching |
| ✅ MOSTLY IMPLEMENTED | 3 | btc-momentum-sync, profitability-fix, short-filter-overhaul |
| PARTIALLY IMPLEMENTED | 4 | chop-v2, continuum-integration, partial-close, wave-period |
| IN SHADOW MODE | 1 | oscillator-matrix-lifecycle |
| NOT IMPLEMENTED | 3 | thesis-validation, structural-awareness, amplitude-enhancement |
| EXISTS (verify) | 2 | trade-watchdog, continuum-engine |

### Remaining High-Value Candidates

1. **chop-v2-spec.md** — Level 2-3 — HIGH VALUE — per-coin trend scoring + chop exit module
2. **partial-close-trailing-runner.md** — Level 2-3 — HIGH VALUE — 50% partial close at trail activation (Option 1 not done, but Option 3 tiered trail IS done)
3. **thesis-validation-system.md** — Level 3 — HIGH VALUE — MFE tracking + re-entry scoring
4. **oscillator-matrix-lifecycle.md** — Level 1 — MEDIUM VALUE — flip OSCILLATOR_MULT_ENABLED to True

### Success Rate: 17/25 fully or mostly implemented (68%)

---

## Plan: short-signal-drought-2026-10-02.md (Fix 1 completion — v2 REGIME_SIGNALS sync)
- **Date scanned:** 2026-10-04 06:05
- **Core request:** Complete Fix 1 from the SHORT-drought plan: keep v1/v2 REGIME_SIGNALS consistent so no table-divergence kill can recur.
- **Difficulty:** Level 1 (6 additive dict entries)
- **Value:** HIGH (insurance against the #1 blocker class from 2026-10-02)
- **Status:** ✅ IMPLEMENTED
- **Reason:** Prior sessions synced v1 (continuum-trend± all regimes + mtf-regime-trend± in NORMAL/HIGH/EXTREME). Reverse gap remained: v2 REGIME_SIGNALS had ZERO mtf-regime-trend entries. Live path today is decider→v1 (correct), and should_trade_v2 is only called from volatility_gate_v2 `__main__` self-test — so this was latent, not bleeding money. Still, the plan explicitly required consistency ("add mtf-regime-trend± to v2 or v1 consistently"), and MTF_REGIME_TREND_MINUS_ENABLED=True (the SHORT side) would die the same way continuum-trend- did if anyone repoints decider to v2. Added mtf-regime-trend± to v2 NORMAL/HIGH/EXTREME (matching v1; FLAT stays out in both). Verified: all 16 regime×signal cells match between v1 and v2; module imports clean.

## Plan: recent-20 reconfirm (short-signal-drought, mtf-regime-trend, TVS, chop-v2, regime-fixes, winrate-fix, continuum-*, pump-chain-v5, trade-watchdog, structural-awareness, pump-catching, system-overhaul, thesis-validation, oscillator-matrix, regime-direction-filter, tier2-merge, btc theses)
- **Date scanned:** 2026-10-04 06:05
- **Core request:** Re-scan the 20 most recent plans/ files.
- **Difficulty:** N/A (evaluation only)
- **Value:** N/A
- **Status:** ⏭️ NO NEW ACTION — all previously audited (2026-10-01/02/03 entries in this file)
- **Reason:** Statuses unchanged. Key reconfirms: TVS fully live; oscillator mult live + retuned; continuum SHORT filter live (SCORE_MAX=30); VEL-FILTER + RSI-CEILING bear exemptions live; PUMP-CHAIN-SHORT-RSI-MIN + SHORT-RSI-FLOOR deliberately NO bear override (bf96d7cd 2026-10-03, data-backed); regime-direction-filter skipped (redundant, spec buggy); tier2 chop-regime merge + system-overhaul pending CEO; mtf-regime-trend PLUS auto-killed, MINUS still enabled; chop_exit.py deferred.

## Sideways finding (this session)
- **Severity:** LOW (latent)
- **Finding:** `should_trade_v2` in volatility_gate_v2.py is dead code in production — only caller is the module's `__main__` self-test (line 819). Decider imports v1 `should_trade` (decider_run.py:1549). Compactor imports v2 for multipliers/classification but not REGIME_SIGNALS membership. Two large v1-only REGIRE_SIGNALS sets remain (52 signals in v1 NORMAL not in v2; 40 in v1 EXTREME not in v2) — many are deliberate v2 exclusions (comments show data-backed removals). Do NOT blind-sync those. Only the mtf-regime-trend± asymmetry was unsafe to leave (enabled SHORT signal, same kill class as the Oct 2 incident).
- **Suggested fix:** None required now. If decider is ever repointed to v2, run a full REGIME_SIGNALS diff and reconcile deliberately — not mechanically.
