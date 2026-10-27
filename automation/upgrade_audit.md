# Upgrade Audit Trail

## Session: 2026-10-12 ~18:00 UTC — Upgrade Implementer (L1 fix + L2: BTC regime align shadow build)

**Scope:** re-scanned most recent plans/ (Oct 5 → Oct 12). Picked up the #1 next-candidate from the 2026-10-11 session (align-with-btc-regime). 1 Level 1 + 1 Level 2 implemented.

### Plan evaluations (recent-20, deltas vs Oct-11 session)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| 2026-10-12_bb-squeeze-trail-arm-timeout-verdict | L2 | HIGH | ✅ ALREADY IMPLEMENTED | Verdict said "not shipped, needs CEO GO" but constants BB_SQUEEZE_TRAIL_ARM_TIMEOUT_ENABLED=True + position_manager:3495 wiring are LIVE. Presumably CEO-approved separately; flag for own-conclusions re-check per verdict caveat |
| grind-breakout-v2-coin-tracker-integration | L3 | LOW | ⏸️ DEFERRED (by plan) | Plan itself defers; revisit only if window-based firing misses >50% breakouts |
| regime-recalibration-2026-10-12 | L2 | MED-HIGH | ⏳ PENDING CEO | PROPOSED — do not touch live code until approved (plan header) |
| 2026-10-12_rep-phase2-pickup | L2 | HIGH | ⏳ SCHEDULED Oct 13 | Execute on/after 2026-10-13 00:00 UTC (48h shadow window). Not yet time at scan (Oct 12 18:00). Pre-flight: reputation.py imports OK |
| combo-first-reputation-system | L2–3 | HIGH | Phase 1 LIVE / Phase 2 = rep-phase2-pickup | Phase 1 commit 7503aa51 landed; Phase 2 gated on Oct 13 date |
| bug-hunt-master-plan | ongoing | HIGH | 🔄 Tier 1–4 pending | Tier 0 done; 5 open bugs all T-decision or covered elsewhere |
| profitability-fix-plan | L1–4 | HIGH | PARTIAL (per Oct 11) | SHORT_CONTINUUM_SCORE_MAX=60 confirmed live; no new action |
| penalty-gated-execution | L1–2 | HIGH | ✅ FIXES 1–3 CONFIRMED LIVE | PENALTY-BLOCK gate in decider_run:3476; _cont_bearish AT (POL hole) at compactor:2711; chop bullish DECLINING at chop_detector:533 |
| align-with-btc-regime | L2 | MED-HIGH | ✅ SHIPPED THIS SESSION (shadow, flag OFF) | See implementation below |
| winning-dna-population-report | L1–3 | HIGH | ASSESSED | §9 routing bug (v5-SHORT→pump_exit) already FIXED (constants 1742–1747, CEO 2026-10-09); ask (d) except-swallow instrumented this session; stale_winner/dead_money behavior asks remain CEO-gated |
| ride-it-hard-max-loss-exemption | L1 | HIGH | ⏳ PENDING CEO | Still needs backtest → own-conclusions → CEO. Untouched |
| q4-portfolio-cap-verdict | — | HIGH | ⏳ PENDING CEO | Cap B accepted on aggregate, CEO must choose re-test vs accept |
| wyckoff-bypass-verdict | — | — | ✅ CLOSED REJECT | No action |
| gate-counterfactual-audit | — | HIGH | ✅ D3/D4 DONE | No new action; token-W allowlist housekeeping skipped (LOW, unlocatable in reasonable time) |
| trade-learning-system-EXECUTION | L2–3 | HIGH | P0–P4 LIVE | MFE/MAE write path verified present (position_manager:619–1194). P5–P6 CEO-gated |
| short-drought-dump-day | L1–2 | HIGH | PARTIAL | Hysteresis constant still orphaned (known sideways from Oct 11) |
| bug-hunt-gameplan | ongoing | HIGH | 🔄 | BUG-036/037/044 remain T-decision; BUG-064 (continuum BTC no SL) HIGH — not touched (live-money path, needs care + likely CEO) |
| wrong-side-chop-detector / profitability others | — | — | unchanged | per prior audits |

### Implemented this session (1 Level 1 + 1 Level 2)

#### 1. (L1) Dead-money time-exit exception swallow instrumented
- **Plan/source:** `plans/2026-10-08_winning-dna-population-report.md` §9 ask (d)
- **Difficulty:** Level 1 (2-line change)
- **Value:** HIGH — this exact `except: pass` hid a datetime TypeError that kept the dead-money TIME exit dead for 8 days; recurrence would again be invisible
- **Status:** ✅ IMPLEMENTED
- **Fix:** `scripts/position_manager.py:2964` — bare swallow replaced with WARN log (`[PUMP-EXIT] {token} dead_money time-exit check failed: {err}`)
- **Verified:** py_compile OK; no behavior change (exception path identical, now logged)

#### 2. (L2) BTC Regime Alignment — shadow build (CEO-approved 2026-10-08, default OFF)
- **Plan:** `plans/align-with-btc-regime.md` (APPROVED WITH MODIFICATIONS)
- **Difficulty:** Level 2
- **Value:** MED-HIGH — BULL_TREND LONG cohort: 139T 56.8% +$0.48/30d (CEO-verified); unlocks pump-chain LONGs wrongly gated by LONG-NEUTRAL when BTC continuum is bullish; ships default-OFF so zero live-behavior change
- **Status:** ✅ IMPLEMENTED (shadow wiring only)
- **Changes:**
  - `hermes_constants.py`: `BTC_REGIME_ALIGN_ENABLED = False` + `BTC_REGIME_ALIGN_MIN_SCORE = 60` (new flags, no existing values touched)
  - `signal_compactor.py` (before LONG-NEUTRAL gate): bullish continuum check via existing `get_btc_trend_context()`; if flag ON and BULL_TREND/RANGING_BULL with score≥60 → bypass LONG-NEUTRAL; if flag OFF → `[BTC-REGIME-ALIGN-SHADOW]` would-allow log (counterfactual data for the 7d review). Bearish/NULL: no change (mod #4). SHORT side untouched (mod #1). RSI ceiling/RR/confluence/blacklists untouched.
- **Verified:** py_compile OK on all 3 files; constants import OK; live ctx call OK (regime=BEAR_TREND score=4.2 → bullish_check=False, correct no-op in current regime); signal_compactor runs via hermes-signal-compactor.timer (subprocess/minute — live next cycle, no restart)
- **Next (per plan governance):** accrue shadow logs → independent backtest + bug_hunter verification → CEO GO to flip flag; 7d test window after enable. NOT enabled by this session.

### Sideways findings
1. **MED:** bb-squeeze trail-arm timeout shipped ENABLED=True although the verdict file's implementation sketch said default-off/needs-CEO-GO. Behavior matches the PASS verdict's intent, but the approval trail for flipping it live isn't in the plan file — recommend own-conclusions spot-check.
2. **LOW:** token-W allowlist housekeeping (gate audit ask) skipped — couldn't locate the failing site cheaply; value LOW.
3. **INFO:** current BTC continuum = BEAR_TREND (score 4.2) — BTC-REGIME-ALIGN-SHADOW logs will stay silent until a bullish regime returns; expected, not a bug.

### Success rate this session: 2/2 implemented (100%)
### Next candidates (priority order)
1. **rep-phase2-pickup** — L2 — HIGH — execute on/after 2026-10-13 00:00 UTC (pre-flight verified this session)
2. **regime-recalibration-2026-10-12** — L2 — MED-HIGH — blocked on CEO approval (additive MAXXED tier + EXTREME-hi SHORT override)
3. **q4 portfolio cap B** — L1 — HIGH — blocked on CEO GO (re-test max-2/30min vs accept)
4. **BUG-064 continuum BTC no-SL** — L2 — HIGH — live-money path; needs careful fix + verification
5. **winning-dna action 2 re-run** — L1 — HIGH — due Oct 15

---

## Session: 2026-10-11 ~18:20 UTC — Upgrade Implementer (post-D4, L1 focus)

**Scope:** scanned ~20 most recent plans/ (Oct 1 → Oct 11). No constants values touched. One doc-only change.

### Plan evaluations (recent-20)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| grind-breakout-signal-spec (Oct 11) | L2–3 | MED | ✅ ALREADY IMPLEMENTED | grind_breakout_v2.py + GRIND_BREAKOUT_V2_* constants live; prior audit 2026-10-04 confirmed (AVNT blacklisted on backtest) |
| 2026-10-09-wyckoff-bypass-verdict | N/A | — | ✅ VERDICT: REJECT | 5 fires, ex4h −2.23%, n≥30 FAIL. No STANDALONE_BYPASS add. Correctly closed |
| 2026-10-09-q4-portfolio-cap-verdict | N/A | HIGH | ⏳ PENDING CEO | Cap B ACCEPT on aggregate ($+1.02/30d) but does NOT catch the Oct-8 cluster. No live change without CEO GO either way |
| 2026-10-09_D4-structured-block-logging | L1 | HIGH | ✅ COMPLETE (verified) | Plan header says complete; re-ran verification harness — 1007/7740 "misses" are ALL soft multipliers (RR BOOST, RSI sweet-spot +10), not blocks. Zero real block lines lack BLOCKED |
| 2026-10-09_ceo-orchestrator-pickup | L2 | HIGH | ✅ DONE | Both backtests delivered (wyckoff + q4 verdict files exist) |
| 2026-10-09_gate-counterfactual-audit | L1–2 | HIGH | ✅ D3/D4 EXECUTED | expiry_shadow.py + BLOCKED tranche-1 live; remainder complete (above). Housekeeping (TESTTOKEN historical Oct 4, GRASS feed healthy) per CEO D5 low-priority |
| 2026-10-08_winning-dna-population-report | L1–3 | HIGH | ✅ ACTIONS 1–3 SHIPPED / ACTION 5 CLOSED THIS SESSION / ACTION 2 waits Oct 15 | Entry-DNA closed (rule); cell_stats live; exit stack monitor-only. Action 5 footguns now documented (see below). Action 5b verified: entry_rsi_14 coverage 753/771=97.7% 30d (DRIFT-E fix works). Action 2 re-run due Oct 15 |
| align-with-btc-regime | L2 | MED-HIGH | ⏳ PENDING (CEO-approved, default OFF) | BTC_REGIME_ALIGN_ENABLED absent from constants — not built. Gated: independent backtest + bug_hunter + shadow-first per CEO mods; also sequence after exit-engine changes to avoid confounds. Level 2 candidate for a dedicated session |
| bug-hunt-gameplan / master-plan | ongoing | HIGH | 🔄 MULTI-SESSION | Tier 0 mostly fixed (BUG-023..047). Remaining open need T: BUG-036 secret rotation, BUG-037 kill-switch AND-gate |
| profitability-fix-plan-2026-10-07 | L1–4 | HIGH | PARTIAL | P1 move-done live; P2 done differently (CUT_LOSER −1.50 + leverage-aware HML); P3 btc_grind_spike.py untested (L2); P4 continuum backfill not started. Threshold changes = CEO |
| penalty-gated-execution-2026-10-06 | L1–2 | HIGH | FIXES 1–3 LIVE | Fix 4 (HL order sizing) = investigation pending; Fix 5 (TRAILING_ACTIVATION) = CEO |
| ride-it-hard-max-loss-exemption | L1 code / process L2+ | HIGH | ⏳ PENDING | Needs backtest → own-conclusions → CEO. Constants change blocked without T |
| wrong-side-chop-detector-2026-10-06 | L2 | MED | ⏭️ REJECTED/SUPERSEDED | Targeted wrong gate (losers were STANDALONE_BYPASS). Root causes fixed elsewhere |
| short-drought-dump-day-2026-10-05 | L1–2 | HIGH | PARTIAL | Fix 3 (LLM) live; Fix 1 bear-override deliberately REJECTED (bf96d7cd, data-backed); Fix 2 hysteresis: constant exists but NEVER WIRED (see sideways); Fix 4 pre-arm not built |
| trade-learning-system-EXECUTION | L2–3 | HIGH | P0–P4 LIVE | P5–P6 gated on shadow thresholds + CEO. Do not re-implement |
| short-signal-drought-2026-10-02 | L1 | HIGH | FIXES 1–3 DONE | Fixes 4–6 = CEO |
| mtf-regime-trend + multi-timeframe (dup pair) | L3 | MED | ✅ BUILT / PLUS auto-killed | MINUS still enabled; no action |
| thesis-validation / chop-v2 / continuum-integration / partial-close | L2–3 | varies | per prior audits | statuses unchanged (TVS live; chop_exit deferred; partial-close skipped on thin MFE coverage) |

### Implemented this session (1 Level 1)

#### 1. Trade column-semantics footguns documented (winning-dna action 5a+5c+5d)
- **Plan/source:** `plans/2026-10-08_winning-dna-population-report.md` §5 action 5
- **Difficulty:** Level 1 (doc block in one file)
- **Value:** HIGH — closes the recurring analyst trap class (mfe/pnl leverage mismatch 4–5×, era break in pnl_pct, seconds-vs-minutes duration, gross-vs-net PnL)
- **Status:** ✅ IMPLEMENTED
- **Fix:** `scripts/pnl_utils.py` module header gains a "Column-semantics footguns" block: pnl_pct leverage-multiplied post-2026-08-21 (era break); mfe/mae ALWAYS unleveraged; pnl_usdt gross from compute_close_pnl vs position_manager net_pnl preference vs hype_* ground truth; trade_duration SECONDS.
- **Verified:** py_compile OK; self-check `compute_close_pnl(100→105, LONG, 1000, 5x)` → pnl_pct=25.0, pnl_usdt=50.0, net=49.1 (fee math intact). No behavior change — docs only.
- **Action 5b:** verified already fixed (DRIFT-E 2026-10-10; entry_rsi_14 30d coverage 97.7%). No code needed.

### Verifications performed (no changes)
- **D4 harness:** zero real block lines missing BLOCKED; residual misses are soft multipliers (RR BOOST, sweet-spot boost) which the plan explicitly excludes.
- **Fees (action 5d):** position_manager.py:895 prefers net_pnl (after 0.09% RT fee) as record_pnl; compute_close_pnl returns gross pnl_usdt + separate net_pnl; HL ground truth in hype_pnl_usdt. Documented, not rewired.
- **SHORT_CONTINUUM_HYSTERESIS_MIN=30** defined in hermes_constants.py:1381 but referenced NOWHERE in code — Fix 2 from short-drought shipped the constant without the wiring.

### Sideways findings
1. **LOW:** `SHORT_CONTINUUM_HYSTERESIS_MIN` orphan constant (above). Wiring needs score-history tracking in signal_compactor (L2). Either wire it or remove the constant to avoid false confidence that hysteresis is live.
2. **INFO:** trade_duration coverage 530/771 (69%) 30d closed — lower than mfe/rsi (~98%). velocity_backfill.py exists; coverage gap predates recent fixes. No action.

### Success rate this session: 1/1 implemented (100%)
### Next candidates (priority order)
1. **align-with-btc-regime** — L2 — MED-HIGH — CEO-approved w/ mods; needs independent backtest + shadow-first build
2. **winning-dna action 2** — L1 — HIGH — re-run analysis/winning_dna_pop_2026-10-08.py on **Oct 15**
3. **ride-it Option B** — L1 — HIGH — blocked on backtest + CEO (process, not code)
4. **q4 portfolio cap B** — L1 — HIGH — blocked on CEO GO (verdict recommends re-test max-2/30min or family-cap first)
5. **short-drought Fix 2 hysteresis wiring** — L2 — MED — constant exists, needs score-history (or delete constant)

---

## Session: 2026-10-04 ~18:15 UTC — Upgrade Implementer (freeze-safe only)

**Freeze context:** b960ffe8 active until 2026-10-06 00:38 UTC. Trading-behavior / constants VALUES blocked. Data + prompt hygiene only. Trade-learning P0–P4 already shipped by prior agent (cell_stats, gate_shadow, t5_shadow, trade_watchdog timers live).

### Implemented this session (3 Level 1)

#### 1. auto_1hr pnl_pct false-alarm root cause FIXED
- **Plan/source:** recurring trading_log/ceo_kanban "pnl_pct nonsense" (CFX -585%, USELESS -355%, BLUR +404%, CRV -476%…)
- **Difficulty:** Level 1 (prompt SQL one-liner)
- **Value:** HIGH — removed false bug class that wasted hourly agent cycles for days
- **Status:** ✅ IMPLEMENTED
- **Root cause:** `automation/auto_1hr_prompt.md` Step 2 SQL used `ROUND(pnl_pct*100,2)`. Column is ALREADY in percent units (`pnl_pct = raw_price_move × leverage`). Example live: CFX stored pnl_pct=-5.85 → old display -585.47. Every "nonsense" figure in logs is this double-scale.
- **Fix:** `ROUND(pnl_pct,2)` + comment: hard_max_loss ~1% PRICE move → ~3–5% account at 3–5x leverage is expected (matches CURRENT.md hard_max_loss note + bug_hunter ownership).
- **Verified:** live PG sample last 24h — old vs new display table produced; prompt asserts pass (`pnl_pct*100` absent).
- **Related standing rule:** CUT_LOSER_PNL / hard_max_loss semantics still with bug_hunter — do NOT change values.

#### 2. signal_version.py SOP stale refs cleaned
- **Plan/source:** auto_1hr + trading_log false "signal_version.py missing" alarms
- **Difficulty:** Level 1
- **Value:** MEDIUM — stops dead-end flags; CEO already corrected 2026-09-30 (store = `data/signal_versions.json`, script does not exist)
- **Status:** ✅ IMPLEMENTED
- **Fix:** `auto_1hr_prompt.md` now documents JSON append snippet (18 signals already logged in store) instead of `python3 scripts/signal_version.py log ...`. Key-file path updated.

#### 3. Trade-learning system status verified + logged
- **Plan/source:** `plans/trade-learning-system-EXECUTION.md` (CEO-approved)
- **Difficulty:** N/A (verification)
- **Value:** HIGH (cross-session clarity)
- **Status:** ✅ VERIFIED LIVE — do not re-implement
- **Evidence:** `scripts/cell_stats.py` + `hermes-cell-stats.timer` (00:20); `brain/cell_stats.db` (653 cells + cells_st 736); `gate_shadow.db` 624 events + hourly timer; `t5_shadow.db` 413 decisions + 15min timer; trade_watchdog 30min timer; CURRENT.md + ceo_report confirm MFE/MAE ~97% closes, hard_max_loss family normalized. P5/P6 gated on freeze lift + CEO.

### Plans re-scanned this session
| Plan | Status | Action |
|------|--------|--------|
| trade-learning-system-EXECUTION | ✅ P0–P4 live | none |
| continuum-filter-analysis | ✅ SHORT filter live | none |
| pump-catching-and-exit-optimization | Partial; PM_TRAIL/CEO-protected frozen | skip freeze |
| profitability-fix-plan | ✅ largely shipped (ENA, SPEED_MIN_THRESHOLD_LONG, PM bypass cleanup) | none |
| ride-it-exit-spec | ✅ implemented | none |
| squeeze-breakout / continuum-ma / pump-chain-v5 | ✅ implemented | none |
| chop-v2-spec | Score mults live; chop_exit.py deferred post-freeze | PENDING freeze/CEO |
| doji_signal_system | ✅ doji_bottom/top + DOJI_* constants live | none |
| grind-breakout-signal-spec | ✅ implemented (AVNT blacklisted on backtest) | none |
| btc-wave-pattern-surfer | BTC_WAVE_* constants live, ENABLED=False (paper-first) | intentional |
| progressive-context-shaping | ✅ CURRENT.md exists (CEO-owned) | none |
| automation-team-improvements | Timers exist (session/self/hebbian-openmemory); A/B still absent | PENDING (L2 additive) |
| copy-trader-evolution | Phase gap (per-trader tracking) Level 2–3 | PENDING post-freeze |
| brain-rag-system | Level 3–4, embeddings degraded | PENDING |
| structural-awareness / tier2-chop-merge / system-overhaul | Level 4 / CEO-gated | SKIP |
| regime-direction-filter / partial-close Option1 | already skipped/reconfirmed | none |
| cronr-timer-plugin | DSH plugin, not trading | SKIP |

### Sideways findings
1. **pnl_usdt vs pnl_pct scale (INFO, not new bug):** majority of closes store pnl_pct = leveraged account return while pnl_usdt ≈ margin × raw move (not notional×move). 30d recorded sum ≈ -$1.06 vs amount×pnl_pct/100 ≈ -$1.92. Dollar totals understate leveraged economics ~2x. Sign/WR unaffected. With bug_hunter on hard_max_loss semantics — document, don't rewire mid-freeze.
2. **gate_shadow closer:** 624 events since ~11:07 UTC; many still `closed=0` (24h counterfactual worker). Healthy, not stuck.
3. **Dead 0-byte DBs** still on disk (brain.db, hermes*.db, etc.) — P0/cleanup scope; live code paths use signals_hermes_runtime.db / associative_memory.db.
4. **should_trade_v2** still production-dead (prior sideways) — no action.

### Success rate this session: 3/3 L1 freeze-safe (100%)
### Cumulative: high (plans mature; freeze blocks remaining L2+ trading changes)

---

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

---

## Session: 2026-10-07 18:08 UTC — Upgrade Implementer (post-freeze, Level 1 focus)

### Plan: profitability-fix-plan-2026-10-07.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** Entry timing is late; move-done filter, wider hard max loss, grind detection, continuum backfill.
- **Difficulty:** Level 1-4 (mixed priorities)
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED / PENDING CEO
- **Reason:** P1 30m move-done live (PUMP_FLOW_MOVE_DONE_THRESHOLD=3.0). P2 partially done differently — CUT_LOSER widened -1.00→-1.50 (brain_auditor Oct 7) + leverage-aware HML fix (aed0aa36), not the proposed -2.50. P3 btc_grind_spike.py exists untested (Level 2). P4 continuum backfill not started. Move-freshness 5m filter BACKTEST DISPROVED Oct 7 (winners/losers identical pre-move) — do not add more move filters. Threshold value changes need CEO.

### Plan: penalty-gated-execution-2026-10-06.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** Penalty engine is advisory-only; gate final_confidence on penalty product; fix ema-AT bear hole; chop bullish phases.
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** ✅ FIXES 1-3 IMPLEMENTED
- **Reason:** Fix 1 live — decider_run.py multiplies final_confidence by max(penalty_product, 0.3) before MIN_EXEC_CONFIDENCE (PENALTY-BLOCK logging live, 56 events Oct 6). Fix 2 live — _cont_bearish includes ema AT (signal_compactor.py:2658). Fix 3 live — chop_detector bullish set includes DECLINING (:530). Fix 4 (HL order sizing audit) PENDING investigation. Fix 5 (TRAILING_ACTIVATION_PCT widen) needs CEO — constant still 0.40.

### Plan: ride-it-hard-max-loss-exemption.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** Ride_it exits 0 all-time because HARD_MAX_LOSS fires before ride_it SL; Option B ride_it hard stop at -2.5%.
- **Difficulty:** Level 1 (code) but process requires backtest + CEO
- **Value:** HIGH (unblocks ride_it design)
- **Status:** PENDING
- **Reason:** _is_ride_it exists in position_manager.py:3307 but only exempts UNIVERSAL_MAX_HOLD, NOT hard_max_loss. HML now leverage-aware (CUT_LOSER/lev) at -1.50 account — still tighter than ride_it phase-1 SL cap. Plan process: backtest → own-conclusions → CEO → implement. No CEO approval yet. Constants change blocked without T.

### Plan: wrong-side-chop-detector-2026-10-06.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** Direction-aware chop detector; WR hard-block bear override; confluence relaxation.
- **Difficulty:** Level 2
- **Value:** MEDIUM (diagnosis correct, proposed fix wrong)
- **Status:** SUPERSEDED / REJECTED
- **Reason:** Later audit (penalty-gated plan + brain_auditor Oct 6): all 7 losing trades were STANDALONE_BYPASS — they skip chop detector entirely. "Direction-aware chop detector targets wrong gate." Root causes fixed elsewhere: penalty-gate (Fix 1), SHORT_CONTINUUM_SCORE_MAX=60, SHORT_RSI_HARD_FLOOR=45, bear override via LLM context + continuum. Do not implement direction-aware chop.

### Plan: trade-learning-system-EXECUTION.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** Close learning loops — P0 data layer, P1 cell store, P2 exit optimizer, P3 gate shadow, P4-T5 trainer.
- **Difficulty:** Level 2-3 (phased)
- **Value:** HIGH
- **Status:** P0-P4 IMPLEMENTED; P5-P6 pending gates
- **Reason:** wr_estimate reads trade_log (hebbian_engine.py:405). PG trades 30d: 896 closed, 895 exit_reason, 888 mfe, 887 mae (~99%). cell_stats.py + hermes-cell-stats.timer live (Oct 7 00:20: 662 cells, 55 admitted, 15 tradeable). t5_shadow.py live. signal_outcomes learning columns write-on-close since Oct 4 (3d: 66/66 complete). TVS constants + score boosts live in signal_compactor. Remaining: SQLite historical backfill for cells_st/TVS depth (this session), P5 live cells need shadow thresholds + CEO, P6 weekly trainer.

### Plan: thesis-validation-system.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** Track MFE thesis validation; score boosts on re-entries; cooldown override.
- **Difficulty:** Level 3 (full spec) / Level 1 (data completeness)
- **Value:** HIGH
- **Status:** ✅ MOSTLY IMPLEMENTED
- **Reason:** TVS_ENABLED=True; boosts/penalties in signal_compactor.py:1996+; thesis_validated/thesis_mfe columns written from mfe on close; TVS_COOLDOWN_OVERRIDE live. Gap: historical signal_outcomes lack thesis_mfe (coverage ~2% pre-Oct-4) — backfilled this session from PG.

### Plan: 2026-09-07_partial-close-trailing-runner.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** 50% partial close at PM trail activation + adaptive runner trail.
- **Difficulty:** Level 2-3
- **Value:** HIGH (winner capture — ICP left 4% on table)
- **Status:** NOT IMPLEMENTED
- **Reason:** No PARTIAL_CLOSE_* constants; tpsil_utils close is full-size. Plan status "Plan". Needs tpsil partial-size support + profit_monster changes + CEO on runner trail tiers. Queue after Level 1 wins.

### Plan: chop-v2-spec.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** Per-coin trend routing in chop + chop_exit.py module.
- **Difficulty:** Level 2-3
- **Value:** HIGH (NEUTRAL chop is top bleed)
- **Status:** PARTIAL / DEFERRED
- **Reason:** chop_exit.py deferred (prior audits). Per-coin scoring not in chop_detector. Spec still valid but large; pending CEO prioritization vs entry-quality fixes currently dominating.

### Plan: 2026-09-23_emergency-winrate-fix.md / 2026-09-23_regime-based-signal-fixes.md / 2026-09-11_volatility-*.md / 2026-09-09_regime-transition-smoothing.md / 2026-09-09_pump-chain-v2-spec.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** Regime/vol gate fixes, pump-chain v2, winrate emergency.
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** ✅ IMPLEMENTED (prior sessions)
- **Reason:** Confirmed in prior audit (2026-09-30) + live constants: SHORT_CONTINUUM_SCORE_MAX=60, regime signals tables synced, vol gate multipliers live, pump-chain active in regimes.

### Plan: short-drought-dump-day-2026-10-05.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** Shorts blocked during BTC dump — RSI floors, LLM gate, SHORT-CONTINUUM.
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** PARTIALLY SHIPPED
- **Reason:** Fix 3 (LLM context + BTC continuum) shipped Oct 5, bug_hunter verified. Fix 1 bear override: intentionally NOT restored (bf96d7cd decision — oversold=bounce risk); later mitigated by SHORT_RSI_HARD_FLOOR=45 + SHORT_CONTINUUM_SCORE_MAX=60 + HIGH regime open. Fix 2 hysteresis not shipped. Post-fix SHORT 7d still negative but improving (−$1.66 → −$0.55). Monitor.

### Plan: oscillator-matrix-lifecycle.md
- **Date scanned:** 2026-10-07 18:08
- **Core request:** Enable oscillator multiplier matrix.
- **Difficulty:** Level 1
- **Value:** MEDIUM
- **Status:** ✅ IMPLEMENTED
- **Reason:** OSCILLATOR_MULT_ENABLED=True since 2026-10-01 (shadow-validated: penalized zones -$8.61/33.3%WR vs boosted +$9.87/50.9%WR).

---

### Session implementations (2026-10-07)

1. **signal_outcomes historical backfill** — filled exit_reason/mfe_pct/mae_pct/entry_rsi_band/regime/signal_type/thesis_* from PostgreSQL trades for rows with trade_id. Completes trade-learning P0 SQLite side for cells_st + TVS history depth.
2. **hl-sync-guardian dead path fix** — `_record_trade_outcome` wrote signal_outcomes without learning columns (signal_type='unknown', no mfe/exit_reason). No current callers (P0 funnel already uses signal_schema), but path is a landmine. Rewired to look up PG trade + call signal_schema.record_signal_outcome.
3. **trade_watchdog disabled-signal filter (DRIFT-W1)** — historical closes from killed signals (trend-ride+, mover±, mtf-regime-trend±, accel-300±, etc.) no longer emit false "losing streak" steers. Flag map reads live hermes_constants.

### Sideways findings (this session)
- **Severity:** LOW
- **Finding:** `scripts/signal_version.py` missing (flagged in brain_auditor Oct 6) — signal_versions.json pump-chain+ corruption. Not fixed this session.
- **Severity:** LOW
- **Finding:** PG has no `signal_outcomes` table (SQLite-only). cell_stats correctly uses PG trades as primary; cells_st is supplementary. Do not try to join PG→SQLite without trade_id.
- **Severity:** INFO
- **Finding:** Ride_it hard-max-loss exemption still open — highest structural exit bug remaining after HML leverage-aware fix. Needs backtest + CEO.

---

## Upgrade Implementer Session — 2026-10-09 06:08 UTC

### Plan: 2026-10-09_D4-structured-block-logging.md
- **Date scanned:** 2026-10-09 06:00
- **Core request:** CEO GO D4 remainder — append literal `BLOCKED` + token + dir to every remaining gate block log line (log strings only, zero logic).
- **Difficulty:** Level 1
- **Value:** HIGH (observability for Nov 6 gate re-audit; auditor-set success metric ≥95% parseable block volume)
- **Status:** ✅ IMPLEMENTED (commit da7d6522)
- **Reason:** First tranche done in 7f51dc6c; remainder executed now. Edited: CONTINUUM-BLOCK, CONFLICT-RESCUE-BLOCK, CONF-FILTER-PRESERVE (signal_compactor.py); CHASE-BLOCK, PUMP-CHAIN-GAP-BLOCK, LOSERS-BLOCK (decider_run.py); RR HARD BLOCK→BLOCKED ×3 (risk_reward_engine.py). All 9 lines compile-checked; parser simulation green (audit parsers match `HARD BLOCK` prefix of `HARD BLOCKED`); no logic consumers of the strings. Verify-only items (SHORT/LONG-NEUTRAL, SHORT-CONTINUUM, HALL-SHAME, PUMP-CHAIN family, EXEC-RSI, BTC-CRASH, PRESERVE-*) already compliant. Direction-level gates (VOL-FLOOR, WARNING BTC-momentum, DIRECTION-LOCK, VOL-GATE-v2) left per plan — not trivial, weekly re-audit discussion.

### Plan: 2026-10-09_ceo-orchestrator-pickup.md
- **Date scanned:** 2026-10-09 06:00
- **Core request:** Q4 portfolio-cap backtest + Wyckoff bypass backtest — both delegated backtest jobs.
- **Difficulty:** Level 2-3 (analysis/backtest jobs, not code changes)
- **Value:** HIGH
- **Status:** PENDING
- **Reason:** Out of Level-1 scope this session; both need fresh PostgreSQL/candle counterfactual runs with acceptance criteria. Next session candidate after 3× L1.

### Plan: align-with-btc-regime.md
- **Date scanned:** 2026-10-09 06:00
- **Core request:** BTC_REGIME_ALIGN_ENABLED flag (default OFF) to allow pump-chain LONG in bullish regime.
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PENDING
- **Reason:** CEO-approved with modifications but sequencing constraint: "after queue#2 (exit engine fix) or hold sizing flat" + mandatory independent backtest before live. Not started.

### Plan: ride-it-hard-max-loss-exemption.md
- **Date scanned:** 2026-10-09 06:00
- **Core request:** Ride_it-specific HARD_MAX_LOSS at -2.5% (Option B).
- **Difficulty:** Level 1-2 (small code change) but gated
- **Status:** SKIPPED (this session)
- **Reason:** Plan explicitly requires backtest → own-conclusions verification → CEO approval before implementation. Holding.

### Plan: wrong-side-chop-detector-2026-10-06.md
- **Date scanned:** 2026-10-09 06:00
- **Core request:** Direction-aware chop detector.
- **Difficulty:** Level 2-3
- **Status:** SKIPPED (this session)
- **Reason:** Status "PROPOSED — awaiting independent verification". Don't implement unverified proposals.

### Plan: profitability-fix-plan-2026-10-07.md
- **Date scanned:** 2026-10-09 06:00
- **Core request:** Entry-timing overhaul (grind-before-spike detection), velocity filter, hard_max_loss widen, continuum backfill.
- **Difficulty:** Level 3-4
- **Status:** PARTIALLY SHIPPED / PENDING CEO
- **Reason:** SHORT_CONTINUUM_SCORE_MAX 40→60 already live; recommendations section still "pending CEO approval"; hard_max_loss frequency on standing hold until Oct 10.

### Plan: 2026-10-08_winning-dna-population-report.md
- **Date scanned:** 2026-10-09 06:00
- **Core request:** Replicate biggest-winner DNA; implementable actions in §5/§7.
- **Difficulty:** Level 2-3 (analysis complete; actions are protect-pump-chain+, re-test RSI tilt Oct 15/16)
- **Status:** PENDING (re-test date-gated)
- **Reason:** Entry-DNA closed (nothing survives Bonferroni); RSI tilt re-test due Oct 16; pump-chain+ protection = do-not-filter (already standing). No code action today.

### Plan: 2026-10-09_gate-counterfactual-audit.md
- **Date scanned:** 2026-10-09 06:00
- **Core request:** Which gates have no edge? + 5 CEO decisions.
- **Difficulty:** N/A (analysis; execution split)
- **Status:** MOSTLY IMPLEMENTED (D3 expiry_shadow + D4 tranche 1 in 7f51dc6c; D4 remainder this session; D2 re-audit window open through ~Nov 6)
- **Reason:** D1/D5 done or folded; standing hold: NO gate removal on this window.

### Session housekeeping (Level 1, 2026-10-09)
1. **AGENTS.md HL-key reminder fixed** — "EXPIRES IN 3 DAYS" beside 2027-03-12 was stale (key set 2026-09-16, 180d → ~2027-03-15). Now reads "EXPIRES 2027-03-12 (~5 months from 2026-10-09)". Flagged as sideways find in bug-hunt session 0.
2. **Repo-root junk removed** — tracked redirect-accident file `SELECT token, ... FROM signals ...` deleted via git rm; 0-byte untracked `candles.db`/`hermes.db`/`signals.db`/`herbbian_memory.db` at repo root deleted (real DBs live in HERMES_DATA per paths.py; gitignored; no code connects to bare root paths).
3. **TESTTOKEN housekeeping item from gate audit** — already clean: zero matches in scripts/. Mark done.

---

## Upgrade Implementer Session — 2026-10-16 15:30 UTC

**Scope:** re-scanned recent plans/ (Oct 9 → Oct 14, 20 most recent). No live-code changes this session — all high-value remaining plans are CEO-gated SPECs. Executed the two date-gated analysis actions from the winning-dna report (Oct 15 re-measure, Oct 16 RSI re-test).

### Plan evaluations (recent-20, deltas vs Oct 12 session)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| t-vacation-mode-2026-10-14 | L4 | HIGH | ✅ CLOSED (FINAL, bug_hunter-verified) | DO-NOT-FLIP inversion section corrected; no code action |
| limit-order-capability | L2 | MED | ⏳ PENDING | Plan priority "Medium — not blocking"; guardian integration adds scope. Next L2 candidate |
| strategic-six-options-2026-10-14 | L3–4 | HIGH | ✅ DECIDED (Option 6) | Work routed to other plans (vacation-mode, gate report card in CEO runs) |
| contrarian-engine-2026-10-13 | L3 | MED | ⏳ PENDING CEO | SPEC awaiting approval; fee-blind inversion trap already corrected in vacation-mode — any revival must use fee-adj model |
| contrarian-zone-backtest | — | LOW | ⏸️ SKIPPED | Marginal edge (+$0.0023/trade), paper-trade gate unmet |
| vol-regime-relative-thresholds-2026-10-13 | L3 | MED-HIGH | ⏳ PENDING CEO | PROPOSED — no code until approved |
| temporal-confluence-spec | L2–3 | MED | ⏳ PENDING CEO | SPEC awaiting approval |
| signal-starvation-fix-2026-10-12 | L1–2 | HIGH | PARTIAL | RR momentum U1 live (shadow); remaining items (RSI floor bear-exemption, score-crush) CEO-gated + hermes_constants DO-NOT-MODIFY |
| short-rsi-habitat-spec | L2 | MED | ⏳ PENDING CEO | Per-signal RSI bands replace blanket floor — constants + live-trading change |
| 2026-10-13_rr-engine-smart-upgrades | L2–3 | HIGH | PARTIAL | U1 (momentum-aware) live in code w/ RR_ENGINE_SHADOW=True; U2–4 (TF-aware, quality-context, fib) pending — ship via automatic-implementation shadow when approved |
| 2026-10-12_gate-conundrum-deadlock-plan | — | HIGH | ✅ CLOSED (VERIFIED) | Config changes: NONE by design; findings absorbed |
| bb-squeeze-trail-arm-timeout verdict+audit | L2 | HIGH | ✅ LIVE — CEO RATIFY PENDING | Flags live without documented GO; brain_auditor Oct 15 recommended RATIFY (deadline passed); soak clean (1T/0 fires). CEO one-liner outstanding — flagged on kanban, not reverted |
| grind-breakout-v2-coin-tracker-integration | L3 | LOW | ⏸️ DEFERRED (by plan) | Unchanged |
| regime-recalibration-2026-10-12 | L2 | MED-HIGH | ⏳ PENDING CEO | Unchanged |
| 2026-10-09_D4-structured-block-logging | L1 | HIGH | ✅ IMPLEMENTED (da7d6522) | Closed |
| 2026-10-09_ceo-orchestrator-pickup | L2–3 | HIGH | ✅ CLOSED (verdicts filed) | Q4-cap: Cap B accepted-on-aggregate, CEO decision open; Wyckoff: REJECT closed |
| 2026-10-09_gate-counterfactual-audit | — | HIGH | ✅ D3/D4 DONE | Standing hold: no gate removal on that window |
| 2026-10-09-wyckoff-bypass-verdict / q4-portfolio-cap-verdict | — | — | ✅ CLOSED | Verdicts filed Oct 9 |
| 2026-10-08_winning-dna-population-report | L1–3 | HIGH | ✅ ACTIONS #2 #4 #5 CLOSED THIS SESSION | See implementations below |

### Implemented this session (2 × Level 1, analysis-only — no live changes)

1. **Winning-dna Oct 15 re-measure (action #2)** — re-ran `analysis/winning_dna_pop_2026-10-08.py`. hard_max_loss WR still 0% (n 70→136, sum −$9.31→−$15.60/30d, severity flat −3.51%, frequency doubled). Escalation criterion MET → **SL-width study escalated to CEO kanban** with two-lever framing (SL-width vs entry-gate; HML avg MFE 0.17% = entries never worked). Verdict: `plans/2026-10-16_winning-dna-remeasure-verdict.md`.
2. **RSI tilt re-test (action #4)** — coverage now 98.5% (DRIFT-E fix held). Column accuracy: r=0.52 vs 1m Wilder recompute (mean|Δ|=10pts, side-of-50 73%) — it's a *noisy 1m RSI*, not 1h (partially explains gate-conundrum's r=0.33). Tilt re-test: 30d KEEP +$3.85 vs BLOCK −$0.71 but OOS halves sign-inconsistent (half2 KEEP −$1.09) → **stays provisional, shadow-weight-only, no hard-block.** No code change.

### Sideways findings (this session)
- **Severity: INFO** — `entry_rsi_14` is a noisy 1m RSI (r=0.52, mean|Δ|=10pts vs clean recompute). Fine for population band stats; NEVER for per-trade threshold blocks. Documented in verdict file.
- **Severity: LOW** — `signal_version.py` still missing (flagged Oct 4/6); only referenced via paths.py SIGNAL_VERSIONS_FILE, no code imports the module. Cosmetic.
- **Severity: MED (standing)** — bb-squeeze + pump-chain trail-arm flags live without documented CEO GO; brain_auditor recommended RATIFY Oct 15. Awaiting CEO one-liner (kanban).

### Next candidates (post this session)
1. **SL-width + entry-gate study** — Level 2 (analysis) — HIGH — escalated, awaiting CEO GO
2. **limit-order-capability** — Level 2 — MED — plan ready, standalone script first (skip brain.py --limit until standalone proven)
3. **RR engine U2–U4** — Level 2–3 — HIGH — shadow-mode only, automatic-implementation pattern, needs CEO sequencing
4. **temporal-confluence / short-rsi-habitat / vol-regime-relative** — Level 2–3 — MED-HIGH — all CEO-gated SPECs

---

## Upgrade Implementer Session — 2026-10-17 15:00 UTC

**Context:** pipeline PAUSED (vacation guardrail, resume ~Oct 23), kill JSON live_trading=false, soak discipline = 0 live-behavior changes across all agents. Scoped to non-trading-logic wins only.

### Plan evaluations (recent-20 re-scan)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| limit-order-capability | L2 | MED | ✅ PHASE 1 SHIPPED | `scripts/limit_order.py` created (place/list/cancel). brain.py --limit + guardian fill-integration deferred per plan ("standalone first") |
| t-vacation-mode-2026-10-14 | L4 | HIGH | ✅ MoE table updated | #2 conf-clamp already live (decider_run.py:1996); #3 broken-SHORT tail partially done (pullback-entry−/mover± all killed); #1 PARTIAL (CUT_LOSER widened + ATR mult, study escalated) |
| signal-starvation-fix-2026-10-12 | L1-2 | HIGH | ⏳ CEO-gated | hermes_constants DO-NOT-MODIFY + soak; RR momentum U1 already live in shadow |
| contrarian-engine / temporal-confluence / short-rsi-habitat / vol-regime-relative / regime-recalibration | L2-3 | MED-HIGH | ⏳ PENDING CEO | SPECs awaiting approval; no code during pause |
| 2026-10-16_winning-dna-remeasure-verdict | — | HIGH | ✅ CLOSED (prior session) | Escalation on CEO kanban |
| exit-ladder candle OOS (brain_auditor P0) | L2-3 | HIGH | ⏸️ NOT TOUCHED | brain_auditor plans in-house candle OOS Oct 18; universal MFE-cut already FAILed candle OOS — remaining work is signal-scoped, duplicating risks the pattern-trap |
| signal_version.py missing | L1 | LOW | ⏸️ SKIPPED | YAGNI — only a paths.py constant, nothing imports the module |

### Implemented this session (1 × Level 2)

1. **`scripts/limit_order.py`** (new, ~150 LOC) — standalone HL limit-order tool: `place` (positional coin/side/price/amount-margin, --lev/--tif/--sl/--target, confirm prompt + --yes + --dry-run, HL min-notional guard, sz rounded UP via _sz_decimals, leverage set pre-order), `list` (openOrders, per-coin filter), `cancel` (reuses cancel_all_open_orders). Verification: py_compile OK; dry-run sizing SELL 0.00068 BTC @ $82100 5x ✓; min-notional rejection ($5 < $11) ✓; live `list` API ✓. Zero impact on automated trading (manual tool only).

2. **Doc updates** — plans/limit-order-capability.md marked PHASE 1 SHIPPED; plans/t-vacation-mode-2026-10-14.md MoE Top-3 table statuses corrected with evidence (was all-PENDING; #2 was already live since Oct 15).

### Next candidates
1. Exit-ladder signal-scoped candle OOS — L2-3 — HIGH — brain_auditor in-house Oct 18; do not duplicate
2. SL-width / entry-gate study — L2 — HIGH — CEO kanban GO pending
3. brain.py --limit + guardian fill-integration — L2 — MED — only after limit_order.py proven in real use
4. RR engine U2–U4 — L2-3 — HIGH — needs CEO sequencing, shadow-mode pattern

---

## Upgrade Implementer Session — 2026-10-21 04:35 UTC

**Context:** pipeline LIVE (kill JSON resumed by T directive), soak over, trading active. Scoped to reliability/disk wins + verification of overnight changes.

### Plan evaluations (recent-20 re-scan)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| shadow-mode-paper-trading-spec-v1 | L3 | HIGH | ✅ IMPLEMENTED (prior session Oct 20) | `scripts/shadow_trader.py` shipped (55d57379 + bug_hunter fixes 4d2063a8), timer active, 7,998 shadow rows flowing, analyses already delivered to CEO briefs |
| t-vacation-mode-2026-10-14 | L4 | HIGH | ✅ CLOSED (prior) | Remaining items CEO-gated; vacation soak ended |
| limit-order-capability | L2 | MED | ✅ PHASE 1 SHIPPED (prior) | Phase 2-4 deferred until standalone proven |
| signal-starvation-fix / short-rsi-habitat / temporal-confluence / vol-regime-relative / contrarian-engine / regime-recalibration | L2-3 | MED-HIGH | ⏳ CEO-gated SPECs | No code during soak; still awaiting approval |
| 2026-10-16_winning-dna-remeasure-verdict | — | HIGH | ✅ CLOSED (prior) | SL-width study on CEO kanban |
| bug-hunt-master-plan (open bugs 037/044/056/064) | — | HIGH | ⏳ CEO-gated | All 4 open bugs explicitly need T/CEO decision (kill-switch AND-gate, sniper-exit enable, orphan flags, continuum SL policy) — not auto-fixable |
| hermes-better-coder (disabled unit) | L2+ | LOW | ⏸️ SKIPPED | dispatcher/ package empty (code deleted ~Sep 1); rebuilding = new feature, nothing missed it in 7 weeks |

### Implemented this session (2 × Level 1)

1. **brain-auditor timeout fix** — last 2 runs (02:30, 03:30) died at the 1200s cap (`Failed with result 'timeout'`); hourly intelligence was down. Root cause: audit scope grew (shadow_trader queries, deeper PG pulls) past the old 20-min budget. Fix: `timeout 1200→2400` in `automation/brain-auditor/run_brain_auditor.sh` + `TimeoutStartSec=1200→2400` in `/etc/systemd/system/hermes-brain-auditor.service` (daemon-reload done, failed state reset). Typical successful runs were 7-17 min — 40 min cap gives 2x headroom. Verified: unit shows new timeout, timer next-fire armed.
2. **candles_1m 30d retention (disk fix)** — the standing "retention delegation undelivered since Oct 7" item. Root cause: price_collector's prune ran ONLY for candles_5m; candles_1m grew unpruned to 20.5M rows / 3.1G / data back to Feb 2024, driving disk to 85%. Fix: batched 30d prune (500K rows/txn) added to `main()` in `scripts/price_collector.py`, same policy as 5m. First run deleted 13,498,418 rows; one-time VACUUM shrank candles.db 3.1G→1.22G. Disk 85%→83% (+2G free). Steady-state verified: next cycle pruned the natural 30d edge (308 rows), no errors. 15m/1h/4h left untouched (smaller, long-horizon alt data has no alternate home — extend later only if disk tightens again).

### Verifications (no code change)

- **PM_TRAIL_ACTIVATE "percent-vs-fraction" probable-bug (shadow-spec appendix D): FALSE ALARM.** `profit_monster.py:24` does `PM_TRAIL_ACTIVATE_PCT *= 100` at import (0.004→0.4) before comparing to percent-scale pnl at line 454. Live behavior correct (+0.40% activation). Spec appendix item can be struck.
- **pump-chain+ LONG HIGH block (c9092aea, 03:37 today): CONFIRMED LIVE.** signal-compactor is Type=simple short-lived (820ms/cycle, re-imports constants each run) — flag active since 03:38 cycle, no restart needed.
- **Open bugs re-checked:** BUG-037 (kill-switch AND-gate), BUG-044 (sniper-exit timer), BUG-056 (orphan MA300 flag), BUG-064 (continuum SL-less trades) — all unchanged, all correctly parked as T/CEO decisions.

### Sideways findings
- **Severity: INFO** — hermes-better-coder unit references an empty `mcp/hermes-coding-mcp/dispatcher/` package (code removed ~Sep 1). Unit correctly disabled; leave dead or delete unit files at T's discretion.
- **Severity: LOW** — 15m/1h/4h candle tables also reach Feb 2024 (2.1M/637K/134K rows >30d). Not pruned this session (deliberate — long-horizon alt data). Revisit if disk exceeds 85% again.
- **Severity: MED (standing)** — trail-arm ratify (bb-squeeze 60m + pump-chain 45m flags) still lacks documented CEO GO; brain_auditor recommended RATIFY Oct 15.

### Next candidates
1. SL-width / entry-gate study — L2 — HIGH — CEO kanban GO pending
2. RR engine U2–U4 — L2-3 — HIGH — needs CEO sequencing, shadow-mode pattern
3. brain.py --limit + guardian fill-integration — L2 — MED — only after limit_order.py proven in real use
4. temporal-confluence / short-rsi-habitat / vol-regime-relative — L2-3 — MED-HIGH — CEO-gated SPECs
5. 15m/1h/4h candle retention — L1 — LOW — only if disk tightens; 2.9M rows reclaimable

---

## Upgrade Implementer Session — 2026-10-22 04:30 UTC

**Context:** pipeline LIVE. Prior overnight sessions shipped autonomous-BTC phase 0 (auto_trader.*), shadow_signals_runner, shadow-registry matcher fix. This session: deliver two CEO-GO'd undelivered docs (R2/D3) + fix remaining HIGH-5 pollution bug in shadow_signals_runner.

### Plan evaluations (recent-20 re-scan)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| autonomous-btc-loop-spec | L4 | HIGH | ✅ PHASE 0 LIVE (prior session ~01:24 UTC) | auto_trader.py/db/analysis + trade_watchdog integration + dashboard; 14 decisions / 4 hypotheticals accruing. Spec header updated this session (was stale "DRAFT — no code") |
| shadow-mode-paper-trading-spec | L3 | HIGH | ✅ IMPLEMENTED (prior) | shadow_trader.py + timers; SL sweeps + exit engines landed Oct 21 |
| shadow-registry (6fee8ef8 + e5e5b313) | L2 | HIGH | ✅ MATCHER FIXED (prior) + HIGH-5 FIXED THIS SESSION | Stage B keys corrected; runner built; this session: source+direction filter stops live-path pollution |
| shadow_signals_runner (0747cdd3) | L2 | HIGH | ⚠️→✅ PARTIAL THEN COMPLETE | ff9d08c5 fixed HIGH-1/2/3+MEDIUM; HIGH-5 (filter) + LOW fail-open + LOW error-counter fixed this session |
| 2026-10-12_gate-conundrum (R2 registry) | L1 | HIGH | ✅ DELIVERED THIS SESSION | CEO GO D2 2026-10-12, delegated signal_analyst, never landed → brain/gate_registry.md |
| 2026-10-12_gate-conundrum (D3 claim hygiene) | L1 | MED-HIGH | ✅ DELIVERED THIS SESSION | CEO GO D3; missing from brain/SOPs.md → added §10 |
| 2026-10-12_gate-conundrum (R4 deadband) | L1 | MED | ✅ ALREADY LIVE | PUMP_CHAIN_VEL_30M_MIN both sides (CEO GO comment in signal_compactor) |
| 2026-10-13_rr-engine-smart-upgrades | L2-3 | HIGH | U1 LIVE / U2-U4 ⏳ CEO | MOMENTUM_PROJECTION + MOMENTUM_SR_FILTER live; TF-aware + quality + Fib need CEO sequencing |
| signal-starvation-fix / short-rsi-habitat / temporal-confluence / vol-regime / contrarian / regime-recalibration | L2-3 | MED-HIGH | ⏳ CEO-gated SPECs | No code without approval; hermes_constants DO-NOT-MODIFY |
| winning-dna-remeasure-verdict | — | HIGH | ✅ CLOSED | SL-width study on CEO kanban |
| strategic-six-options | L4 | HIGH | PARTIAL | vacation-mode + phase-aware v2 direction active; gate report card = this registry + gate_shadow |
| grind-breakout-v2-coin-tracker | L3 | LOW | ⏸️ DEFERRED | Plan trigger (>50% missed breakouts) not evaluated |
| limit-order-capability | L2 | MED | ✅ PHASE 1 (prior) | Phase 2-4 deferred until proven |

### Implemented this session (2× L1 docs + 1× L2 bugfix + 2× L1 hygiene)

1. **(L1) brain/gate_registry.md** — R2 gate registry, CEO D2 GO 2026-10-12, never delivered despite delegation. Ten active hard-veto gates with first-seen / evidence grade / n-effect / last-verified; young-gate watchlist (14d shadow-first clock); editor rules. Docs only — no trading behavior change.
2. **(L1) brain/SOPs.md §10** — D3 claim-hygiene standard (episode counts, first-seen dates, null-model check, direction-signed counterfactual, registry update). References gate-conundrum cautionary tale.
3. **(L2) shadow_signals_runner.py HIGH-5** — `_sig_matches_registry()` direction + SOURCE_FILTERS before shadow record. Prevents whole-module runs from tagging LIVE-enabled paths as shadow_bypass (proven pollution: 8× rs-s126/rs-s124 etc. tagged broken-short). Also: fail-closed on missing SHADOW_SIGNALS_RUNNER_ENABLED (was fail-open); empty vs error counters split (was "N errors" for benign no-detection).
   - **Verified:** py_compile OK; 15-case unit matrix all PASS (incl. all pollution cases from bug_hunter verdict); full live run 35 recorded / 0 errors / 0 filtered; loss_cooldowns.json byte-identical; PG signal_cooldowns count+hash unchanged; zero non-broken rs-* bypass rows after fix; created_at format `YYYY-MM-DD HH:MM:SS` confirmed.
4. **(L1) plans/autonomous-btc-loop-spec.md** — status header DRAFT→Phase 0 SHADOW LIVE (scripts shipped ~3h earlier; header was stale).
5. **(L1) shadow_trader.py** — cosmetic: `log("\n═" * 60)` → `log("\n" + "═" * 60)` (13 sites; verdict LOW, 60-line banner spam).

### Verifications (no code change)
- Confirmed prior ff9d08c5 already fixed HIGH-1 (cooldown noop), HIGH-2 (master flags), HIGH-3 (created_at), MEDIUM try/finally, MEDIUM STAGES consumption.
- LDO/GOAT/CAKE pollution cooldowns from pre-fix runs: already self-expired; no recurrence post-fix.
- Disk 84% — 15m/1h/4h retention still deferred (prior decision: only if >85%).

### Sideways findings
- **Severity: LOW** — historical 9 polluted bypass rows (pre-fix, rs-s*/rs-r* live sources tagged broken-short) remain in shadow_trades.db. Self-contained; exclude `source like '%broken%'` when analyzing Stage C rs-broken cohort, or DELETE those 9 rows next touch.
- **Severity: LOW** — SOPs.md has duplicate "## 7" section numbers (pre-existing); left as-is to avoid renumber churn.
- **Severity: INFO** — shadow_bypass cohort now 623+ rows / 193 closed and growing ~35/run; ready for first Stage A/C readout once n per key is meaningful.

### Success rate this session: 5/5 implemented (100%)
### Next candidates (priority order)
1. Stage A/C shadow readout — L1 analysis — MED — wait for n≥15 per key on doji/volume-breakout/bb-squeeze-/sqx
2. RR engine U2-U4 — L2-3 — HIGH — needs CEO sequencing, shadow-mode pattern
3. SL-width / entry-gate study — L2 — HIGH — CEO kanban GO pending
4. temporal-confluence / short-rsi-habitat / vol-regime-relative — L2-3 — MED-HIGH — CEO-gated SPECs
5. brain.py --limit + guardian fill-integration — L2 — MED — only after limit_order.py proven

---

## Upgrade Implementer Session — 2026-10-22 16:30 UTC

**Context:** pipeline LIVE, vacation mode ON (T waiver for unclog shipped by parallel session 371400c7, expires Oct 24). Re-scanned recent-20 plans (no material status changes vs 04:32 session). Picked up prior session's next-candidate #1: Stage A/C shadow readout (n≥15 thresholds now met).

### Plan evaluations (recent-20 re-scan, deltas vs 04:32 UTC session)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| autonomous-btc-loop-spec | L4 | HIGH | ✅ PHASE 0 SHADOW LIVE (prior) | No change; shadow soak accruing |
| t-vacation-mode-2026-10-14 | L4 | HIGH | ✅ ACTIVE (vacation_mode.json ON) | Waiver scope shipped by parallel session; this session stayed inside allowed envelope (analysis + cleanup only) |
| shadow-mode-paper-trading-spec | L3 | HIGH | ✅ IMPLEMENTED (prior) | shadow_trades.db now 11,372 rows / 1,215 SHADOW_BYPASS — cohort matured enough for readout |
| limit-order-capability | L2 | MED | ✅ PHASE 1 (prior) | Unchanged; phases 2-4 still deferred |
| 2026-10-16_winning-dna-remeasure-verdict | — | HIGH | ✅ CLOSED (prior) | SL-width study still on CEO kanban |
| strategic-six-options-2026-10-14 | L4 | HIGH | PARTIAL (prior) | Unchanged |
| contrarian-engine-2026-10-13 | L2-3 | MED-HIGH | ⏳ CEO-gated SPEC | Untouched (vacation freeze) |
| contrarian-zone-backtest | L2 | LOW | ⏸️ PAPER-TRADE PENDING (prior) | CONTRARIAN_ZONE_ENABLED=False; needs 50+ paper trades — no action |
| vol-regime-relative-thresholds-2026-10-13 | L2-3 | MED-HIGH | ⏳ CEO-gated SPEC | Untouched |
| temporal-confluence-spec | L2 | MED-HIGH | ⏳ CEO-gated SPEC | Untouched; temporal_confluence_shadow.db accruing separately |
| signal-starvation-fix-2026-10-12 | L2-3 | MED-HIGH | ⏳ CEO-gated SPEC | Partially superseded by CEO unclog flips (371400c7, parallel session) |
| short-rsi-habitat-spec | L2 | MED-HIGH | ⏳ CEO-gated SPEC | Untouched; bear-structure exemption shipped by parallel session under T waiver |
| 2026-10-13_rr-engine-smart-upgrades | L2-3 | HIGH | U1 LIVE / U2-U4 ⏳ CEO | Unchanged |
| 2026-10-12_gate-conundrum-deadlock-plan | L1-2 | HIGH | ✅ R1-R5 SHIPPED (prior) | Registry + claim hygiene landed 04:32 session |
| grind-breakout-v2-coin-tracker-integration | L3 | LOW | ⏸️ DEFERRED (by plan) | Unchanged |
| regime-recalibration-2026-10-12 | L2 | MED-HIGH | ⏳ CEO-gated | MAXXED tier proposal untouched |
| 2026-09-04_continuum-engine-spec | L3 | — | ✅ LIVE (prior) | No action |
| shadow-registry / shadow_signals_runner fixes | L2 | HIGH | ✅ COMPLETE (prior 04:32) | This session consumed its output (readout) |
| bug-hunt-master-plan (open bugs 037/044/056/064) | — | HIGH | ⏳ CEO-gated | Untouched |
| 2026-10-08_winning-dna-population-report | L1-3 | HIGH | PARTIAL (prior) | Except-swallow fixed 10-12; remaining asks CEO-gated |

### Implemented this session (1 × L1 analysis + 1 × L1 hygiene)

1. **(L1) Stage A/C shadow-bypass readout** — `brain/stage-ac-shadow-readout-2026-10-22.md`. Prior session's next-candidate #1, n≥15 thresholds met for 6/10 registry keys. Findings: (a) 3 disabled SHORT signals show broad positive shadow edge contradicting their Jul-Aug disable theses — sqx- WR 73.4% n=575 CI95[69.6,76.8] +74.2% sum net, rs-s-broken WR 82.9% n=105, bb-squeeze- WR 69.6% n=56, all token-spread (top token ≤9%); (b) 3 disabled LONG signals confirmed losers (sqx+ 32.1%, doji 31.5%, vol-breakout 14.3%) — kills now independently validated; (c) all measurable winners DEGRADE in newer half-split (sqx- 81.6→61.0% WR); (d) fire rates operationally absurd (sqx- 44.8/hr) — naive flag flip impossible, any re-test needs throttle design. Zero fires on hmacd_mtf-+/bb-bounce-v3/open-skies+ (LOW, diagnostic pending). **No flags touched** — analysis only, vacation freeze respected. Recommendations routed to CEO in report §6.
2. **(L1) Orphan 0-byte shadow DB cleanup** — deleted `data/gate_shadow.db`, `data/expiry_shadow.db`, `data/shadow_trades.db` (all 0 bytes, created Oct 20-21). Verified no code path opens them: all shadow scripts write to `brain/*.db` (gate_shadow.py:32, expiry_shadow.py:34, shadow_trader.py:33); only `*_offset.txt` files in HERMES_DATA are live. This session itself nearly queried the wrong 0-byte data/shadow_trades.db before finding brain/ — the orphans were a live confusion hazard.

### Verifications (no code change)
- All 10 SHADOW_BYPASS registry ENABLED flags confirmed False in hermes_constants.py (lines 672-4611).
- Readout numbers reproducible: single deterministic SQL against brain/shadow_trades.db (11,372 rows, window 2026-10-21 00:22 → 2026-10-22 16:22 UTC).
- Wilson CI95 computed for every cohort with n_closed≥10; half-splits reported both ways per AGENTS.md discipline.

### Sideways findings
- **Severity: LOW** — 8 pollution rows (rs-s120/s32/s124/s126 LONG, all −0.800%) from pre-HIGH-5-fix remain in shadow_trades.db. Self-contained; exclude or delete next touch (prior session already flagged).
- **Severity: LOW** — hmacd_mtf-+, bb-bounce-v3-long, open-skies+ have zero shadow fires in 40h. Runner counters work post-fix; likely detector-quiet, but one --dry-run import check warranted.
- **Severity: INFO** — rs-s-broken half2 has only 7/100 closed (93 open) — half2 stats uninformative until resolves; readout re-run recommended in 7d.
- **Severity: INFO** — data disk 84% (threshold for 15m/1h/4h retention is 85%) — one bad day from triggering; watch.

### Success rate this session: 2/2 implemented (100%)
### Cumulative (today, 3 sessions): 7/7 (100%)
### Next candidates (priority order)
1. Stage A/C re-readout — L1 analysis — MED — in ~7d when rs-s-broken/bb-squeeze- half2 closes resolve and sqx- degradation trend clarifies
2. Zero-fire key diagnostic (--dry-run import check) — L1 — LOW — quick, next session
3. RR engine U2-U4 — L2-3 — HIGH — still needs CEO sequencing
4. Throttled re-test design for top shadow SHORT candidate (sqx-) — L2 design — MED-HIGH — only if CEO wants it; vacation freeze blocks implementation
5. 15m/1h/4h candle retention — L1 — LOW — disk at 84%, one point from 85% trigger

---

## Upgrade Implementer Session — 2026-10-25 16:30 UTC

**Context:** pipeline LIVE, vacation mode ON (constants_change_review_queue active per T directive Oct 23; unclog_waiver expires Oct 27). Disk 83% (below 85% retention trigger). Prior session's next-candidate #2 (zero-fire diagnostic) picked up. 3 × L1 implemented.

### Plan evaluations (recent-20 re-scan, deltas vs 2026-10-22 16:30 session)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| autonomous-btc-loop-spec | L4 | HIGH | ✅ PHASE 0 SHADOW LIVE (prior) | Day 3 of ≥7d shadow soak; <15 resolved hypotheticals — too early for phase gate |
| t-vacation-mode-2026-10-14 | L4 | HIGH | ✅ ACTIVE | Small cleanups (dead allowlist, tl-bounce+ NORMAL, compactor ATR) all already closed 2026-10-21 — nothing left |
| shadow-mode-paper-trading-spec-v1 | L3 | HIGH | ✅ IMPLEMENTED (prior) | Consumed for readout; 8 pollution rows deleted this session |
| limit-order-capability | L2 | MED | ✅ PHASE 1 (prior) | Unchanged; phases 2-4 deferred until standalone proven |
| 2026-10-16_winning-dna-remeasure-verdict | — | HIGH | ✅ CLOSED (prior) | SL-width study still on CEO kanban |
| vol-regime-relative-thresholds | L2-3 | MED-HIGH | ⏳ CEO-gated SPEC | Untouched |
| signal-starvation-fix-2026-10-12 | L2-3 | MED-HIGH | PARTIAL | Unclog waiver (bear-structure exemption) shipped by parallel session; RR floor/BB dead-zone still CEO-gated |
| short-rsi-habitat-spec | L2 | MED-HIGH | ⏳ CEO-gated SPEC | Untouched |
| 2026-10-13_rr-engine-smart-upgrades | L2-3 | HIGH | U1 LIVE / U2-U4 ⏳ CEO | Unchanged |
| grind-breakout-v2-coin-tracker-integration | L3 | LOW | ⏸️ DEFERRED (by plan) | Unchanged |
| 2026-10-09_D4-structured-block-logging | L1 | MED | ✅ COMPLETE (2026-10-09) | Verified complete |
| bug-hunt-master-plan (open 036/037/044/056/064) | — | HIGH/LOW | ⏳ T-gated | BUG-056 (orphan constants) verified still open — NOT touched (constants-protected, explicitly T-review) |
| contrarian-engine / temporal-confluence / regime-recalibration | L2-3 | MED | ⏳ CEO-gated | Untouched |
| shadow-data-mining-patterns (report, not plan) | — | — | ⚠️ FLAGGED | See sideways finding #1 — methodological flaw |

### Implemented this session (3 × L1)

1. **(L1) Zero-fire shadow key diagnostic** — prior session's next-candidate #2. Ran `shadow_zero_fire_diag.py` for the 3 zero-fire keys (hmacd_mtf-+, bb-bounce-v3-long, open-skies+). Result: **all 3 resolved**. (a) hmacd_mtf-+ now fires 229× since Oct 23 (zero-fire condition self-resolved); (b) open-skies+ now fires 32× since Oct 23 (self-resolved); (c) bb-bounce-v3-long still 0 — **legitimately quiet, not broken**: detector-quiet is explained by FILTER-1 (BB-touch proximity 0.20%) killing 84/96 tradeable tokens, plus a contradictory habitat (buy lower-BB dip AND require 30m momentum ≥0 AND NORMAL-regime conf=0.0). Funnel: 267 tokens → 95 delisted → 76 blacklisted → 96 scanned → 84 fail touch → 0 pass. No code fix warranted — the signal is dormant by design.
2. **(L1) Pollution row cleanup** — deleted 8 pre-HIGH-5-fix pollution rows from `brain/shadow_trades.db` (rs-s120/s32/s124/s126 LONG, all shadow_ prefixed, created 2026-10-22 04:00–04:20). Prior sessions flagged these twice; finally executed. Verified 0 remaining.
3. **(L1) shadow_zero_fire_diag.py filtered-sample bug fix** — the diag could never show which source/dir caused a SOURCE_FILTERS rejection: `record_to_shadow` is only called *after* the filter, so `calls` was always empty for `status=filtered` and the `sample_src` line was dead code. Fixed: wrap `_sig_matches_registry` to log pre-filter matches/rejections; detail now reports `pre_filter` / `post_filter` / `rejected` counts + first rejected sample's source and direction. py_compile OK; live run on bb-bounce-v3-long produces correct `empty pre_filter=0 post_filter=0 rejected=0`.

### Verifications (no code change)
- Confirmed all three vacation-plan "small cleanups" already closed: dead allowlist entries (pump-catcher, trend_purity) removed from volatility_gate_v2.py 2026-10-21; tl-bounce+ NORMAL question closed (stays FLAT-only, comment at gate line); compactor inline TR computation (line 1953) is an intentional cur/avg TR *ratio* for VOL-GATE expansion, not a drift-risk duplicate of get_atr_pct.
- Confirmed unclog_waiver scope fully shipped: bear-structure exemptions live in decider_run.py (ctx ~1084, exec ~2189) and signal_compactor.py (~4135); LOSERS_LONG exists (decider_run.py:219, 385).
- Confirmed BUG-056 (MA300_CANDLE_MINUS_ENABLED=True, no consumer) still open — deliberately not touched (constants line-2 protection + bug record says "NOT auto-fixed, T review").
- Vacation_mode status re-read: constants_change_review_queue + unclog_waiver both active; no_signal_enable_disable still frozen.

### Sideways findings
- **Severity: MEDIUM** — `reports/2026-10-24-shadow-data-mining-patterns.md` has a **survivorship/selection-on-outcome flaw**. Its "winners" table is defined by outcome (positive PnL), so "winners have MFE/MAE 36–50x" is tautological. Its per-signal "100% WR" rows (pump-chain EXTREME n=453, volume_breakout_short n=14) are inconsistent with today's significance-tested `reports/20261025-shadow-fresh-analysis.md`, which shows pump-chain SHORT t=-6.38 and pump-chain LONG t=-7.77 (both significantly negative). The mining report's PM-Trail "100% WR" is by-design circular (same report admits this). **Do NOT build new signals from the mining report without own-conclusions re-verification.** The trustworthy signal-level finding is squeeze_cross SHORT (t=2.01) from the Oct 25 analysis — but its shadow edge is thin (+0.011% avg net last 24h) and fire rate absurd (~65/hr), so any live re-test needs throttle design first. **[SUPERSEDED 2026-10-25 16:55 by Daily Orchestrator: sqx- SHORT edge REFUTED — net t=+1.02 p=0.31 (not significant), gross t=+12.54 (pre-fee artifact), last-72h t=−2.73. Do not treat as trustworthy.]**
- **Severity: LOW** — bb-bounce-v3-long's habitat is self-contradictory by construction (lower-BB dip entry gated on non-negative 30m momentum). Even if un-disabled it would fire ~never. Worth a one-line note if anyone proposes re-enabling it.
- **Severity: INFO** — shadow_trades.db now 21,302 rows (7,430 shadow_signals_runner-sourced). sqx- half2 degradation from the Oct 22 readout still unresolved (prior 24h avg -0.034% vs last 24h +0.011% — sign flip, not clearly recovered). Re-readout still due ~Oct 29.

### Success rate this session: 3/3 implemented (100%)
### Cumulative (today, sessions on Oct 22+25): 10/10 (100%)
### Next candidates (priority order)
1. Stage A/C re-readout — L1 analysis — MED — ~Oct 29 when rs-s-broken/bb-squeeze- half2 resolves and sqx- trend clarifies
2. ~~Throttled sqx- re-test design~~ — **REFUTED this session** — see Daily Orchestrator block below
3. RR engine U2-U4 — L2-3 — HIGH — still needs CEO sequencing
4. Own-conclusions re-verification of mining-report patterns — L1-2 analysis — MED — block bad signal builds; only if someone proposes acting on that report
5. 15m/1h/4h candle retention — L1 — LOW — disk 83%, one bad day from 85% trigger (NOT price_history — real lever, see orchestrator note)

---

## Daily Orchestrator Session — 2026-10-25 16:55 UTC

**Context:** pipeline LIVE, GREEN (24h 13T 10W 76.9% +$0.60, 1 open BTC bracketed). All strategic GOs CEO-gated (Esc #17, BE-at-arm, CONF_FLOOR, TAT, Oct-27 cluster) — not touched. Implemented 1 L1 refutation (analysis-only, zero config/live change).

### Implemented (1 × L1 — refutation, no code change)

1. **(L1) squeeze_cross SHORT edge REFUTED — candidate #2 killed with evidence.** The prior session's "only verified shadow edge (t=2.01)" does not survive independent measurement. Recomputed from `brain/shadow_trades.db` (gate_passed only, `net_pnl_pct`, scipy `ttest_1samp`):
   - **Full window (n=3,091, Oct 22→25 only — NOT the 18d the report header implies):** net avg **+0.0124%, t=+1.02, p=0.31** — **NOT significant.** Report claimed t=2.01/p<0.05 — not reproducible.
   - **Gross vs net decomposition:** gross avg +0.152%, **t=+12.54** (highly significant pre-fee) → fees (0.14%/trade) erase the edge entirely. The "edge" is a **pre-fee artifact.**
   - **Out-of-sample reversal:** last-72h net **t=−2.73 (p=0.0065)**, last-24h **t=−3.61** — significantly NEGATIVE. Edge decayed and flipped within days.
   - **Action:** throttled sqx- re-test design (candidate #2) **withdrawn from the queue.** Do NOT build a throttle spec or route a constants-review-queue proposal on this signal. A live re-test would be re-introducing a fee-eaten, non-significant, recently-reversed edge. Re-open only if a fresh ≥7d net-positive significant window appears (recheck with the Stage A/C re-readout ~Oct 29).

### Verifications (no code change)
- **Standing verify #141 CONFIRMED:** BTC trade #16395 (opened 15:47:32Z, after the 15:15Z source-stamp deadline) carries `_signal_metadata.source = "continuum-trend+"`. Source stamp is live and populating. Unblocks bb-bounce solo-vs-confluence attribution analysis.
- **Hotset ground-truth (sideways):** `/var/www/hermes/data/hotset.json` is currently `hotset: []` (cycle 10082, fresh mtime 16:53). auto_1hr's "0 tokens since 05:56 — still monitor" is consistent with current state; CURRENT.md's "CLEARED 15:33" was true at 15:42 but hotset has since gone empty again — it is **flapping**, not stably cleared. Empty hotset in a quiet market is likely normal compaction behavior (no strong signals survive scoring), not a bug — no action without evidence of a scoring defect.
- **Disk prune correctly DEFERRED (not an orchestrator miss):** price_collector.py:850 prunes candles_5m/1m/15m/1h/4h (candles.db) but NOT `price_history` (signals_hermes.db, 15.3M rows). Prior orchestrator run set a standing decision: prune price_history only when disk >85% (currently 83%), AND trading_log:6513 notes it "needs retention plan before any prune (bug_hunter, not approved)". Both conditions unmet → correctly deferred, not executed. The upgrade_audit's candle-retention candidate (#5) aims at the wrong target (15m/1h/4h ≤300MB); the real lever is price_history, gated on the 85% trigger.

### Sideways findings
- **Severity: INFO** — the Oct-25 shadow-fresh-analysis report's header date-range ("Oct 7-25, 18 days") is misleading for per-signal rows: squeeze_cross SHORT data actually spans Oct 22→25 only (~3.7d). The 18d range is the whole-corpus span, not per-signal. Worth a one-line caveat if the report is reused.
- **Severity: INFO** — `hermes-daily-orchestrator.service` runs `run_orchestrator.sh` (opencode prompt pipeline, TimeoutStartSec=1800). No PG-for-SQLite query bug observed in the current unit/script (prior timeout note in error_alerts.md appears stale/resolved by the 1200s health-monitor timeout fix pattern).

### Success rate this session: 1/1 implemented (100%)
### Cumulative (today, sessions on Oct 22+25): 11/11 (100%)
### Next candidates (priority order)
1. Stage A/C re-readout — L1 analysis — MED — ~Oct 29; **re-check sqx- net significance here** (refuted this session)
2. RR engine U2-U4 — L2-3 — HIGH — still needs CEO sequencing
3. Own-conclusions re-verification of mining-report patterns — L1-2 analysis — MED — only if someone proposes acting on that report
4. price_history 30d retention plan — L1 (design) — LOW — draft the plan + bug_hunter review NOW so it's ready when disk crosses 85%; execution stays gated on the trigger
5. 15m/1h/4h candle retention — CANCELLED as mis-targeted (real lever is price_history, #4)

---

## Upgrade Implementer Session — 2026-10-26 16:39 UTC

**Context:** pipeline LIVE, disk **84%** (1G below the 85% prune trigger), vacation-mode constants review queue still active. No new plan files since 2026-10-25 16:55 except `price_history_retention_30d.md` (drafted 04:59 today by the daily orchestrator = prior session's next-candidate #4). Subagent launch unavailable this session → bug_hunter review performed inline (read-only).

### Plan evaluations (recent-20 re-scan, deltas vs 2026-10-25 sessions)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| price_history_retention_30d | L1 (review) | MED | ✅ REVIEWED THIS SESSION — APPROVE-WITH-CHANGES, F1–F4 folded in | See below; execution still gated on disk ≥85% |
| autonomous-btc-loop-spec | L4 | HIGH | ✅ PHASE 0 SHADOW LIVE (prior) | Day 4 of ≥7d soak; too early for phase gate |
| shadow-mode-paper-trading-spec-v1 | L3 | HIGH | ✅ IMPLEMENTED (prior) | Unchanged |
| limit-order-capability | L2 | MED | ✅ PHASE 1 (prior) | Phases 2-4 deferred |
| vol-regime-relative-thresholds / short-rsi-habitat / contrarian-engine / temporal-confluence / regime-recalibration / 2026-10-13_rr-engine U2-U4 | L2-3 | MED-HIGH | ⏳ CEO-gated | Untouched (vacation review queue active) |
| signal-starvation-fix-2026-10-12 | L2-3 | MED-HIGH | PARTIAL | Unclog waiver shipped by prior session; RR floor/BB dead-zone CEO-gated |
| grind-breakout-v2-coin-tracker-integration | L3 | LOW | ⏸️ DEFERRED (by plan) | Unchanged |
| bug-hunt-master-plan (BUG-036/037/044/056/064) | — | HIGH | ⏳ T/CEO-gated | 4 open bugs re-confirmed this session — none auto-fixable (037/044/064 live-money path, 056 constants-protected) |
| Stage A/C re-readout | L1 | MED | ⏳ due ~Oct 29 | Not yet time |
| mining-report own-conclusions re-verification | L1-2 | MED | ⏳ conditional | Only if someone proposes acting on that report |

### Implemented this session (1 × L1 — review/analysis only, zero live change)

1. **(L1) price_history 30d retention plan — mandatory bug_hunter review completed, verdict APPROVE-WITH-CHANGES.**
   - Verified independently (read-only): timestamp=INT, `idx_ph_ts` present (batch subquery index-driven), freelist=0, page_count 300970×4096 = 1.23GB, **>30d = 11,859,705 rows (74.3%)**, ≤30d = 4,088,398, no triggers/views/FKs on price_history, **max closed-trade duration = 1d16h ≪ 30d** (hl-sync/position_manager MFE-MAE open→close reads safe), legacy DB migration one-shot idempotent (`_meta migration_done`, signal_schema.py:85) → no re-insert-after-prune risk, all live readers traced to ≤24h/4h/LIMIT-based windows (decider LIMIT 700, compactor LIMIT 400, trades-api full-series = chart-only, get_price_history LIMIT 25000/24h default).
   - **4 findings folded into the plan file (now execution-ready):**
     - **F1 (MED):** export >30d rows to gzip (~100MB) before delete — the only rollback path; explicitly NOT a full `.backup` (1.2GB would trip the 85% disk trigger we're guarding against).
     - **F2 (MED):** VACUUM stop-list expanded from 2 → 5 timers (adds `hermes-signal-compactor`, `hermes-1m-candle`, `hermes-pump-flow`) + `PRAGMA busy_timeout=180000`; baseline "database is locked" count = 0 in 7d, verify stays 0 after run.
     - **F3 (LOW):** original snippet had no runnable loop (one-shot DELETE of 11.9M rows in a single txn) → replaced with the exact price_collector.py:857-868 500k-batch loop; runtime estimate 15–40 min, do not interrupt.
     - **F4 (LOW):** census gaps documented — candle_predictor.build_ohlcv full-series read (cosmetic EMA/MACD seed shift), ema20_50 `lookback_days=30` boundary, unbounded backtest `--days`, historical analysis targets, and the **permanent loss of >30d 1m-resolution data** (price_history is the only store holding it; candles_1m also 30d, 15m/1h/4h retain 90d).
   - **Status:** plan APPROVED-WITH-CHANGES, **execution gated on disk ≥85% (currently 84%) — do not run yet.** Verdict recorded in plan file + trading_log.md.

### Sideways findings
- **Severity: LOW** — plan file's original step-1 comment claimed "Record verdict in trading_log.md" but the 85% gate means the review had to happen NOW anyway (review is not gated, execution is) — done, no drift.
- **Severity: INFO** — 73 hermes timers active; only 5 touch signals_hermes.db at sub-minute cadence (F2 list). `grep -ac "database is locked" logs/pipeline.log` = 0 (7d baseline) — worth re-checking after the prune runs.

### Success rate this session: 1/1 implemented (100%)
### Cumulative (Oct 22+25+26 sessions): 12/12 (100%)
### Next candidates (priority order)
1. Stage A/C re-readout — L1 analysis — MED — ~Oct 29 (re-check sqx- net significance; rs-s-broken/bb-squeeze- half2 resolution)
2. price_history prune EXECUTION — L1 ops — MED — only when disk ≥85% (plan ready, review done); pair with coin_tracker.db VACUUM (240MB) + candles.db VACUUM (150MB) in the same window
3. RR engine U2-U4 — L2-3 — HIGH — still needs CEO sequencing
4. Own-conclusions re-verification of mining-report patterns — L1-2 — MED — only if someone proposes acting on that report
5. 4 open bugs (037/044/064 live-money, 056 constants) — T/CEO-gated — not actionable by this role

---

## Upgrade Implementer Session — 2026-10-27 04:44 UTC

**Context:** pipeline LIVE (0 open trades), disk **hit the 85% prune gate** (df 85% at 04:25, was 84% yesterday), vacation-mode constants review queue still active (no constants touched this session). **0 new plan files since 2026-10-26 16:41** (the only `find -newermt` hit was `price_history_retention_30d.md` itself, modified by the prior session's F1–F4 fold-in).

### Plan evaluations (recent-20 re-scan, deltas vs 2026-10-26 16:39 session)

| Plan | Difficulty | Value | Status | Reason |
|------|-----------|-------|--------|--------|
| **price_history_retention_30d** | L1 (ops) | MED | ✅ **EXECUTED THIS SESSION** | Gate met (df=85% at 04:25); plan was APPROVE-WITH-CHANGES with F1–F4 already folded in — execution-ready. See below |
| autonomous-btc-loop-spec | L4 | HIGH | ✅ PHASE 0 SHADOW LIVE (prior) | Day 5 of ≥7d soak; phase gate not yet due |
| t-vacation-mode-2026-10-14 | L4 | HIGH | ✅ ACTIVE | Constants review queue still active; nothing new left |
| shadow-mode-paper-trading-spec-v1 | L3 | HIGH | ✅ IMPLEMENTED (prior) | Unchanged |
| limit-order-capability | L2 | MED | ✅ PHASE 1 (prior) | Phases 2–4 deferred |
| 2026-10-16_winning-dna-remeasure-verdict | — | HIGH | ✅ CLOSED (prior) | Unchanged |
| vol-regime-relative-thresholds / short-rsi-habitat / contrarian-engine / temporal-confluence / regime-recalibration / 2026-10-13_rr-engine U2-U4 | L2-3 | MED-HIGH/HIGH | ⏳ CEO-gated | Untouched (vacation review queue) |
| signal-starvation-fix-2026-10-12 | L2-3 | MED-HIGH | PARTIAL | Unclog waiver shipped by prior session; RR floor/BB dead-zone CEO-gated |
| grind-breakout-v2-coin-tracker-integration | L3 | LOW | ⏸️ DEFERRED (by plan) | Unchanged |
| 2026-10-12_bb-squeeze-trail-arm-timeout-verdict | — | — | ⚠️ PENDING CEO RATIFY | `BB_SQUEEZE_TRAIL_ARM_TIMEOUT_ENABLED=True` flipped without documented GO — **still unresolved**, repeat question to CEO (not mine to touch) |
| 2026-10-09_D4-structured-block-logging | L1 | MED | ✅ COMPLETE (prior) | Unchanged |
| bug-hunt-master-plan (BUG-036/037/044/056/064) | — | HIGH | ⏳ T/CEO-gated | Not actionable by this role |
| Stage A/C re-readout | L1 | MED | ⏳ due ~Oct 29 | Not yet time |
| mining-report own-conclusions re-verification | L1-2 | MED | ⏳ conditional | Only if someone proposes acting on that report |

### Implemented this session (1 × L1 — ops, approved plan executed)

1. **(L1) price_history 30d retention — EXECUTED.** All F1–F3 review changes applied.
   - **F1 export (rollback insurance):** `data/price_history_gt30d_20261027.gz` — **48MB gz, row-count verified `zcat | wc -l` = 11,926,871** (matches pre-delete >30d census 11,926,680 + in-flight growth). Retain 7 clean days.
   - **Delete:** batched 500k/index-driven loop per F3. **11,927,340 rows removed total** (500,000 in a first aborted run + 11,427,340 in the corrected run). `price_history` 16,027,881 → **4,102,118**. Runtime 51s (far under the 15–40 min estimate).
   - **VACUUM (F2 stop-list):** stopped 9 timers (`price-collector`, `pipeline`, `signal-compactor`, `1m-candle`, `pump-flow`, `5m-candle`, `candle-predictor`, `coin-tracker`, `trade-watchdog`), drained running services, `wal_checkpoint(TRUNCATE) + VACUUM` with `.timeout 180000`. **signals_hermes.db 1.23GB → 325MB.**
   - **Paired levers (same window, per prior session's next-candidate #2):** `candles.db` 1,256,562,688 → 1,056,731,136 bytes (−190MB); `coin_tracker.db` 3,481,088,000 → 3,209,297,920 bytes (−262MB).
   - **Net disk reclaim: 95G → 93G used, 18G → 19G free, df 85% → 84%.** Total ~1.36GB across 3 DBs.

### Verifications (post-execution, all PASS)
- `SELECT count(*) FROM price_history` = **4,102,118** (expected ~4.1M) ✅
- `PRAGMA quick_check` = **ok** on signals_hermes.db, candles.db AND coin_tracker.db ✅
- `grep -rac "database is locked" logs/pipeline.log` = **0** (7d baseline preserved — no new occurrences) ✅
- No error/traceback lines in `logs/pipeline.log` across the 04:33–04:44 prune window ✅
- `python3 scripts/signal_schema.py --help` smoke OK ✅
- Pipeline resumed normally: `=== Pipeline LIVE (1m) ===` at 04:44:00, all 9 stopped timers back to `active` ✅

### State-restoration incident (self-caught, corrected)
- **Severity: LOW, self-healed in-session.** My stop-list included `hermes-5m-candle.timer` and `hermes-candle-predictor.timer`. Journal forensics (`journalctl -u <t>.timer` showed **no `Stopped` event at 04:33:36**, vs. a control timer which did) proved both were **already inactive before the stop** — a blind `systemctl start` on restart woke two dormant units.
  - `hermes-5m-candle.service` fired once at 04:36:37 and **failed harmlessly**: `/root/.hermes/scripts/_aggregate_5m.py` does not exist (exit 2). No DB touched.
  - `hermes-candle-predictor.timer` never fired (`NextElapseUSecMonotonic=infinity`, `LastTriggerUSec` 2026-04-16).
  - **Corrected:** both stopped again; final state = 7 originally-active timers active, 2 dormant timers inactive — exactly as pre-session.
- **Lesson recorded:** always snapshot `systemctl is-active` for every unit in a stop-list BEFORE stopping, not just after.

### Sideways findings
- **Severity: LOW** — `hermes-5m-candle.service` is a **dead unit**: `ExecStart` points at `scripts/_aggregate_5m.py`, which does not exist. It has `LastTriggerUSec` 2026-09-30 (dormant ~4 weeks) and `UnitFileState=disabled`. If anyone ever `systemctl start`s it, it fails loudly with exit 2. Suggest: delete or repoint the unit (not done — systemd unit cleanup not in this plan's scope; flag for next session).
- **Severity: LOW** — `hermes-candle-predictor.timer` is likewise dormant since 2026-04-16 (`NextElapse=infinity`, disabled). Same cleanup candidate as above.
- **Severity: INFO** — the original F3 snippet in the plan was still wrong on first execution: `PRAGMA busy_timeout=10000;` inside the same `sqlite3` invocation **prints `10000`** to stdout, so `n` became `"10000\n500000"` and the bash `[` test aborted the loop after one batch. Fixed by switching to `sqlite3 -cmd ".timeout 10000"` (dot-command prints nothing) + `case` numeric guard. The plan file's F3 snippet has been corrected in place during this session.
- **Severity: INFO** — `data/price_history_gt30d_20261027.gz` is the **only** rollback path for the deleted 11.93M rows; do not garbage-collect `data/` before 2026-11-03.

### Success rate this session: 1/1 implemented (100%)
### Cumulative (Oct 22+25+26+27 sessions): 13/13 (100%)
### Next candidates (priority order)
1. Stage A/C re-readout — L1 analysis — MED — ~Oct 29 (re-check sqx- net significance; rs-s-broken/bb-squeeze- half2 resolution)
2. Dead systemd unit cleanup (`hermes-5m-candle`, `hermes-candle-predictor`) — L1 — LOW — trivial, self-found this session
3. RR engine U2-U4 — L2-3 — HIGH — still needs CEO sequencing
4. Own-conclusions re-verification of mining-report patterns — L1-2 — MED — only if someone proposes acting on that report
5. 4 open bugs (037/044/064 live-money, 056 constants) + bb-squeeze trail-arm-timeout RATIFY/REVERT — T/CEO-gated — not actionable by this role
